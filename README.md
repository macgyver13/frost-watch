# FROST Watch

FROST Watch is a feed-first public-source activity tracker for FROST and directly related dependencies such as ChillDKG, FROST DKG work, threshold Schnorr implementations, and FROST usage in Bitcoin/Taproot contexts.

Primary artifacts:

- `feed.json` — canonical latest structured feed
- `feed.xml` — RSS feed
- `items.jsonl` — normalized item stream
- `projects.json` — project catalog
- `sources.json` — monitored source catalog

The Hugo site under `site/` renders the public website from these artifacts.

## Scope

This project aggregates public source metadata and activity. Inclusion is not endorsement, technical review, security assessment, production-readiness judgment, or a canonical roadmap.

## Development

Generate public artifacts and Hugo content:

```bash
python3 scripts/build_seed_feed.py
python3 scripts/sync_hugo_content.py
python3 scripts/verify_public_artifacts.py
```

`config/source-seeds.yaml` also supports live GitHub repository discovery under
`live_collectors.github_repository_searches`. Each collector runs a GitHub
repository search during refresh and emits candidate `source_discovered` items
into the structured feed alongside the static seeded sources.

Build the site:

```bash
hugo --source site --minify
```

Cloudflare Pages settings:

- Root directory: `site`
- Build command: `hugo --minify`
- Build output directory: `public`
- Environment: `HUGO_VERSION=0.164.0`
