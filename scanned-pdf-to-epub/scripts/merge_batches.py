#!/usr/bin/env python3
"""按批次序号顺序合并 raws/ 下所有 batch_XXX.md 为 draft.md。

用法:
    python scripts/merge_batches.py <raws_dir> [-o draft.md]

合并保留各批内的 PAGE/CH/__ 标记（供校对定位与跨批次 __ 切口衔接）；
合并时校验批次序号连续（1..K 无缺，缺失会破坏页码/切口连续性）。
合并后规范化行距：任意两个相邻非空行之间恰好 1 个空行
（跨页 __ 切口连接的行除外——上一行以 __ 结尾或下一行以 __ 开头时保持紧密相连）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BATCH_RE = re.compile(r"^batch_(\d{3})\.md$")
TAIL_UU_RE = re.compile(r"__\s*$")
HEAD_UU_RE = re.compile(r"^\s*__")


def force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def normalize_spacing(text: str) -> str:
    """规范化行距：任意两个相邻非空行之间恰好 1 个空行。

    跨页 `__` 切口连接的行（上一行以 __ 结尾或下一行以 __ 开头）之间不放空行，
    保持跨页段落的两部分紧密相连（供校对阶段合并为一段）。
    合并多个空行为单个空行，缺失的补上；文件以单个换行结尾。
    """
    out: list[str] = []
    prev_content = False  # 上一个输出行是否为内容行（非空行）
    prev_tail_uu = False  # 上一个内容行是否以 __ 结尾
    for line in text.splitlines():
        if not line.strip():
            continue
        if out and prev_content and out[-1] != "" and not (prev_tail_uu or HEAD_UU_RE.search(line)):
            out.append("")
        out.append(line)
        prev_content = True
        prev_tail_uu = bool(TAIL_UU_RE.search(line))
    return "\n".join(out) + ("\n" if out else "")


def main() -> None:
    force_utf8()
    ap = argparse.ArgumentParser(description="按序号顺序合并各批次 batch_XXX.md 为 draft.md")
    ap.add_argument("raws_dir", help="批次文件目录（含 batch_XXX.md）")
    ap.add_argument("-o", "--output", default="draft.md", help="输出 draft.md 路径（默认 draft.md）")
    args = ap.parse_args()

    raws = Path(args.raws_dir)
    if not raws.is_dir():
        print(f"目录不存在：{raws}")
        sys.exit(1)

    batches = sorted(
        (p for p in raws.iterdir() if BATCH_RE.match(p.name)),
        key=lambda p: int(BATCH_RE.match(p.name).group(1)),
    )
    if not batches:
        print(f"未在 {raws} 中找到 batch_XXX.md")
        sys.exit(1)

    nums = [int(BATCH_RE.match(p.name).group(1)) for p in batches]
    if nums != list(range(1, len(nums) + 1)):
        print(f"警告：批次序号不连续 {nums}，缺失批次会导致页码/切口断裂，请先检查各批次。")

    parts = []
    for p in batches:
        t = p.read_text(encoding="utf-8")
        parts.append(t if t.endswith("\n") else t + "\n")
    draft = normalize_spacing("".join(parts))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(draft, encoding="utf-8")
    print(f"已合并 {len(batches)} 个批次（{nums[0]}–{nums[-1]}）→ {out}（行距已规范化为段间 1 空行）")


if __name__ == "__main__":
    main()
