---
name: linkgo
description: Manage a remote LinkGo v3 instance via its HTTP API. Use when the user wants to list/add/edit/delete service cards, modify page settings, upload icons, change passwords, export/import config, or query debug info on the LinkGo navigation page. Also triggers for "导航页", "服务卡片", "LinkGo", "add card", "edit card", "sublink" and similar card management tasks.
metadata:
  skill_version: "2.0.0"
---

# LinkGo v3 远程管理

通过 HTTP API 管理 LinkGo v3 实例的服务卡片、页面配置和系统设置。

## 实例信息

从环境变量读取：
- `LINKGO_HOST` — 实例地址，如 `http://192.168.124.12:80`
- `LINKGO_PASSWORD` — 管理密码

> 💡 环境变量可配置 `scripts/.env` 模板文件。脚本会自动加载。

## 使用方式

所有操作通过 `python3 scripts/linkgo.py` 执行。

### 命令速查

```bash
# 连通性测试
python3 scripts/linkgo.py ping

# ─── 查询 ──────────────────────────────────────────────

# 列出启用的服务卡片（默认）
python3 scripts/linkgo.py list

# 列出所有服务卡片（含禁用）
python3 scripts/linkgo.py list --all

# 查询指定 id 的卡片
python3 scripts/linkgo.py list --id agent

# ─── 卡片管理 ──────────────────────────────────────────

# 添加卡片（JSON 字符串参数）
python3 scripts/linkgo.py add '{"id":"myservice","title":"我的服务","href":"http://example.com","icon":"static/icon/link.svg","displayAddress":"example.com","description":"服务描述","status":1}'

# 编辑卡片（按 id 定位，只传要改的字段）
python3 scripts/linkgo.py edit myservice '{"title":"新标题","href":"http://new.example.com"}'

# 删除卡片
python3 scripts/linkgo.py delete myservice

# 启用/禁用卡片
python3 scripts/linkgo.py enable myservice
python3 scripts/linkgo.py disable myservice

# ─── 页面设置 ──────────────────────────────────────────

# 修改页面设置
python3 scripts/linkgo.py page '{"title":"新标题","searchEnabled":0}'

# ─── 图标 ──────────────────────────────────────────────

# 上传图标
python3 scripts/linkgo.py upload-icon /path/to/icon.svg

# 列出可用图标
python3 scripts/linkgo.py icons

# ─── 配置导入导出 ──────────────────────────────────────

# 导出配置到文件
python3 scripts/linkgo.py export -o web.json

# 导出到 stdout
python3 scripts/linkgo.py export

# 导入配置（覆盖全部数据）
python3 scripts/linkgo.py import web.json

# 恢复默认配置
python3 scripts/linkgo.py reset

# ─── 密码与调试 ────────────────────────────────────────

# 修改管理密码
python3 scripts/linkgo.py change-password <旧密码> <新密码>

# 调试信息
python3 scripts/linkgo.py debug
```

## 服务卡片字段

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `id` | ✅ | string | 唯一标识，**只能包含英文字母和数字**，创建后不可修改 |
| `title` | ✅ | string | 显示标题，支持变量替换 |
| `href` | ✅ | string | 点击跳转地址，支持 `javascript:` 伪协议 |
| `icon` | ❌ | string | 图标路径（如 `static/icon/home.svg`），上传后可用 |
| `displayAddress` | ❌ | string | 卡片上显示的地址文本 |
| `description` | ❌ | string | 描述文本，支持变量替换和 HTML |
| `status` | ❌ | int | `1`=启用（默认），`0`=禁用 |

### description 中的变量语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `{link:URL,文本}` | 普通链接 | `{link:https://example.com,示例}` |
| `{sublink:URL,文本}` | 蓝色加粗链接 | `{sublink:https://example.com,详情}` |
| `{modallink:URL,标题,文本}` | iframe 模态框链接 | `{modallink:http://x:8080,服务,查看}` |
| `{tip:内容}` | 搜索关键词提示（不显示） | `{tip:关键词1 关键词2}` |
| `{space}` | 间隔空格 | `第一行{space}第二行` |
| `{icon_path}` | 图标目录 | `{icon_path}myicon.svg` → `/static/icon/myicon.svg` |
| `{hostname}` | 动态主机名 | `http://{hostname}:8088` |

### 动态变量（前端自动替换）

`{host}` / `{hostname}` / `{port}` / `{protocol}` / `{pathname}` / `{href}` / `%s`

## 操作说明

### 编辑卡片

`edit` 是增量合并——只传要改的字段，其他保持不变。可一次改多个字段：

```bash
python3 scripts/linkgo.py edit myservice '{"title":"新标题","description":"新描述{space} {sublink:https://x.com,新链接}"}'
```

### 添加 sublink 到已有卡片

读取当前 description → 追加 `{sublink:URL,名称}` → 编辑写回：

```bash
# 1. 查看当前卡片
python3 scripts/linkgo.py list --id agent

# 2. 拼接新的 description（在 tip 之前插入 sublink）
# 3. edit 写回
python3 scripts/linkgo.py edit agent '{"description":"原内容 {sublink:https://new.url,新链接}{tip:原有关键词}"}'
```

### 备份

导入、恢复默认、编辑操作前建议先备份：

```bash
python3 scripts/linkgo.py export -o backup_$(date +%Y%m%d_%H%M%S).json
```

## 完整 API 文档

如需了解 LinkGo v3 的全部 API 接口、变量替换系统、前端模块和部署配置，参阅 `references/api.md`。

## 注意事项

- `import` 和 `reset` 会**覆盖全部数据**，操作前务必备份
- `reset` 不可逆，会清空所有自定义卡片
- 图标上传限制 1MB，格式：SVG/PNG/JPG/JPEG/GIF/WEBP/ICO
- 密码修改会自动更新服务器端 `config.php`
