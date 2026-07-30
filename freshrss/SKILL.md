---
name: freshrss
description: "Access and interact with my FreshRSS instance via python scripts. Use for any RSS-related question, including reading articles, searching past content, finding feeds, getting recommendations, managing subscriptions, checking unread counts, marking read/star, or exploring what I follow. Triggers on keywords: RSS, FreshRSS, feed, unread, headlines, articles, subscriptions, starred."
---

# FreshRSS

Self-hosted RSS reader accessed via Google Reader compatible API (GReader).
All operations go through a single python script.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Environment Variables

| Variable | Description |
|---|---|
| `FRESHRSS_URL` | Base URL (e.g. `http://127.0.0.1:1180`) |
| `FRESHRSS_API_USER` | API username |
| `FRESHRSS_API_PASSWORD` | API password |

> 💡 Environment variables can be configured in a `.env` file in the script directory or current working directory. The script uses `load_dotenv()` to load them automatically.

## Usage

```bash
python scripts/freshrss.py <command> [options]
```

Common options for reading commands: `--count N` (default 20), `-v`/`--verbose` (include summary text).

## Reading Articles

### Recent articles
```bash
python scripts/freshrss.py recent --count 10
python scripts/freshrss.py recent --count 5 -v    # with summary
```

### Unread articles
```bash
python scripts/freshrss.py unread --count 20
```

### Articles from a specific feed
```bash
python scripts/freshrss.py feed --url "https://example.com/rss" --count 10
```

### Articles from a category
```bash
python scripts/freshrss.py category --name "Technology" --count 15
```

### Starred articles
```bash
python scripts/freshrss.py starred --count 20
```

### Search articles
Title only (fast, default 200 articles scanned, max 1000):
```bash
python scripts/freshrss.py search -k "keyword"
```
Title + content (slower, use `--batch` to control scan size):
```bash
python scripts/freshrss.py search -k "keyword" --deep --batch 500
```

## Feed Management

### List all subscriptions
```bash
python scripts/freshrss.py list-feeds
```

### List categories
```bash
python scripts/freshrss.py list-categories
```

### Unread counts
```bash
python scripts/freshrss.py unread-count
```

### Add a feed
```bash
python scripts/freshrss.py add-feed --url "https://example.com/feed.xml" --category "News"
```

### Move feed to another category
```bash
python scripts/freshrss.py move-feed --feed-id "feed/https://..." --to "NewCat" --from "OldCat"
```

### Remove a feed
```bash
python scripts/freshrss.py remove-feed --feed-id "feed/https://..."
```

### Mark article as read
```bash
python scripts/freshrss.py mark-read --item-id "tag:google.com,2005:reader/item/..."
```

### Star an article
```bash
python scripts/freshrss.py star --item-id "tag:google.com,2005:reader/item/..."
```

## Feed Recommendations

When asked for recommendations:
1. Run `list-feeds` to see current subscriptions and categories
2. Identify themes from feed titles and categories
3. Use web search to find feeds in similar topics the user doesn't already follow
4. Present recommendations grouped by interest area

## Notes

- Auth token is fetched fresh on each invocation (no caching needed)
- All output is JSON for easy parsing
- Search is client-side filtered since GReader API lacks native search
- Feed stream IDs use format `feed/https://example.com/rss`
- Use `-v` to include article summary in output (works on all reading commands)
