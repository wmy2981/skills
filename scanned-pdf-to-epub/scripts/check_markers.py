#!/usr/bin/env python3
"""检查 Markdown 中的流程标记（PAGE / CH / __）并输出报告。

用法:
    python scripts/check_markers.py <md_file...> [-o report.txt]

可检查各批次 batch_XXX.md，也可检查合并后的 draft.md。检查项:
    - PAGE: 列出全部页码，检查连续性（缺号 / 重复 / 乱序）
    - CH:   列出全部锚点与行号，检查层级是否跳级（如 CH1 直接跳 CH3，作警告）
    - __:   列出全部跨页连接标记，检查行尾 / 行首是否成对

退出码: 0 = 无问题（可含警告），1 = 发现需重跑的问题（PAGE 缺失/乱序、__ 不成对）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PAGE_RE = re.compile(r"<!--\s*PAGE\s+(\d{4})\s*-->")
CH_RE = re.compile(r"<!--\s*CH(\d)\s*:\s*(.*?)\s*-->")
TAIL_UU = re.compile(r"__\s*$")
HEAD_UU = re.compile(r"^\s*__")


def force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def analyze(text: str):
    """返回 (pages, chs, tail_uus, head_uus)。pages=[(页码,行号)]，chs=[(层级,标题,行号)]，uu=[行号]。"""
    pages, chs, tail_uus, head_uus = [], [], [], []
    for i, line in enumerate(text.splitlines(), 1):
        m = PAGE_RE.search(line)
        if m:
            pages.append((int(m.group(1)), i))
        m = CH_RE.search(line)
        if m:
            chs.append((int(m.group(1)), m.group(2).strip(), i))
        if TAIL_UU.search(line):
            tail_uus.append(i)
        if HEAD_UU.search(line):
            head_uus.append(i)
    return pages, chs, tail_uus, head_uus


def inspect(path: Path) -> tuple[list[str], list[str], list[str]]:
    """返回 (报告行, 问题列表[FAIL], 警告列表[WARN])。"""
    text = path.read_text(encoding="utf-8")
    pages, chs, tail_uus, head_uus = analyze(text)

    lines = [f"文件: {path}"]
    probs: list[str] = []
    warns: list[str] = []

    pno = [p for p, _ in pages]
    lines.append(f"PAGE 标记 {len(pages)} 个: {pno if pno else '（无）'}")
    if pno:
        for a, b in zip(pno, pno[1:]):
            if b <= a:
                probs.append(f"PAGE 顺序异常: {a} → {b}（重复或乱序）")
        seen = set(pno)
        missing = [x for x in range(min(pno), max(pno) + 1) if x not in seen]
        if missing:
            probs.append(f"PAGE 缺失页码: {missing}")

    lines.append(f"CH 锚点 {len(chs)} 个:")
    prev = None  # None 表示尚无锚点；首个锚点不判跳级（原书可能直接以章开头）
    for lv, t, ln in chs:
        lines.append(f"  CH{lv}: {t}（L{ln}）")
        if prev is not None and lv > prev + 1:
            warns.append(f"L{ln} CH{prev} → CH{lv} 层级跳级（缺中间层级，可能需人工确认）")
        prev = lv

    lines.append(
        f"__ 连接标记: 行尾 {len(tail_uus)} 个（L{tail_uus}）、行首 {len(head_uus)} 个（L{head_uus}）"
    )
    if len(tail_uus) != len(head_uus):
        diff = len(tail_uus) - len(head_uus)
        # 跨批次边界判断：切口单侧出现在批次首/末（以 PAGE 标记界定批次范围）
        page_linenos = [ln for _, ln in pages]
        boundary = False
        if diff == 1 and tail_uus and page_linenos:
            # 行尾 __ 出现在最后一个 PAGE 标记之后 → 跨出到下一批
            boundary = tail_uus[-1] > page_linenos[-1]
        if diff == -1 and head_uus and page_linenos:
            # 行首 __ 出现在首个 PAGE 标记之后、次个 PAGE 标记之前 → 承接上一批
            boundary = head_uus[0] > page_linenos[0] and (len(page_linenos) < 2 or head_uus[0] < page_linenos[1])
        if boundary:
            warns.append("__ 切口单侧出现在批次首/末（可能是跨批次切口），合并后须复查成对")
        else:
            probs.append(f"__ 行尾({len(tail_uus)}) 与 行首({len(head_uus)}) 数量不匹配，跨页切口未成对")

    return lines, probs, warns


def main() -> None:
    force_utf8()
    ap = argparse.ArgumentParser(description="检查 Markdown 流程标记（PAGE/CH/__）")
    ap.add_argument("files", nargs="+", help="要检查的 Markdown 文件（可多个）")
    ap.add_argument("-o", "--output", help="报告输出路径（默认输出到 stdout）")
    args = ap.parse_args()

    all_lines: list[str] = []
    total_probs = 0
    total_warns = 0
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"找不到文件：{p}")
            sys.exit(1)
        lines, probs, warns = inspect(p)
        all_lines.extend(lines)
        for w in warns:
            all_lines.append(f"[WARN] {w}")
        for e in probs:
            all_lines.append(f"[FAIL] {e}")
        all_lines.append("")
        total_probs += len(probs)
        total_warns += len(warns)

    all_lines.append(f"共检查 {len(args.files)} 个文件：{total_probs} 项问题、{total_warns} 项警告。")
    report = "\n".join(all_lines)

    if args.output:
        Path(args.output).write_text(report + "\n", encoding="utf-8")
        print(f"标记检查报告 → {args.output}")
    else:
        print(report)
    print(("通过" if total_probs == 0 else f"{total_probs} 项问题需处理") + f"，{total_warns} 项警告")
    sys.exit(0 if total_probs == 0 else 1)


if __name__ == "__main__":
    main()
