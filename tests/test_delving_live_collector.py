#!/usr/bin/env python3
"""Tests for Delving Bitcoin topic live collection."""
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

FROST = {
    "id": 99,
    "title": "FROST for threshold Schnorr",
    "slug": "frost-for-threshold-schnorr",
    "created_at": "2026-01-10T12:00:00Z",
    "last_posted_at": "2026-08-01T15:00:00Z",
    "excerpt": "Using FROST to build threshold Schnorr signing.",
    "tags": [],
}

GAME = {
    "id": 100,
    "title": "FROST quest minigame",
    "slug": "frost-quest-minigame",
    "created_at": "2026-02-01T12:00:00Z",
    "last_posted_at": "2026-02-02T12:00:00Z",
    "excerpt": "A video game about frost wizards.",
    "tags": [],
}

CHILLDKG = {
    "id": 101,
    "title": "ChillDKG notes",
    "slug": "chilldkg-notes",
    "created_at": "2026-03-01T12:00:00Z",
    "last_posted_at": "2026-03-02T12:00:00Z",
    "excerpt": "Distributed key generation with ChillDKG.",
    "tags": [],
}


def _empty_artifacts(out: Path) -> None:
    (out / "feed.json").write_text(json.dumps({"items": []}))
    (out / "projects.json").write_text(json.dumps({"projects": []}))
    (out / "sources.json").write_text(json.dumps({"sources": []}))


def _search_cfg(query: str = "FROST") -> dict:
    return {
        "seeded_sources": {},
        "live_collectors": {
            "delving_topic_searches": [
                {
                    "id": "delving-frost",
                    "query": query,
                    "tags": ["frost", "candidate", "topic-discovery"],
                }
            ]
        },
    }


class DelvingLiveCollectorTests(unittest.TestCase):
    def test_relevance_keeps_protocol_drops_game(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                _empty_artifacts(out)
                items, _projects, sources = build_seed_feed.build_items(
                    _search_cfg(),
                    delving_search_fetcher=lambda _q: [FROST, GAME],
                )
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["title"], FROST["title"])
                self.assertEqual(items[0]["source_type"], "delving_topic")
                self.assertEqual(items[0]["confidence"], "delving_search")
                self.assertNotIn("delving-search:delving-frost:100", sources)
            finally:
                build_seed_feed.OUT = old_out

    def test_chilldkg_matches_without_frost_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                _empty_artifacts(out)
                items, _projects, _sources = build_seed_feed.build_items(
                    _search_cfg("chilldkg"),
                    delving_search_fetcher=lambda _q: [CHILLDKG],
                )
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["id"], "delving-search:delving-frost:101")
            finally:
                build_seed_feed.OUT = old_out

    def test_discovered_at_uses_topic_created_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                _empty_artifacts(out)
                items, _projects, _sources = build_seed_feed.build_items(
                    _search_cfg(),
                    delving_search_fetcher=lambda _q: [FROST],
                )
                self.assertEqual(items[0]["discovered_at"], "2026-01-10T12:00:00Z")
                self.assertEqual(items[0]["activity_at"], "2026-08-01T15:00:00Z")
                self.assertEqual(items[0]["evidence"][0]["query"], "FROST")
            finally:
                build_seed_feed.OUT = old_out


if __name__ == "__main__":
    unittest.main()
