---
name: deepseek_balance
description: 查询 DeepSeek 开放平台账户余额与 API 使用情况。触发场景：用户问"DeepSeek 余额""API 余额""还有多少钱""还剩多少额度"。需要 DEEPSEEK_APIKEY 环境变量。
metadata:
  skill_version: "0.1.0"
---

# DeepSeek 开放平台余额查询

查询 DeepSeek 开放平台账户余额。

## 触发条件

用户提及以下任一关键词时使用此 skill：
- "DeepSeek 余额" / "deepseek 余额" / "DS 余额" / "ds 余额"
- "查 DeepSeek 余额" / "查余额"
- "DeepSeek 还有多少钱"
- "deepseek balance"

## 使用方式

```bash
python3 scripts/check_balance.py [--output results.csv]
```

脚本从环境变量 `DEEPSEEK_APIKEY` 读取 API Key，输出原始 JSON 到 stdout。Agent 读取 JSON 后自行解析告知用户余额情况。

> 💡 环境变量可配置 `scripts/.env` 模板文件。脚本会自动加载。

## 输出格式

脚本输出原始 JSON（不格式化）：
```json
{"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"number","granted_balance":"number","topped_up_balance":"number"}]}
```

## 字段说明

| 字段 | 说明 |
|------|------|
| `is_available` | 当前账户是否有余额可供 API 调用 |
| `total_balance` | 总余额 |
| `granted_balance` | 赠送余额 |
| `topped_up_balance` | 充值余额 |

## CSV 记录

使用 `--output <路径>` 可指定 CSV 输出路径。每次查询结果会追加记录到该 CSV 文件，包含字段：`datetime`, `is_available`, `currency`, `total_balance`, `granted_balance`, `topped_up_balance`。不传入 `--output` 时只输出 JSON 到 stdout。

用户要求查看历史记录时，读取 `--output` 指定的 CSV 文件。不要求查看不要读取。

## 报价纪律

报价时**只报价格表格**，不附加任何换算建议（如"能跑多少 tokens""余额够用多久"等）。用户问了才回答。

## 💰 计价（元/百万 tokens）

| 模型 | 缓存命中 | 缓存未命中 | 输出 |
|------|----------|-----------|------|
| deepseek-v4-flash | 0.02 | 1 | 2 |
| deepseek-v4-pro | 0.025 | 3 | 6 |

## 📋 报价纪律

**用户不问就不说定价。** 查余额时只报余额数字，不主动提价格、不附加换算建议、不提醒峰谷策略。用户问了价格才报价。

## 参考资料

- 官方文档: https://api-docs.deepseek.com/zh-cn/api/get-user-balance
