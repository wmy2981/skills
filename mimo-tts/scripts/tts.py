#!/usr/bin/env python3
"""
MiMo-V2.5-TTS 语音合成 API 客户端
使用 OpenAI-compatible /v1/chat/completions 接口

覆盖功能：
  - 预置音色合成 (mimo-v2.5-tts)
  - 文本设计音色 (mimo-v2.5-tts-voicedesign)
  - 音色复刻 (mimo-v2.5-tts-voiceclone)
  - 自然语言风格控制
  - 流式/非流式输出
  - 查询音色列表

环境变量：MIMO_APIKEY
提示词传参方式：写入 txt 文件后用 $(cat) 传入
"""

import json, os, sys, argparse, base64, datetime
import urllib.request, urllib.error
from dotenv import load_dotenv

API_BASE = "https://api.xiaomimimo.com/v1"


def get_api_key():
    key = os.environ.get("MIMO_APIKEY", "")
    if not key:
        raise RuntimeError("环境变量 MIMO_APIKEY 未设置")
    return key


def resolve_output_path(output_arg):
    """确定输出路径。不指定则默认到当前工作目录"""
    if output_arg:
        d = os.path.dirname(output_arg)
        if d:
            os.makedirs(d, exist_ok=True)
        return output_arg
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.getcwd(), f"tts_{ts}.wav")


def chat_completion(payload, stream=False):
    headers = {
        "api-key": get_api_key(),
        "Content-Type": "application/json",
    }
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=body, headers=headers, method="POST")
    try:
        if stream:
            return urllib.request.urlopen(req, timeout=300)
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        return {"error": True, "status": e.code, "message": err}
    except urllib.error.URLError as e:
        return {"error": True, "message": str(e.reason)}


def save_audio_from_response(resp_body, output_path):
    """解析 OpenAI 格式响应，提取音频 base64 并保存"""
    try:
        data = json.loads(resp_body)
        audio_b64 = data["choices"][0]["message"]["audio"]["data"]
    except (KeyError, TypeError, json.JSONDecodeError, IndexError):
        print(json.dumps({"error": True, "message": "响应中未找到音频数据", "raw": str(resp_body)[:500]}, ensure_ascii=False))
        return
    audio_bytes = base64.b64decode(audio_b64)
    out = resolve_output_path(output_path)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as f:
        f.write(audio_bytes)
    print(json.dumps({"status": "ok", "path": out, "size_bytes": len(audio_bytes)}))


def handle_stream_response(stream, output_path):
    """处理流式 SSE 响应，拼接 PCM 数据"""
    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        print(json.dumps({"error": True, "message": "流式输出需要 numpy 和 soundfile，请先 pip install numpy soundfile"}))
        return
    collected = np.array([], dtype=np.float32)
    buffer = ""
    for chunk in iter(lambda: stream.read(8192), b""):
        buffer += chunk.decode(errors="replace")
        while True:
            idx = buffer.find("\n")
            if idx == -1:
                break
            line = buffer[:idx].strip()
            buffer = buffer[idx + 1:]
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                ds = line[6:]
                if ds == "[DONE]":
                    break
                try:
                    d = json.loads(ds)
                except json.JSONDecodeError:
                    continue
                delta = d.get("choices", [{}])[0].get("delta", {})
                audio = delta.get("audio", {})
                if "data" in audio:
                    pcm = np.frombuffer(base64.b64decode(audio["data"]), dtype=np.int16).astype(np.float32) / 32768.0
                    collected = np.concatenate((collected, pcm))
    out = resolve_output_path(output_path)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    sf.write(out, collected, samplerate=24000)
    print(json.dumps({"status": "ok", "path": out, "samples": len(collected)}))


