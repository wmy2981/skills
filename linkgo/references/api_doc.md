# LinkGo_v3文档

# LinkGo v3 用户文档

> 版本：v3_20250823 | 最后更新：2025年8月28日

---

## 目录

1. [项目概述](#1-项目概述)
2. [快速开始](#2-快速开始)
3. [用户主页（index.html）](#3-用户主页indexhtml)
4. [管理后台（admin.html）](#4-管理后台adminhtml)
5. [API 接口详解](#5-api-接口详解)
6. [配置文件详解](#6-配置文件详解)
7. [变量替换系统](#7-变量替换系统)
8. [前端模块说明](#8-前端模块说明)
9. [主题系统](#9-主题系统)
10. [部署与安全](#10-部署与安全)
11. [常见问题](#11-常见问题)

---

## 1. 项目概述

LinkGo 是一个**自托管的服务导航页面系统**，提供一个可自定义的"服务卡片导航"主页，集中展示和组织你的各类内网服务链接。系统由 **PHP 后端 + 纯前端 HTML/JS** 组成，无需数据库，所有数据存储在 JSON 文件中。

### 核心特性

- 🎴 **服务卡片导航**：以卡片网格形式展示所有服务，带图标、描述、跳转链接
- 🔍 **实时搜索过滤**：根据标题和描述字段实时过滤服务卡片
- 🎨 **自动主题切换**：跟随系统深色/浅色模式，也支持强制切换
- 📝 **变量替换引擎**：在标题、描述、链接等位置使用变量动态替换
- 📦 **iframe 模态框**：支持在弹出模态框中预览被链接的页面
- 🔗 **连通性测试**：前端自动检测各服务卡片的链接是否可达
- 🔐 **管理后台**：密码保护，支持增删改查服务卡片、修改密码
- 🖼️ **图标管理**：支持上传自定义图标（SVG/PNG/JPG/GIF/WEBP/ICO）
- 💾 **自动备份**：每次保存配置自动生成时间戳备份
- 🔄 **配置文件初始化**：一键恢复默认配置

### 技术栈

|层|技术|
| ---------------| --------------------------------------------|
|后端|PHP（纯原生，无框架）|
|前端|原生 HTML/CSS/JS + TailwindCSS（CDN）|
|数据存储|JSON 文件 (`json/web.json`)|
|Markdown 渲染|marked.js + highlight.js + KaTeX + Mermaid|

---

## 2. 快速开始

### 2.1 部署要求

- **Web 服务器**：Apache / Nginx / IIS（推荐 IIS，项目自带 `web.config`）
- **PHP**：≥ 7.4
- **文件权限**：`json/`​ 目录和 `api/config.php` 需 PHP 进程可读写
- 无需数据库

### 2.2 部署步骤

1. 将项目所有文件上传到 Web 服务器的网站根目录
2. 确保 `json/web.json`​ 文件存在（不存在则复制 `static/default_web.json` 并重命名）
3. 确保 `api/config.php` 可被 PHP 进程读写
4. 确保以下目录存在且可写：

   - ​`json/` — 数据文件
   - ​`_backup/` — 备份目录
   - ​`static/icon/` — 图标目录
   - ​`log/api/` — 日志目录
5. 访问首页 → 即可看到服务卡片

### 2.3 初始密码

默认管理密码：**​`123`​**

> ⚠️ **部署后第一件事：修改默认密码！**

---

## 3. 用户主页（index.html）

访问网站根目录即进入用户主页。主页展示所有启用的服务卡片。

### 3.1 页面结构

```
┌─────────────────────────────────────────┐
│              页面标题                      │
│         [🔍 搜索框]                       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 服务  │ │ 服务  │ │ 服务  │ │ 服务  │   │
│  │ 卡片  │ │ 卡片  │ │ 卡片  │ │ 卡片  │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
│              底部文本                      │
└─────────────────────────────────────────┘
```

### 3.2 搜索功能

- 实时过滤：在搜索框输入关键词，卡片列表即时过滤
- 匹配范围：服务卡片的 **标题（title）**  和 **描述（description）**
- 搜索框右侧有清除按钮
- ​`searchEnabled`​ 设为 `0` 可全局禁用搜索

### 3.3 服务卡片

每张卡片包含：

|元素|说明|
| --------------| ---------------------------------------------------|
|图标|显示在卡片左上角，图标加载失败时使用默认 link.svg|
|标题|加粗显示的服务名称|
|描述|正文描述，支持 Markdown 和变量替换|
|显示地址|灰色小字，显示服务 URL 或自定义地址|
|连通性指示器|右上角小圆点：绿色=连通，红色=不可达，灰色=测试中|
|点击行为|点击卡片跳转到对应链接|

### 3.4 底部文本

页面底部显示来自 `web.json`​ 中 `endTextContent` 数组的内容，支持变量替换。默认包含：

- 指向管理后台的链接（`{link:/admin.html,管理}`）
- 项目名称和版本号

### 3.5 主题切换

​`applyTheme.js` 自动检测系统深色模式偏好，也支持手动强制切换：

|URL 参数|效果|
| ----------| ----------------------|
|​`?theme=light`|强制浅色模式（保存）|
|​`?theme=dark`|强制深色模式（保存）|
|​`?theme=system`|跟随系统（保存）|
|​`?theme=light_ls`|临时浅色（不保存）|
|​`?theme=dark_ls`|临时深色（不保存）|

---

## 4. 管理后台（admin.html）

访问 `/admin.html` 进入管理后台。首次需要输入管理密码。

### 4.1 密码验证

- 弹窗输入密码，密码正确后进入管理界面
- 点击"忘记密码"可查看密码重置方法（需服务器权限）
- 密码存储在 `api/config.php`​ 的 `ADMIN_PASSWORD` 常量中

### 4.2 管理界面布局

```
┌───────────────────────────────────────┐
│  管理                    [格式指南] [高级设置] [退出编辑]  │
├───────────────────────────────────────┤
│  📋 JSON编辑器（可折叠/禁用）            │
├───────────────────────────────────────┤
│  📝 添加服务卡片表单                    │
│  标题: [___] 图标: [选择] [上传]        │
│  跳转地址: [___] [预览]                │
│  描述: [___] ID: [___]               │
│  显示地址: [___] 状态: [启用/禁用]     │
│  [添加/更新]                          │
├───────────────────────────────────────┤
│  📋 服务卡片列表                       │
│  ┌─────────────────────────────────┐ │
│  │ [图标] 标题 | 地址 | [编辑][删除]  │ │
│  │ [图标] 标题 | 地址 | [编辑][删除]  │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘
```

### 4.3 服务卡片字段

|字段|必填|说明|
| ------| ------| --------------------------------------------------------|
|**标题 (title)**|✅|服务名称，支持变量替换|
|**跳转地址 (href)**|✅|点击卡片跳转的 URL，支持 `javascript:` 伪协议|
|**图标 (icon)**|❌|图标文件路径，从 `static/icon/` 目录选择或自行上传|
|**显示地址 (displayAddress)**|❌|卡片上显示的 URL 文本，支持变量替换|
|**描述 (description)**|❌|卡片描述文本，支持变量替换和 HTML 标签|
|**ID**|✅|服务唯一标识，用于程序内部引用，创建后不可在编辑时修改|
|**状态 (status)**|✅|​`1`​=启用（主页显示），`0`=禁用（主页隐藏）|

### 4.4 服务卡片操作

- **添加**：填写表单点击"添加"按钮
- **编辑**：点击列表中某行的"编辑"按钮，表单自动填充数据，修改后点"更新"
- **删除**：点击"删除"按钮，弹出模态框确认后删除
- **预览**：点击地址旁的"预览"按钮，在模态框中 iframe 加载目标 URL
- **图标选择**：点击"选择"按钮，弹出模态框显示 `static/icon/` 下所有可用图标
- **图标上传**：点击"上传"按钮选择本地图片文件，支持 JPG/PNG/GIF/SVG/WEBP/ICO，最大 1MB
- **图标刷新**：重新扫描图标目录

### 4.5 JSON 编辑器

- 直接编辑 `web.json` 原始 JSON 内容
- 支持语法高亮
- 可**折叠**：点击标题栏切换显示/隐藏
- 可在高级设置中**禁用**整个 JSON 编辑器
- 修改后需点击"提交 JSON"保存
- 折叠状态下，通过表单操作修改的内容会自动同步到底层数据

### 4.6 高级设置面板

|功能|说明|
| ------| --------------------------------------------------|
|**修改管理密码**|输入旧密码+新密码，直接更新 `config.php`|
|**下载配置文件**|下载当前 `web.json` 文件到本地|
|**配置文件初始化**|将 `web.json`​ 恢复为 `default_web.json` 的内容，要求再次输入管理密码确认|
|**禁用 JSON 编辑器**|勾选后管理页面不再显示 JSON 编辑器（防止误操作）|

---

## 5. API 接口详解

所有 API 均位于 `api/` 目录下，为 PHP 脚本。

### 5.1 获取显示数据（公开）

```
GET /api/get_show_data.php
```

无需认证。返回主页需要的数据（只含启用服务）。

**响应示例：**

```json
{
  "success": true,
  "data": {
    "page": {
      "title": "我的导航",
      "searchEnabled": 1,
      "endTextContent": ["{link:/admin.html,管理}"]
    },
    "services": [
      {
        "id": "svc01",
        "title": "ExampleService",
        "href": "http://localhost:8080",
        "icon": "static/icon/home.svg",
        "displayAddress": "localhost:8080",
        "description": "AI助手平台",
        "status": 1
      }
    ]
  }
}
```

注意：`status`​ 为 `0` 的服务不会出现在返回结果中。

### 5.2 加载完整数据（需认证）

```
GET /api/load_data.php
```

**请求头：**

```
X-Admin-Password: <管理密码>
```

**成功响应：**  返回 `json/web.json` 的完整内容（含所有服务，包括禁用的）。

**失败响应 (401)：**

```json
{"error": "Unauthorized access"}
```

### 5.3 更新数据（需认证）

```
POST /api/update_json.php
Content-Type: application/json
```

**请求体：**

```json
{
  "password": "<管理密码>",
  "content": "<JSON 字符串>"
}
```

**流程：**

1. 验证密码
2. 自动备份当前 `web.json`​ 到 `_backup/web_json_backup_<时间戳>.json`
3. 验证 JSON 中每个服务的 `id` 不为空
4. 写入新数据

**初始化请求（恢复默认）：**

```json
{
  "password": "<管理密码>",
  "content": "INITIALIZE_WEB_JSON"
}
```

会先清空 `_backup/`​ 目录，然后从 `static/default_web.json`​ 读取模板数据写入 `web.json`。

### 5.4 修改密码（需认证）

```
POST /api/change_password.php
Content-Type: application/json
```

**请求体：**

```json
{
  "old_password": "<当前密码>",
  "new_password": "<新密码>"
}
```

- 新密码长度至少 3 个字符
- 通过正则替换 `config.php`​ 中的 `ADMIN_PASSWORD` 定义行
- 操作记录到 `log/api/password_change_<日期>.log`

### 5.5 重置密码（仅限本地）

```
GET /api/reset_password.php
```

⚠️ **仅允许** **​`127.0.0.1`​**​ **访问**。生成随机 8 位小写字母+数字密码并更新 `config.php`，返回新密码文本。

**使用方式：**

```bash
# 在服务器上执行
curl http://127.0.0.1/api/reset_password.php
```

### 5.6 上传图标（需认证）

```
POST /api/upload_icon.php
Content-Type: multipart/form-data
X-Admin-Password: <管理密码>
```

**表单字段：**

- ​`icons`：文件字段，支持多文件上传

**限制：**

- 格式：SVG、PNG、JPG、JPEG、GIF、WEBP、ICO
- 大小：单个文件最大 1MB
- 上传至 `static/icon/` 目录

**响应：**

```json
{
  "success": true,
  "uploaded": ["new-icon.svg"],
  "count": 1,
  "duplicates": [],
  "errors": []
}
```

### 5.7 获取图标列表（需认证）

```
GET /api/get_icons.php
X-Admin-Password: <管理密码>
```

**响应：**

```json
{
  "success": true,
  "icons": ["admin.svg", "home.svg", "link.svg", ...]
}
```

扫描 `static/icon/` 目录，返回所有图片文件名。

### 5.8 调试信息

```
GET /api/debugInfo.php
```

返回服务器和客户端的调试信息：

```json
{
  "serverIpPort": "127.0.0.1:80",
  "requestUrl": "http://example.com/",
  "clientIp": "10.0.0.5",
  "userAgent": "Mozilla/5.0 ...",
  "Time": "2025-08-28 15:30:00"
}
```

### 5.9 认证方式

所有需要认证的 API 使用以下两种方式之一：

|接口|认证方式|
| ------| --------------------|
|​`load_data.php`|HTTP Header: `X-Admin-Password`|
|​`update_json.php`|POST Body: `password` 字段|
|​`change_password.php`|POST Body: `old_password` 字段|
|​`upload_icon.php`|HTTP Header: `X-Admin-Password`|
|​`get_icons.php`|HTTP Header: `X-Admin-Password`|

---

## 6. 配置文件详解

### 6.1 `api/config.php` — 主配置

```php
<?php
// 禁止直接访问
if (basename($_SERVER['SCRIPT_FILENAME']) == basename(__FILE__)) {
    header('HTTP/1.0 403 Forbidden');
    die('Access Denied');
}

// 管理后台密码
define('ADMIN_PASSWORD', '123');

// 备份配置
define('BACKUP_DIR', dirname(__DIR__) . DIRECTORY_SEPARATOR . '_backup');

// 日志配置
define('LOG_DIR', dirname(__DIR__) . DIRECTORY_SEPARATOR . 'log/api');
define('MAX_LOG_SIZE', 10485760); // 10MB in bytes (注释写50MB但实际值是10MB)
?>
```

|常量|默认值|说明|
| ------| -------------| ------------------------------|
|​`ADMIN_PASSWORD`|​`'123'`|管理后台密码|
|​`BACKUP_DIR`|​`../_backup`|JSON 备份存储目录|
|​`LOG_DIR`|​`../log/api`|日志存储目录|
|​`MAX_LOG_SIZE`|​`10485760` (10MB)|单个日志文件最大尺寸（字节）|

⚠️ 该文件禁止直接 URL 访问（通过 `SCRIPT_FILENAME`​ 检测），仅供其他 PHP 文件 `require` 引用。

### 6.2 `json/web.json` — 数据文件

```json
{
  "page": {
    "title": "标题",
    "searchEnabled": 1,
    "endTextContent": [
      "{link:/admin.html,管理}",
      "{project_name} {link:/pages/program/markdown.php?url=docs/CHANGELOG.md&mode=basic,{project_version}}"
    ]
  },
  "services": [
    {
      "id": "admin",
      "title": "无数据",
      "href": "/admin.html",
      "icon": "static/icon/admin.svg",
      "displayAddress": "admin.html",
      "description": "web.json中没有数据，请前往管理页面进行添加。",
      "status": 1
    }
  ]
}
```

#### `page` 配置

|字段|类型|说明|
| ------| --------| ----------------------------------|
|​`title`|string|页面标题（浏览器标签页标题）|
|​`searchEnabled`|int|​`1`​=显示搜索框，`0`=隐藏|
|​`endTextContent`|array|页面底部显示的文本，支持变量替换|

#### `services[]` 配置

|字段|类型|说明|
| ------| --------| ------------------------------------|
|​`id`|string|唯一标识符，创建后不可修改|
|​`title`|string|服务名称，支持变量替换|
|​`href`|string|点击跳转地址，支持 `javascript:` 协议|
|​`icon`|string|图标文件路径（相对根目录）|
|​`displayAddress`|string|卡片上显示的小字地址|
|​`description`|string|服务描述，支持变量替换和 HTML|
|​`status`|int|​`1`​=启用，`0`=禁用（不在主页显示）|

### 6.3 `static/replaceRules.json` — 替换规则

```json
{
  "rules": [
    {"text": "{project_name}", "replace": "LinkGo"},
    {"text": "{project_version}", "replace": "v3_20250823"},
    {"text": "{space}", "replace": "&nbsp;&nbsp;&nbsp;"},
    {"text": "{link:$1,$2}", "replace": "<a href='$1'>$2</a>"},
    {"text": "{sublink:$1,$2}", "replace": "<a class='detailHref' href='$1'>$2</a>"},
    {"text": "{modallink:$1,$2,$3}", "replace": "<a class='modal-link detailHref' href='javascript:void(0)' data-href='$1' data-title='$2'>$3</a>"},
    {"text": "{tip:$1}", "replace": "<span class='tip'>$1</span>"},
    {"text": "{icon_path}", "replace": "/static/icon/"},
    {"text": "{api_path}", "replace": "/api/"},
    {"text": "{static_path}", "replace": "/static/"},
    {"text": "{pages_path}", "replace": "/pages/"},
    {"text": "{addr_prefit}", "replace": "地址："},
    {"text": "{page_info}", "replace": "<span id='page_info' style='user-select: text;'></span>"}
  ]
}
```

详见 [变量替换系统](#7-变量替换系统) 章节。

### 6.4 `static/default_web.json` — 默认配置模板

配置文件初始化时使用的模板。结构同 `web.json`​，但只包含一个引导用的 `admin` 服务卡片。

### 6.5 `web.config` — IIS 配置

```xml
<configuration>
    <system.webServer>
        <httpErrors>
            <!-- 自定义错误页映射 -->
        </httpErrors>
        <security>
            <requestFiltering>
                <hiddenSegments>
                    <!-- 隐藏 config.json, web.json, config.php 直接访问 -->
                </hiddenSegments>
            </requestFiltering>
        </security>
        <staticContent>
            <!-- .md/.ps1/.webp 的 MIME 映射 -->
        </staticContent>
    </system.webServer>
</configuration>
```

**保护的文件（禁止直接 HTTP 访问）：**

- ​`config.json`
- ​`web.json`
- ​`config.php`

---

## 7. 变量替换系统

LinkGo 内置了一套变量替换系统，让你可以在多处使用动态内容。

### 7.1 替换生效位置

|位置|支持替换|
| -------------------| --------------|
|服务卡片 **标题**|✅|
|服务卡片 **描述**|✅|
|服务卡片 **显示地址**|✅|
|服务卡片 **图标路径**|✅|
|服务卡片 **跳转地址**|✅|
|底部文本 `endTextContent`|✅|
|Markdown 文档页面|✅（PHP 端）|

### 7.2 动态变量

这些变量根据当前页面环境自动替换：

|变量|说明|示例|
| ------| -------------------| ------------|
|​`{host}`|主机名+端口|​`localhost:8080`|
|​`{hostname}`|主机名|​`localhost`|
|​`{pathname}`|当前 URL 路径|​`/index.html`|
|​`{href}`|完整 URL|​`http://localhost:8080/index.html`|
|​`{protocol}`|协议|​`http`​ 或 `https`|
|​`{port}`|端口号|​`8080`|
|​`%s`|兼容别名，等同 `{host}`|​`localhost:8080`|

### 7.3 静态变量

|变量|替换结果|
| ------| ---------------|
|​`{project_name}`|​`LinkGo`|
|​`{project_version}`|​`v3_20250823`|
|​`{addr_prefit}`|​`地址：`|
|​`{space}`|三个空格 (`&nbsp;&nbsp;&nbsp;`)|
|​`{icon_path}`|​`/static/icon/`|
|​`{api_path}`|​`/api/`|
|​`{static_path}`|​`/static/`|
|​`{pages_path}`|​`/pages/`|

### 7.4 带参数的替换（仅用于 description）

|语法|说明|示例|
| ------| ----------------------------| ------|
|​`{link:URL,文本}`|普通链接|​`{link:https://example.com,示例网站}`|
|​`{sublink:URL,文本}`|蓝色加粗链接|​`{sublink:https://example.com,详情}`|
|​`{modallink:URL,标题,文本}`|点击弹模态框 iframe 加载|​`{modallink:http://localhost:8080,我的服务,点击查看}`|
|​`{tip:内容}`|搜索提示（不显示在页面上）|​`{tip:关键词1}`|
|​`{page_info}`|页面信息占位（可选中文本）|​`{page_info}`|

### 7.5 编程调用

```javascript
// 在前端 JS 中使用
"某个文本 {project_name}".replacer()  // → "某个文本 LinkGo"
replacer("地址：{host}")               // → "地址：localhost:8080"
```

---

## 8. 前端模块说明

### 8.1 `modal.js` — 模态框组件

功能完善的响应式模态框，路径 `/static/modal.js`。

#### 基本用法

```javascript
showModal({
    title: '标题',
    content: '<p>HTML内容</p>',
    width: '500px',
    height: 'auto',
    maskOpacity: 0.5
});
```

#### 高级参数

|参数|类型|默认值|说明|
| ------| ----------| --------| -------------------------|
|​`title`|string|—|模态框标题（必填）|
|​`content`|string|—|HTML 内容（必填）|
|​`width`|string|​`'400px'`|宽度，支持 px/百分比|
|​`height`|string|​`'auto'`|高度|
|​`maskOpacity`|number|​`0.5`|遮罩透明度 (0-1)|
|​`type`|string|—|​`'iframe_address'` 显示 iframe 地址栏|
|​`customStyles`|object|—|注入自定义 CSS 变量|
|​`autoClose`|number|—|自动关闭时间（毫秒）|
|​`onOpen`|function|—|打开回调|
|​`onClose`|function|—|关闭回调|

#### 关闭模态框

```javascript
closeModal();                    // 关闭最近打开的
closeModal(modalElement);        // 关闭指定实例
```

#### iframe 支持

```javascript
showModal({
    title: '服务预览',
    content: '<iframe src="http://localhost:8080"></iframe>',
    width: '80%',
    height: '80%',
    type: 'iframe_address'
});
```

在 LinkGo 中，通过 `{modallink:URL,标题,文本}` 变量即可自动创建 iframe 模态框链接。

### 8.2 `showToast.js` — Toast 提示

路径 `/static/showToast.js`。

```javascript
showToast('操作成功', 'success');               // 绿色，2秒
showToast('操作失败', 'error');                 // 红色，5秒（error类型默认延长）
showToast('请注意', 'warning');                  // 橙色，2秒
showToast('信息', 'info');                      // 蓝色，2秒
showToast('自定义颜色', '#8B5CF6', 3000);       // 紫色，3秒
```

#### URL 参数初始化

在 URL 中添加参数，页面加载时自动弹出 Toast：

```
?toast=操作成功&type=success&duration=3000
```

### 8.3 `applyTheme.js` — 主题切换

路径 `/static/applyTheme.js`。

```javascript
applyTheme('light');        // 强制浅色模式（保存）
applyTheme('dark');         // 强制深色模式（保存）
applyTheme('system');       // 跟随系统（保存）
applyTheme('light', false); // 临时浅色（不保存）
```

详见 [主题系统](#9-主题系统) 章节。

### 8.4 `replacer.js` — 变量替换引擎

路径 `/static/replacer.js`​。加载 `replaceRules.json` 后注册全局替换规则。

```javascript
// 两种调用方式
"文本 {project_name}".replacer()
replacer("文本 {project_name}")
```

### 8.5 `debugInfo.js` — 调试信息

路径 `/static/debugInfo.js`。

```javascript
// 通过 javascript:debugInfo() 调用（如管理后台的服务卡片）
// 获取服务器/客户端信息并复制到剪贴板
debugInfo();
```

### 8.6 `contextMenu.js` — 右键菜单

路径 `/static/contextMenu.js`。自定义右键菜单组件（当前版本预留，尚未在主页面使用）。

```javascript
const menu = new ContextMenu('<ul class="_menu-list"><li>选项1</li><li>选项2</li></ul>');
menu.handleMenus().then(result => {
    console.log('点击了:', result.target.textContent);
});
```

### 8.7 `fullscreenMask.js` — 全屏遮罩

路径 `/static/fullscreenMask.js`。显示一个不可关闭的全屏遮罩层（当前版本预留）。

```javascript
showFullscreenMask({
    content: '<h1>警告</h1><p>不可关闭的遮罩</p>'
});
```

---

## 9. 主题系统

### 9.1 CSS 变量体系

LinkGo 使用 CSS 变量 + `data-theme` 属性实现主题切换：

```css
/* 系统默认浅色 */
:root {
    --card-bg: #ffffff;
    --text-primary: #1a202c;
    --text-secondary: #4a5568;
    --search-bg: #ffffff;
    --search-border: #e2e8f0;
    --search-focus: #3182ce;
    --input-bg: rgba(247,250,252,0.85);
}

/* 系统默认深色 */
@media (prefers-color-scheme: dark) {
    :root {
        --card-bg: #2d3748;
        --text-primary: #f7fafc;
        --text-secondary: #cbd5e0;
        ...
    }
}

/* 强制浅色 */
[data-theme="light"] { ... }

/* 强制深色 */
[data-theme="dark"] { ... }
```

### 9.2 优先级

1. URL 参数 `?theme=xxx` （最高优先级）
2. localStorage 中的 `theme` 键
3. 系统 `prefers-color-scheme` 媒体查询（默认）

### 9.3 自定义主题

在页面 CSS 中添加 `[data-theme="light"]`​ 和 `[data-theme="dark"]` 下的变量覆盖即可自定义颜色。

---

## 10. 部署与安全

### 10.1 Web 服务器配置

#### IIS（推荐）

项目自带 `web.config`，直接部署即可。配置了：

- 自定义错误页（401/403/404/500 → `error.php`）
- 隐藏敏感段（`web.json`​、`config.php`​、`config.json` 禁止直接 URL 访问）
- MIME 类型映射（`.md`​、`.ps1`​、`.webp`）

#### Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/linkgo;

    index index.html index.php;

    # 禁止直接访问敏感文件
    location ~ /(json/web\.json|api/config\.php) {
        deny all;
    }

    # PHP 处理
    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    # 自定义错误页
    error_page 401 403 404 500 /pages/program/error.php;
}
```

#### Apache

```apache
# .htaccess 放在项目根目录
RewriteEngine On

# 禁止访问敏感文件
<FilesMatch "^(web\.json|config\.php|config\.json)$">
    Require all denied
</FilesMatch>

# 自定义错误页
ErrorDocument 401 /pages/program/error.php?code=401
ErrorDocument 403 /pages/program/error.php?code=403
ErrorDocument 404 /pages/program/error.php?code=404
ErrorDocument 500 /pages/program/error.php?code=500
```

### 10.2 安全建议

1. **修改默认密码**：部署后立即修改 `ADMIN_PASSWORD`
2. **使用 HTTPS**：建议配合 SSL 证书使用
3. **限制管理后台访问**：可配合 Web 服务器 IP 白名单限制 `/api/` 路径
4. **文件权限**：

   ```bash
   chmod 644 api/config.php
   chmod 755 json/
   chmod 755 _backup/
   chmod 755 static/icon/
   chmod 755 log/
   ```
5. **定期备份**：每次保存配置会自动备份到 `_backup/`，建议定期下载到本地
6. **日志监控**：检查 `log/api/` 目录，发现异常 IP 访问及时处理
7. **密码重置保护**：`reset_password.php` 仅限本地访问，无法远程利用

### 10.3 备份与恢复

#### 自动备份

每次通过管理后台或 API 保存配置时，系统自动在 `_backup/` 目录创建时间戳备份：

```
_backup/
  web_json_backup_2025_08_28_15_30_00.json
  web_json_backup_2025_08_28_14_20_00.json
```

#### 手动恢复

将备份文件内容复制到 `json/web.json`，或通过管理后台的 JSON 编辑器粘贴。

#### 下载备份

通过管理后台 → 高级设置 → "下载配置文件" 下载当前配置。

---

## 11. 常见问题

### Q: 如何修改管理密码？

**方法 A（推荐）：**  登录管理后台 → 高级设置 → 修改管理密码

**方法 B：**  在服务器执行：

```bash
curl http://127.0.0.1/api/reset_password.php
```

**方法 C：**  直接编辑 `api/config.php`：

```php
define('ADMIN_PASSWORD', '你的新密码');
```

### Q: 忘记密码怎么办？

登录服务器，执行 `curl http://127.0.0.1/api/reset_password.php`，会生成新密码并直接返回。

### Q: 如何添加一个新的服务卡片？

1. 访问 `/admin.html` 登录管理后台
2. 在表单区域填写服务信息
3. 设置一个唯一 ID（如 `my-service`）
4. 点击"添加"

### Q: 如何让某个服务不在主页显示？

将该服务的 `status`​ 设为 `0`（禁用）。

### Q: 图标加载不出来怎么办？

- 确保图标文件存在于 `static/icon/` 目录
- 确保 `icon`​ 字段路径正确（如 `static/icon/myicon.svg`）
- 图标加载失败时会自动使用 `link.svg` 作为降级

### Q: 如何自定义页面标题？

编辑 `web.json`​ 中 `page.title` 字段，或通过管理后台的 JSON 编辑器修改。

### Q: 如何关闭搜索框？

将 `web.json`​ 中 `page.searchEnabled`​ 设为 `0`。

### Q: 如何更改底部文本？

编辑 `web.json`​ 中 `page.endTextContent` 数组，支持变量替换。

### Q: 支持哪些图片图标格式？

SVG、PNG、JPG、JPEG、GIF、WEBP、ICO。推荐使用 SVG（矢量，缩放不失真）。

### Q: 如何备份我的配置？

- **自动：**  每次保存自动在 `_backup/` 创建备份
- **手动：**  管理后台 → 高级设置 → 下载配置文件

### Q: 如何恢复默认配置？

管理后台 → 高级设置 → 配置文件初始化（需要输入管理密码确认）。这会删除所有自定义服务卡片！

### Q: 如何在卡片描述中使用链接？

使用变量替换语法：

```
{link:https://example.com,示例链接}            → 普通链接
{sublink:https://example.com,详细信息}         → 蓝色加粗链接
{modallink:https://example.com,标题,点击查看}  → 模态框加载
```

### Q: 服务卡片跳转可以执行 JS 吗？

可以。在 `href`​ 字段使用 `javascript:` 协议：

```
javascript:debugInfo();
```

### Q: 如何查看日志？

日志文件位于 `log/api/`​ 目录，文件命名格式 `php_log_<时间戳>.log`​。单文件超过 `MAX_LOG_SIZE`（默认 10MB）后自动创建新文件。日志内容包含时间戳、客户端IP、服务器IP、请求URL和操作描述。

### Q: 如何在外网部署此项目？

建议使用 **Nginx 反向代理** 或 **Cloudflare Tunnel**：

```nginx
# Nginx 反向代理示例
server {
    listen 443 ssl;
    server_name nav.yourdomain.com;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> ⚠️ 外网部署务必修改默认密码并启用 HTTPS！

### Q: 如何批量管理服务卡片？

直接编辑 `json/web.json`​ 文件是最快的方式。在编辑器中按 JSON 格式批量添加 `services[]` 数组元素即可。也可通过管理后台的 JSON 编辑器进行批量操作。

### Q: 支持数据库吗？

目前仅支持 JSON 文件存储，无需数据库。这使项目极其轻量，适合个人和小团队使用。如需数据库支持，可自行修改 PHP 文件。

### Q: 如何贡献或二次开发？

项目为纯 PHP + HTML/JS，无构建工具，直接修改文件即可。关键入口：

- 前端主页：`index.html`
- 管理后台：`admin.html`
- API 路由：`api/*.php`
- JS 模块：`static/*.js`
- 数据格式：`json/web.json`

---

*本文档由 AI 助手根据项目源码自动分析生成。如有疑问，请查阅项目源码或* *​`development/`​* ​ *目录下的开发者文档。*

日志文件位于 `log/api/`​ 目录，文件命名格式 `php_log_<时间戳>.log`​。单文件超过 `MAX_LOG_SIZE`
