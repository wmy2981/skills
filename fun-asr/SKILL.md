---
name: fun-asr
description: Use when the user shares an audio file (mp3, wav, m4a, flac) and asks to transcribe it to text — includes queries containing "speech recognition", "audio to text", "transcribe", "transcription", "ASR", "meeting notes", "convert audio", "subtitle", "SRT", "speaker diarization", "who said what". Also triggers on audio meeting recordings, interviews, phone calls, lectures, voice memos, podcasts. Requires BAILIAN_APIKEY (Alibaba Cloud Bailian / DashScope) and S3-compatible storage credentials.
---

# Fun-ASR: Audio Transcription

Transcribe audio files using Alibaba Cloud Bailian's Fun-ASR non-real-time speech recognition model. Supports speaker diarization, multi-language recognition, and multiple output formats (plain text, JSON, SRT subtitles).

## Workflow

```
Audio → S3 → Fun-ASR async → Poll → Save file → Agent reads
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
| `--output` | auto-generated | Custom output file path (default: `~/.wmyskills/fun-asr/outputs/`) |
| `--format` | `text` | Output format: `text`, `json`, `srt` |
| `--keep-s3` | (off) | Keep the uploaded file on S3 after transcription |
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

# Custom output path
python fun_asr_cli.py audio.wav --output ~/Desktop/transcript.txt
```

## Output Formats

### text (default)

Plain text with speaker labels and timestamps: `[Speaker N] HH:MM:SS - HH:MM:SS`, followed by the text.

### json

Full JSON with all metadata — timestamps, speaker IDs, confidence scores, and the raw API response.

### srt

Standard SRT subtitle format: `NN \n HH:MM:SS,mmm --> HH:MM:SS,mmm \n [SN] text`.

## Agent Instructions

### Execution Strategy

> **Don't check dependencies, environment variables, or configuration before running the script.** Just execute the transcription command directly. If it fails due to missing dependencies or env vars, the script will exit with a clear error code and message — fix whatever is broken and retry. This avoids wasting time on pre-flight checks when everything is already set up.

### After Transcription Completes

Output is always saved to a file — never printed to terminal. The default output directory is `~/.wmyskills/fun-asr/outputs/`.

When transcription succeeds, stdout contains **only** the output file path. Failures print full error logs to stderr.

On success you **must** deliver the result to the user:

1. Capture the output file path (the only stdout line)
2. Read and present the file content to the user
3. Provide a brief summary: audio duration, number of speakers detected (if diarization was enabled), and a concise overview of the content

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
- **Pricing**: Fun-ASR costs **CNY 0.00022 / second** of audio. The script estimates cost before starting and reports actual cost on completion.

