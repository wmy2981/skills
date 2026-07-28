---
name: domain-query
description: >-
  Domain name multi-query tool — one-shot lookup of ICP filing (备案), WHOIS
  registration info, and WeChat block status (微信防红) for any domain. Triggered
  whenever the user mentions "domain lookup", "ICP", "备案", "WHOIS",
  "registration info", "check this domain", "domain details", "微信防红",
  "域名查询", "查一下这个域名", "帮我查这个域名", or simply pastes a domain and
  asks "check it" or "查一下". Trigger even for one-line requests.
---

# Domain Query

Queries the [接口盒子 API](https://apihz.cn) for ICP filing, WHOIS registration information, and WeChat block detection for any domain — all in one command.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `JKHZ_ID` | 接口盒子 (apihz.cn) user ID |
| `JKHZ_KEY` | 接口盒子 API key |

The script loads these from `scripts/.env` automatically. See `scripts/.env.example` for the template.

## Requirements

```bash
pip install python-dotenv
```

## Usage

Script: `scripts/domain_query.py`

### Query all (ICP + WHOIS + WeChat check)
```bash
python scripts/domain_query.py example.com
```

### Specify a custom URL for WeChat check
```bash
python scripts/domain_query.py example.com --url https://example.com/page
```

### WHOIS live query (skip cache)
```bash
python scripts/domain_query.py example.com --live
```

### Query only one item
```bash
python scripts/domain_query.py example.com --only icp
python scripts/domain_query.py example.com --only whois
python scripts/domain_query.py example.com --only wxfh
```

### Output raw JSON
```bash
python scripts/domain_query.py example.com --json
```

## Query Items

| Item | Content |
|------|---------|
| 📋 ICP Filing (ICP 备案) | Filing number, organization name, type, review date |
| 📝 WHOIS | Registrar, registration/expiration dates, DNS servers, domain status, etc. |
| 🔗 WeChat Block Status (微信防红) | Whether the URL is blocked / safe in WeChat |

## Arguments

| Arg | Description |
|-----|-------------|
| `domain` | Domain name (required), e.g. `example.com` |
| `--url` | Target URL for WeChat block check; defaults to `https://{domain}` |
| `--live` | WHOIS live query (bypasses cache; cached is faster) |
| `--only` | Query only one of: `icp`, `whois`, `wxfh` |
| `--json` | Output raw JSON (debugging) |

## Notes

- Default behavior queries all three items at once
- WHOIS cache mode is faster; `--live` gives the freshest data but takes longer
- WeChat check URL defaults to `https://` + domain; use `--url` for a specific page path
