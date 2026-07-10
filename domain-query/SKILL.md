---
name: domain-query
description: 域名全查询工具，一键查询域名的ICP备案信息、WHOIS注册信息（缓存/实时）、微信防红检测状态。当用户提到"域名查询""域名备案""ICP查询""WHOIS""域名信息""查一下这个域名""域名备案号""注册信息""微信防红""域名检测"时触发。即使用户只是发了一个域名说"查一下""帮我查"也要触发。
metadata:
  skill_version: "1.0.0"
---

# 域名全查询

基于接口盒子 API，一站式查询域名的 ICP 备案、WHOIS 注册信息和微信防红检测。

## 环境变量

| 变量 | 说明 |
|------|------|
| `JKHZ_ID` | 接口盒子用户 ID |
| `JKHZ_KEY` | 接口盒子 API Key |

## 调用方式

脚本路径：`scripts/domain_query.py`。环境变量可配置 `scripts/.env` 模板文件，脚本会自动加载。

### 查询全部（ICP + WHOIS + 微信防红）

```bash
python3 scripts/domain_query.py example.com
```

### 指定微信防红检测 URL

```bash
python3 scripts/domain_query.py example.com --url https://example.com/page
```

### WHOIS 实时查询（不使用缓存）

```bash
python3 scripts/domain_query.py example.com --live
```

### 只查询某一项

```bash
python3 scripts/domain_query.py example.com --only icp
python3 scripts/domain_query.py example.com --only whois
python3 scripts/domain_query.py example.com --only wxfh
```

### 输出原始 JSON

```bash
python3 scripts/domain_query.py example.com --json
```

## 返回信息

| 查询项 | 包含内容 |
|--------|----------|
| 📋 ICP 备案 | 备案号、单位名称、类型、审核时间 |
| 📝 WHOIS | 注册商、注册日期、到期日期、DNS 服务器、域名状态等完整注册信息 |
| 🔗 微信防红 | URL 在微信中是否被拦截/安全 |

## 参数说明

| 参数 | 说明 |
|------|------|
| `domain` | 域名（必填），如 `example.com` |
| `--url` | 微信防红检测的目标 URL，默认 `https://{domain}` |
| `--live` | WHOIS 实时查询，绕过缓存（默认使用缓存，速度更快） |
| `--only` | 只查询 `icp`、`whois`、`wxfh` 其中之一 |
| `--json` | 输出原始 JSON 数据（调试用） |

## 注意事项

- 默认一次性查询全部三项
- WHOIS 缓存模式速度更快，实时模式（`--live`）数据最新但较慢
- 微信防红检测的 URL 默认为 `https://` + 域名，如有具体页面路径请用 `--url` 指定
