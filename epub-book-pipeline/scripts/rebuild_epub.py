#!/usr/bin/env python
"""
rebuild_epub.py — Inject translated text back into EPUB and repackage.

Usage:
    python rebuild_epub.py --epub <origin.epub> --translation <translation.md> --output <final.epub>

What it does:
- Copies the original EPUB as base
- Maps <!-- FILE: ... --> markers from translation.md to XHTML files
- Replaces text content paragraph-by-paragraph
- Preserves <head> content (unlike ebooklib's set_content)
- Removes ruby tags
- Changes writing direction: vertical-rl → horizontal-tb
- Updates CSS, OPF metadata, NCX TOC for Chinese translation
- Adds Chinese chapter titles below heading images
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning
import warnings

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def parse_translation_md(md_path):
    """Split translation.md by <!-- FILE: ... --> markers."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    sections = re.split(r'(<!-- FILE: .*?\.xhtml -->)', content)
    file_map = {}
    current_file = None
    current_lines = []
    for part in sections:
        m = re.match(r'<!-- FILE: (.*\.xhtml) -->', part)
        if m:
            if current_file:
                file_map[current_file] = current_lines
            current_file = m.group(1)
            current_lines = []
        elif current_file is not None:
            current_lines.append(part)
    if current_file:
        file_map[current_file] = current_lines
    return file_map


def extract_text_lines(file_lines):
    """Extract plain text lines from a FILE section (skip comments and H1)."""
    text_lines = []
    for part in file_lines:
        for line in part.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("<!--") and stripped.endswith("-->"):
                continue
            if stripped.startswith('<p class="chapter-title-cn">') and stripped.endswith("</p>"):
                continue
            if stripped.startswith("# ") and not stripped.startswith("##"):
                continue
            text_lines.append(stripped)
    return text_lines


def parse_heading_title(file_lines):
    """Extract chapter heading title from a FILE section, if any."""
    for part in file_lines:
        for line in part.splitlines():
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("##"):
                # Return the heading after '# '
                return stripped[2:].strip()
    return ""


def remove_ruby(soup):
    """Remove ruby annotations while preserving the base text."""
    for ruby_tag in soup.find_all("ruby"):
        for annotation in ruby_tag.find_all(["rt", "rp"]):
            annotation.decompose()
        ruby_tag.replace_with(ruby_tag.get_text())
    return soup


def replace_paragraphs(soup, translated_lines):
    """
    Replace <p> text content paragraph-by-paragraph in order.

    Mapping rules (match source.md extraction logic):
    - Normal <p>: replace content, advance idx
    - ○/● <p> (scene break): skip content, advance idx (consumes '---' line)
    - Empty <p>: skip content, DON'T advance idx (was skipped during extraction)
    - Image <p>: skip content, DON'T advance idx (preserved as-is)
    """
    idx = 0
    total_lines = len(translated_lines)
    for p_tag in soup.find_all("p"):
        p_text = p_tag.get_text(strip=True)
        is_empty = not p_text
        is_circle = p_text in ("○", "●")
        is_image = p_tag.find("img") is not None

        if not is_empty and not is_circle and not is_image:
            # Normal paragraph — replace content
            # Use fallback empty string if translation has fewer lines than needed
            replacement = translated_lines[idx] if idx < len(translated_lines) else ""
            links = p_tag.find_all("a")
            if len(links) == 1:
                link = links[0]
                p_tag.clear()
                link.clear()
                link.append(NavigableString(replacement))
                p_tag.append(link)
            else:
                # Clear nested source markup as well as direct text before inserting the translation.
                p_tag.clear()
                p_tag.append(NavigableString(replacement))
            idx += 1
        elif is_circle:
            # Scene break ○/● → consume the '---' line from translation
            idx += 1
        # else: empty or image → skip, don't advance idx
    return soup


def add_chapter_title(soup, title_text):
    """Add Chinese chapter title after h1>img if found."""
    h1 = soup.find("h1")
    if h1 and h1.find("img"):
        new_p = soup.new_tag("p")
        new_p["class"] = "chapter-title-cn"
        new_p.string = title_text
        h1.insert_after(new_p)


def translate_fixed_headings(soup):
    """Translate visible headings that are not represented as markdown blocks."""
    heading_map = {"あとがき": "后记"}
    for heading in soup.find_all(["h2", "h3"]):
        translated = heading_map.get(heading.get_text(strip=True))
        if translated:
            heading.clear()
            heading.append(NavigableString(translated))


