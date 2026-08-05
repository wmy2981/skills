---
name: chinese-poetry-api
description: >-
  Query the Chinese classical poetry API service (chinese-poetry-api, repo:
  https://github.com/palemoky/chinese-poetry-api) — 370k+ poems from Tang/Song/Yuan
  dynasties, with authors, dynasties, poetry types, full-text search, and random poem
  drawing. Use whenever the user asks to look up, search, or list classical Chinese
  poetry (古诗/唐诗/宋词/元曲), a specific poet's works, random poems, 飞花令 (single-character
  draws), or poetry metadata — even casual queries like "帮我找一首李白的诗" or "来一首五言绝句".
  Covers every REST endpoint: health, stats, poems (filtered lists), search, random,
  authors, dynasties, types. All output is raw server JSON, passed through unchanged.
metadata:
  skill_version: "1.0.0"
---

# Chinese Poetry API

CLI wrapper around the [chinese-poetry-api](https://github.com/palemoky/chinese-poetry-api)
REST service (Go, ~370k poems, simplified/traditional Chinese via `lang`).

## Execution Rule

Run the user's command directly without pre-checking; fix on failure.

## Requirements

- [Bun](https://bun.sh) runtime (>= 1.0)
- A reachable chinese-poetry-api instance

## Setup

The script reads the `POETRY_API_URL` environment variable — a **full API base URL**
(the script appends no prefix). The default is `https://poetry.palemoky.com/api`, an
online test instance provided by the upstream developer. It may rate-limit, change data,
or go offline without notice — treat it as a demo only. For real work, point
`POETRY_API_URL` at your own instance (local Docker or self-hosted deployment).

1. Read `scripts/.env.example` for the variable name.
2. Add or update `POETRY_API_URL` in the shared global file `~/.wmyskills/.env`.
3. Do **not** copy `.env.example` to `.env` directly — that would overwrite existing config.

If the user's request needs an instance that isn't running, start one after notifying the user:

```bash
docker run -d -p 1279:1279 palemoky/chinese-poetry-api:latest
```

## Usage

```bash
bun run scripts/main.ts <command> [options]
```

All output is the raw JSON body from the server — print it verbatim, do not reformat
or summarize it. Non-2xx responses print `Error <status>: <body>` to stderr and exit 1.

| Command    | Description                                  | Options |
|------------|----------------------------------------------|---------|
| `health`   | Health check                                | — |
| `stats`    | Overall statistics                          | — |
| `poems`    | List poems (filters are combinable)         | `--dynasty` `--author` `--dynasty-id` `--type-id` (repeatable, OR) `--page` `--page-size` (max 100) |
| `search`   | Full-text search (FTS5)                     | `--q` (required) `--type` (`all` default, `title`, `content`, `author`) `--page` `--page-size` |
| `random`   | Random poem                                 | `--author` `--author-id` `--dynasty` `--dynasty-id` `--type` (repeatable, OR) `--type-id` `--char` |
| `authors`  | List authors (paginated)                    | `--page` `--page-size` |
| `author`   | Author by ID                                | `--id` (required) |
| `dynasties`| List dynasties (with poem counts)           | — |
| `dynasty`  | Dynasty by ID                               | `--id` (required) |
| `types`    | List poetry types                           | — |
| `type`     | Poetry type by ID                           | `--id` (required) |

Every command accepts `--lang zh-Hans|zh-Hant` to switch simplified/traditional
Chinese (`zh-Hans` is the default). Invalid flags or arguments are rejected with an
error before any request is sent.

## Examples

```bash
# Health check and overall stats
bun run scripts/main.ts health
bun run scripts/main.ts stats

# Li Bai's poems, page 2
bun run scripts/main.ts poems --author 李白 --page 2 --page-size 10

# Poems from the Tang dynasty in traditional Chinese
bun run scripts/main.ts poems --dynasty 唐 --lang zh-Hant

# Full-text search
bun run scripts/main.ts search --q 静夜思
bun run scripts/main.ts search --q 明月光 --type content

# Random 五言绝句 by Li Bai (multiple types are OR)
bun run scripts/main.ts random --author 李白 --type 五言绝句 --type 七言绝句

# 飞花令 — poem containing a single character
bun run scripts/main.ts random --char 春

# Metadata
bun run scripts/main.ts authors --page 1 --page-size 20
bun run scripts/main.ts author --id 1
bun run scripts/main.ts dynasties
bun run scripts/main.ts dynasty --id 6
bun run scripts/main.ts types
bun run scripts/main.ts type --id 10
```

## Notes

- `--char` (飞花令) accepts exactly one character and can only be combined with
  `--lang` — other filters return 400 from the server.
- Query params are validated server-side: unknown params or `page_size` over 100
  return 400, so don't invent filters the API doesn't document.
