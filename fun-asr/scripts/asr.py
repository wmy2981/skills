#!/usr/bin/env python3
"""
语音识别 CLI — 基于阿里云百炼 Fun-ASR
支持说话人分离、多语言、多格式输出

S3 方式：presigned PUT 上传 + presigned GET URL 提供音频给 ASR 服务
"""

import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import boto3
import requests
from botocore.config import Config as BotoConfig
from dotenv import load_dotenv

# ============================================================
# 配置
# ============================================================

TZ = timezone(timedelta(hours=8))  # Asia/Shanghai

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "").rstrip("/")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_PREFIX = os.environ.get("S3_PREFIX", "asr-uploads")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1"
SUBMIT_URL = f"{DASHSCOPE_URL}/services/audio/asr/transcription"
QUERY_URL = f"{DASHSCOPE_URL}/tasks"

POLL_INTERVAL = 2       # 轮询间隔（秒）
MAX_WAIT = 1800         # 最长等待（秒），30分钟
PRESIGNED_EXPIRE = 7200 # Presigned URL 有效期（秒），2小时，确保异步任务完成前 URL 不过期
PRICE_PER_SECOND = 0.00022  # Fun-ASR 价格：元/秒


def get_api_key():
    """从 BAILIAN_APIKEY 获取 API Key"""
    key = os.getenv("BAILIAN_APIKEY") or os.getenv("DASHSCOPE_API_KEY")
    if not key:
        die("BAILIAN_APIKEY 环境变量未设置")
    return key


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# S3 操作（Presigned URL 方式）
# ============================================================

def get_s3_client():
    """创建 S3 客户端（凭证由 boto3 从默认凭证链自动获取）"""
    if not S3_ENDPOINT:
        die("环境变量 S3_ENDPOINT 未设置")
    if not S3_BUCKET:
        die("环境变量 S3_BUCKET 未设置")

    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        config=BotoConfig(signature_version="s3v4", region_name=S3_REGION),
        region_name=S3_REGION,
    )


def upload_to_s3(local_path: str) -> tuple:
    """
    上传本地文件到 S3（通过 presigned PUT URL）。
    返回 (presigned_get_url, s3_key)
    """
    path = Path(local_path)
    if not path.exists():
        die(f"文件不存在: {local_path}")

    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > 2048:
        die(f"文件过大 ({file_size_mb:.1f} MB)，超过 2GB 限制")

    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    safe_name = path.name.replace(" ", "_")
    key = f"{S3_PREFIX}/{ts}_{safe_name}"

    print(f"📤 上传到 S3: {key} ({file_size_mb:.1f} MB) ...")

    s3 = get_s3_client()

    # 生成 presigned PUT URL
    put_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600,
    )

    # 上传
    try:
        with open(path, "rb") as f:
            resp = requests.put(put_url, data=f, timeout=600)
        if resp.status_code != 200:
            die(f"上传失败 (HTTP {resp.status_code}): {resp.text[:200]}")
    except requests.RequestException as e:
        die(f"上传失败: {e}")

    print(f"✅ 上传完成")

    # 生成 presigned GET URL（供 Fun-ASR 下载）
    get_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=PRESIGNED_EXPIRE,
    )
    print(f"🔗 生成下载链接 (有效期 {PRESIGNED_EXPIRE // 3600}h)")

    return get_url, key


def delete_from_s3(key: str):
    """删除 S3 上的临时文件"""
    try:
        s3 = get_s3_client()
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
        print(f"🗑️  已清理 S3: {key}")
    except Exception as e:
        print(f"⚠️  清理 S3 文件失败: {e}")


# ============================================================
# 音频预处理
# ============================================================