def load_toc_translations(toc_path):
    """Load toc_original.yaml and extract label → label_cn mapping."""
    if not toc_path or not toc_path.exists():
        return None, ""
    try:
        with open(toc_path, "r", encoding="utf-8") as f:
            text = f.read()
        # Parse book_title
        title_m = re.search(r'^book_title_cn:\s*(.+)', text, re.MULTILINE)
        book_title_cn = title_m.group(1).strip() if title_m else ""
        if not book_title_cn:
            title_m = re.search(r'^book_title:\s*(.+)', text, re.MULTILINE)
            book_title_cn = title_m.group(1).strip() if title_m else ""

        # Parse TOC entries with label_cn
        toc_map = {}
        pattern = re.compile(
            r'^\s+-\s+play_order:\s*(\d+)\s*\n'
            r'(?:\s+label:\s*"([^"]*)"\s*\n)?'
            r'(?:\s+label_cn:\s*"([^"]*)"\s*\n)?'
            r'(?:\s+src:\s*"([^"]*)"\s*\n)?',
            re.MULTILINE
        )
        # Simpler line-by-line approach
        lines = text.split('\n')
        current_order = None
        current_label = None
        current_label_cn = None
        for line in lines:
            line_stripped = line.strip()
            m_po = re.match(r'- play_order:\s*(\d+)', line_stripped)
            if m_po:
                if current_order is not None and current_label_cn:
                    toc_map[current_label] = current_label_cn
                current_order = m_po.group(1)
                current_label = None
                current_label_cn = None
                continue
            m_l = re.match(r'label:\s*"(.+)"', line_stripped)
            if m_l:
                current_label = m_l.group(1)
                continue
            m_lc = re.match(r'label_cn:\s*"(.+)"', line_stripped)
            if m_lc:
                current_label_cn = m_lc.group(1)
        # Last entry
        if current_order is not None and current_label_cn:
            toc_map[current_label] = current_label_cn

        if toc_map:
            print(f"  Loaded {len(toc_map)} TOC translations from {toc_path.name}")
            return toc_map, book_title_cn
        print(f"  ⚠️  No label_cn entries found in {toc_path.name}, NCX will not be translated")
        return None, book_title_cn
    except Exception as e:
        print(f"  ⚠️  Failed to load TOC translations: {e}")
        return None, ""


def translate_ncx_labels(ncx_text, toc_map, book_title_cn):
    """Replace NCX text labels with Chinese translations."""
    if not toc_map:
        return ncx_text

    # Replace docTitle
    if book_title_cn:
        ncx_text = re.sub(
            r'(<docTitle>\s*<text>).*?(</text>\s*</docTitle>)',
            rf'\1{book_title_cn}\2',
            ncx_text, flags=re.DOTALL
        )

    # Replace navLabel text entries
    for jp_label, cn_label in toc_map.items():
        jp_escaped = re.escape(jp_label)
        ncx_text = re.sub(
            rf'(<text>){jp_escaped}(</text>)',
            rf'\1{cn_label}\2',
            ncx_text
        )

    return ncx_text


