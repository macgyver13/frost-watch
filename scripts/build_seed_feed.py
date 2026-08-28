#!/usr/bin/env python3
"""Build FROST Watch v0 public feed artifacts from seeded sources."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "source-seeds.yaml"
OUT = ROOT / "data" / "public"
STATIC = ROOT / "site" / "static"


def parse_seed_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text())
    except Exception:
        # Tiny fallback parser would be fragile; fail with clear instruction.
        raise SystemExit("PyYAML is required to parse config/source-seeds.yaml")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def source_url_for(entry: dict, kind: str) -> str:
    if "url" in entry:
        return entry["url"]
    if "repo" in entry:
        return "https://github.com/" + entry["repo"]
    if kind == "crates":
        return entry.get("url") or "https://crates.io/crates/" + entry["name"]
    raise ValueError(f"cannot derive URL for {entry}")


def source_type_for(kind: str) -> str:
    return {
        "docs_pages": "docs_page",
        "github_repositories": "github_repository",
        "github_pull_requests": "github_pull_request",
        "crates": "package_crate",
    }.get(kind, kind)


def title_for(entry: dict, kind: str) -> str:
    if "name" in entry:
        return entry["name"]
    if "repo" in entry:
        return entry["repo"]
    return entry.get("url", entry.get("id", "Seeded source"))


def build_items(cfg: dict) -> tuple[list[dict], dict, dict]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    observed_at = now.isoformat().replace("+00:00", "Z")
    sources: dict[str, dict] = {}
    projects: dict[str, dict] = {}
    items: list[dict] = []
    for kind, entries in cfg.get("seeded_sources", {}).items():
        for entry in entries or []:
            url = source_url_for(entry, kind)
            source_id = entry.get("id") or slugify(url)
            project = entry.get("project") or entry.get("repo") or entry.get("name") or source_id
            tags = list(dict.fromkeys(["frost", *entry.get("tags", [])]))
            source_type = source_type_for(kind)
            item = {
                "id": f"seed:{source_id}",
                "title": title_for(entry, kind),
                "summary": f"Seeded monitored source for FROST Watch: {title_for(entry, kind)}.",
                "source_url": url,
                "source_type": source_type,
                "event_type": "source_seeded",
                "project": project,
                "tags": tags,
                "status": "seeded",
                "event_time": observed_at,
                "observed_at": observed_at,
                "confidence": "seeded_source",
                "evidence": [{"url": url, "retrieved_at": observed_at}],
            }
            items.append(item)
            sources[source_id] = {
                "id": source_id,
                "name": title_for(entry, kind),
                "url": url,
                "source_type": source_type,
                "project": project,
                "tags": tags,
                "confidence": "seeded_source",
                "first_seen": observed_at,
                "last_checked": observed_at,
            }
            pslug = slugify(project)
            projects.setdefault(pslug, {
                "id": pslug,
                "name": project,
                "tags": [],
                "sources": [],
                "first_seen": observed_at,
                "last_observed_activity": observed_at,
            })
            projects[pslug]["tags"] = sorted(set(projects[pslug]["tags"]) | set(tags))
            projects[pslug]["sources"].append(source_id)
    return items, projects, sources


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_rss(path: Path, items: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    def esc(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                 .replace('"', "&quot;"))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        '<title>FROST Watch</title>',
        '<link>https://frost-watch.pages.dev/</link>',
        '<description>Public-source activity tracking for FROST and directly related dependencies.</description>',
        f'<lastBuildDate>{format_datetime(now)}</lastBuildDate>',
    ]
    for item in items:
        parts.extend([
            '<item>',
            f'<title>{esc(item["title"])}</title>',
            f'<link>{esc(item["source_url"])}</link>',
            f'<guid isPermaLink="false">{esc(item["id"])}</guid>',
            f'<description>{esc(item["summary"])}</description>',
            f'<pubDate>{format_datetime(now)}</pubDate>',
            '</item>',
        ])
    parts.append('</channel></rss>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n")


def main() -> int:
    cfg = parse_seed_yaml(CONFIG)
    items, projects, sources = build_items(cfg)
    feed = {
        "schema_version": "frost-watch.feed.v0",
        "title": "FROST Watch",
        "description": cfg.get("scope_note", "Public-source FROST activity feed."),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "items": items,
    }
    projects_list = sorted(projects.values(), key=lambda x: x["name"].lower())
    sources_list = sorted(sources.values(), key=lambda x: x["name"].lower())
    for base in (OUT, STATIC):
        write_json(base / "feed.json", feed)
        write_json(base / "projects.json", {"schema_version": "frost-watch.projects.v0", "projects": projects_list})
        write_json(base / "sources.json", {"schema_version": "frost-watch.sources.v0", "sources": sources_list})
        (base / "items.jsonl").write_text("".join(json.dumps(i, sort_keys=True) + "\n" for i in items))
        write_rss(base / "feed.xml", items)
    print(f"wrote {len(items)} seed items, {len(projects_list)} projects, {len(sources_list)} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