def handle_http_response(result, output_path, stream):
    if isinstance(result, dict) and result.get("error"):
        print(json.dumps(result, ensure_ascii=False))
        return
    if stream:
        handle_stream_response(result, output_path)
    else:
        save_audio_from_response(result, output_path)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="MiMo-V2.5-TTS 语音合成")
    sub = parser.add_subparsers(dest="command")

    # voices
    pv = sub.add_parser("voices", help="列出可用音色")
    pv.add_argument("--format", choices=["json", "text"], default="json")

    # synthesize
    ps = sub.add_parser("synthesize", aliases=["tts"], help="预置音色合成")
    ps.add_argument("text", help="合成文本 (用 \$(cat) 传参)")
    ps.add_argument("--voice", "-v", default="mimo_default")
    ps.add_argument("--user-prompt", "-up", help="自然语言风格指令 (用 \$(cat) 传参)")
    ps.add_argument("--format", choices=["wav", "mp3", "pcm16"], default="wav")
    ps.add_argument("--stream", action="store_true")
    ps.add_argument("--output", "-o")
    ps.add_argument("--outfmt", choices=["json", "text"], default="json")

    # design
    pd = sub.add_parser("design", help="文本设计音色")
    pd.add_argument("voice_prompt", help="音色描述文本 (用 \$(cat) 传参)")
    pd.add_argument("--text", "-t", help="合成文本 (用 \$(cat) 传参，可选)")
    pd.add_argument("--format", choices=["wav", "mp3", "pcm16"], default="wav")
    pd.add_argument("--stream", action="store_true")
    pd.add_argument("--output", "-o")
    pd.add_argument("--outfmt", choices=["json", "text"], default="json")

    # clone
    pc = sub.add_parser("clone", help="音色复刻")
    pc.add_argument("audio_sample", help="音频样本文件路径")
    pc.add_argument("text", help="合成文本 (用 \$(cat) 传参)")
    pc.add_argument("--user-prompt", "-up", help="自然语言风格指令 (用 \$(cat) 传参)")
    pc.add_argument("--format", choices=["wav", "mp3", "pcm16"], default="wav")
    pc.add_argument("--stream", action="store_true")
    pc.add_argument("--output", "-o")
    pc.add_argument("--outfmt", choices=["json", "text"], default="json")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # voices
    if args.command == "voices":
        voices = [
            {"id": "mimo_default", "name": "MiMo-默认", "lang": "auto", "gender": "auto"},
            {"id": "冰糖", "name": "冰糖", "lang": "zh", "gender": "female"},
            {"id": "茉莉", "name": "茉莉", "lang": "zh", "gender": "female"},
            {"id": "苏打", "name": "苏打", "lang": "zh", "gender": "male"},
            {"id": "白桦", "name": "白桦", "lang": "zh", "gender": "male"},
            {"id": "Mia", "name": "Mia", "lang": "en", "gender": "female"},
            {"id": "Chloe", "name": "Chloe", "lang": "en", "gender": "female"},
            {"id": "Milo", "name": "Milo", "lang": "en", "gender": "male"},
            {"id": "Dean", "name": "Dean", "lang": "en", "gender": "male"},
        ]
        if args.format == "text":
            for v in voices:
                print(f"  {v['name']} ({v['id']}) — {v['lang']} {v['gender']}")
        else:
            print(json.dumps({"voices": voices}, ensure_ascii=False, indent=2))
        return

    # synthesize
    if args.command in ("synthesize", "tts"):
        text = args.text
        messages = []
        if args.user_prompt:
            messages.append({"role": "user", "content": args.user_prompt})
        messages.append({"role": "assistant", "content": text})
        payload = {"model": "mimo-v2.5-tts", "messages": messages,
                   "audio": {"format": args.format, "voice": args.voice}}
        if args.stream:
            payload["stream"] = True
        result = chat_completion(payload, stream=args.stream)
        handle_http_response(result, args.output, args.stream)
        return

    # design
    if args.command == "design":
        voice_prompt = args.voice_prompt
        messages = [{"role": "user", "content": voice_prompt}]
        if args.text:
            messages.append({"role": "assistant", "content": args.text})
        payload = {"model": "mimo-v2.5-tts-voicedesign", "messages": messages,
                   "audio": {"format": args.format, "optimize_text_preview": True}}
        if args.stream:
            payload["stream"] = True
        result = chat_completion(payload, stream=args.stream)
        handle_http_response(result, args.output, args.stream)
        return

    # clone
    if args.command == "clone":
        with open(args.audio_sample, "rb") as f:
            sample_bytes = f.read()
        ext = os.path.splitext(args.audio_sample)[1].lower()
        mime = "audio/mpeg" if ext in (".mp3",) else "audio/wav"
        voice_b64 = base64.b64encode(sample_bytes).decode()
        voice_data = f"data:{mime};base64,{voice_b64}"
        text = args.text
        messages = []
        if args.user_prompt:
            messages.append({"role": "user", "content": args.user_prompt})
        else:
            messages.append({"role": "user", "content": ""})
        messages.append({"role": "assistant", "content": text})
        payload = {"model": "mimo-v2.5-tts-voiceclone", "messages": messages,
                   "audio": {"format": args.format, "voice": voice_data}}
        if args.stream:
            payload["stream"] = True
        result = chat_completion(payload, stream=args.stream)
        handle_http_response(result, args.output, args.stream)
        return


if __name__ == "__main__":
    main()
