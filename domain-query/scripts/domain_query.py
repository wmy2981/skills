#!/usr/bin/env python3
"""Domain query — ICP filing + WHOIS + WeChat block check via 接口盒子 API"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://cn.apihz.cn/api/wangzhan"

API_ICP = f"{BASE}/icp.php"
API_WHOIS = f"{BASE}/whoisall.php"
API_WXFH = f"{BASE}/wxfh.php"


def api_request(url: str, params: dict) -> dict:
    api_id = os.environ.get("JKHZ_ID", "")
    api_key = os.environ.get("JKHZ_KEY", "")
    if not api_id or not api_key:
        return {"error": "环境变量 JKHZ_ID 或 JKHZ_KEY 未设置"}

    params["id"] = api_id
    params["key"] = api_key
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"

    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "DomainQuery/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            # 清理控制字符
            raw = raw.replace("\r", "").replace("\x00", "")
            # API 返回的 whois 字段值中可能含有未转义的双引号（如 ("VeriSign")）
            # 先尝试直接解析
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # 用正则提取各顶层字段
                return _parse_broken_json(raw)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _parse_broken_json(raw: str) -> dict:
    """解析含有未转义引号的 JSON 字符串，提取各字段值"""
    result = {}
    # 匹配 "key":"value" 模式，value 中可能含有未转义的引号
    # 策略：逐个字段提取，用下一个 "key": 的位置作为当前 value 的结束
    import re
    # 找所有顶层 key
    keys = list(re.finditer(r'"(\w+)"\s*:', raw))
    for i, m in enumerate(keys):
        key = m.group(1)
        val_start = m.end()
        if i + 1 < len(keys):
            # value 结束于下一个 key 之前
            val_end = keys[i + 1].start()
        else:
            val_end = raw.rfind("}")
        val = raw[val_start:val_end].strip().strip(",").strip('"')
        result[key] = val
    return result


def query_icp(domain: str) -> dict:
    return api_request(API_ICP, {"domain": domain})


def query_whois(domain: str, live: bool = False) -> dict:
    return api_request(API_WHOIS, {"domain": domain, "type": 2 if live else 1})


def query_wxfh(url: str) -> dict:
    return api_request(API_WXFH, {"url": url})


def _is_ok(data: dict) -> bool:
    return str(data.get("code", "")).strip() == "200"


def format_icp(data: dict) -> str:
    if data.get("error"):
        return f"📋 ICP 备案查询: {data['error']}"
    # API 对无备案域名返回 code=200 但 icp 字段为"查询失败"
    icp = data.get("icp", "")
    if icp == "查询失败" or not _is_ok(data):
        return f"📋 ICP 备案查询: {data.get('msg', '该域名未进行 ICP 备案或查询失败')}"
    lines = [
        "📋 ICP 备案信息",
        "=" * 30,
        f"  域名: {data.get('domain', '-')}",
        f"  备案号: {data.get('icp', '-')}",
        f"  单位: {data.get('unit', '-')}",
        f"  类型: {data.get('type', '-')}",
        f"  审核时间: {data.get('time', '-')}",
    ]
    return "\n".join(lines)


def format_whois(data: dict) -> str:
    if _is_ok(data):
        whois_raw = data.get("whois", "")
        lines = ["📝 WHOIS 信息", "=" * 30]
        lines.append(f"  域名: {data.get('domain', '-')}")
        lines.append("")
        # 解析 whois 中的 key: value 对
        if whois_raw:
            for part in whois_raw.split("<br>"):
                part = part.strip()
                if part and ":" in part:
                    k, v = part.split(":", 1)
                    lines.append(f"  {k.strip()}: {v.strip()}")
                elif part:
                    lines.append(f"  {part}")
        return "\n".join(lines)
    else:
        return f"📝 WHOIS 查询: {data.get('msg', data.get('error', '未知'))}"


def format_wxfh(data: dict) -> str:
    if _is_ok(data):
        lines = [
            "🔗 微信防红检测",
            "=" * 30,
            f"  URL: {data.get('url', '-')}",
            f"  状态: {data.get('msg', '-')}",
        ]
        return "\n".join(lines)
    else:
        return f"🔗 微信防红检测: {data.get('msg', data.get('error', '未知'))}"


def main():
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    parser = argparse.ArgumentParser(description="域名全查询（ICP + WHOIS + 微信防红）")
    parser.add_argument("domain", help="要查询的域名（如 example.com）")
    parser.add_argument("--url", help="微信防红检测的 URL（默认用 https://domain）")
    parser.add_argument("--live", action="store_true", help="WHOIS 实时查询（不使用缓存）")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    parser.add_argument("--only", choices=["icp", "whois", "wxfh"], help="只查询指定项")
    args = parser.parse_args()

    domain = args.domain.strip().lower()
    check_url = args.url or f"https://{domain}"

    result = {}

    if args.only:
        targets = [args.only]
    else:
        targets = ["icp", "whois", "wxfh"]

    if "icp" in targets:
        result["icp"] = query_icp(domain)

    if "whois" in targets:
        result["whois"] = query_whois(domain, live=args.live)

    if "wxfh" in targets:
        result["wxfh"] = query_wxfh(check_url)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"🌐 域名全查询: {domain}")
        print("=" * 40)
        print()

        if "icp" in result:
            print(format_icp(result["icp"]))
            print()

        if "whois" in result:
            print(format_whois(result["whois"]))
            print()

        if "wxfh" in result:
            print(format_wxfh(result["wxfh"]))
            print()


if __name__ == "__main__":
    main()
