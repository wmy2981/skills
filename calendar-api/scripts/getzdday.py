#!/usr/bin/env python3
"""万年历 - 取指定日期信息（接口盒子 API）"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

API_URL = "https://cn.apihz.cn/api/time/getzdday.php"
TZ = ZoneInfo("Asia/Shanghai")


def get_calendar_info(year: int, month: int, day: int) -> dict:
    api_id = os.environ.get("JKHZ_ID", "")
    api_key = os.environ.get("JKHZ_KEY", "")
    if not api_id or not api_key:
        return {"error": "环境变量 JKHZ_ID 或 JKHZ_KEY 未设置"}

    params = urllib.parse.urlencode({
        "id": api_id,
        "key": api_key,
        "nian": year,
        "yue": month,
        "ri": day,
    })
    url = f"{API_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "CalendarSkill/1.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# 字段分组展示，按重要程度排序
DISPLAY_GROUPS = [
    ("📆 公历", [
        ("ynian", "年"), ("yyue", "月"), ("yri", "日"),
        ("xingqi", "星期"), ("YLLEAP", "闰年"),
    ]),
    ("🌙 农历", [
        ("nnian", "年"), ("nyue", "月"), ("nri", "日"),
    ]),
    ("🎊 节日", [
        ("jieri", "阳历节日"), ("YIFESTIVAL", "阴历节日"),
    ]),
    ("⭐ 星座与生肖", [
        ("xingzuo", "星座"), ("shengxiao", "生肖"), ("DAYSHENGXIAO", "日生肖"),
    ]),
    ("📜 干支", [
        ("YEARGANZHI", "年干支"), ("ganzhiyue", "月干支"), ("ganzhiri", "日干支"),
        ("DAYNAYIN", "日纳音"),
    ]),
    ("🌿 节气与物候", [
        ("jieqi", "节气"), ("JIEQICN", "节气描述"), ("WUHOU", "物候"),
        ("SHUJIU", "数九"), ("FU", "三伏"),
    ]),
    ("☯ 宜忌", [
        ("yi", "宜"), ("ji", "忌"),
        ("DAYJISHEN", "吉神宜趋"), ("DAYXIONGSHA", "凶神宜忌"),
    ]),
    ("🧭 方位", [
        ("DAYPOSITIONXI", "喜神"), ("DAYPOSITIONYANGGUI", "阳贵神"),
        ("DAYPOSITIONYINGUI", "阴贵神"), ("DAYPOSITIONFU", "福神"),
        ("DAYPOSITIONCAI", "财神"),
    ]),
    ("⚠️ 冲煞", [
        ("xiangchong", "相冲"), ("DAYCHONGDESC", "日冲"),
        ("DAYTIANSHEN", "天神"), ("DAYTIANSHENTYPE", "黄/黑道"), ("DAYTIANSHENLUCK", "吉凶"),
    ]),
    ("🔢 值星与神煞", [
        ("ZHIXING", "值星（十二值星）"), ("shiershen", "十二神"),
        ("liuyao", "六曜"), ("YUEXIANG", "月相"),
    ]),
    ("🌟 星宿", [
        ("xingxiu", "星宿"), ("XIU", "二十八宿"), ("XIUANIMAL", "宿动物"),
        ("XIULUCK", "宿吉凶"), ("ZHENG", "七曜"), ("GONG", "四宫"), ("SHOU", "四神兽"),
    ]),
    ("📖 彭祖与胎神", [
        ("pengzu", "彭祖百忌"),
        ("taishen", "本日胎神"), ("MONTHPOSITIONTAI", "本月胎神"),
        ("DAYPOSITIONTAISUI", "太岁方位"),
    ]),
    ("📅 佛道历", [
        ("FOTO", "佛历"), ("TAO", "道历"), ("yisilan", "伊斯兰历"),
    ]),
    ("📊 其他", [
        ("rulueri", "儒略日"), ("DAYNINESTAR", "九星值日"),
        ("nianwuxing", "年五行"), ("yuewuxing", "月五行"), ("riwuxing", "日五行"),
        ("jijie", "季节"), ("DAYSOFYEAR", "本年总天数"), ("DAYSINYEAR", "当年第几天"),
    ]),
]


def format_output(data: dict, year: int, month: int, day: int) -> str:
    """将 API 返回格式化为可读文本"""
    if "error" in data:
        return f"❌ 查询失败: {data['error']}"

    if data.get("code") == 400:
        return f"❌ API 错误: {data.get('msg', '未知错误')}"

    if data.get("code") != 200 and "ynian" not in data:
        return f"❌ API 错误: {data.get('msg', '未知错误')}\n原始数据: {json.dumps(data, ensure_ascii=False)}"

    lines = [f"📅 {year}年{month}月{day}日 万年历", "=" * 30]

    for group_name, fields in DISPLAY_GROUPS:
        items = []
        for key, label in fields:
            val = data.get(key)
            if val is not None and str(val).strip() and str(val).strip() != "FALSE":
                # 格式化分隔符
                display = str(val).replace("|", "｜")
                items.append(f"{label}: {display}")
        if items:
            lines.append(f"\n{group_name}")
            for item in items:
                lines.append(f"  {item}")

    return "\n".join(lines)


def main():
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    parser = argparse.ArgumentParser(description="万年历 - 查询指定日期信息")
    parser.add_argument("date", nargs="?", help="日期，格式 YYYY-MM-DD，默认今天")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = parser.parse_args()

    if args.date:
        try:
            dt = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ 日期格式错误: {args.date}，应为 YYYY-MM-DD")
            sys.exit(1)
    else:
        dt = datetime.now(TZ)

    data = get_calendar_info(dt.year, dt.month, dt.day)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_output(data, dt.year, dt.month, dt.day))


if __name__ == "__main__":
    main()
