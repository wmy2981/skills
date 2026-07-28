#!/usr/bin/env python
"""
extract_epub.py — Extract EPUB to structured Markdown for translation.

Usage:
    python extract_epub.py --epub <input.epub> --output-dir <output_dir>

What it does:
- Parses EPUB structure (OPF, NCX, spine)
- Extracts text-bearing XHTML files into a single merged Markdown
- Removes <ruby> tags (keeps base text)
- Adds <!-- FILE: ... --> markers for rebuild mapping
- Adds markers for images and chapter heading images
- Extracts NCX TOC entries to toc_original.yaml
- Scans terminology candidates to terminology_candidates.md

Output (in output_dir):
    source.md              - Merged Markdown (input for baoyu-translate)
    toc_original.yaml       - Original-language TOC entries
    terminology_candidates.md - Auto-detected proper noun candidates
"""

import argparse
import re
import subprocess
import sys
import warnings
from collections import Counter
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
from ebooklib import epub

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def parse_ncx_toc(book):
    """Extract TOC entries from NCX or EPUB3 navigation documents."""
    toc_entries = []
    title_metadata = book.get_metadata("DC", "title")
    book_title = title_metadata[0][0] if title_metadata else ""
    for item in book.get_items():
        is_navigation_item = item.get_type() == ebooklib.ITEM_NAVIGATION
        is_xhtml_item = item.get_name().lower().endswith((".xhtml", ".html"))
        if is_navigation_item or is_xhtml_item:
            content = item.get_content().decode("utf-8")
            soup = BeautifulSoup(content, "xml")
            dt = soup.find("docTitle")
            if dt:
                tt = dt.find("text")
                if tt:
                    book_title = tt.get_text()
            nav_map = soup.find("navMap")
            if nav_map:
                for np in nav_map.find_all("navPoint"):
                    label_tag = np.find("navLabel")
                    text_tag = label_tag.find("text") if label_tag else None
                    label = text_tag.get_text() if text_tag else ""
                    content_tag = np.find("content")
                    src = content_tag.get("src", "") if content_tag else ""
                    play_order = np.get("playOrder", "")
                    toc_entries.append({
                        "label": label,
                        "src": src,
                        "play_order": play_order,
                    })
            else:
                toc_nav = soup.find("nav", attrs={"epub:type": "toc"})
                if toc_nav is None:
                    toc_nav = soup.find("nav", id="toc")
                if toc_nav:
                    for play_order, anchor in enumerate(toc_nav.find_all("a"), start=1):
                        label = anchor.get_text(strip=True)
                        src = anchor.get("href", "")
                        if label or src:
                            toc_entries.append({
                                "label": label,
                                "src": src,
                                "play_order": str(play_order),
                            })
    return book_title, toc_entries


def remove_ruby(soup):
    """Remove ruby annotations while preserving the base text."""
    for ruby_tag in soup.find_all("ruby"):
        for annotation in ruby_tag.find_all(["rt", "rp"]):
            annotation.decompose()
        ruby_tag.replace_with(ruby_tag.get_text())
    return soup