def check_and_convert_audio(file_path: str, require_mono: bool) -> str:
    """
    检查音频格式，如果需要单声道但非单声道则自动转换。
    返回最终使用的文件路径。
    """
    path = Path(file_path)
    if not require_mono:
        return file_path

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "stream=channels",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(path)],
            capture_output=True, text=True, timeout=10
        )
        channels = result.stdout.strip()
        if not channels:
            print("⚠️  无法检测声道数，跳过声道检查")
            return file_path

        channels = int(channels.split("\n")[0])
        if channels == 1:
            print(f"✅ 音频为单声道，无需转换")
            return file_path

        print(f"⚠️  音频为 {channels} 声道，说话人分离要求单声道，正在转换...")

        output_path = str(path.parent / f"{path.stem}_mono{path.suffix}")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ac", "1", output_path],
            capture_output=True, text=True, check=True, timeout=300
        )
        print(f"✅ 已转换为单声道: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        print(f"⚠️  ffprobe/ffmpeg 执行失败: {e.stderr}")
        return file_path
    except FileNotFoundError:
        print("⚠️  ffmpeg 未安装，跳过声道检查")
        return file_path


def get_audio_duration(file_path: str) -> float:
    """获取音频时长（秒）"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0


# ============================================================
# Fun-ASR 异步转写
# ============================================================

def submit_task(file_url: str, model: str, diarization: bool,
                 language: str, channel_id: int) -> str:
    """提交转写任务，返回 task_id"""
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    payload = {
        "model": model,
        "input": {
            "file_urls": [file_url]
        },
        "parameters": {
            "channel_id": [channel_id],
        }
    }

    if language:
        payload["parameters"]["language_hints"] = [language]

    if diarization:
        payload["parameters"]["diarization_enabled"] = True

    print(f"📝 提交转写任务 (model={model}, diarization={diarization}, lang={language}) ...")

    try:
        resp = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as e:
        die(f"提交任务失败: {e}")

    if resp.status_code != 200:
        die(f"提交任务失败 (HTTP {resp.status_code}): {resp.text}")

    data = resp.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        die(f"未获取到 task_id: {json.dumps(data, ensure_ascii=False)}")

    print(f"✅ 任务已提交: task_id={task_id}")
    return task_id


def poll_task(task_id: str) -> dict:
    """轮询任务状态直到完成，返回完整响应"""
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-DashScope-Async": "enable",
    }

    start = time.time()
    last_status = ""

    while True:
        elapsed = time.time() - start
        if elapsed > MAX_WAIT:
            die(f"任务超时 ({MAX_WAIT}s)，task_id={task_id}")

        try:
            resp = requests.get(f"{QUERY_URL}/{task_id}", headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"⚠️  轮询请求失败 ({e})，{POLL_INTERVAL}s 后重试...")
            time.sleep(POLL_INTERVAL)
            continue

        if resp.status_code != 200:
            print(f"⚠️  查询返回 {resp.status_code}，{POLL_INTERVAL}s 后重试...")
            time.sleep(POLL_INTERVAL)
            continue

        data = resp.json()
        output = data.get("output", {})
        status = output.get("task_status", "")

        if status != last_status:
            print(f"⏳ 任务状态: {status} (已等待 {elapsed:.0f}s)")
            last_status = status

        if status == "SUCCEEDED":
            print(f"✅ 转写完成 (耗时 {elapsed:.0f}s)")
            return data
        elif status == "FAILED":
            msg = output.get("message", "未知错误")
            die(f"转写失败: {msg}")
        elif status == "UNKNOWN":
            die(f"任务状态异常: UNKNOWN")

        time.sleep(POLL_INTERVAL)


def download_result(task_response: dict) -> dict:
    """从任务响应中下载转写结果 JSON"""
    results = task_response.get("output", {}).get("results", [])
    if not results:
        die("响应中无 results")

    all_data = []
    for i, r in enumerate(results):
        if r.get("subtask_status") != "SUCCEEDED":
            print(f"⚠️  子任务 {i} 状态异常: {r.get('subtask_status')}")
            continue

        url = r.get("transcription_url")
        if not url:
            print(f"⚠️  子任务 {i} 无 transcription_url")
            continue

        print(f"📥 下载结果 {i+1}/{len(results)} ...")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            data["_file_url"] = r.get("file_url", "")
            all_data.append(data)
        except Exception as e:
            print(f"⚠️  下载结果 {i} 失败: {e}")

    if not all_data:
        die("无法下载任何转写结果")

    return all_data[0] if len(all_data) == 1 else all_data


# ============================================================
# 格式化输出
# ============================================================

def _ms_to_time_str(ms: int) -> str:
    """毫秒 → HH:MM:SS"""
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _ms_to_srt_time(ms: int) -> str:
    """毫秒 → SRT 时间戳 HH:MM:SS,mmm"""
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_text(result: dict) -> str:
    """输出纯文本格式"""
    lines = []
    transcripts = result.get("transcripts", [])

    for t in transcripts:
        for sent in t.get("sentences", []):
            speaker = sent.get("speaker_id", "")
            bt = _ms_to_time_str(sent.get("begin_time", 0))
            et = _ms_to_time_str(sent.get("end_time", 0))
            text = sent.get("text", "").strip()

            if speaker != "":
                header = f"[说话人 {speaker}] {bt} - {et}"
            else:
                header = f"[{bt} - {et}]"

            lines.append(header)
            lines.append(text)
            lines.append("")

    return "\n".join(lines)


def format_srt(result: dict) -> str:
    """输出 SRT 字幕格式"""
    blocks = []
    idx = 0

    transcripts = result.get("transcripts", [])
    for t in transcripts:
        for sent in t.get("sentences", []):
            idx += 1
            bt = _ms_to_srt_time(sent.get("begin_time", 0))
            et = _ms_to_srt_time(sent.get("end_time", 0))
            text = sent.get("text", "").strip()

            speaker = sent.get("speaker_id", "")
            speaker_tag = f"[S{speaker}] " if speaker != "" else ""

            blocks.append(f"{idx}")
            blocks.append(f"{bt} --> {et}")
            blocks.append(f"{speaker_tag}{text}")
            blocks.append("")

    return "\n".join(blocks)


def format_result(result: dict, fmt: str) -> str:
    """按指定格式输出"""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "srt":
        return format_srt(result)
    else:
        return format_text(result)


# ============================================================
# 主流程
# ============================================================

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="语音识别 - 阿里云百炼 Fun-ASR (说话人分离)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  asr.py meeting.mp3                          # 转写为文本（默认说话人分离）
  asr.py meeting.mp3 --format json            # 输出完整 JSON
  asr.py meeting.mp3 --format srt             # 输出 SRT 字幕
  asr.py lecture.wav --no-diarization         # 禁用说话人分离
  asr.py jp.mp3 --language ja --model paraformer-v2
        """
    )

    parser.add_argument("file", help="音频文件路径")
    parser.add_argument("--model", default="fun-asr",
                        choices=["fun-asr", "paraformer-v2", "paraformer-v1",
                                 "fun-asr-mtl", "paraformer-mtl-v1"],
                        help="模型选择 (默认: fun-asr)")
    parser.add_argument("--diarization", action="store_true", default=True,
                        help="启用说话人分离 (默认)")
    parser.add_argument("--no-diarization", dest="diarization",
                        action="store_false",
                        help="禁用说话人分离")
    parser.add_argument("--language", default="zh",
                        help="语言代码 (默认: zh)")
    parser.add_argument("--channel-id", type=int, default=0,
                        help="声道编号 (默认: 0)")
    parser.add_argument("--output", default=None,
                        help="输出文件路径 (默认: 自动生成)")
    parser.add_argument("--format", default="text",
                        choices=["text", "json", "srt"],
                        help="输出格式 (默认: text)")
    parser.add_argument("--keep-s3", action="store_true",
                        help="保留 S3 上的临时文件")

    args = parser.parse_args()

    # 1. 检查文件
    file_path = args.file
    if not os.path.isfile(file_path):
        die(f"文件不存在: {file_path}")

    # 2. 检查音频时长（说话人分离要求 ≤ 2 小时）
    dur = get_audio_duration(file_path)
    estimated_cost = dur * PRICE_PER_SECOND
    print(f"⏱️  音频时长: {dur:.1f} 秒 ({dur/60:.1f} 分钟)")
    print(f"💰 预估费用: ¥{estimated_cost:.4f} (¥{PRICE_PER_SECOND}/秒)")

    if args.diarization:
        if dur > 7200:
            die(f"音频时长 {dur/3600:.1f} 小时，说话人分离要求 ≤ 2 小时。请用 --no-diarization 或截取片段")

    # 3. 声道转换（如果需要）
    file_path = check_and_convert_audio(file_path, args.diarization)

    # 4. 上传到 S3
    s3_url, s3_key = upload_to_s3(file_path)

    # 5. 提交任务
    task_id = submit_task(
        file_url=s3_url,
        model=args.model,
        diarization=args.diarization,
        language=args.language,
        channel_id=args.channel_id,
    )

    # 6. 轮询等待
    task_response = poll_task(task_id)

    # 7. 下载结果
    result = download_result(task_response)

    # 8. 格式化输出
    output = format_result(result, args.format)

    # 计算实际费用
    actual_cost = dur * PRICE_PER_SECOND

    # 9. 保存文件
    if args.output:
        out_path = args.output
    else:
        base = Path(args.file).stem
        ext_map = {"text": "txt", "json": "json", "srt": "srt"}
        ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
        out_path = f"{base}_{ts}.{ext_map[args.format]}"

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n📄 结果已保存: {out_path}")
    print(f"💰 本次识别费用: ¥{actual_cost:.4f}")

    # 输出到 stdout
    if args.format in ("text", "srt"):
        print("\n" + "=" * 50)
        print(output)

    # 清理 S3
    if not args.keep_s3:
        delete_from_s3(s3_key)


if __name__ == "__main__":
    main()
