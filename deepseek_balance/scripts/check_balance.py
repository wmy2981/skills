#!/usr/bin/env python3
"""DeepSeek 开放平台余额查询
从环境变量 DEEPSEEK_APIKEY 获取 API Key，调用余额接口。
输出原始 JSON 到 stdout。指定 --output 路径时，同时将结果追加记录到该 CSV 文件。
"""

import json
import os
import sys
import argparse
from csv import DictWriter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from urllib.request import Request, urlopen
from urllib.error import URLError

API_URL = "https://api.deepseek.com/user/balance"


def main():
    parser = argparse.ArgumentParser(description="DeepSeek 开放平台余额查询")
    parser.add_argument("--output", "-o", help="CSV 输出路径（可选），不指定则只输出 JSON 到 stdout")
    args = parser.parse_args()

    load_dotenv()

    api_key = os.environ.get("DEEPSEEK_APIKEY")
    if not api_key:
        print(json.dumps({"error": "环境变量 DEEPSEEK_APIKEY 未设置"}, ensure_ascii=False))
        sys.exit(1)

    req = Request(API_URL, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
    except URLError as e:
        print(json.dumps({"error": f"API 请求失败: {e}"}, ensure_ascii=False))
        sys.exit(1)

    print(body)

    # CSV 记录（仅 --output 时写入）
    if args.output:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return  # 无法解析就不写 CSV

        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).isoformat(timespec="seconds")
        is_available = data.get("is_available")
        balance_infos = data.get("balance_infos", [])
        if not balance_infos:
            return
        info = balance_infos[0]

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = output_path.exists()
        with open(output_path, "a", newline="", encoding="utf-8") as f:
            writer = DictWriter(f, fieldnames=[
                "datetime", "is_available", "currency",
                "total_balance", "granted_balance", "topped_up_balance",
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "datetime": now,
                "is_available": is_available,
                "currency": info.get("currency", ""),
                "total_balance": info.get("total_balance", ""),
                "granted_balance": info.get("granted_balance", ""),
                "topped_up_balance": info.get("topped_up_balance", ""),
            })


if __name__ == "__main__":
    main()
