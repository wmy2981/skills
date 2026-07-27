---
name: speech-recognition
description: 使用阿里云百炼 Fun-ASR 非实时语音识别模型将音频文件转写为文本。支持说话人分离、多语言识别、时间戳输出。触发场景：用户发送音频文件要求转文字、提到"语音识别""音频转文字""会议转写""ASR""录音转文本""说话人分离"。需要 BAILIAN_APIKEY 环境变量，以及 S3 配置（S3_ENDPOINT、S3_BUCKET 和 AWS 凭证）。
metadata:
  skill_version: "0.1.0"
---

# Speech Recognition

使用阿里云百炼 Fun-ASR 非实时语音识别模型，将音频文件转写为文本。支持说话人分离、多语言识别、时间戳输出。

## 使用场景

- 用户发送音频文件要求转文字
- 用户提到"语音识别""音频转文字""会议转写""ASR""录音转文本"
- 用户需要对会议录音、采访、通话录音进行文字转写

## 核心流程

本地音频 → S3（获取公网 URL）→ Fun-ASR 异步转写 → 轮询 → 下载结果 → 格式化输出 → **将输出产物交付给用户**

## 调用方式

所有操作通过 `scripts/asr.py` 完成：

```
python3 scripts/asr.py <音频文件路径> [选项]
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `file`（位置参数） | 本地音频文件路径 | 必填 |
| `--model` | 模型选择：`fun-asr` / `paraformer-v2` | `fun-asr` |
| `--diarization` | 启用说话人分离 | 默认启用 |
| `--no-diarization` | 禁用说话人分离 | |
| `--language` | 语言代码，如 `zh` `en` `ja` | `zh` |
| `--output` | 输出文件路径（覆盖默认路径） | `{源文件名}_{时间戳}.{ext}（当前目录）` |
| `--format` | 输出格式：`json` `text` `srt` | `text` |
| `--channel-id` | 声道编号（单声道为 `0`） | `0` |

### 注意事项

- **说话人分离**：默认开启，要求音频为单声道且 ≤ 2 小时。如果音频是多声道或超过 2 小时，程序会自动报错提示。
- **声道转换**：如果音频非单声道，程序会调用 `ffmpeg` 自动转为单声道。优先用 ffmpeg skill。
- **文件格式**：支持 aac、wav、mp3、m4a、flac、ogg 等主流格式。
- **文件大小**：≤ 2GB。
- **API Key**：从环境变量 `BAILIAN_APIKEY` 获取（同时也是 DashScope API Key）。
- **S3 存储**：音频通过 S3 兼容存储中转。配置环境变量 `S3_ENDPOINT`、`S3_BUCKET`、`S3_PREFIX`（默认 `asr-uploads`），AWS 凭证由 boto3 从默认凭证链自动获取。使用 presigned URL 方式（PUT 上传 + GET 下载）。
- **上传路径**：`{S3_PREFIX}/{timestamp}_{filename}`
- **转写完成后**：自动清理 S3 上的临时文件。
- **输出目录**：结果统一保存在当前工作目录。
- **环境变量**：可配置 `scripts/.env` 模板文件。脚本会自动加载。
- **⚠️ 无效语音片段检测**：如果 API 返回 `ASR_RESPONSE_HAVE_NO_WORDS` 或 `SUCCESS_WITH_NO_VALID_FRAGMENT`，说明音频中未检测到有效人声（可能是静音、音量过低或噪音过大）。**必须立即停止，直接向用户报告失败原因，禁止自动重试、替换模型重试或修改音频参数重试。** 只有用户明确要求重试时才可以再次尝试。

### 💰 计价

Fun-ASR 语音识别：0.00022 元/每秒。脚本会在运行时自动检测音频时长并输出预估费用和最终费用。

## Agent 使用示例

```
# 基本用法：转写音频，输出纯文本
python3 scripts/asr.py meeting.mp3
# → 转写完成后将产物文件交付给用户

# 输出 JSON（含时间戳、说话人信息）
python3 scripts/asr.py meeting.mp3 --format json

# 输出 SRT 字幕
python3 scripts/asr.py interview.wav --format srt

# 禁用说话人分离
python3 scripts/asr.py lecture.mp3 --no-diarization

# 指定语言和模型
python3 scripts/asr.py japanese.mp3 --language ja --model paraformer-v2
```

## 输出交付

**转写完成后，必须执行以下步骤：**

1. 读取输出产物文件路径（脚本运行后会提示保存位置）
2. 将产物文件交付给用户
3. 同时在 chat 中简要概括转写结果（时长、说话人数量、核心内容摘要）

> ⚠️ 输出产物只在终端打印不够——用户看不到。必须将文件送达用户。

## 输出格式

### text 格式（默认）
纯文本，按说话人和时间顺序排列：
```
[说话人 0] 00:00:01 - 00:00:05
你好，我们今天讨论项目进度。

[说话人 1] 00:00:05 - 00:00:10
好的，我先汇报一下。
```

### json 格式
完整 JSON 结果，包含所有元数据（时间戳、说话人 ID、置信度等）。

### srt 格式
标准 SRT 字幕文件格式，可直接导入视频编辑软件。
