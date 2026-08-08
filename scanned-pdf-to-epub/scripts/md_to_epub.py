#!/usr/bin/env python3
"""book.md → EPUB：按 Markdown 标题层级（h1/h2/h3）切分章节，生成导航目录，打包 EPUB。

优先使用 pandoc（Markdown → EPUB 事实标准，自动生成可点击导航目录）；
pandoc 不可用时回退用 ebooklib 手工组包（同样生成两级导航目录）。

用法:
    python scripts/md_to_epub.py book/book.md -o book/book.epub --title "书名" --author "作者" --lang zh [--cover book/pages/page_0001.png]

输入约定（来自 SKILL.md 阶段 6）：book.md 已是干净的层级化 Markdown，
h1 = 全书最高级标题（有部/卷则为部/卷，无则为章），h2、h3 依层级递减；无锚点注释、无版权页候选标记。
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


def force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Markdown 解析：拆成带层级的 section
# --------------------------------------------------------------------------- #

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_md(md_text: str) -> list[dict]:
    """把 markdown 拆为 [{'level': int, 'title': str, 'lines': [str, ...]}, ...]。

    h1 之前的文字并入首个 level=0 的假 section（书前内容）。
    """
    sections: list[dict] = []
    for line in md_text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            sections.append(
                {"level": len(m.group(1)), "title": m.group(2).strip(), "lines": []}
            )
        else:
            if not sections:
                sections.append({"level": 0, "title": "", "lines": []})
            sections[-1]["lines"].append(line)
    return sections


# --------------------------------------------------------------------------- #
# 极简 Markdown → HTML（ebooklib 兜底用；pandoc 路径无需此转换）
# --------------------------------------------------------------------------- #

def inline_md(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def block_to_html(lines: list[str]) -> str:
    """把一组 markdown 行转成 HTML（段落 / 列表 / 表格 / 代码块）。"""
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("```"):  # 代码块
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # 跳过结束 ```
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
        elif line.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            # 表格：表头 + 分隔行 + 数据行
            def cells(row: str) -> list[str]:
                return [c.strip() for c in row.strip().strip("|").split("|")]

            rows = [cells(line)]
            i += 2  # 跳过表头与分隔行
            while i < n and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            thead = "".join(f"<th>{inline_md(c)}</th>" for c in rows[0])
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in r) + "</tr>"
                for r in rows[1:]
            )
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>")
        elif re.match(r"^\s*[-*+]\s+", line):  # 无序列表
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i].strip()):
                text = re.sub(r"^\s*[-*+]\s+", "", lines[i].strip())
                items.append(f"<li>{inline_md(text)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
        elif re.match(r"^\s*\d+[.)]\s+", line):  # 有序列表
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i].strip()):
                text = re.sub(r"^\s*\d+[.)]\s+", "", lines[i].strip())
                items.append(f"<li>{inline_md(text)}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
        else:  # 段落（合并连续非空行）
            buf = [line]
            i += 1
            while i < n and lines[i].strip() and not lines[i].strip().startswith("```") and not lines[i].strip().startswith("|") and not re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            out.append("<p>" + inline_md("　".join(buf)) + "</p>")
    return "\n".join(out)


def slug(text: str) -> str:
    """生成稳定锚点 id。"""
    return "h-" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def pandoc_extra_args(title: str, author: str, lang: str, cover: str = "") -> list[str]:
    args = ["--toc", "--toc-depth=2", "--split-level=1", f"--metadata=title={title}"]
    if author:
        args.append(f"--metadata=author={author}")
    if lang:
        args.append(f"--metadata=lang={lang}")
    if cover:
        args.append(f"--epub-cover-image={cover}")
    return args


# --------------------------------------------------------------------------- #
# 打包路径一：pandoc
# --------------------------------------------------------------------------- #

def build_with_pandoc(md_path: Path, out_path: Path, title: str, author: str, lang: str, cover: str = "") -> None:
    cmd = ["pandoc", str(md_path), "-o", str(out_path)] + pandoc_extra_args(title, author, lang, cover)
    subprocess.run(cmd, check=True)
    print(f"已用 pandoc 生成 {out_path}")


# --------------------------------------------------------------------------- #
# 打包路径二：pypandoc（pip 安装 pypandoc-binary 捆绑的 pandoc）
# --------------------------------------------------------------------------- #

def build_with_pypandoc(md_path: Path, out_path: Path, title: str, author: str, lang: str, cover: str = "") -> None:
    import pypandoc

    pypandoc.convert_file(
        str(md_path), "epub", outputfile=str(out_path), extra_args=pandoc_extra_args(title, author, lang, cover)
    )
    print(f"已用 pypandoc（内置 pandoc {pypandoc.get_pandoc_version()}）生成 {out_path}")


# --------------------------------------------------------------------------- #
# 打包路径三：ebooklib 兜底
# --------------------------------------------------------------------------- #

def build_with_ebooklib(md_path: Path, out_path: Path, title: str, author: str, lang: str, cover: str = "") -> None:
    from ebooklib import epub

    md_text = md_path.read_text(encoding="utf-8")
    sections = parse_md(md_text)

    book = epub.EpubBook()
    book.set_identifier(hashlib.md5(str(md_path).encode()).hexdigest())
    book.set_title(title or md_path.stem)
    book.set_language(lang or "zh")
    if author:
        book.add_author(author)

    if cover:  # 封面图：显式 EpubImage + cover-image 属性（PNG/JPG 均可）
        cov = Path(cover)
        img = epub.EpubImage()
        img.file_name = "cover" + cov.suffix.lower()
        img.media_type = "image/png" if cov.suffix.lower() == ".png" else "image/jpeg"
        img.content = cov.read_bytes()
        img.properties = ["cover-image"]
        book.add_item(img)
        book.add_metadata(None, "meta", "", OrderedDict([("name", "cover"), ("content", img.id)]))

    toc: list = []
    chapters: list[object] = []
    file_no = 0

    def make_chapter(sec_title: str, body_html: str, filename: str, toc_entry: list | None = None) -> epub.EpubHtml:
        nonlocal file_no
        file_no += 1
        # ebooklib 0.20 的 EpubHtml/Link 不自动生成 uid，必须显式给出，否则 NCX 生成失败
        ch = epub.EpubHtml(title=sec_title, file_name=filename, uid=f"item-{filename}", lang=lang)
        ch.content = body_html
        book.add_item(ch)
        chapters.append(ch)
        if toc_entry is not None:
            toc.append(toc_entry)
        return ch

    # 书前内容（h1 之前的文字）
    front = [s for s in sections if s["level"] == 0]
    if front:
        body = "".join(f"<p>{inline_md(line)}</p>" for line in front[0]["lines"] if line.strip())
        if body.strip():
            make_chapter("前言", f"<h2>前言</h2>{body}", "front.xhtml")

    # 章节：h1 为顶级，h2/h3 渲染为章内标题并进入目录
    cur_ch: epub.EpubHtml | None = None
    cur_html: list[str] = []
    h2_ids: list[tuple[str, str]] = []  # (id, text) 供目录二级跳转

    def flush_chapter() -> None:
        nonlocal cur_ch, cur_html, h2_ids
        if cur_ch is None:
            return
        body = "\n".join(cur_html)
        cur_ch.content = body  # 关键：把累计的章节 HTML 写回章节文件
        if h2_ids:
            sub_links = [epub.Link(f"{cur_ch.file_name}#{i}", t, uid=f"sub-{cur_ch.file_name}-{i}") for i, t in h2_ids]
            toc.append([cur_ch, sub_links])
        else:
            toc.append(cur_ch)
        cur_html = []
        h2_ids = []

    for s in sections:
        if s["level"] == 0:
            continue
        if s["level"] == 1:
            flush_chapter()
            file_no += 1
            cur_ch = epub.EpubHtml(title=s["title"], file_name=f"ch{file_no:03d}.xhtml", uid=f"item-ch{file_no:03d}", lang=lang)
            cur_ch.content = ""
            book.add_item(cur_ch)
            chapters.append(cur_ch)
            cur_html.append(f"<h1>{inline_md(s['title'])}</h1>")
        elif s["level"] == 2:
            _id = slug(s["title"])
            cur_html.append(f'<h2 id="{_id}">{inline_md(s["title"])}</h2>')
            h2_ids.append((_id, s["title"]))
        else:
            cur_html.append(f"<h{min(s['level'], 6)}>{inline_md(s['title'])}</h{min(s['level'], 6)}>")
        if s["lines"]:
            cur_html.append(block_to_html(s["lines"]))
    flush_chapter()

    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + [c for c in chapters if hasattr(c, "file_name")]
    epub.write_epub(str(out_path), book)
    print(f"已用 ebooklib 兜底生成 {out_path}")


# --------------------------------------------------------------------------- #

def main() -> None:
    force_utf8()
    ap = argparse.ArgumentParser(description="把校对后的 Markdown 打包为带导航目录的 EPUB")
    ap.add_argument("input", help="输入 book.md 路径")
    ap.add_argument("-o", "--output", default="book.epub", help="输出 EPUB 路径（默认 book.epub）")
    ap.add_argument("--title", default="", help="书名")
    ap.add_argument("--author", default="", help="作者")
    ap.add_argument("--lang", default="zh", help="语言（默认 zh）")
    ap.add_argument("--cover", default="", help="封面图片路径（PNG/JPG，通常为拆页得到的 page_0001.png）")
    args = ap.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(f"找不到输入文件：{md_path}")
        sys.exit(1)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cover = args.cover
    if cover:
        if not Path(cover).exists():
            print(f"找不到封面图片：{cover}")
            sys.exit(1)
        if Path(cover).suffix.lower() not in (".png", ".jpg", ".jpeg"):
            print(f"封面格式不支持（需 PNG/JPG）：{cover}")
            sys.exit(1)

    # 预处理：校验输入是干净的层级化 Markdown（无残留锚点/版权页标记）
    text = md_path.read_text(encoding="utf-8")
    for pat in (r"<!--\s*CH\d\s*:", r"COPYRIGHT_CANDIDATE", r"<!--\s*PAGE\s*\d", r"(?m)^\s*__|__\s*$"):
        if re.search(pat, text):
            print(f"警告：输入中仍含 {pat} 残留，请先运行 SKILL.md 阶段 6 主代理校对。")
    if not re.search(r"^#{1,6}\s+\S", text, re.M):
        print("警告：输入中未发现任何 Markdown 标题，无法切分章节。")

    if shutil.which("pandoc"):
        build_with_pandoc(md_path, out_path, args.title, args.author, args.lang, cover)
    else:
        try:
            build_with_pypandoc(md_path, out_path, args.title, args.author, args.lang, cover)
        except ImportError:
            try:
                build_with_ebooklib(md_path, out_path, args.title, args.author, args.lang, cover)
            except ImportError:
                print("pandoc/pypandoc 与 ebooklib 均不可用：请 `pip install pypandoc-binary` 或 `pip install ebooklib`")
                sys.exit(1)


if __name__ == "__main__":
    main()