def extract_xhtml_to_md(filepath, content, is_heading_page=False, chapter_title=""):
    """Convert XHTML content to structured Markdown section."""
    soup = BeautifulSoup(content, "lxml")
    lines = []
    lines.append(f"\n<!-- FILE: {filepath} -->")

    # Detect page type from body class (via string check since lxml loses class)
    body_tag = soup.find("body")
    body_str = str(body_tag) if body_tag else ""
    is_image_page = "p-image" in body_str or "p-cover" in body_str

    # Image-only page
    if is_image_page:
        imgs = soup.find_all("img")
        for img in imgs:
            src = img.get("src", "")
            if src:
                lines.append(f"<!-- IMAGE-PAGE: {src} -->")
        svg_images = soup.find_all("image")
        for svg_img in svg_images:
            href = svg_img.get("xlink:href", "") or svg_img.get("href", "")
            if href:
                lines.append(f"<!-- IMAGE-PAGE: {href} -->")
        lines.append("")
        return "\n".join(lines)

    # Chapter heading with image
    if is_heading_page:
        lines.append(f"<!-- CHAPTER-HEADING-IMAGE: {chapter_title} -->")
        lines.append(f"# {chapter_title}\n")

    # Remove ruby
    soup = remove_ruby(soup)

    # Extract text from paragraphs
    main_div = soup.find("div", class_="main")
    container = main_div if main_div else soup.find("body")
    if not container:
        return "\n".join(lines) + "\n"

    scene_break = re.compile(r'^[○●]$')

    for element in container.children:
        if not isinstance(element, Tag):
            continue
        if element.name in ("br", "hr"):
            continue
        if element.name in ("h1", "h2", "h3"):
            img = element.find("img")
            if img:
                continue  # image heading handled above
            text = element.get_text(strip=True)
            if text:
                lines.append(f"## {text}")
            continue
        if element.name == "p":
            if not element.get_text(strip=True) and not element.find("img"):
                continue
            img = element.find("img")
            if img and not element.get_text(strip=True):
                lines.append(f"<!-- IMAGE: {img.get('src', '')} -->")
                continue
            text = element.get_text().replace("　", "").strip()
            text = re.sub(r'\s+', '', text)
            if scene_break.match(text):
                lines.append("---")
                continue
            if text:
                lines.append(text)
            continue
        if element.name == "div":
            p = element.find("p")
            if p:
                p_text = p.get_text(strip=True)
                if scene_break.match(p_text):
                    lines.append("---")
                    continue
                text = p.get_text().replace("　", "").strip()
                text = re.sub(r'\s+', '', text)
                if text and text not in ("○", "●"):
                    lines.append(text)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract EPUB to structured Markdown for translation."
    )
    parser.add_argument("--epub", required=True, help="Path to input EPUB file")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()

    epub_path = Path(args.epub)
    output_dir = Path(args.output_dir)

    if not epub_path.exists():
        print(f"Error: EPUB file not found: {epub_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading EPUB: {epub_path}")
    book = epub.read_epub(str(epub_path), {"ignore_ncx": False})

    # Extract NCX TOC
    print("Extracting NCX TOC...")
    book_title, toc_entries = parse_ncx_toc(book)
    print(f"  Book: {book_title}")
    print(f"  TOC entries: {len(toc_entries)}")

    # Save TOC
    toc_path = output_dir / "toc_original.yaml"
    with open(toc_path, "w", encoding="utf-8") as f:
        f.write(f"# Original TOC - {book_title}\n")
        f.write(f"book_title: {book_title}\n")
        f.write("toc:\n")
        for e in toc_entries:
            f.write(f"  - play_order: {e['play_order']}\n")
            f.write(f'    label: "{e["label"]}"\n')
            f.write(f'    src: "{e["src"]}"\n')
    print(f"  Saved: {toc_path}")

    # Build chapter heading info from NCX
    heading_files = {}
    for entry in toc_entries:
        src = entry["src"]
        # Strip anchor (#toc-xxx)
        file_part = src.split("#")[0] if "#" in src else src
        heading_files[file_part] = entry["label"]

    # Extract text content — process all document items in spine order
    print("Extracting XHTML → Markdown...")
    all_parts = []
    total_chars = 0
    processed = set()

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        item_name = item.get_name()
        if item_name in processed:
            continue
        processed.add(item_name)

        # Determine if this is a chapter heading page
        is_heading = item_name in heading_files
        ch_title = heading_files.get(item_name, "")

        content = item.get_content().decode("utf-8")
        md_content = extract_xhtml_to_md(item_name, content, is_heading, ch_title)

        # Count chars (rough)
        text_only = re.sub(r'<!--.*?-->', '', md_content)
        text_only = re.sub(r'#.*?\n', '', text_only)
        text_only = re.sub(r'\s', '', text_only)
        char_count = len(text_only)
        total_chars += char_count

        label = "[T]" if char_count > 0 else "[I]"
        print(f"  {label} {item_name} ({char_count} chars)")

        all_parts.append(md_content)

    # Write source.md
    source_md = "\n".join(all_parts)
    source_path = output_dir / "source.md"
    with open(source_path, "w", encoding="utf-8") as f:
        f.write(source_md)
    print(f"\nSaved: {source_path}")
    print(f"Total chars: {total_chars}")

    # Write terminology candidates (basic)
    term_path = output_dir / "terminology_candidates.md"
    with open(term_path, "w", encoding="utf-8") as f:
        f.write("# Terminology Candidates (review before translation)\n\n")
        f.write("Extract katakana sequences that may be proper nouns.\n")
        f.write("Add known terms and remove common words before translation.\n\n")
        # Basic katakana scan
        katakana_words = re.findall(r'[゠-ヿー]{2,}', source_md)
        common = {"コスプレ", "コンサート", "アドバイザー", "ローブ", "ブローチ",
                   "ファン", "テーブル", "ハート", "ドア", "ページ",
                   "サービス", "テスト", "レベル", "メニュー", "カラー"}
        for word, count in Counter(katakana_words).most_common(50):
            if count >= 3 and word not in common:
                f.write(f"- {word} ({count}x)\n")
        f.write("\n---\n")
        f.write("> Review and confirm these terms before starting translation.\n")
    print(f"Saved: {term_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
