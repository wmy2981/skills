---
name: enterprise-info
description: >-
  Chinese enterprise registration info lookup — queries the 接口盒子 API for
  company registration details (工商信息) by company name or Unified Social Credit
  Code (统一社会信用代码). Triggered whenever the user asks about a Chinese company:
  "查公司", "查企业", "企业信息", "工商信息", "查一下XX公司",
  "查XX的统一信用代码", "这家公司信息", "营业执照查询", "企业工商查询",
  "查一下这家公司", "看看这家企业", "this company info", or pastes a company
  name or credit code and asks to look it up. Supports both full company name
  and 18-digit Unified Social Credit Code.
metadata:
  skill_version: "1.0.0"
---

# Enterprise Info Query

Queries the [接口盒子 API](https://cn.apihz.cn/api/shiming/qyinfo.php) to retrieve Chinese company registration details from the official business registry.

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

Script: `scripts/query.py`

### Query by company name or credit code

```bash
python scripts/query.py "Company Name"
python scripts/query.py "91440101MA5XXXXXXX"
```

The script automatically determines success or failure. On success it prints structured key fields; on failure it prints the error reason.

## Output Fields

| Field | Description |
|-------|-------------|
| Company Name | Full registered business name |
| Unified Social Credit Code | 18-digit credit code |
| Legal Representative | Legal person name |
| Registered Capital | Registered capital (10K CNY) |
| Establishment Date | Date of founding |
| Business Status | Active / Deregistered / Revoked, etc. |
| Approval Date | Last approval date |
| Registration Authority | Registering bureau |
| Registered Address | Business address |
| Business Scope | Main business scope |
| Contact Phone | Company phone number |
| Email | Company email |
| Company Type | LLC, etc. |
| Taxpayer Qualification | General taxpayer / small-scale, etc. |
| Personnel Scale | Number of insured employees |
| Shareholder Info | Major shareholders |

Additional fields shown when available: paid-in capital, industry, operating period, website, historical names, key personnel.

## Error Handling

- HTTP request failure → network error message
- API returns code=400 → specific error (e.g. "company name not found")
- Env vars not set → configuration missing prompt
