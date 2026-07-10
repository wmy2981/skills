---
name: zurl
description: 管理 Zurl 短链接服务。当用户需要创建短链接、缩短 URL、编辑/删除/查看短链接、搜索短链、批量管理短链时使用。即使用户只说"缩短这个链接""生成短链""把这个转成短链接"等也要触发。
metadata:
  skill_version: "1.0.0"
---

# Zurl 短链接管理

短链接管理服务，API 地址从环境变量 `ZURL_APIURL` 获取。

## 重要规则

### 1. API 接入规则
API 地址从环境变量 `ZURL_APIURL` 获取，禁止在调用中硬编码地址。创建/编辑短链后，**必须展示所有配置的短链接域名**（通过环境变量 `ZURL_DISPLAY_URLS` 配置，逗号分隔，脚本返回的 `short_links` 字段自动包含所有域名下的完整链接）。

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `ZURL_APIURL` | ✅ | Zurl API 地址，如 `http://192.168.124.12:3088` |
| `ZURL_TOKEN` | ❌ | API 认证 Token（如服务端开启了鉴权则必填） |
| `ZURL_DISPLAY_URLS` | ❌ | 逗号分隔的展示域名列表，默认使用上一行的 API 地址加两个公网域名 |

> 💡 环境变量可配置 `scripts/.env` 模板文件。脚本会自动加载。

### 3. 自动生成短链接代号
用户要求缩短 URL 但未指定短链接代号时，脚本自动生成 **4 位随机字符**（大小写字母 + 数字）。

### 4. 新建短链不设标题
新建短链时，title 参数传空字符串 `""`，让 Zurl 自动抓取页面标题。Agent 不要自行填写标题。

### 5. 二维码使用展示域名
如果生成短链后还需要生成二维码，**在用户不指定域名的情况下，使用 `ZURL_DISPLAY_URLS` 中的第一个域名作为二维码内容**。

## 脚本调用

脚本路径：`scripts/zurl_api.py`
Token 从环境变量 `ZURL_TOKEN` 获取。

### 创建短链接
```bash
python3 scripts/zurl_api.py shorten <long_url> [short_url] [title] [description] [ttl_days]
```
| 参数 | 必填 | 说明 |
|---|---|---|
| `long_url` | ✅ | 原始长链接 |
| `short_url` | ❌ | 自定义短链接代号，不传自动生成4位随机字符 |
| `title` | ❌ | 标题 |
| `description` | ❌ | 描述 |
| `ttl_days` | ❌ | 有效期（天） |

### 更新短链接
```bash
python3 scripts/zurl_api.py update <id> [long_url] [short_url] [title] [description] [ttl_days]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `id` | ✅ | 短链接数据库 ID（从 list/search 获取） |
| `long_url` | ✅ | 原始长链接 |
| `short_url` | ✅ | 短链接代号 |
| `title` | ❌ | 标题 |
| `description` | ❌ | 描述 |
| `ttl_days` | ❌ | 有效期（天） |

**⚠️ update 注意事项：**
- `long_url` 和 `short_url` 为 **必填参数**，不传会导致 422 错误
- 可选字段（title/description/ttl_days）传空字符串会**清空**对应字段，不想修改的字段直接不传或用 `""` 占位
- `short_url` 传空字符串会导致 500 错误，脚本已过滤空值
- 更新不存在的 ID 返回 404

### 删除单个短链接
```bash
python3 scripts/zurl_api.py delete <short_url>
```

### 批量删除
```bash
python3 scripts/zurl_api.py delete_batch <id1,id2,...>
```

### 查看列表
```bash
python3 scripts/zurl_api.py list [page] [limit]
```

### 搜索
```bash
python3 scripts/zurl_api.py search <keyword> [filter_type]
```
- `filter_type`：`all` / `long_url` / `short_url` / `title`

### 获取 URL 元数据
```bash
python3 scripts/zurl_api.py metadata <url>
```
返回目标网页的标题和描述。

## API 端点验证状态

| API | 状态 |
|---|---|
| `/api/shorten_url` (POST JSON) | ✅ 通过 |
| `/api/update_url/{id}` (POST JSON) | ✅ 通过 |
| `/api/delete/url` (POST form) | ✅ 通过 |
| `/api/delete/urls` (POST JSON) | ✅ 通过 |
| `/api/urls` (GET) | ✅ 通过 |
| `/api/search` (POST JSON) | ✅ 通过 |
| `/api/get_url_metadata` (POST form) | ✅ 通过 |
| `/api/get_url_info` (POST form) | ❌ 500，已移除 |
| `/api/import` (multipart) | ❌ 未验证，已移除 |

## 返回格式

成功：`{"code": 200, "msg": "...", "data": {...}, "short_links": [...]}`
失败：`{"error": true, "status": ..., "detail": {...}}`

## 输出格式

Agent 输出短链结果时按以下格式（展示域名来自 `ZURL_DISPLAY_URLS`，脚本 `short_links` 字段）：
```
✅ 短链接创建成功

短链接：
  {domain1}/{short_url}
  {domain2}/{short_url}
  ...

原始链接：{long_url}
标题：{title}
```
