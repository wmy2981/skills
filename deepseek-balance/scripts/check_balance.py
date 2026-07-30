#!/usr/bin/env python
"""DeepSeek Open Platform balance query — minimal version.

Reads the API key from the DEEPSEEK_APIKEY environment variable,
calls the balance API, and prints raw JSON to stdout.
A .env file in the same directory is also loaded automatically.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)

API_URL = "https://api.deepseek.com/user/balance"


def _load_env():
    """加载同级 .env 文件中的环境变量（仅处理 KEY=VALUE 格式，不覆盖已有变量）。"""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def main():
    _load_env()

    api_key = os.environ.get("DEEPSEEK_APIKEY")
    if not api_key:
        print(json.dumps({"error": "DEEPSEEK_APIKEY environment variable not set"}, ensure_ascii=False))
        sys.exit(1)

    req = Request(API_URL, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
    except URLError as e:
        print(json.dumps({"error": f"API request failed: {e}"}, ensure_ascii=False))
        sys.exit(1)

    print(body)


if __name__ == "__main__":
    main()
