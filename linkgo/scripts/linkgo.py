#!/usr/bin/env python3
"""LinkGo v3 远程管理 CLI

通过 HTTP API 管理 LinkGo v3 实例的服务卡片、页面配置和系统设置。
需要环境变量: LINKGO_HOST, LINKGO_PASSWORD
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

# ─── 配置 ─────────────────────────────────────────────────

BASE_URL = os.environ.get("LINKGO_HOST", "")
PASSWORD = os.environ.get("LINKGO_PASSWORD", "")

if not BASE_URL or not PASSWORD:
    print("错误: 环境变量 LINKGO_HOST 或 LINKGO_PASSWORD 未设置", file=sys.stderr)
    sys.exit(1)

API_URL = f"{BASE_URL}/api"


# ─── HTTP 工具 ─────────────────────────────────────────────

def _request(method: str, path: str, data: dict | None = None,
             headers: dict | None = None, auth_header: bool = False) -> dict:
    """统一 HTTP 请求，返回 JSON dict。"""
    url = f"{API_URL}{path}"
    hdrs = {"Content-Type": "application/json"}
    if auth_header:
        hdrs["X-Admin-Password"] = PASSWORD
    if headers:
        hdrs.update(headers)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = Request(url, data=body, headers=hdrs, method=method)

    try:
        with urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except (URLError, json.JSONDecodeError) as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


def api_get(path: str, auth: bool = False) -> dict:
    return _request("GET", path, auth_header=auth)


def api_post(path: str, data: dict, auth: bool = False) -> dict:
    return _request("POST", path, data=data, auth_header=auth)


def load_full_data() -> dict:
    """加载完整配置（含禁用卡片），失败则退出。"""
    raw = api_get("/load_data.php", auth=True)
    if "error" in raw:
        print(f"错误: 无法加载数据 — {raw['error']}", file=sys.stderr)
        sys.exit(1)
    return raw


def save_data(data: dict) -> dict:
    """通过 update_json.php 保存完整配置。"""
    payload = {"password": PASSWORD, "content": json.dumps(data, ensure_ascii=False)}
    return api_post("/update_json.php", payload)


def output(obj):
    """格式化输出 JSON。"""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ─── 子命令 ────────────────────────────────────────────────

def cmd_list(args):
    """列出服务卡片。"""
    if args.all:
        raw = load_full_data()
    else:
        raw = api_get("/get_show_data.php")

    services = raw.get("services", raw.get("data", {}).get("services", []))
    if args.enabled:
        services = [s for s in services if s.get("status", 1) == 1]

    if args.id:
        found = [s for s in services if s.get("id") == args.id]
        if found:
            output(found[0])
        else:
            print(f"未找到 id={args.id} 的卡片", file=sys.stderr)
            sys.exit(1)
    else:
        output(services)


def cmd_add(args):
    """添加服务卡片。"""
    card = json.loads(args.json)
    if "id" not in card:
        print("错误: 卡片 JSON 中缺少 id 字段", file=sys.stderr)
        sys.exit(1)

    data = load_full_data()
    existing = [s.get("id") for s in data.get("services", [])]
    if card["id"] in existing:
        print(f"错误: id '{card['id']}' 已存在，请用 edit 或更换 id", file=sys.stderr)
        sys.exit(1)

    data.setdefault("services", []).append(card)
    result = save_data(data)
    output(result)
    print(f"✓ 已添加卡片 '{card.get('title', card['id'])}'")


def cmd_edit(args):
    """编辑服务卡片（按 id 合并字段）。"""
    patch = json.loads(args.json)
    data = load_full_data()

    found = False
    for s in data.get("services", []):
        if s.get("id") == args.id:
            for k, v in patch.items():
                if k != "id":
                    s[k] = v
            found = True
            break

    if not found:
        print(f"错误: 未找到 id='{args.id}' 的卡片", file=sys.stderr)
        sys.exit(1)

    result = save_data(data)
    output(result)
    print(f"✓ 已更新卡片 '{args.id}'")


def cmd_delete(args):
    """删除服务卡片。"""
    data = load_full_data()
    before = len(data.get("services", []))
    data["services"] = [s for s in data.get("services", []) if s.get("id") != args.id]
    after = len(data["services"])

    if before == after:
        print(f"错误: 未找到 id='{args.id}' 的卡片", file=sys.stderr)
        sys.exit(1)

    result = save_data(data)
    output(result)
    print(f"✓ 已删除卡片 '{args.id}'")


def cmd_enable(args):
    """启用服务卡片。"""
    _set_status(args.id, 1)


def cmd_disable(args):
    """禁用服务卡片。"""
    _set_status(args.id, 0)


def _set_status(card_id: str, status: int):
    data = load_full_data()
    found = False
    for s in data.get("services", []):
        if s.get("id") == card_id:
            s["status"] = status
            found = True
            break

    if not found:
        print(f"错误: 未找到 id='{card_id}' 的卡片", file=sys.stderr)
        sys.exit(1)

    result = save_data(data)
    output(result)
    label = "启用" if status == 1 else "禁用"
    print(f"✓ 已{label}卡片 '{card_id}'")


def cmd_page(args):
    """修改页面设置。"""
    patch = json.loads(args.json)
    data = load_full_data()

    page = data.get("page", {})
    page.update(patch)
    data["page"] = page

    result = save_data(data)
    output(result)
    print("✓ 页面设置已更新")


def cmd_upload_icon(args):
    """上传图标文件。"""
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    filepath = args.filepath
    if not os.path.isfile(filepath):
        print(f"错误: 文件不存在 — {filepath}", file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()
    allowed = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
    if ext not in allowed:
        print(f"错误: 不支持的格式 {ext}，允许: {', '.join(sorted(allowed))}", file=sys.stderr)
        sys.exit(1)

    size = os.path.getsize(filepath)
    if size > 1 * 1024 * 1024:
        print(f"错误: 文件过大 ({size} bytes)，上限 1MB", file=sys.stderr)
        sys.exit(1)

    # multipart/form-data 手动构建
    boundary = "----LinkGoBoundary" + str(os.getpid())
    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="icons"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{API_URL}/upload_icon.php"
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("X-Admin-Password", PASSWORD)

    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            output(result)
            if result.get("success"):
                print(f"✓ 已上传 {len(result.get('uploaded', []))} 个文件")
    except (HTTPError, URLError) as e:
        print(f"上传失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_icons(args):
    """列出可用图标。"""
    result = api_get("/get_icons.php", auth=True)
    output(result)


def cmd_export(args):
    """导出完整配置到文件或 stdout。"""
    data = load_full_data()
    formatted = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"✓ 已导出到 {args.output}")
    else:
        print(formatted)


def cmd_import(args):
    """导入配置文件（覆盖全部数据）。"""
    with open(args.filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = save_data(data)
    output(result)
    print("✓ 配置已导入")


def cmd_reset(args):
    """恢复默认配置（清空所有自定义卡片）。"""
    payload = {"password": PASSWORD, "content": "INITIALIZE_WEB_JSON"}
    result = api_post("/update_json.php", payload)
    output(result)
    print("✓ 已恢复默认配置")


def cmd_change_password(args):
    """修改管理密码。"""
    result = api_post("/change_password.php", {
        "old_password": args.old_password,
        "new_password": args.new_password,
    })
    output(result)
    if result.get("success"):
        print("✓ 密码已修改")


def cmd_debug(args):
    """获取调试信息。"""
    result = api_get("/debugInfo.php")
    output(result)


def cmd_ping(args):
    """连通性测试。"""
    try:
        result = api_get("/get_show_data.php")
        services = result.get("data", result).get("services", [])
        print(f"✓ 连接成功，共 {len(services)} 个服务卡片")
        return True
    except Exception as e:
        print(f"✗ 连接失败: {e}", file=sys.stderr)
        return False


# ─── CLI 入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="linkgo",
        description="LinkGo v3 远程管理 CLI",
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")

    # list
    p = sub.add_parser("list", help="列出服务卡片")
    p.add_argument("--all", action="store_true", help="显示所有卡片（含禁用）")
    p.add_argument("--enabled", action="store_true", help="仅显示启用的卡片（默认）")
    p.add_argument("--id", help="查询指定 id 的卡片")
    p.set_defaults(func=cmd_list)

    # add
    p = sub.add_parser("add", help="添加服务卡片")
    p.add_argument("json", help='卡片 JSON，如 \'{"id":"x","title":"X",...}\'')
    p.set_defaults(func=cmd_add)

    # edit
    p = sub.add_parser("edit", help="编辑服务卡片")
    p.add_argument("id", help="目标卡片 id")
    p.add_argument("json", help='要更新的字段 JSON，如 \'{"title":"新标题"}\'')
    p.set_defaults(func=cmd_edit)

    # delete
    p = sub.add_parser("delete", help="删除服务卡片")
    p.add_argument("id", help="目标卡片 id")
    p.set_defaults(func=cmd_delete)

    # enable / disable
    p = sub.add_parser("enable", help="启用服务卡片")
    p.add_argument("id")
    p.set_defaults(func=cmd_enable)

    p = sub.add_parser("disable", help="禁用服务卡片")
    p.add_argument("id")
    p.set_defaults(func=cmd_disable)

    # page
    p = sub.add_parser("page", help="修改页面设置")
    p.add_argument("json", help='页面字段 JSON')
    p.set_defaults(func=cmd_page)

    # upload-icon
    p = sub.add_parser("upload-icon", help="上传图标文件")
    p.add_argument("filepath", help="图标文件路径")
    p.set_defaults(func=cmd_upload_icon)

    # icons
    p = sub.add_parser("icons", help="列出可用图标")
    p.set_defaults(func=cmd_icons)

    # export
    p = sub.add_parser("export", help="导出配置文件")
    p.add_argument("-o", "--output", help="输出文件路径（不指定则打印到 stdout）")
    p.set_defaults(func=cmd_export)

    # import
    p = sub.add_parser("import", help="导入配置文件（覆盖全部数据）")
    p.add_argument("filepath", help="配置文件路径")
    p.set_defaults(func=cmd_import)

    # reset
    p = sub.add_parser("reset", help="恢复默认配置")
    p.set_defaults(func=cmd_reset)

    # change-password
    p = sub.add_parser("change-password", help="修改管理密码")
    p.add_argument("old_password")
    p.add_argument("new_password")
    p.set_defaults(func=cmd_change_password)

    # debug
    p = sub.add_parser("debug", help="获取调试信息")
    p.set_defaults(func=cmd_debug)

    # ping
    p = sub.add_parser("ping", help="连通性测试")
    p.set_defaults(func=cmd_ping)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
