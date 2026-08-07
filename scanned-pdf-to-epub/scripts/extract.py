#!/usr/bin/env python3
"""PDF 拆页渲染：把扫描版 PDF 的每一页渲染为 PNG/JPG 图片，保持页码顺序。

用法:
    python scripts/extract.py <input.pdf> -o book/pages [--dpi 300] [--start 1] [--end N]
    python scripts/extract.py --check            # 仅检查依赖是否齐全

产物: book/pages/page_0001.png, page_0002.png, ...（1 起连续编号）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def force_utf8() -> None:
    """Windows 终端默认 GBK，强制 stdout/stderr 用 UTF-8，避免中文输出乱码。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def check_deps() -> bool:
    import shutil

    missing = []
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        try:
            import fitz  # noqa: F401
        except ImportError:
            missing.append("pymupdf（pip install pymupdf）")
    has_pandoc = shutil.which("pandoc") is not None or _importable("pypandoc")
    has_ebooklib = _importable("ebooklib")
    if not (has_pandoc or has_ebooklib):
        missing.append("pandoc/pypandoc 或 ebooklib（pip install pypandoc-binary / ebooklib；打包必需）")
    if missing:
        print("缺少依赖：" + "; ".join(missing))
        return False
    print("依赖齐全：pymupdf + pandoc/pypandoc（或 ebooklib 兜底）")
    return True


def main() -> None:
    force_utf8()
    ap = argparse.ArgumentParser(description="把 PDF 每页渲染为图片，保持页码顺序")
    ap.add_argument("input", nargs="?", help="输入 PDF 路径")
    ap.add_argument("-o", "--outdir", default="pages", help="输出图片目录（默认 pages）")
    ap.add_argument("--dpi", type=int, default=300, help="渲染 DPI（默认 300，中文小字建议 ≥300）")
    ap.add_argument("--start", type=int, default=1, help="起始页（从 1 计，默认 1）")
    ap.add_argument("--end", type=int, help="结束页（默认最后一页）")
    ap.add_argument("--format", default="png", choices=["png", "jpg"], help="图片格式（默认 png）")
    ap.add_argument("--check", action="store_true", help="仅检查依赖并退出")
    args = ap.parse_args()

    if args.check:
        sys.exit(0 if check_deps() else 1)
    if not args.input:
        ap.error("缺少输入 PDF 路径")

    try:
        import pymupdf as fitz  # PyMuPDF 1.28+ 推荐入口；老版本回退 fitz
    except ImportError:
        import fitz

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(args.input)
    total = doc.page_count
    start = max(1, args.start)
    end = min(total, args.end or total)
    if start > end:
        print(f"页码范围无效：start={start} > end={end}（总页数 {total}）")
        sys.exit(1)

    zoom = args.dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    print(f"开始拆页：共 {total} 页，渲染 {start}–{end} 页，{args.dpi} DPI，格式 {args.format}")

    for i in range(start - 1, end):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        name = outdir / f"page_{i + 1:04d}.{args.format}"
        pix.save(str(name))
        print(f"  {name.name}  {int(page.rect.width)}x{int(page.rect.height)}px")

    print(f"完成：{end - start + 1} 页 → {outdir}")
    doc.close()


if __name__ == "__main__":
    main()
