# FROST Watch

FROST Watch is a feed-first public-source activity tracker for FROST and directly related dependencies such as ChillDKG, FROST DKG work, threshold Schnorr implementations, and FROST usage in Bitcoin/Taproot contexts.

Site: https://frost-watch.pages.dev/

Engine comes from [source-watch](https://github.com/macgyver13/source-watch). This repo is the instance: seeds, identity, feed artifacts, and the refresh script. To pick up template bug fixes and styles:

```bash
git fetch source-watch
git merge source-watch/main
```

Conflicts should stay in `config/` and the FROST+Silent Payments topic layout hook.

Primary artifacts:

- `feed.json` — canonical latest structured feed
- `feed.xml` — RSS feed
- `items.jsonl` — normalized item stream
- `projects.json` — project catalog
- `sources.json` — monitored source catalog
- `watch.json` — instance identity for the client

The Hugo site under `site/` renders the public website from these artifacts.


## Scope

This project aggregates public source metadata and activity. Inclusion is not endorsement, technical review, security assessment, production-readiness judgment, or a canonical roadmap.

## Local pipeline

Needs Python 3, [PyYAML](https://pyyaml.org/), and [Hugo](https://gohugo.io/). Pages pins `HUGO_VERSION=0.164.0`.

```bash
GITHUB_TOKEN=$(gh auth token) python3 scripts/build_seed_feed.py
python3 scripts/sync_hugo_content.py
python3 scripts/verify_public_artifacts.py
hugo --source site --minify
```

Live collectors: `github_repository_searches`, `github_pull_request_searches`, `delving_topic_searches`. A seeded parent repo does not hide matching PRs. Discovery dates on existing items stay put; activity moves if GitHub or Delving is newer.

Seed-only (no GitHub or Delving HTTP):

```bash
python3 scripts/build_seed_feed.py --seed-only
```

Scheduled publish (`scripts/update_frost_watch.py`) already runs this pipeline and pushes `main` so Cloudflare Pages redeploys. No extra cron step.

```bash
python3 -m unittest discover -s tests -v
```

## Cloudflare Pages (static mode)

- Root directory: `site`
- Build command: `hugo --minify`
- Build output directory: `public`
- Environment: `HUGO_VERSION=0.164.0`

