---
name: deepseek-balance
description: Query DeepSeek Open Platform account balance. Triggered when user asks "DeepSeek balance", "API balance", "how much credit left", "check my quota". Requires DEEPSEEK_APIKEY env var.
---

# DeepSeek Open Platform Balance Query

Use this skill when the user asks about their DeepSeek account balance.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Usage

The script reads the API key from the `DEEPSEEK_APIKEY` environment variable (or `.env` file in the same directory), calls the balance API, and outputs raw JSON to stdout.

```bash
python scripts/check_balance.py
```

## Output Format

The script outputs raw JSON (no pretty-printing):

```json
{"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"110.00","granted_balance":"10.00","topped_up_balance":"100.00"}]}
```

## Fields

| Field | Description |
|-------|-------------|
| `is_available` | Whether the balance is sufficient for API calls |
| `currency` | Currency type, `CNY` or `USD` |
| `total_balance` | Total available balance (including granted + topped-up) |
| `granted_balance` | Unexpired granted balance |
| `topped_up_balance` | Topped-up balance |

## Notes

- Only report the balance number. Do not volunteer pricing or conversion advice (e.g. "how many tokens this covers") unless the user asks.
- The `DEEPSEEK_APIKEY` environment variable must be set (or configured in `.env`).
