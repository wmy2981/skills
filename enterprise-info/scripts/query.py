#!/usr/bin/env python3
"""企业工商信息查询 - 通过接口盒子API查询企业工商登记信息"""

import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

API_URL = "https://cn.apihz.cn/api/shiming/qyinfo.php"


def query_company(words: str) -> dict:
    """查询企业信息，返回原始 JSON 响应"""
    api_id = os.environ.get("JKHZ_ID")
    api_key = os.environ.get("JKHZ_KEY")

    if not api_id or not api_key:
        return {"code": 400, "msg": "环境变量 JKHZ_ID 或 JKHZ_KEY 未设置"}

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
        return {"code": 400, "msg": f"HTTP错误: {e.code} {e.reason}"}
    except urllib.error.URLError as e:
        return {"code": 400, "msg": f"网络错误: {e.reason}"}
    except json.JSONDecodeError:
        return {"code": 400, "msg": "API返回非JSON格式数据"}
    except Exception as e:
        return {"code": 400, "msg": f"请求异常: {str(e)}"}


def safe_val(d: dict, *keys, default="-"):
    """从字典中按多个key依次取值，返回第一个非空值"""
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() and str(v).strip() not in ("-", "0"):
            return str(v).strip()
    return default


def format_contacts(contacts: dict) -> list:
    """格式化联系方式"""
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
                lines.append(f"  📞 联系电话：{v}")

    emails = contacts.get("email", [])
    if emails and isinstance(emails, list):
        vals = set()
        for e in emails:
            v = e.get("value", "")
            if v and v not in vals:
                vals.add(v)
                lines.append(f"  📧 邮箱：{v}")

    websites = contacts.get("website", [])
    if websites and isinstance(websites, list):
        vals = set()
        for w in websites:
            v = w.get("value", "")
            if v and v not in vals:
                vals.add(v)
                lines.append(f"  🌐 网站：{v}")

    return lines


def format_array_field(items: list, name_key: str, val_key: str,
                       item_label: str, max_show: int = 5, suffix: str = "") -> list:
    """格式化数组型字段（如股东、人员等）"""
    lines = []
    if not items or not isinstance(items, list) or len(items) == 0:
        return lines
    lines.append("")
    lines.append(f"  {item_label}：")
    for i, item in enumerate(items[:max_show], 1):
        name = item.get(name_key, "")
        val = item.get(val_key, "")
        if name:
            txt = f"    {i}. {name}"
            if val and suffix:
                txt += f"　{val}{suffix}"
            elif val:
                txt += f"　{val}"
            lines.append(txt)
    if len(items) > max_show:
        lines.append(f"    ... 共 {len(items)} 项")
    return lines


def format_result(data: dict) -> str:
    """将API返回的数据格式化为易读文本"""
    if data.get("code") != 200:
        msg = data.get("msg", "未知错误")
        return f"❌ 查询失败：{msg}"

    info = data.get("data", data)
    name = safe_val(info, "companyName", "entName", "企业名称")

    lines = []
    lines.append("=" * 50)
    lines.append(f"  🏢 {name}")
    lines.append("=" * 50)

    # 核心字段
    credit = safe_val(info, "creditNo", "creditCode", "creditcode", "统一社会信用代码")
    if credit != "-":
        lines.append(f"  📌 统一社会信用代码：{credit}")

    lines.append(f"  📌 法定代表人：{safe_val(info, 'legalPerson', 'frName', '法定代表人')}")
    lines.append(f"  📌 注册资本：{safe_val(info, 'capital', 'regCapital', 'regcap', '注册资本')}")
    lines.append(f"  📌 经营状态：{safe_val(info, 'companyStatus', 'regStatus', 'regstatus', '经营状态')}")
    lines.append(f"  📌 成立日期：{safe_val(info, 'establishDate', 'esDate', 'esdate', '成立日期')}")
    lines.append(f"  📌 企业类型：{safe_val(info, 'companyType', 'entType', 'enttype', '企业类型')}")
    lines.append(f"  📌 登记机关：{safe_val(info, 'authority', 'regOrg', 'regorg', '登记机关')}")
    lines.append(f"  📌 注册地址：{safe_val(info, 'companyAddress', 'regAddr', 'regaddr', 'address', '注册地址')}")
    lines.append(f"  📌 行业：{safe_val(info, 'industry', 'industryPhy', '行业')}")

    real_cap = safe_val(info, 'realCapital', '实收资本', '实缴资本')
    if real_cap != "-":
        lines.append(f"  📌 实缴资本：{real_cap}")

    taxpayer = safe_val(info, 'taxpayerQual', 'taxpayerqual', '纳税人资质')
    if taxpayer != "-":
        lines.append(f"  📌 纳税人资质：{taxpayer}")

    emp = safe_val(info, 'empCount', 'empcount', '人员规模')
    if emp != "-":
        lines.append(f"  📌 人员规模：{emp}")

    issue = safe_val(info, 'issueDate', '核准日期', '批准日期')
    if issue != "-":
        lines.append(f"  📌 核准日期：{issue}")

    op_start = safe_val(info, 'operationStartdate', '营业起始日期')
    op_end = safe_val(info, 'operationEnddate', '营业截止日期')
    if op_start != "-" and op_end != "-":
        lines.append(f"  📌 营业期限：{op_start} 至 {op_end}")
    elif op_start != "-":
        lines.append(f"  📌 营业起始：{op_start}")

    # 经营范围
    scope = safe_val(info, 'businessScope', 'opScope', 'opscope', '经营范围')
    if scope != "-":
        lines.append(f"  📌 经营范围：{scope}")

    # 联系信息
    contacts = info.get("contacts")
    if contacts:
        contact_lines = format_contacts(contacts)
        lines.extend(contact_lines)

    # 历史名称
    hist = safe_val(info, 'historyNames', '历史名称')
    if hist != "-":
        lines.append(f"  📌 曾用名：{hist}")

    # 股东信息
    shareholders = info.get(
        "股东信息",
        info.get("shareholders",
                 info.get("holders", []))
    )
    if shareholders and isinstance(shareholders, list):
        sh_lines = format_array_field(
            shareholders, "股东名称", "出资比例",
            "👥 股东信息", max_show=5, suffix=""
        )
        # 如果没有"股东名称"字段，试试其他字段名
        if not sh_lines:
            sh_lines = format_array_field(
                shareholders, "name", "amount",
                "👥 股东信息", max_show=5
            )
        lines.extend(sh_lines)

    # 主要人员
    persons = info.get("主要人员", info.get("persons", info.get("keyPersons", [])))
    if persons and isinstance(persons, list):
        p_lines = format_array_field(
            persons, "姓名", "职务",
            "👤 主要人员", max_show=10
        )
        if not p_lines:
            p_lines = format_array_field(
                persons, "name", "position",
                "👤 主要人员", max_show=10
            )
        lines.extend(p_lines)

    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print("❌ 请提供企业名称或统一社会信用代码")
        print(f"用法: python3 {sys.argv[0]} \"企业名称或信用代码\"")
        sys.exit(1)

    words = sys.argv[1].strip()
    if not words:
        print("❌ 查询内容不能为空")
        sys.exit(1)

    result = query_company(words)
    output = format_result(result)

    print(output)


if __name__ == "__main__":
    main()