def translate_nav_labels(nav_text, toc_map):
    """Replace nav.xhtml link text with Chinese translations."""
    if not toc_map:
        return nav_text
    for jp_label, cn_label in toc_map.items():
        # Match <a ...>TEXT</a> where TEXT is the Japanese label
        jp_escaped = re.escape(jp_label)
        nav_text = re.sub(
            rf'(<a[^>]*>){jp_escaped}(</a>)',
            rf'\1{cn_label}\2',
            nav_text
        )
    return nav_text


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild EPUB from translated markdown."
    )
    parser.add_argument("--epub", required=True, help="Path to original EPUB")
    parser.add_argument("--translation", required=True, help="Path to translation.md")
    parser.add_argument("--output", required=True, help="Path for output EPUB")
    parser.add_argument("--to-lang", default="zh-CN", help="Target language code")
    parser.add_argument("--from-lang", default="ja", help="Source language code")
    parser.add_argument("--toc", default=None, help="Path to toc_original.yaml (auto-detected if not set)")
    args = parser.parse_args()

    epub_path = Path(args.epub)
    trans_path = Path(args.translation)
    out_path = Path(args.output)
    to_lang = args.to_lang
    from_lang = args.from_lang

    # Auto-detect TOC translations next to translation file
    toc_path = Path(args.toc) if args.toc else trans_path.parent / "toc_original.yaml"
    toc_map, book_title_cn = load_toc_translations(toc_path)

    if not epub_path.exists():
        print(f"Error: EPUB not found: {epub_path}")
        sys.exit(1)
    if not trans_path.exists():
        print(f"Error: Translation file not found: {trans_path}")
        sys.exit(1)

    print(f"Reading translation: {trans_path}")
    file_map = parse_translation_md(trans_path)
    print(f"  Found {len(file_map)} FILE sections")

    print(f"Building EPUB: {out_path}")
    tmp_path = out_path.with_suffix(".tmp.epub")

    with zipfile.ZipFile(epub_path, "r") as src_zip:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as out_zip:
            for item_info in src_zip.infolist():
                path = item_info.filename
                data = src_zip.read(path)

                # ── Nav (EPUB3 navigation) — check BEFORE general XHTML ──
                if "nav" in path and (path.endswith(".xhtml") or path.endswith(".html")):
                    nav_text = data.decode("utf-8")
                    nav_text = translate_nav_labels(nav_text, toc_map)
                    data = nav_text.encode("utf-8")
                    print(f"  [NAV] {path}")

                # ── XHTML content files ──
                elif path.endswith(".xhtml") or path.endswith(".html"):
                    # Determine the short name used in translation FILE markers
                    # EPUBs use various directory structures; try to match
                    short_name = None
                    for candidate in [path, path.replace("OEBPS/", "", 1), path.split("/", 1)[1] if "/" in path else path]:
                        if candidate in file_map:
                            short_name = candidate
                            break

                    if short_name and file_map[short_name]:
                        lines = file_map[short_name]
                        text_lines = extract_text_lines(lines)
                        heading = parse_heading_title(lines)

                        if text_lines or heading:
                            content = data.decode("utf-8")
                            soup = BeautifulSoup(content, "lxml")
                            soup = remove_ruby(soup)

                            if text_lines:
                                soup = replace_paragraphs(soup, text_lines)

                            translate_fixed_headings(soup)

                            # Update html attributes
                            html_tag = soup.find("html")
                            if html_tag:
                                classes = html_tag.get("class", [])
                                if "vrtl" in classes:
                                    html_tag["class"] = ["hltr" if c == "vrtl" else c for c in classes]
                                    classes = html_tag["class"]
                                if "hltr" not in classes:
                                    classes.append("hltr")
                                html_tag["class"] = classes
                                if html_tag.get("xml:lang") == from_lang:
                                    html_tag["xml:lang"] = to_lang

                            # Add chapter heading title
                            if heading:
                                add_chapter_title(soup, heading)

                            data = soup.encode("utf-8")
                            print(f"  [XHTML] {short_name} ({len(text_lines)} paragraphs)")

                # ── CSS files ──
                elif path.endswith(".css"):
                    css_text = data.decode("utf-8")
                    modified = False
                    if "flow0009" in path or "vertical-rl" in css_text:
                        css_text = css_text.replace(
                            "-webkit-writing-mode: vertical-rl;",
                            "-webkit-writing-mode: horizontal-tb;"
                        )
                        modified = True
                    if "flow0011" in path or path.endswith("custom.css"):
                        cn_rules = f"""
/* === {to_lang} horizontal layout (added by rebuild_epub.py) === */
html, body {{
    writing-mode: horizontal-tb;
    -epub-writing-mode: horizontal-tb;
    -webkit-writing-mode: horizontal-tb;
}}
p {{
    text-indent: 2em;
    line-height: 1.8;
    text-align: justify;
}}
h1, h2, h3 {{
    text-align: center;
    text-indent: 0;
}}
.chapter-title-cn {{
    text-align: center;
    font-size: 1.2em;
    margin: 1.5em 0 1em 0;
    text-indent: 0;
    font-weight: bold;
}}
"""
                        css_text += cn_rules
                        modified = True
                    if modified:
                        data = css_text.encode("utf-8")
                        print(f"  [CSS] {path}")

                # ── OPF metadata ──
                elif path.endswith(".opf"):
                    opf_text = data.decode("utf-8")
                    # Remove vertical writing mode metadata
                    opf_text = re.sub(r'<meta name="primary-writing-mode".*?/>', "", opf_text)
                    # Set page progression to ltr
                    opf_text = opf_text.replace(
                        'page-progression-direction="rtl"',
                        'page-progression-direction="ltr"'
                    )
                    # Update language (remove duplicates, set target)
                    opf_text = re.sub(
                        r'<dc:language>.*?</dc:language>',
                        f'<dc:language>{to_lang}</dc:language>',
                        opf_text
                    )
                    # Remove any Amazon/Kindle extra metadata that might contain original title
                    opf_text = re.sub(
                        r'<meta name="Updated_Title.*?/>',
                        '',
                        opf_text
                    )
                    # Replace dc:title with Chinese book title if available
                    if book_title_cn:
                        opf_text = re.sub(
                            r'(<dc:title[^>]*>).*?(</dc:title>)',
                            rf'\1{book_title_cn}\2',
                            opf_text
                        )
                    data = opf_text.encode("utf-8")
                    print(f"  [OPF] {path}")

                # ── NCX ──
                elif path.endswith(".ncx"):
                    ncx_text = data.decode("utf-8")
                    ncx_text = translate_ncx_labels(ncx_text, toc_map, book_title_cn)
                    data = ncx_text.encode("utf-8")
                    print(f"  [NCX] {path}")

                out_zip.writestr(item_info, data)

    # Replace temp with final
    if out_path.exists():
        out_path.unlink()
    os.rename(tmp_path, out_path)

    size = os.path.getsize(out_path)
    print(f"\nDone! {out_path}")
    print(f"  Size: {size / 1024:.1f} KB ({size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
