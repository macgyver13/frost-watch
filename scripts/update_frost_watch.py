#!/usr/bin/env python3
"""Regenerate, verify, build, and optionally publish FROST Watch.

This script is cron-friendly: it prints a short status line and exits 0 when
nothing changed. It reads the GitHub token only from the frost-watch Hermes
profile env by default, keeping credentials partitioned from the default profile.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ENV = Path.home() / ".hermes" / "profiles" / "frost-watch" / ".env"
TOKEN_KEY = "FROST_WATCH_GITHUB_TOKEN"
REMOTE = "https://github.com/macgyver13/frost-watch.git"


def run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def load_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def ensure_venv() -> Path:
    py = ROOT / ".venv" / "bin" / "python"
    if not py.exists():
        run([sys.executable, "-m", "venv", ".venv"])
        run([str(py), "-m", "pip", "install", "--upgrade", "pip", "PyYAML"])
    return py


def has_changes() -> bool:
    result = run(["git", "status", "--porcelain"], check=True)
    return bool(result.stdout.strip())


def push_with_token(token: str) -> str:
    push_url = f"https://x-access-token:{token}@github.com/macgyver13/frost-watch.git"
    try:
        out = run(["git", "push", push_url, "main"]).stdout
    finally:
        run(["git", "remote", "set-url", "origin", REMOTE], check=False)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-push", action="store_true", help="Regenerate/build but do not commit or push")
    parser.add_argument("--allow-empty", action="store_true", help="Commit even if no files changed")
    parser.add_argument("--message", default="chore: refresh FROST Watch feed", help="Commit message")
    args = parser.parse_args()

    py = ensure_venv()
    steps = [
        [str(py), "scripts/build_seed_feed.py"],
        [str(py), "scripts/sync_hugo_content.py"],
        [str(py), "scripts/verify_public_artifacts.py"],
        ["hugo", "--source", "site", "--minify"],
    ]
    for step in steps:
        out = run(step).stdout.strip()
        if out:
            print(out)

    if args.no_push:
        print("refresh complete: no-push mode")
        return 0

    if not has_changes() and not args.allow_empty:
        print("refresh complete: no changes to publish")
        return 0

    run(["git", "add", "config", "data", "scripts", "site", "README.md", "LICENSE", ".gitignore"], check=True)
    commit_cmd = ["git", "commit", "-m", args.message]
    if args.allow_empty:
        commit_cmd.insert(2, "--allow-empty")
    commit_out = run(commit_cmd).stdout.strip()
    if commit_out:
        print(commit_out)

    token = os.environ.get(TOKEN_KEY) or load_env_value(PROFILE_ENV, TOKEN_KEY)
    if not token:
        raise SystemExit(f"missing {TOKEN_KEY} in environment or {PROFILE_ENV}")
    push_out = push_with_token(token).strip()
    if push_out:
        print(push_out)
    print("refresh complete: published to GitHub; Cloudflare Pages should redeploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
