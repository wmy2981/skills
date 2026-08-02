#!/usr/bin/env python3
"""Enterprise info query — lookup Chinese company registration via 接口盒子 API"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

API_URL = "https://cn.apihz.cn/api/shiming/qyinfo.php"


def query_company(words: str) -> dict:
    """查询企业信息，返回原始 JSON 响应"""
    api_id = os.environ.get("JKHZ_ID")
    api_key = os.environ.get("JKHZ_KEY")

    if not api_id or not api_key:
        return {"code": 400, "msg": "Environment variables JKHZ_ID or JKHZ_KEY not set"}

    params = {
        "id": api_id,
        "key": api_key,
        "words": words,
    }

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        return {"code": 400, "msg": f"HTTP error: {e.code} {e.reason}"}
    except urllib.error.URLError as e:
        return {"code": 400, "msg": f"Network error: {e.reason}"}
    except json.JSONDecodeError:
        return {"code": 400, "msg": "API returned non-JSON data"}
    except Exception as e:
        return {"code": 400, "msg": f"Request failed: {str(e)}"}


def safe_val(d: dict, *keys, default="-"):
    """从字典中按多个key依次取值，返回第一个非空值"""
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() and str(v).strip() != "-":
            return str(v).strip()
    return default


def format_contacts(contacts: dict) -> list:
    """Format contact information."""
    lines = []
    if not contacts or not isinstance(contacts, dict):
        return lines

    phones = contacts.get("phoneNumber", [])
    if phones and isinstance(phones, list):
        vals = set()
        for p in phones:
            v = p.get("value", "")
            if v and v not in vals:
                vals.add(v)
                lines.append(f"  📞 Phone: {v}")

    emails = contacts.get("email", [])
    if emails and isinstance(emails, list):
        vals = set()
        for e in emails:
            v = e.get("value", "")
            if v and v not in vals:
                vals.add(v)
                lines.append(f"  📧 Email: {v}")

    websites = contacts.get("website", [])
    if websites and isinstance(websites, list):
        vals = set()
        for w in websites:
            v = w.get("value", "")
            if v and v not in vals:
                vals.add(v)
                lines.append(f"  🌐 Website: {v}")

    return lines


def format_array_field(items: list, name_key: str, val_key: str,
                       item_label: str, max_show: int = 5, suffix: str = "") -> list:
    """Format array-type fields (shareholders, personnel, etc.)."""
    lines = []
    if not items or not isinstance(items, list) or len(items) == 0:
        return lines
    lines.append("")
    lines.append(f"  {item_label}:")
    for i, item in enumerate(items[:max_show], 1):
        name = item.get(name_key, "")
        val = item.get(val_key, "")
        if name:
            txt = f"    {i}. {name}"
            if val and suffix:
                txt += f"  {val}{suffix}"
            elif val:
                txt += f"  {val}"
            lines.append(txt)
    if len(items) > max_show:
        lines.append(f"    ... {len(items)} total")
    return lines


def format_result(data: dict) -> str:
    """Format API response into readable text."""
    if data.get("code") != 200:
        msg = data.get("msg", "Unknown error")
        return f"❌ Query failed: {msg}"

    info = data.get("data", data)
    name = safe_val(info, "companyName", "entName", "企业名称")

    lines = []
    lines.append("=" * 50)
    lines.append(f"  🏢 {name}")
    lines.append("=" * 50)

    credit = safe_val(info, "creditNo", "creditCode", "creditcode", "统一社会信用代码")
    if credit != "-":
        lines.append(f"  📌 Credit Code: {credit}")

    lines.append(f"  📌 Legal Rep: {safe_val(info, 'legalPerson', 'frName', '法定代表人')}")
    lines.append(f"  📌 Registered Capital: {safe_val(info, 'capital', 'regCapital', 'regcap', '注册资本')}")
    lines.append(f"  📌 Status: {safe_val(info, 'companyStatus', 'regStatus', 'regstatus', '经营状态')}")
    lines.append(f"  📌 Established: {safe_val(info, 'establishDate', 'esDate', 'esdate', '成立日期')}")
    lines.append(f"  📌 Type: {safe_val(info, 'companyType', 'entType', 'enttype', '企业类型')}")
    lines.append(f"  📌 Authority: {safe_val(info, 'authority', 'regOrg', 'regorg', '登记机关')}")
    lines.append(f"  📌 Address: {safe_val(info, 'companyAddress', 'regAddr', 'regaddr', 'address', '注册地址')}")
    lines.append(f"  📌 Industry: {safe_val(info, 'industry', 'industryPhy', '行业')}")

    real_cap = safe_val(info, 'realCapital', '实收资本')
    if real_cap != "-":
        lines.append(f"  📌 Paid-in Capital: {real_cap}")

    taxpayer = safe_val(info, 'taxpayerQual', 'taxpayerqual', '纳税人资质')
    if taxpayer != "-":
        lines.append(f"  📌 Taxpayer Type: {taxpayer}")

    emp = safe_val(info, 'empCount', 'empcount', '人员规模')
    if emp != "-":
        lines.append(f"  📌 Employees: {emp}")

    issue = safe_val(info, 'issueDate', '核准日期')
    if issue != "-":
        lines.append(f"  📌 Approval Date: {issue}")

    op_start = safe_val(info, 'operationStartdate', '营业起始日期')
    op_end = safe_val(info, 'operationEnddate', '营业截止日期')
    if op_start != "-" and op_end != "-":
        lines.append(f"  📌 Operating Period: {op_start} to {op_end}")
    elif op_start != "-":
        lines.append(f"  📌 Operating Start: {op_start}")

    scope = safe_val(info, 'businessScope', 'opScope', 'opscope', '经营范围')
    if scope != "-":
        lines.append(f"  📌 Business Scope: {scope}")

    # Contact info
    contacts = info.get("contacts")
    if contacts:
        contact_lines = format_contacts(contacts)
        lines.extend(contact_lines)

    # Historical names
    hist = safe_val(info, 'historyNames')
    if hist != "-":
        lines.append(f"  📌 Former Names: {hist}")

    # Shareholders
    shareholders = info.get("shareholders", info.get("holders", info.get("股东信息", [])))
    if shareholders and isinstance(shareholders, list):
        sh_lines = format_array_field(
            shareholders, "name", "amount",
            "👥 Shareholders", max_show=5
        )
        if not sh_lines:
            sh_lines = format_array_field(
                shareholders, "股东名称", "出资比例",
                "👥 Shareholders", max_show=5
            )
        lines.extend(sh_lines)

    # Key personnel
    persons = info.get("keyPersons", info.get("persons", info.get("主要人员", [])))
    if persons and isinstance(persons, list):
        p_lines = format_array_field(
            persons, "name", "position",
            "👤 Key Personnel", max_show=10
        )
        if not p_lines:
            p_lines = format_array_field(
                persons, "姓名", "职务",
                "👤 Key Personnel", max_show=10
            )
        lines.extend(p_lines)

    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    # .env priority: scripts/.env (per-skill) > ~/.wmyskills/.env (shared).
    # load_dotenv never overrides, so script dir loads first, user global second.
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    load_dotenv(dotenv_path=Path.home() / ".wmyskills" / ".env")
    if len(sys.argv) < 2:
        print("❌ Please provide a company name or Unified Social Credit Code")
        print(f"Usage: python {sys.argv[0]} \"company name or credit code\"")
        sys.exit(1)

    words = sys.argv[1].strip()
    if not words:
        print("❌ Query content cannot be empty")
        sys.exit(1)

    result = query_company(words)
    output = format_result(result)

    print(output)


if __name__ == "__main__":
    main()
