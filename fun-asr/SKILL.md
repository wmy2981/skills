---
name: fun-asr
description: Use when the user shares an audio file (mp3, wav, m4a, flac) and asks to transcribe it to text — includes queries containing "speech recognition", "audio to text", "transcribe", "transcription", "ASR", "meeting notes", "convert audio", "subtitle", "SRT", "speaker diarization", "who said what". Also triggers on audio meeting recordings, interviews, phone calls, lectures, voice memos, podcasts. Requires BAILIAN_APIKEY (Alibaba Cloud Bailian / DashScope) and S3-compatible storage credentials.
metadata:
  skill_version: "0.2.0"
---

# Fun-ASR: Audio Transcription

Transcribe audio files using Alibaba Cloud Bailian's Fun-ASR non-real-time speech recognition model. Supports speaker diarization, multi-language recognition, and multiple output formats (plain text, JSON, SRT subtitles).

## Workflow

```
Local audio file → S3 (presigned URL) → Fun-ASR async transcription → Poll → Download → Format → Deliver to user
```

## Requirements

### Environment Variables

Set these in `scripts/.env` (copy from the `.env` template):

| Variable | Required | Description |
|----------|----------|-------------|
| `BAILIAN_APIKEY` | Yes | Alibaba Cloud Bailian (DashScope) API key |
| `S3_ENDPOINT` | Yes | S3-compatible storage endpoint URL |
| `S3_BUCKET` | Yes | S3 bucket name for audio uploads |
| `S3_REGION` | No | S3 region (default: `us-east-1`) |
| `S3_PREFIX` | No | Key prefix for uploads (default: `asr-uploads`) |
| `AWS_ACCESS_KEY_ID` | No* | AWS access key (needed if not using IAM/default chain) |
| `AWS_SECRET_ACCESS_KEY` | No* | AWS secret key (needed if not using IAM/default chain) |

The script finds `.env` automatically — it searches the script directory (`scripts/`), the skill root (`fun-asr/`), and the current working directory.

### Python Dependencies

```bash
pip install boto3 requests python-dotenv
```

### Optional: ffmpeg

ffmpeg/ffprobe is needed for:
- Detecting audio channel count
- Converting multi-channel audio to mono (required for speaker diarization)

Without ffmpeg, the script skips mono conversion and uses the original file.

## Usage

```bash
python fun_asr_cli.py <audio-file> [options]
```

Run from the `scripts/` directory or provide the full path to `fun_asr_cli.py`.

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `file` | Path to the audio file (aac, wav, mp3, m4a, flac, ogg, etc.) |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `fun-asr` | ASR model: `fun-asr`, `paraformer-v2`, `paraformer-v1`, `fun-asr-mtl`, `paraformer-mtl-v1` |
| `--no-diarization` | (enabled) | Disable speaker diarization |
| `--language` | `zh` | Language hint: `zh`, `en`, `ja`, `ko`, `yue`, etc. |
| `--channel-id` | `0` | Audio channel to transcribe (0 = first/mono) |
| `--output` | auto-generated | Custom output file path |
| `--format` | `text` | Output format: `text`, `json`, `srt` |
| `--keep-s3` | (off) | Keep the uploaded file on S3 after transcription |
| `--quiet` | (off) | Suppress progress messages; show only errors and the final result |
| `--version` | — | Show script version and exit |

### Examples

```bash
# Basic transcription (text format, Chinese)
python fun_asr_cli.py meeting.mp3

# JSON output with full metadata (timestamps, speaker IDs, confidence)
python fun_asr_cli.py interview.wav --format json

# SRT subtitle output
python fun_asr_cli.py lecture.mp3 --format srt

# Disable speaker diarization
python fun_asr_cli.py meeting.mp3 --no-diarization

# Specify language and model
python fun_asr_cli.py japanese_audio.mp3 --language ja --model paraformer-v2

# Quiet mode (machine-readable progress on stderr)
python fun_asr_cli.py audio.wav --quiet
```

## Output Formats

### text (default)

Plain text with speaker labels and timestamps:

```
[Speaker 0] 00:00:01 - 00:00:05
Hello, let's discuss the project progress today.

[Speaker 1] 00:00:05 - 00:00:10
Sure, let me report first.
```

### json

Full JSON structure with all metadata — timestamps, speaker IDs, confidence scores, and the raw API response.

### srt

Standard SRT subtitle format, compatible with video editing software:

```
1
00:00:01,000 --> 00:00:05,000
[S0] Hello, let's discuss the project progress today.

2
00:00:05,000 --> 00:00:10,000
[S1] Sure, let me report first.
```

## Agent Instructions

### After Transcription Completes

When transcription succeeds, you **must** deliver the result to the user:

1. Read the output file path from the script's result JSON (printed to stdout on success)
2. Send the file to the user
3. Provide a brief summary: audio duration, number of speakers detected (if diarization was enabled), and a concise overview of the content

> ⚠️ The result is only printed in the terminal — the user cannot see it there. You must deliver the file to them.

### Error Scenarios

The script exits with specific codes for programmatic handling:

- **Code 2** — Configuration error: missing env vars. Check `.env` and system environment.
- **Code 3** — File error: file not found, too large, or exceeds limits.
- **Code 4** — API/network error: submission or polling failed.
- **Code 5** — Audio processing error.
- **Code 6** — Task failure: ASR API returned an error. Check the error message.
- **Code 7** — Timeout: transcription took longer than 30 minutes.
- **Code 8** — Invalid arguments.

### Important Rules

- **No valid speech detected**: If the API returns `ASR_RESPONSE_HAVE_NO_WORDS` or `SUCCESS_WITH_NO_VALID_FRAGMENT`, the audio contains no detectable human speech (silence, too quiet, or pure noise). **Stop immediately and report this to the user. Do NOT retry automatically, switch models, or modify audio parameters.** Only retry if the user explicitly asks.
- **Speaker diarization** requires mono audio ≤ 2 hours. The script auto-converts multi-channel audio via ffmpeg. If the file exceeds 2 hours, diarization is disabled automatically.
- **Diarization cost**: The script charges per audio second regardless of diarization; there is no extra fee for enabling it.
- **S3 cleanup**: Temporary files on S3 are deleted automatically after transcription unless `--keep-s3` is passed.

## Pricing

Fun-ASR voice recognition costs **CNY 0.00022 / second** of audio. The script estimates the cost before starting and reports the actual cost on completion.

## Skill Version History

- **0.2.0** — Refactored: English output, structured JSON logging, error classification with exit codes, `--quiet` and `--version` flags, improved `.env` loading, temp file cleanup.
- **0.1.0** — Initial version.
