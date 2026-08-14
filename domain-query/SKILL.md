---
name: domain-query
description: >-
  Domain name multi-query tool — one-shot lookup of ICP filing (备案) and WHOIS
  registration info for any domain. Triggered whenever the user mentions
  "domain lookup", "ICP", "备案", "WHOIS", "registration info", "check this
  domain", "domain details", "域名查询", "查一下这个域名", or
  simply pastes a domain and asks "check it" or "查一下". Trigger even for
  one-line requests.
metadata:
  skill_version: "1.0.1"
---

# Domain Query

Queries the [接口盒子 API](https://apihz.cn) for ICP filing and WHOIS registration information for any domain — all in one command.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `JKHZ_ID` | 接口盒子 (apihz.cn) user ID |
| `JKHZ_KEY` | 接口盒子 API key |

The script loads these from `~/.wmyskills/.env` (shared across skills) automatically; a `scripts/.env` in the script directory takes priority if present. Use `scripts/.env.example` as the template — add the variables to `~/.wmyskills/.env`, never overwriting an existing file.

## Requirements

```bash
pip install python-dotenv
```

## Usage

Script: `scripts/domain_query.py`

### Query all (ICP + WHOIS)
```bash
python scripts/domain_query.py example.com
```

### WHOIS live query (skip cache)
```bash
python scripts/domain_query.py example.com --live
```

### Query only one item
```bash
python scripts/domain_query.py example.com --only icp
python scripts/domain_query.py example.com --only whois
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

## Arguments

| Arg | Description |
|-----|-------------|
| `domain` | Domain name (required), e.g. `example.com` |
| `--live` | WHOIS live query (bypasses cache; cached is faster) |
| `--only` | Query only one of: `icp`, `whois` |
| `--json` | Output raw JSON (debugging) |

## Notes

- Default behavior queries both items at once
- WHOIS cache mode is faster; `--live` gives the freshest data but takes longer
