#!/usr/bin/env python3
"""Instance relevance: drop cake/UI frosting hits, keep protocol FROST."""
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

FROSTING_REPO = {
    "full_name": "kenny25-gif/annies-frosting-delight",
    "html_url": "https://github.com/kenny25-gif/annies-frosting-delight",
    "description": "annie's frosting delight website",
    "created_at": "2026-09-08T13:54:40Z",
    "pushed_at": "2026-09-08T14:39:43Z",
    "updated_at": "2026-09-08T14:39:43Z",
    "topics": [],
}

FROSTED_REPO = {
    "full_name": "example/authentik-frosted-theme",
    "html_url": "https://github.com/example/authentik-frosted-theme",
    "description": "Apply a frosted glass design to Authentik.",
    "created_at": "2026-09-01T00:00:00Z",
    "pushed_at": "2026-09-01T00:00:00Z",
    "updated_at": "2026-09-01T00:00:00Z",
    "topics": ["css"],
}

FROST_REPO = {
    "full_name": "Onyekachukwu-Nweke/bitcoin-frost-wallet",
    "html_url": "https://github.com/Onyekachukwu-Nweke/bitcoin-frost-wallet",
    "description": "FROST (Flexible Round-Optimized Schnorr Threshold) signatures with ChillDKG.",
    "created_at": "2026-08-01T00:00:00Z",
    "pushed_at": "2026-08-01T00:00:00Z",
    "updated_at": "2026-08-01T00:00:00Z",
    "topics": ["bitcoin", "frost"],
}

FROSTED_PR = {
    "html_url": "https://github.com/GoreeCloud/goreecloud-launcher/pull/82",
    "title": "Migrate Launcher to GLAZE UI V1.2 Frosted Neutral",
    "body": "Frosted glass chrome for the launcher.",
    "number": 82,
    "created_at": "2026-09-08T14:59:37Z",
    "updated_at": "2026-09-08T14:59:37Z",
    "pull_request": {"html_url": "https://github.com/GoreeCloud/goreecloud-launcher/pull/82"},
    "repository_url": "https://api.github.com/repos/GoreeCloud/goreecloud-launcher",
}

FROSTING_PR = {
    "html_url": "https://github.com/example/bakery/pull/4",
    "title": "Add cupcake frosting gallery",
    "body": "Photos of buttercream frosting.",
    "number": 4,
    "created_at": "2026-09-08T12:00:00Z",
    "updated_at": "2026-09-08T12:00:00Z",
    "pull_request": {"html_url": "https://github.com/example/bakery/pull/4"},
    "repository_url": "https://api.github.com/repos/example/bakery",
}

FROST_PR = {
    "html_url": "https://github.com/bitcoin/bips/pull/2070",
    "title": "BIP445: FROST Signing Protocol for BIP340 Signatures",
    "body": "Specify the FROST signing protocol for BIP340.",
    "number": 2070,
    "created_at": "2026-08-01T00:00:00Z",
    "updated_at": "2026-08-01T00:00:00Z",
    "pull_request": {"html_url": "https://github.com/bitcoin/bips/pull/2070"},
    "repository_url": "https://api.github.com/repos/bitcoin/bips",
}


def _empty_artifacts(out: Path) -> None:
    (out / "feed.json").write_text(json.dumps({"items": []}))
    (out / "projects.json").write_text(json.dumps({"projects": []}))
    (out / "sources.json").write_text(json.dumps({"sources": []}))


def _frost_collectors(kind: str) -> list[dict]:
    seeds = build_seed_feed.parse_yaml(build_seed_feed.CONFIG)
    collectors = (seeds.get("live_collectors") or {}).get(kind) or []
    return [c for c in collectors if "frost" in str(c.get("id") or "").lower() and "chilldkg" not in str(c.get("id") or "").lower()]


def _cfg() -> dict:
    return {
        "seeded_sources": {},
        "live_collectors": {
            "github_repository_searches": _frost_collectors("github_repository_searches"),
            "github_pull_request_searches": _frost_collectors("github_pull_request_searches"),
        },
    }


class FrostWatchRelevanceTests(unittest.TestCase):
    def test_frost_github_queries_exclude_frosting_and_frosted(self) -> None:
        queries = [str(c.get("query") or "") for c in (
            *_frost_collectors("github_repository_searches"),
            *_frost_collectors("github_pull_request_searches"),
        )]
        self.assertTrue(queries)
        for query in queries:
            self.assertIn("-frosting", query)
            self.assertIn("-frosted", query)

    def test_frosting_and_frosted_hits_are_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            old_out = build_seed_feed.OUT
            build_seed_feed.OUT = out
            try:
                _empty_artifacts(out)
                items, _projects, _sources = build_seed_feed.build_items(
                    _cfg(),
                    github_repo_fetcher=lambda _q: [FROSTING_REPO, FROSTED_REPO, FROST_REPO],
                    github_pr_fetcher=lambda _q: [FROSTED_PR, FROSTING_PR, FROST_PR],
                    watch=build_seed_feed.load_watch(),
                )
                urls = {item["source_url"] for item in items}
                self.assertIn(FROST_REPO["html_url"], urls)
                self.assertIn(FROST_PR["html_url"], urls)
                self.assertNotIn(FROSTING_REPO["html_url"], urls)
                self.assertNotIn(FROSTED_REPO["html_url"], urls)
                self.assertNotIn(FROSTED_PR["html_url"], urls)
                self.assertNotIn(FROSTING_PR["html_url"], urls)
            finally:
                build_seed_feed.OUT = old_out


if __name__ == "__main__":
    unittest.main()
