#!/usr/bin/env python3
"""Render slim Hugo content pages from FROST Watch public JSON artifacts.

Dashboard, atlas, week, and sources pages are hydrated client-side from
feed.json / projects.json / sources.json. Markdown here only needs to exist
so Hugo emits the URLs, plus week section pages so the week rail can list them.
"""
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


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def fm(title: str, extra: str = "") -> str:
    return f"---\ntitle: {json.dumps(title)}\n{extra}---\n\n"


def week_title(slug: str) -> str:
    match = re.match(r"(\d{4})-W(\d{1,2})$", slug)
    if match:
        return f"Week {int(match.group(2))}, {match.group(1)}"
    return slug


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main() -> int:
    feed = json.loads((STATIC / "feed.json").read_text())
    items = feed.get("items", [])
    week = datetime.now(timezone.utc).strftime("%G-W%V")

    write(CONTENT / "_index.md", fm("Activity"))
    write(CONTENT / "projects" / "_index.md", fm("Projects"))
    write(CONTENT / "sources" / "_index.md", fm("Sources"))

    week_root = CONTENT / "weeks"
    week_root.mkdir(parents=True, exist_ok=True)
    write(week_root / week / "_index.md", fm(week_title(week)))
    week_dirs = sorted((p.name for p in week_root.iterdir() if p.is_dir()), reverse=True)
    for slug in week_dirs:
        page = week_root / slug / "_index.md"
        if not page.exists() or "weekly rollup" in page.read_text().lower() or page.read_text().count("\n") > 8:
            write(page, fm(week_title(slug)))
        else:
            # Keep slim title pages in the Week NN, YYYY form.
            write(page, fm(week_title(slug)))
    write(week_root / "_index.md", fm("Weeks"))

    write(
        CONTENT / "topics" / "_index.md",
        fm("Topics") + "- [FROST + Silent Payments](/topics/frost-silent-payments/)\n",
    )
    write(
        CONTENT / "topics" / "frost-silent-payments" / "_index.md",
        fm("FROST + Silent Payments")
        + "Working notes on the overlap between FROST and Silent Payments.\n",
    )

    # Keep leftover archive URLs alive without legal blockquotes or ISO-in-code lists.
    by_tag: dict[str, list] = defaultdict(list)
    by_type: dict[str, list] = defaultdict(list)
    for item in items:
        by_type[item.get("source_type", "unknown")].append(item)
        for tag in item.get("tags", []):
            by_tag[tag].append(item)

    def link_list(rows: list[dict]) -> str:
        lines = []
        for item in rows:
            title = item.get("title") or item.get("id") or "item"
            url = item.get("source_url") or "#"
            lines.append(f"- [{title}]({url})")
        return "\n".join(lines) + ("\n" if lines else "")

    write(CONTENT / "latest" / "_index.md", fm("Latest activity") + link_list(items))
    write(CONTENT / "tags" / "_index.md", fm("Tags") + "\n".join(
        [f"## {tag}\n\n{link_list(rows)}" for tag, rows in sorted(by_tag.items())]
    ) + "\n")
    write(CONTENT / "source-types" / "_index.md", fm("Source types") + "\n".join(
        [f"## {st}\n\n{link_list(rows)}" for st, rows in sorted(by_type.items())]
    ) + "\n")
    write(CONTENT / "recently-changed" / "_index.md", fm("Recently changed") + link_list(items))
    write(CONTENT / "newly-discovered" / "_index.md", fm("Newly discovered") + link_list(items))
    write(
        CONTENT / "needs-human-source-seeding" / "_index.md",
        fm("Needs human source seeding") + "No live collector events queued for human seeding.\n",
    )

    print(f"rendered slim Hugo content from {len(items)} items, weeks={week_dirs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
