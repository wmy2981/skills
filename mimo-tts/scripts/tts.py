#!/usr/bin/env python3
"""
MiMo-V2.5-TTS speech synthesis API client.

OpenAI-compatible /v1/chat/completions interface supporting:
  - Preset voice synthesis (mimo-v2.5-tts)
  - Voice design from text description (mimo-v2.5-tts-voicedesign)
  - Voice cloning from audio sample (mimo-v2.5-tts-voiceclone)
  - Natural language style control
  - Streaming / non-streaming output
  - List available voices

Environment variable: MIMO_APIKEY
"""

import argparse
import base64
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

API_BASE = "https://api.xiaomimimo.com/v1"


def get_api_key():
    key = os.environ.get("MIMO_APIKEY", "")
    if not key:
        raise RuntimeError("Environment variable MIMO_APIKEY not set")
    return key


def resolve_output_path(output_arg):
    """Determine output path. Defaults to ~/.wmyskills/mimo-tts/outputs/ with timestamp name."""
    if output_arg:
        d = os.path.dirname(output_arg)
        if d:
            os.makedirs(d, exist_ok=True)
        return output_arg
    out_dir = Path.home() / ".wmyskills" / "mimo-tts" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(out_dir / f"tts_{ts}.wav")


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
    """Parse OpenAI-format response, extract base64 audio, save to file."""
    try:
        data = json.loads(resp_body)
        audio_b64 = data["choices"][0]["message"]["audio"]["data"]
    except (KeyError, TypeError, json.JSONDecodeError, IndexError):
        print(json.dumps({"error": True, "message": "No audio data in response", "raw": str(resp_body)[:500]}, ensure_ascii=False))
        return
    audio_bytes = base64.b64decode(audio_b64)
    out = resolve_output_path(output_path)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as f:
        f.write(audio_bytes)
    print(json.dumps({"status": "ok", "path": out, "size_bytes": len(audio_bytes)}))


def handle_stream_response(stream, output_path):
    """Handle SSE stream response, concatenate PCM chunks."""
    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        print(json.dumps({"error": True, "message": "Streaming requires numpy and soundfile — pip install numpy soundfile"}))
        return
    collected = np.array([], dtype=np.float32)
    buffer = ""
    done = False
    for chunk in iter(lambda: stream.read(8192), b""):
        if done:
            break
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
                    done = True
                    break
                try:
                    d = json.loads(ds)
                except json.JSONDecodeError:
                    continue
                choices = d.get("choices")
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
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
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    parser = argparse.ArgumentParser(description="MiMo-V2.5-TTS Speech Synthesis")
    sub = parser.add_subparsers(dest="command")

    # voices
    pv = sub.add_parser("voices", help="List available voices")
    pv.add_argument("--format", choices=["json", "text"], default="json")

    # synthesize
    ps = sub.add_parser("synthesize", aliases=["tts"], help="Synthesize with preset voice")
    ps.add_argument("text", help="Text to synthesize (pipe via $(cat))")
    ps.add_argument("--voice", "-v", default="mimo_default")
    ps.add_argument("--user-prompt", "-up", help="Natural language style prompt (pipe via $(cat))")
    ps.add_argument("--format", choices=["wav", "mp3", "pcm16"], default="wav")
    ps.add_argument("--stream", action="store_true")
    ps.add_argument("--output", "-o")
    ps.add_argument("--outfmt", choices=["json", "text"], default="json")

    # design
    pd = sub.add_parser("design", help="Design voice from text description")
    pd.add_argument("voice_prompt", help="Voice description (pipe via $(cat))")
    pd.add_argument("--text", "-t", help="Text to synthesize (pipe via $(cat), optional)")
    pd.add_argument("--format", choices=["wav", "mp3", "pcm16"], default="wav")
    pd.add_argument("--stream", action="store_true")
    pd.add_argument("--output", "-o")
    pd.add_argument("--outfmt", choices=["json", "text"], default="json")

    # clone
    pc = sub.add_parser("clone", help="Clone voice from audio sample")
    pc.add_argument("audio_sample", help="Path to audio sample file")
    pc.add_argument("text", help="Text to synthesize (pipe via $(cat))")
    pc.add_argument("--user-prompt", "-up", help="Natural language style prompt (pipe via $(cat))")
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
            {"id": "mimo_default", "name": "MiMo-Default", "lang": "auto", "gender": "auto"},
            {"id": "冰糖", "name": "Bingtang", "lang": "zh", "gender": "female"},
            {"id": "茉莉", "name": "Moli", "lang": "zh", "gender": "female"},
            {"id": "苏打", "name": "Soda", "lang": "zh", "gender": "male"},
            {"id": "白桦", "name": "Birch", "lang": "zh", "gender": "male"},
            {"id": "Mia", "name": "Mia", "lang": "en", "gender": "female"},
            {"id": "Chloe", "name": "Chloe", "lang": "en", "gender": "female"},
            {"id": "Milo", "name": "Milo", "lang": "en", "gender": "male"},
            {"id": "Dean", "name": "Dean", "lang": "en", "gender": "male"},
        ]
        if args.format == "text":
            for v in voices:
                label = f"{v['name']} ({v['id']})" if v['name'] != v['id'] else v['id']
                print(f"  {label} — {v['lang']} {v['gender']}")
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
