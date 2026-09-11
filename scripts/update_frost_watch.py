#!/usr/bin/env python3
"""Collect FROST Watch into the Cloudflare Worker, or publish static artifacts.

Service mode (`serving.mode: service`): ingest into D1. Does not commit feed JSON
or push to Pages. Needs `SOURCE_WATCH_INGEST_TOKEN` and `serving.service_url`.

Static mode: regenerate, commit, and optionally push so Pages redeploys.
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
INGEST_TOKEN_KEY = "SOURCE_WATCH_INGEST_TOKEN"
REMOTE = "https://github.com/macgyver13/frost-watch.git"
WATCH = ROOT / "config" / "watch.yaml"


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


def sync_with_origin_main() -> None:
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "rebase", "origin/main"], check=True)


def push_with_token(token: str) -> str:
    push_url = f"https://x-access-token:{token}@github.com/macgyver13/frost-watch.git"
    try:
        out = run(["git", "push", push_url, "main"]).stdout
    finally:
        run(["git", "remote", "set-url", "origin", REMOTE], check=False)
    return out


def load_serving() -> tuple[str, str]:
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(WATCH.read_text()) or {}
    except Exception:
        return "static", ""
    serving = data.get("serving") if isinstance(data.get("serving"), dict) else {}
    mode = str(serving.get("mode") or "static").strip().lower()
    url = str(serving.get("service_url") or "").strip()
    if url and not url.endswith("/"):
        url += "/"
    return mode, url


def print_step(out: str) -> None:
    text = out.strip()
    if text:
        print(text)


def ensure_ingest_token() -> None:
    if os.environ.get(INGEST_TOKEN_KEY, "").strip():
        return
    token = load_env_value(PROFILE_ENV, INGEST_TOKEN_KEY)
    if token:
        os.environ[INGEST_TOKEN_KEY] = token
        return
    raise SystemExit(f"missing {INGEST_TOKEN_KEY} in environment or {PROFILE_ENV}")


def ingest_service(py: Path) -> int:
    _mode, url = load_serving()
    if not url:
        raise SystemExit(
            "serving.service_url is empty. Deploy the Worker, set config/watch.yaml "
            "serving.service_url to the Worker origin (trailing slash), then re-run."
        )
    ensure_ingest_token()
    for step in (
        [str(py), "scripts/build_seed_feed.py"],
        [str(py), "scripts/verify_public_artifacts.py"],
    ):
        print_step(run(step).stdout)
    print(f"refresh complete: ingested into {url}")
    return 0


def refresh_static(py: Path) -> None:
    for step in (
        [str(py), "scripts/build_seed_feed.py"],
        [str(py), "scripts/sync_hugo_content.py"],
        [str(py), "scripts/verify_public_artifacts.py"],
        ["hugo", "--source", "site", "--minify"],
    ):
        print_step(run(step).stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-push", action="store_true", help="Regenerate/ingest but do not commit or push")
    parser.add_argument("--allow-empty", action="store_true", help="Commit even if no files changed (static mode)")
    parser.add_argument("--message", default="chore: refresh FROST Watch feed", help="Commit message (static mode)")
    args = parser.parse_args()

    py = ensure_venv()
    mode, _url = load_serving()
    if mode == "service":
        return ingest_service(py)

    if args.no_push:
        refresh_static(py)
        print("refresh complete: no-push mode")
        return 0

    sync_with_origin_main()
    refresh_static(py)

    if not has_changes() and not args.allow_empty:
        print("refresh complete: no changes to publish")
        return 0

    run(["git", "add", "config", "data", "scripts", "site", "README.md", "LICENSE", ".gitignore"], check=True)
    commit_cmd = ["git", "commit", "-m", args.message]
    if args.allow_empty:
        commit_cmd.insert(2, "--allow-empty")
    print_step(run(commit_cmd).stdout)

    token = os.environ.get(TOKEN_KEY) or load_env_value(PROFILE_ENV, TOKEN_KEY)
    if not token:
        raise SystemExit(f"missing {TOKEN_KEY} in environment or {PROFILE_ENV}")
    print_step(push_with_token(token))
    print("refresh complete: published to GitHub; Cloudflare Pages should redeploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
