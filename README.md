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

This instance runs in **service mode**: the collector ingests into Cloudflare D1. Do not publish feed JSON to Pages. First deploy, secrets, and `/admin`: `AGENTS.md` **Service mode**. Hourly refresh is `.github/workflows/refresh-feed.yml` via Worker cron or `workflow_dispatch`.

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

`python3 scripts/build_seed_feed.py` refreshes seeded GitHub repo/PR
timestamps and runs live collectors
(`github_repository_searches`, `github_pull_request_searches`,
`delving_topic_searches`, `delving_category_listings`). Repository search
does not see PRs inside an already-seeded repo; PR search does. Each
collector emits **candidate** `source_discovered` items alongside seeds.
A candidate is a search or category hit that passed `watch.yaml`
`relevance` and, if set, `discovered_after`; it is not yet in the accepted
`seeded_sources` catalog. Hits whose name, URL, or text contains
`source-watch` (this engine and forks) are dropped.
Seeded GitHub repos/PRs take live `created_at` as `discovered_at` when that
stamp is on or after `discovered_after`; older `created_at` keeps the seed
date. Activity moves if GitHub or Delving is newer. Docs, crates, and
`--seed-only` keep seed or first-seen discovery.

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


Pages builds Hugo from `site/`. Feed artifacts in `site/static/` come from the Python pipeline above. Do not create a Worker for a `serving.mode: static` instance.

## Cloudflare Worker (service mode)

Set `serving.mode: service` in `config/watch.yaml`. The Worker serves Hugo assets, live `/feed.json` from D1, and `/admin`. The Python collector POSTs into the service instead of writing `site/static/`.

Numbered first deploy, secret matrix, and operator notes: `AGENTS.md` **Service mode**. Short path:

1. `npx wrangler d1 create source-watch` → paste `database_id` into `wrangler.jsonc`.
2. `npx wrangler d1 migrations apply source-watch --remote`
3. `npx wrangler secret put ADMIN_TOKEN` and `INGEST_TOKEN` (collector env `SOURCE_WATCH_INGEST_TOKEN` must be the **same value** as `INGEST_TOKEN`). Optional `GITHUB_DISPATCH_TOKEN` plus `vars.GITHUB_DISPATCH_REPO` for hourly refresh.
4. `python3 scripts/sync_hugo_content.py`. Former static site: `python3 scripts/promote_to_service.py` then sync again.
5. Build `hugo --source site --minify`, deploy `npx wrangler deploy`, `HUGO_VERSION=0.164.0`.
6. Set `serving.service_url` and `base_url` to `https://<worker>.<subdomain>.workers.dev/`. Ingest: `SOURCE_WATCH_INGEST_TOKEN=… python3 scripts/build_seed_feed.py`. `--seed-only` requires `--allow-partial-ingest`.

`GET /admin` is public chrome; APIs need `ADMIN_TOKEN`. Failed admin auths: 10 per IP per minute, then 429. Hide/exclude update the public feed immediately; include terms and seed additions apply on the next collect.

Local Worker: `.dev.vars` with `ADMIN_TOKEN` / `INGEST_TOKEN`, Node 22+, `npx wrangler d1 migrations apply source-watch --local`, `npx wrangler dev --test-scheduled`, ingest against `http://localhost:8787/`.



## GitHub Pages

Use the same Hugo settings: build from `site/` with `hugo --minify`,
`HUGO_VERSION=0.164.0`, output `public`.

A typical setup is a GitHub Pages workflow (or the Pages UI) that publishes
the Hugo output, or a `gh-pages` branch containing the built `public/`
directory.

## Config

- `config/watch.yaml` — instance identity: name, base URL, description, default tag, preferred chips, hidden tags, relevance rules, optional `discovered_after` (ISO date; drop live hits and ignore GitHub `created_at` before this), optional topic tiles, optional `serving` (`mode: static|service`; `service_url` required in service mode). Chips, hidden tags, and name ship in `watch.json` for the client. `relevance` filters live collector hits (`always_match` short-circuits accept; `required_any` / `context_any` must appear in the GitHub description/topics, PR title/body, or Delving title/excerpt/tags).
- `config/source-seeds.yaml` — seeded sources and live collectors. Pipeline input only; not read at request time.


## Tests

```bash
python3 -m unittest discover -s tests -v
```
