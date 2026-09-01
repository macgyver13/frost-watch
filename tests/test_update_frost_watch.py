#!/usr/bin/env python3
"""Tests for Frostwatch publish orchestration."""
from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_frost_watch.py"

spec = importlib.util.spec_from_file_location("update_frost_watch", SCRIPT)
assert spec is not None
update_frost_watch = cast(Any, importlib.util.module_from_spec(spec))
assert spec.loader is not None
spec.loader.exec_module(cast(ModuleType, update_frost_watch))


class UpdateFrostWatchTests(unittest.TestCase):
    def test_publish_syncs_with_origin_main_before_building(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
            calls.append(cmd)
            if cmd == ["git", "status", "--porcelain"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=" M data/public/feed.json\n")
            if cmd[:2] == ["git", "commit"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="[main abc123] chore: refresh FROST Watch feed\n")
            if cmd[:2] == ["git", "push"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="pushed\n")
            if cmd[:3] == ["git", "remote", "set-url"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="")
            return subprocess.CompletedProcess(cmd, 0, stdout="")

        with mock.patch.object(update_frost_watch, "ensure_venv", return_value=Path("/tmp/fake-python")):
            with mock.patch.object(update_frost_watch, "load_env_value", return_value="token"):
                with mock.patch.object(update_frost_watch, "run", side_effect=fake_run):
                    with mock.patch("sys.argv", ["update_frost_watch.py"]):
                        rc = update_frost_watch.main()

        self.assertEqual(rc, 0)
        self.assertGreaterEqual(len(calls), 7)
        self.assertEqual(calls[0], ["git", "fetch", "origin", "main"])
        self.assertEqual(calls[1], ["git", "rebase", "origin/main"])
        self.assertEqual(calls[2], ["/tmp/fake-python", "scripts/build_seed_feed.py"])

    def test_no_push_mode_skips_git_sync(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="")

        with mock.patch.object(update_frost_watch, "ensure_venv", return_value=Path("/tmp/fake-python")):
            with mock.patch.object(update_frost_watch, "run", side_effect=fake_run):
                with mock.patch("sys.argv", ["update_frost_watch.py", "--no-push"]):
                    rc = update_frost_watch.main()

        self.assertEqual(rc, 0)
        self.assertEqual(calls[0], ["/tmp/fake-python", "scripts/build_seed_feed.py"])
        self.assertNotIn(["git", "fetch", "origin", "main"], calls)
        self.assertNotIn(["git", "rebase", "origin/main"], calls)


if __name__ == "__main__":
    unittest.main()
