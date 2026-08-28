#!/usr/bin/env python3
"""Render Hugo content pages from FROST Watch public JSON artifacts."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
STATIC = SITE / "static"
CONTENT = SITE / "content"

DISCLAIMER = """FROST Watch aggregates public-source activity related to FROST and directly related dependencies. Inclusion means only that a source matched the monitoring criteria. This site does not provide technical review, endorsement, security assessment, production-readiness judgment, or a canonical roadmap."""


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def fm(title: str, extra: str = "") -> str:
    return f"---\ntitle: {json.dumps(title)}\n{extra}---\n\n"


def rel_static(name: str) -> str:
    return f"/{name}"


def item_line(item: dict) -> str:
    tags = ", ".join(f"`{t}`" for t in item.get("tags", []))
    return f"- [{item['title']}]({item['source_url']}) — {item['summary']}  \n  _Project:_ {item.get('project','')} · _Type:_ `{item.get('source_type','')}` · _Tags:_ {tags}"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main() -> int:
    feed = json.loads((STATIC / "feed.json").read_text())
    projects = json.loads((STATIC / "projects.json").read_text())["projects"]
    sources = json.loads((STATIC / "sources.json").read_text())["sources"]
    items = feed["items"]
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    write(CONTENT / "_index.md", fm("FROST Watch") + f"""
> {DISCLAIMER}

## Latest activity

FROST Watch is currently bootstrapped with {len(items)} seeded monitored sources. Live collectors will add repository, package, docs, and discovery events to the structured feed.

- [Latest activity](/latest/)
- [Projects](/projects/)
- [Sources](/sources/)
- [Tags](/tags/)
- [Source types](/source-types/)
- [Weekly archive](/weeks/)
- [Recently changed](/recently-changed/)
- [Newly discovered repos](/newly-discovered/)
- [Needs human source seeding](/needs-human-source-seeding/)
- [FROST + Silent Payments overlap](/topics/frost-silent-payments/)

## Machine-readable feeds

- [feed.json]({rel_static('feed.json')})
- [feed.xml]({rel_static('feed.xml')})
- [items.jsonl]({rel_static('items.jsonl')})
- [projects.json]({rel_static('projects.json')})
- [sources.json]({rel_static('sources.json')})

Generated: `{now}`
""")

    write(CONTENT / "latest" / "_index.md", fm("Latest activity") + "\n".join([f"> {DISCLAIMER}\n", *[item_line(i) for i in items]]) + "\n")

    project_items = defaultdict(list)
    for item in items:
        project_items[item.get("project", "Unknown")].append(item)
    body = [f"> {DISCLAIMER}\n"]
    for p in projects:
        body.append(f"## {p['name']}\n")
        body.append("Tags: " + ", ".join(f"`{t}`" for t in p.get("tags", [])) + "\n")
        for item in project_items.get(p["name"], []):
            body.append(item_line(item))
        body.append("")
    write(CONTENT / "projects" / "_index.md", fm("Project catalog") + "\n".join(body) + "\n")

    body = [f"> {DISCLAIMER}\n", "| Source | Type | Project | Tags |", "|---|---|---|---|"]
    for s in sources:
        body.append(f"| [{s['name']}]({s['url']}) | `{s['source_type']}` | {s['project']} | {' '.join('`'+t+'`' for t in s.get('tags', []))} |")
    write(CONTENT / "sources" / "_index.md", fm("Source coverage") + "\n".join(body) + "\n")

    by_tag = defaultdict(list)
    by_type = defaultdict(list)
    for item in items:
        by_type[item.get("source_type", "unknown")].append(item)
        for tag in item.get("tags", []):
            by_tag[tag].append(item)
    body = [f"> {DISCLAIMER}\n"]
    for tag in sorted(by_tag):
        body.append(f"## `{tag}`\n")
        for item in by_tag[tag]: body.append(item_line(item))
        body.append("")
    write(CONTENT / "tags" / "_index.md", fm("By tag") + "\n".join(body) + "\n")

    body = [f"> {DISCLAIMER}\n"]
    for st in sorted(by_type):
        body.append(f"## `{st}`\n")
        for item in by_type[st]: body.append(item_line(item))
        body.append("")
    write(CONTENT / "source-types" / "_index.md", fm("By source type") + "\n".join(body) + "\n")

    week = datetime.now(timezone.utc).strftime("%G-W%V")
    week_dir = CONTENT / "weeks" / week
    write(CONTENT / "weeks" / "_index.md", fm("Weekly archive") + f"- [{week}](/weeks/{week}/)\n")
    write(week_dir / "_index.md", fm(f"FROST Watch weekly rollup {week}") + f"""
> {DISCLAIMER}

This bootstrap rollup is generated from the structured feed and currently contains seeded monitored sources. Future weekly rollups will summarize repository activity, package/docs changes, accepted sources, and candidate discoveries from the same feed.

## Seeded activity

""" + "\n".join(item_line(i) for i in items) + "\n")

    placeholder = f"> {DISCLAIMER}\n\nNo live collector events yet. This view will populate after continuous collection is enabled.\n"
    write(CONTENT / "recently-changed" / "_index.md", fm("Recently changed") + placeholder)
    write(CONTENT / "newly-discovered" / "_index.md", fm("Newly discovered repos") + placeholder)
    write(CONTENT / "needs-human-source-seeding" / "_index.md", fm("Needs human source seeding") + placeholder)

    write(CONTENT / "topics" / "frost-silent-payments" / "_index.md", fm("FROST + Silent Payments overlap") + f"""
> Working notes. {DISCLAIMER}

This topic tracks the intersection between FROST and Silent Payments integration work.

## Initial areas to track

- Verification-share availability: FROST verifying shares are DKG outputs and must be available to DLEQ verifiers.
- Key management and hardware-signer UX: FROST shares are Shamir shares and require persistence/recovery beyond ordinary BIP-32 seed derivation.
- Epoch consistency: refreshed or reshared participant shares must not be mixed across epochs.
- PSBT/group-config surfaces for FROST configuration, signing commitments, signature shares, and participant verifying shares.

Future updates should link back to structured feed items and public sources.
""")

    print(f"rendered Hugo content from {len(items)} items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
