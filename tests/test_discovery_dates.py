#!/usr/bin/env python3
"""Regression tests for stable Frostwatch discovery dates."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_seed_feed.py"

spec = importlib.util.spec_from_file_location("build_seed_feed", SCRIPT)
assert spec is not None
build_seed_feed = cast(Any, importlib.util.module_from_spec(spec))
assert spec.loader is not None
spec.loader.exec_module(cast(ModuleType, build_seed_feed))


class DiscoveryDateTests(unittest.TestCase):
    def test_existing_item_discovered_at_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                (out / "feed.json").write_text(json.dumps({
                    "items": [{
                        "id": "seed:frost-zfnd",
                        "title": "Old title",
                        "source_url": "https://frost.zfnd.org/index.html",
                        "event_time": "2026-08-28T00:00:00Z",
                        "observed_at": "2026-08-29T00:00:00Z",
                    }]
                }))
                (out / "projects.json").write_text(json.dumps({"projects": []}))
                (out / "sources.json").write_text(json.dumps({"sources": []}))

                cfg = {"seeded_sources": {"docs_pages": [{
                    "id": "frost-zfnd",
                    "name": "FROST reference",
                    "url": "https://frost.zfnd.org/index.html",
                    "project": "Zcash Foundation FROST",
                    "tags": ["spec"],
                }]}}
                items, _projects, _sources = build_seed_feed.build_items(cfg)
                self.assertEqual(items[0]["discovered_at"], "2026-08-28T00:00:00Z")
                self.assertEqual(items[0]["event_time"], "2026-08-28T00:00:00Z")
                self.assertNotEqual(items[0]["last_seen_at"], "2026-08-28T00:00:00Z")
            finally:
                build_seed_feed.OUT = old_out

    def test_existing_project_first_seen_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                (out / "feed.json").write_text(json.dumps({"items": []}))
                (out / "projects.json").write_text(json.dumps({
                    "projects": [{
                        "id": "zcash-foundation-frost",
                        "name": "Zcash Foundation FROST",
                        "first_seen": "2026-08-27T00:00:00Z",
                    }]
                }))
                (out / "sources.json").write_text(json.dumps({"sources": []}))

                cfg = {"seeded_sources": {"docs_pages": [{
                    "id": "frost-zfnd",
                    "name": "FROST reference",
                    "url": "https://frost.zfnd.org/index.html",
                    "project": "Zcash Foundation FROST",
                    "tags": ["spec"],
                }]}}
                _items, projects, _sources = build_seed_feed.build_items(cfg)
                self.assertEqual(projects["zcash-foundation-frost"]["discovered_at"], "2026-08-27T00:00:00Z")
                self.assertEqual(projects["zcash-foundation-frost"]["first_seen"], "2026-08-27T00:00:00Z")
            finally:
                build_seed_feed.OUT = old_out

    def test_project_latest_discovered_at_tracks_newest_child_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                (out / "feed.json").write_text(json.dumps({
                    "items": [{
                        "id": "seed:old-source",
                        "discovered_at": "2026-08-27T00:00:00Z",
                    }]
                }))
                (out / "projects.json").write_text(json.dumps({"projects": []}))
                (out / "sources.json").write_text(json.dumps({"sources": []}))

                cfg = {"seeded_sources": {"docs_pages": [
                    {
                        "id": "old-source",
                        "name": "Old source",
                        "url": "https://example.com/old",
                        "project": "Shared project",
                        "tags": ["docs"],
                    },
                    {
                        "id": "new-source",
                        "name": "New source",
                        "url": "https://example.com/new",
                        "project": "Shared project",
                        "tags": ["docs"],
                    },
                ]}}
                _items, projects, _sources = build_seed_feed.build_items(cfg)
                latest = projects["shared-project"]["latest_discovered_at"]
                self.assertGreater(latest, "2026-08-27T00:00:00Z")
            finally:
                build_seed_feed.OUT = old_out

    def test_seed_summary_is_used_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                (out / "feed.json").write_text(json.dumps({"items": []}))
                (out / "projects.json").write_text(json.dumps({"projects": []}))
                (out / "sources.json").write_text(json.dumps({"sources": []}))
                cfg = {"seeded_sources": {"docs_pages": [{
                    "id": "frost-zfnd",
                    "name": "FROST reference",
                    "url": "https://frost.zfnd.org/index.html",
                    "project": "Zcash Foundation FROST",
                    "tags": ["spec"],
                    "summary": "Zcash Foundation FROST book: protocol, ciphersuites, and library usage.",
                }]}}
                items, _projects, _sources = build_seed_feed.build_items(cfg)
                self.assertEqual(
                    items[0]["summary"],
                    "Zcash Foundation FROST book: protocol, ciphersuites, and library usage.",
                )
                self.assertFalse(items[0]["summary"].startswith("Seeded monitored source"))
            finally:
                build_seed_feed.OUT = old_out



if __name__ == "__main__":
    unittest.main()
