---
name: freshrss
description: "Access and interact with my FreshRSS instance via python3 scripts. Use for any RSS-related question, including reading articles, searching past content, finding feeds, getting recommendations, managing subscriptions, checking unread counts, marking read/star, or exploring what I follow. Triggers on keywords: RSS, FreshRSS, feed, unread, headlines, articles, subscriptions, starred."
---

# FreshRSS

Self-hosted RSS reader accessed via Google Reader compatible API (GReader).
All operations go through a single python3 script.

## Environment Variables

| Variable | Description |
|---|---|
| `FRESHRSS_URL` | Base URL (e.g. `http://192.168.124.12:1180`) |
| `FRESHRSS_API_USER` | API username |
| `FRESHRSS_API_PASSWORD` | API password |

> 💡 Environment variables can be configured in `scripts/.env`. The script loads them automatically.

## Usage

```bash
python3 scripts/freshrss.py <command> [options]
```

Common options for reading commands: `--count N` (default 20), `-v`/`--verbose` (include summary text).

## Reading Articles

### Recent articles
```bash
python3 scripts/freshrss.py recent --count 10
python3 scripts/freshrss.py recent --count 5 -v    # with summary
```

### Unread articles
```bash
python3 scripts/freshrss.py unread --count 20
```

### Articles from a specific feed
```bash
python3 scripts/freshrss.py feed --url "https://example.com/rss" --count 10
```

### Articles from a category
```bash
python3 scripts/freshrss.py category --name "Technology" --count 15
```

### Starred articles
```bash
python3 scripts/freshrss.py starred --count 20
```

### Search articles
Title only (fast, default 200 articles scanned):
```bash
python3 scripts/freshrss.py search -k "keyword"
```
Title + content (slower, use `--batch` to control scan size):
```bash
python3 scripts/freshrss.py search -k "keyword" --deep --batch 500
```

## Feed Management

### List all subscriptions
```bash
python3 scripts/freshrss.py list-feeds
```

### List categories
```bash
python3 scripts/freshrss.py list-categories
```

### Unread counts
```bash
python3 scripts/freshrss.py unread-count
```

### Add a feed
```bash
python3 scripts/freshrss.py add-feed --url "https://example.com/feed.xml" --category "News"
```

### Move feed to another category
```bash
python3 scripts/freshrss.py move-feed --feed-id "feed/https://..." --to "NewCat" --from "OldCat"
```

### Remove a feed
```bash
python3 scripts/freshrss.py remove-feed --feed-id "feed/https://..."
```

### Mark article as read
```bash
python3 scripts/freshrss.py mark-read --item-id "tag:google.com,2005:reader/item/..."
```

### Star an article
```bash
python3 scripts/freshrss.py star --item-id "tag:google.com,2005:reader/item/..."
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
