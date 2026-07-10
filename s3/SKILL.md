---
name: s3
description: S3 兼容对象存储操作工具。支持上传、下载（含 presigned URL 下载链接生成）、删除、列表、文件元信息查询等全面存储桶操作。触发场景：用户需要上传/下载文件到 S3 存储、生成分享链接、查看存储桶文件、删除云端文件、或其他技能需要 S3 上传/下载操作。需要配置 S3_ENDPOINT、S3_BUCKET 环境变量及 AWS 凭证。
metadata:
  skill_version: "0.1.0"
---

# S3 存储操作

S3 兼容对象存储工具，支持上传、下载、生成分享链接、列表、删除、文件信息查询等全面操作。

## 使用场景

- 用户需要将文件上传到 S3 存储
- 用户需要从 S3 下载文件
- 用户需要生成文件分享链接（供他人下载或上传）
- 用户需要查看存储桶中的文件列表
- 用户需要删除存储桶中的文件
- 用户需要查询文件的元信息
- **其他 skill 需要上传/下载文件时也可优先使用本 skill**

## 配置

- **Endpoint**：环境变量 `S3_ENDPOINT`（S3 兼容存储地址）
- **Bucket**：环境变量 `S3_BUCKET`（存储桶名称）
- **Region**：环境变量 `S3_REGION`（默认 `us-east-1`）
- **凭证**：环境变量 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`（boto3 自动读取）
- **签名方式**：SigV4（presigned URL 方式上传/下载通常更兼容）
- **环境变量**：可配置 `scripts/.env` 模板文件。脚本会自动加载。
- **依赖**：Python boto3 + requests

## 调用方式

所有操作通过 `scripts/s3.py` 完成：

```
python3 scripts/s3.py <子命令> [参数]
```

### 子命令一览

| 子命令 | 功能 | 关键参数 |
|--------|------|---------|
| `upload` | 上传本地文件到 S3 | `<本地路径>` `--remote <远程路径>` `[--presigned]` |
| `download` | 从 S3 下载到本地 | `<远程路径>` `[--local <本地路径>]` |
| `gen-url` | 生成 presigned 下载/上传 URL | `<远程路径>` `[--expire <秒>]` `[--upload]` |
| `list` | 列出文件 | `[--prefix <前缀>]` `[--limit <数量>]` |
| `delete` | 删除文件 | `<远程路径>` `[-y 跳过确认]` |
| `info` | 查询文件元信息 | `<远程路径>` |

### 注意事项

- **presigned URL 上传**：部分 S3 兼容服务禁止公开读写，此时需要使用 `--presigned` 参数上传。默认先尝试 boto3 SDK 直传，失败时可回退到 presigned URL。
- **下载**：程序自动用 presigned GET URL 下载（兼容公开读取和私有桶）。
- **生成 URL**：生成的链接默认有效期 1 小时，用 `--expire` 调整（最长 7 天=604800 秒）。
- **删除需确认**：默认需要交互确认，用 `-y` 跳过。
- **路径规范**：建议按 `用途/日期_文件名` 的层级结构组织远程路径。

### Agent 使用示例

```
# 上传文件
python3 scripts/s3.py upload ./report.pdf --remote docs/2026/report.pdf
python3 scripts/s3.py upload ./bigfile.zip --presigned

# 下载文件
python3 scripts/s3.py download asr-uploads/meeting.mp3 --local ./got.mp3

# 生成分享下载链接（24 小时有效）
python3 scripts/s3.py gen-url share/data.csv --expire 86400

# 生成上传链接（供他人上传）
python3 scripts/s3.py gen-url uploads/target.zip --upload --expire 7200

# 列出文件
python3 scripts/s3.py list --prefix asr-uploads/
python3 scripts/s3.py list --limit 100

# 删除文件
python3 scripts/s3.py delete old/temp.txt -y

# 查看文件信息
python3 scripts/s3.py info backup/db.json
```

## 与其他 skill 集成

- 其他需要存储文件的 skill 应优先使用本 skill 而非自己实现 S3 逻辑
