#!/usr/bin/env python3
"""FreshRSS CLI — 通过 Google Reader API 管理 FreshRSS 实例。

环境变量:
    FRESHRSS_URL          FreshRSS 实例地址 (如 http://192.168.1.100:1180)
    FRESHRSS_API_USER     API 用户名
    FRESHRSS_API_PASSWORD API 密码 (在 FreshRSS → 设置 → 个人资料 → API 管理 中设置)
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

try:
    import requests
except ImportError:
    sys.exit("错误: 需要 requests 库。请运行: pip install requests")


# ---------------------------------------------------------------------------
# 环境变量 & 常量
# ---------------------------------------------------------------------------

def _get_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        sys.exit(f"错误: 环境变量 {key} 未设置")
    return val


def ensure_utf8_console():
    """Force stdout/stderr to UTF-8 encoding on Windows (terminal defaults to GBK)."""
    if sys.platform == "win32":
        for stream_name in ("stdout", "stderr"):
            stream = getattr(sys, stream_name)
            if stream and hasattr(stream, "buffer"):
                setattr(sys, stream_name,
                        io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))
        try:
            subprocess.run(["chcp", "65001"], capture_output=True, check=True)
        except Exception:
            pass


BASE_URL = os.environ.get("FRESHRSS_URL", "").rstrip("/")
API_USER = os.environ.get("FRESHRSS_API_USER", "")
API_PASS = os.environ.get("FRESHRSS_API_PASSWORD", "")

GREADER = "/api/greader.php"


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------

def get_auth_token() -> str:
    """获取 GReader API 认证令牌。"""
    url = f"{BASE_URL}{GREADER}/accounts/ClientLogin"
    try:
        resp = requests.post(url, data={"Email": API_USER, "Passwd": API_PASS}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f"认证请求失败: {e}")

    match = re.search(r"Auth=(.+)", resp.text)
    if not match:
        sys.exit(f"认证失败，返回内容:\n{resp.text}")
    return match.group(1)


def _headers(token: str) -> dict:
    return {"Authorization": f"GoogleLogin auth={token}"}


def _api(token: str, path: str, method: str = "GET", **kwargs) -> requests.Response:
    """发送 API 请求并统一处理错误。"""
    url = f"{BASE_URL}{GREADER}{path}"
    try:
        resp = requests.request(method, url, headers=_headers(token), timeout=30, **kwargs)
        if resp.status_code == 401:
            sys.exit("API 请求失败: 认证过期或无效，请检查环境变量")
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        sys.exit(f"API 请求失败 [{path}]: {e}")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    """移除 HTML 标签并反转义。"""
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text).strip()


def _ts_to_str(ts) -> str:
    """Unix 秒时间戳 → 可读字符串。"""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError, OSError):
        return str(ts)


def _items(resp: requests.Response) -> list[dict]:
    """从响应中提取 items 列表。"""
    data = resp.json()
    return data.get("items", [])


def _fmt_item(item: dict, verbose: bool = False) -> dict:
    """格式化单篇文章为可读字典。"""
    result = {
        "title": item.get("title", "(无标题)"),
        "published": _ts_to_str(item.get("published")),
        "source": item.get("origin", {}).get("title", ""),
    }
    alternates = item.get("alternate", [])
    if alternates:
        result["link"] = alternates[0].get("href", "")
    if verbose:
        summary_html = item.get("summary", {}).get("content", "")
        result["summary"] = _strip_html(summary_html)[:500]
    result["id"] = item.get("id", "")
    return result


def _stream_query(token: str, stream_id: str, count: int, exclude_read: bool = False,
                  continuation: str = "", verbose: bool = False) -> dict:
    """通用流内容查询。"""
    params = {"output": "json", "n": str(count)}
    if exclude_read:
        params["xt"] = "user/-/state/com.google/read"
    if continuation:
        params["c"] = continuation

    resp = _api(token, f"/reader/api/0/stream/contents/{stream_id}", params=params)
    items = _items(resp)
    result = {
        "count": len(items),
        "articles": [_fmt_item(i, verbose=verbose) for i in items],
    }
    cont = resp.json().get("continuation")
    if cont:
        result["continuation"] = cont
    return result


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# 子命令: 文章读取
# ---------------------------------------------------------------------------

def cmd_recent(args):
    """获取最新文章。"""
    token = get_auth_token()
    data = _stream_query(token, "reading-list", args.count, verbose=args.verbose)
    _print_json(data)


def cmd_unread(args):
    """获取未读文章。"""
    token = get_auth_token()
    data = _stream_query(token, "reading-list", args.count, exclude_read=True, verbose=args.verbose)
    _print_json(data)


def cmd_feed(args):
    """获取指定订阅源的文章。"""
    token = get_auth_token()
    stream_id = f"feed/{args.url}"
    data = _stream_query(token, stream_id, args.count, verbose=args.verbose)
    _print_json(data)


def cmd_category(args):
    """获取指定分类下的文章。"""
    token = get_auth_token()
    stream_id = f"user/-/label/{args.name}"
    data = _stream_query(token, stream_id, args.count, verbose=args.verbose)
    _print_json(data)


def cmd_starred(args):
    """获取收藏文章。"""
    token = get_auth_token()
    data = _stream_query(token, "user/-/state/com.google/starred", args.count, verbose=args.verbose)
    _print_json(data)


def cmd_search(args):
    """关键词搜索文章（客户端过滤，GReader API 无原生搜索）。"""
    token = get_auth_token()
    # 大批量抓取后本地过滤
    batch_size = min(args.batch, 1000)
    resp = _api(token, "/reader/api/0/stream/contents/reading-list",
                params={"output": "json", "n": str(batch_size)})
    items = _items(resp)

    keyword = args.keyword.lower()
    matched = []
    for item in items:
        title = item.get("title", "")
        summary = _strip_html(item.get("summary", {}).get("content", ""))
        if keyword in title.lower() or (args.deep and keyword in summary.lower()):
            matched.append(_fmt_item(item, verbose=args.deep))

    _print_json({"keyword": args.keyword, "count": len(matched), "articles": matched})


# ---------------------------------------------------------------------------
# 子命令: 未读计数
# ---------------------------------------------------------------------------

def cmd_unread_count(args):
    """获取每个订阅源的未读数。"""
    token = get_auth_token()
    resp = _api(token, "/reader/api/0/unread-count", params={"output": "json"})
    data = resp.json()
    counts = []
    for uc in data.get("unreadcounts", []):
        counts.append({"id": uc.get("id", ""), "count": uc.get("count", 0)})
    _print_json({"unread_counts": counts})


# ---------------------------------------------------------------------------
# 子命令: 订阅管理
# ---------------------------------------------------------------------------

def cmd_list_feeds(args):
    """列出所有订阅源。"""
    token = get_auth_token()
    resp = _api(token, "/reader/api/0/subscription/list", params={"output": "json"})
    data = resp.json()
    feeds = []
    for sub in data.get("subscriptions", []):
        cats = [c.get("label", "") for c in sub.get("categories", [])]
        feeds.append({
            "title": sub.get("title", ""),
            "id": sub.get("id", ""),
            "url": sub.get("url", ""),
            "categories": cats,
        })
    _print_json({"count": len(feeds), "feeds": feeds})


def cmd_list_categories(args):
    """列出所有分类（标签）。"""
    token = get_auth_token()
    resp = _api(token, "/reader/api/0/tag/list", params={"output": "json"})
    data = resp.json()
    labels = []
    for tag in data.get("tags", []):
        tid = tag.get("id", "")
        if "/label/" in tid:
            labels.append(tid.split("/label/")[-1])
    _print_json({"count": len(labels), "categories": labels})


def cmd_add_feed(args):
    """添加订阅源，可选指定分类。"""
    token = get_auth_token()

    # quickadd
    resp = _api(token, "/reader/api/0/subscription/quickadd",
                method="POST", data={"quickadd": args.url})
    result = resp.json()
    stream_id = result.get("streamId", "")
    if not stream_id:
        _print_json({"success": False, "error": "添加失败", "raw": result})
        return

    # 如果指定了分类，移动到该分类
    if args.category:
        _api(token, "/reader/api/0/subscription/edit", method="POST", data={
            "ac": "edit",
            "s": stream_id,
            "a": f"user/-/label/{args.category}",
        })

    _print_json({"success": True, "stream_id": stream_id, "category": args.category or ""})


def cmd_move_feed(args):
    """在分类间移动订阅源。"""
    token = get_auth_token()
    data = {
        "ac": "edit",
        "s": args.feed_id,
        "a": f"user/-/label/{args.to}",
    }
    if args._from:
        data["r"] = f"user/-/label/{args._from}"
    _api(token, "/reader/api/0/subscription/edit", method="POST", data=data)
    _print_json({"success": True, "feed_id": args.feed_id, "to": args.to, "from": args._from or ""})


def cmd_remove_feed(args):
    """删除订阅源。"""
    token = get_auth_token()
    _api(token, "/reader/api/0/subscription/edit", method="POST", data={
        "ac": "unsubscribe",
        "s": args.feed_id,
    })
    _print_json({"success": True, "feed_id": args.feed_id})


# ---------------------------------------------------------------------------
# 子命令: 标记操作
# ---------------------------------------------------------------------------

def cmd_mark_read(args):
    """标记文章为已读。"""
    token = get_auth_token()
    _api(token, "/reader/api/0/edit-tag", method="POST", data={
        "i": args.item_id,
        "a": "user/-/state/com.google/read",
    })
    _print_json({"success": True, "action": "mark_read", "item_id": args.item_id})


def cmd_star(args):
    """标记文章为收藏。"""
    token = get_auth_token()
    _api(token, "/reader/api/0/edit-tag", method="POST", data={
        "i": args.item_id,
        "a": "user/-/state/com.google/starred",
    })
    _print_json({"success": True, "action": "star", "item_id": args.item_id})


# ---------------------------------------------------------------------------
# CLI 解析
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="freshrss",
        description="FreshRSS CLI — 通过 Google Reader API 管理 FreshRSS 实例",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # --- 文章读取 ---
    def add_count_verbose(sp):
        sp.add_argument("--count", type=int, default=20, help="返回文章数量 (默认 20)")
        sp.add_argument("--verbose", "-v", action="store_true", help="输出摘要内容")

    s = sub.add_parser("recent", help="获取最新文章")
    add_count_verbose(s)
    s.set_defaults(func=cmd_recent)

    s = sub.add_parser("unread", help="获取未读文章")
    add_count_verbose(s)
    s.set_defaults(func=cmd_unread)

    s = sub.add_parser("feed", help="获取指定订阅源的文章")
    s.add_argument("--url", required=True, help="订阅源 URL")
    add_count_verbose(s)
    s.set_defaults(func=cmd_feed)

    s = sub.add_parser("category", help="获取指定分类下的文章")
    s.add_argument("--name", required=True, help="分类名称")
    add_count_verbose(s)
    s.set_defaults(func=cmd_category)

    s = sub.add_parser("starred", help="获取收藏文章")
    add_count_verbose(s)
    s.set_defaults(func=cmd_starred)

    s = sub.add_parser("search", help="关键词搜索文章 (客户端过滤)")
    s.add_argument("--keyword", "-k", required=True, help="搜索关键词")
    s.add_argument("--deep", action="store_true", help="同时搜索摘要内容 (更慢)")
    s.add_argument("--batch", type=int, default=200, help="抓取文章数量用于搜索 (默认 200)")
    s.set_defaults(func=cmd_search)

    # --- 未读计数 ---
    s = sub.add_parser("unread-count", help="获取每个订阅源的未读数")
    s.set_defaults(func=cmd_unread_count)

    # --- 订阅管理 ---
    s = sub.add_parser("list-feeds", help="列出所有订阅源")
    s.set_defaults(func=cmd_list_feeds)

    s = sub.add_parser("list-categories", help="列出所有分类")
    s.set_defaults(func=cmd_list_categories)

    s = sub.add_parser("add-feed", help="添加订阅源")
    s.add_argument("--url", required=True, help="订阅源 URL")
    s.add_argument("--category", help="添加到指定分类")
    s.set_defaults(func=cmd_add_feed)

    s = sub.add_parser("move-feed", help="在分类间移动订阅源")
    s.add_argument("--feed-id", required=True, help="订阅源 ID (如 feed/https://...)")
    s.add_argument("--to", required=True, help="目标分类")
    s.add_argument("--from", dest="_from", help="源分类")
    s.set_defaults(func=cmd_move_feed)

    s = sub.add_parser("remove-feed", help="删除订阅源")
    s.add_argument("--feed-id", required=True, help="订阅源 ID")
    s.set_defaults(func=cmd_remove_feed)

    # --- 标记操作 ---
    s = sub.add_parser("mark-read", help="标记文章为已读")
    s.add_argument("--item-id", required=True, help="文章 ID")
    s.set_defaults(func=cmd_mark_read)

    s = sub.add_parser("star", help="标记文章为收藏")
    s.add_argument("--item-id", required=True, help="文章 ID")
    s.set_defaults(func=cmd_star)

    return p


def main():
    ensure_utf8_console()

    # 启动前检查环境变量
    _get_env("FRESHRSS_URL")
    _get_env("FRESHRSS_API_USER")
    _get_env("FRESHRSS_API_PASSWORD")

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
