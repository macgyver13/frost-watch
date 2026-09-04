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

`config/source-seeds.yaml` also supports live discovery under
`live_collectors.github_repository_searches` and
`live_collectors.delving_topic_searches`. Each collector runs during refresh
and emits candidate `source_discovered` items alongside seeded sources.
Delving queries match the GitHub terms (`FROST`, `chilldkg`). The scheduled
`update_frost_watch.py` run already calls `build_seed_feed.py`, so no extra
cron step is required.

Build the site:

```bash
hugo --source site --minify
```

Cloudflare Pages settings:

- Root directory: `site`
- Build command: `hugo --minify`
- Build output directory: `public`
- Environment: `HUGO_VERSION=0.164.0`
