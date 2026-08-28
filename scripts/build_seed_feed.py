#!/usr/bin/env python3
"""Build FROST Watch v0 public feed artifacts from seeded sources.

The generated artifacts are static, but discovery metadata must be stable across
runs. This script loads the previous public artifacts, merges the current seeded
source set into them, and preserves first-discovery timestamps for known items,
sources, and projects.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "source-seeds.yaml"
OUT = ROOT / "data" / "public"
STATIC = ROOT / "site" / "static"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except Exception:
            return None


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
    if kind == "github_pull_requests" and "url" in entry:
        match = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)/?$", entry["url"])
        if match:
            return f"{match.group(1)} PR #{match.group(2)}"
    if "repo" in entry:
        return entry["repo"]
    return entry.get("url", entry.get("id", "Seeded source"))


def load_existing_artifacts() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Load previous static artifacts so discovery dates do not refresh each run."""
    existing_items: dict[str, dict] = {}
    existing_projects: dict[str, dict] = {}
    existing_sources: dict[str, dict] = {}

    feed_path = OUT / "feed.json"
    projects_path = OUT / "projects.json"
    sources_path = OUT / "sources.json"
    if feed_path.exists():
        for item in json.loads(feed_path.read_text()).get("items", []):
            if item.get("id"):
                existing_items[item["id"]] = item
    if projects_path.exists():
        for project in json.loads(projects_path.read_text()).get("projects", []):
            if project.get("id"):
                existing_projects[project["id"]] = project
    if sources_path.exists():
        for source in json.loads(sources_path.read_text()).get("sources", []):
            if source.get("id"):
                existing_sources[source["id"]] = source
    return existing_items, existing_projects, existing_sources


def discovery_time(old: dict, observed_at: str) -> str:
    """Return the stable first-seen timestamp for a previously known record."""
    return (
        old.get("discovered_at")
        or old.get("first_seen")
        or old.get("event_time")
        or old.get("observed_at")
        or observed_at
    )


def item_activity_at(item: dict) -> str:
    """Best single timeline date for activity-oriented views."""
    return (
        item.get("source_updated_at")
        or item.get("source_published_at")
        or item.get("activity_at")
        or item.get("event_time")
        or item.get("discovered_at")
        or item.get("observed_at")
        or item.get("last_seen_at")
        or utc_now_iso()
    )


def build_items(cfg: dict) -> tuple[list[dict], dict, dict]:
    observed_at = utc_now_iso()
    existing_items, existing_projects, existing_sources = load_existing_artifacts()
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
            item_id = f"seed:{source_id}"
            old_item = existing_items.get(item_id, {})
            discovered_at = discovery_time(old_item, observed_at)
            item = {
                "id": item_id,
                "title": title_for(entry, kind),
                "summary": f"Seeded monitored source for FROST Watch: {title_for(entry, kind)}.",
                "source_url": url,
                "source_type": source_type,
                "event_type": "source_seeded",
                "project": project,
                "tags": tags,
                "status": "seeded",
                "discovered_at": discovered_at,
                "event_time": discovered_at,
                "activity_at": item_activity_at({**old_item, "event_time": discovered_at}),
                "observed_at": observed_at,
                "last_seen_at": observed_at,
                "confidence": "seeded_source",
                "evidence": [{"url": url, "retrieved_at": observed_at}],
            }
            items.append(item)

            old_source = existing_sources.get(source_id, {})
            source_discovered_at = discovery_time(old_source, observed_at)
            sources[source_id] = {
                "id": source_id,
                "name": title_for(entry, kind),
                "url": url,
                "source_type": source_type,
                "project": project,
                "tags": tags,
                "confidence": "seeded_source",
                "discovered_at": source_discovered_at,
                "first_seen": source_discovered_at,
                "last_checked": observed_at,
            }

            pslug = slugify(project)
            old_project = existing_projects.get(pslug, {})
            project_discovered_at = discovery_time(old_project, observed_at)
            projects.setdefault(pslug, {
                "id": pslug,
                "name": project,
                "tags": [],
                "sources": [],
                "discovered_at": project_discovered_at,
                "first_seen": project_discovered_at,
                "activity_at": old_project.get("activity_at") or old_project.get("last_observed_activity") or observed_at,
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
        pub_dt = parse_iso(item.get("discovered_at") or item.get("event_time")) or now
        parts.extend([
            '<item>',
            f'<title>{esc(item["title"])}</title>',
            f'<link>{esc(item["source_url"])}</link>',
            f'<guid isPermaLink="false">{esc(item["id"])}</guid>',
            f'<description>{esc(item["summary"])}</description>',
            f'<pubDate>{format_datetime(pub_dt)}</pubDate>',
            '</item>',
        ])
    parts.append('</channel></rss>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n")


def main() -> int:
    cfg = parse_seed_yaml(CONFIG)
    items, projects, sources = build_items(cfg)
    items = sorted(items, key=lambda x: x.get("discovered_at", ""), reverse=True)
    feed = {
        "schema_version": "frost-watch.feed.v0",
        "title": "FROST Watch",
        "description": cfg.get("scope_note", "Public-source FROST activity feed."),
        "generated_at": utc_now_iso(),
        "items": items,
    }
    projects_list = sorted(projects.values(), key=lambda x: x.get("discovered_at", ""), reverse=True)
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
