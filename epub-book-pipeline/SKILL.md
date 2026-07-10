---
name: epub-book-pipeline
description: >-
  Full EPUB book translation pipeline — handles the EPUB-specific operations
  that baoyu-translate does not cover. Use this when translating a complete
  EPUB-format book (novel, light novel, etc.) from one language to another.
  This skill extracts EPUB to structured markdown so baoyu-translate can
  translate it, then rebuilds the translated markdown back into a valid EPUB.
  Trigger keywords: "epub 翻译", "整本书", "翻译 ebook/epub/book", "epub 打包",
  "epub 解包", "epub rebuild", "epub repackage", "整本 epub 翻译",
  or any request involving translating an EPUB file end-to-end.
---

# EPUB Book Pipeline

Companion skill for **[baoyu-translate](../baoyu-translate/SKILL.md)**. Handles EPUB-specific operations before and after translation.

## Overview

```
origin.epub → [Step 1] Extract → [Step 2] Chunk → [baoyu-translate] → [Step 3] Rebuild → final.epub
                                                                              [Step 4] Validate
```

## Requirements

```bash
pip install ebooklib beautifulsoup4 lxml
```

Scripts at `{baseDir}/scripts/`.

## Step 1: Extract EPUB → Markdown

```bash
python {baseDir}/scripts/extract_epub.py --epub <input.epub> --output-dir <output_dir>
```

**What it does:**
- Parses EPUB structure (OPF, NCX, CSS, spine)
- Extracts text-bearing XHTML into a single merged markdown
- Removes `<ruby>` (furigana) tags
- Adds structural markers: `<!-- FILE: ... -->`, `<!-- CHAPTER-HEADING-IMAGE: ... -->`, `<!-- IMAGE: ... -->`
- Extracts NCX navLabel entries into `toc_original.yaml`
- Scans katakana sequences into `terminology_candidates.md`

**Output:**

| File | Description |
|------|-------------|
| `source.md` | Merged markdown with all text + structural markers |
| `toc_original.yaml` | NCX TOC entries + Chinese title/entries (see below) |
| `terminology_candidates.md` | Proper noun candidates for review |

**Critical:** `<!-- FILE: ... -->` markers map each section to its original XHTML file. **Never remove or modify them**.

**TOC translation setup:** After deciding chapter title translations, add `label_cn` entries:

```yaml
book_title: 魔女の旅々２２
book_title_cn: 魔女之旅 22
toc:
  - play_order: 1
    label: "第一章　伝説の略奪者"
    label_cn: "第一章　传说的掠夺者"
    src: "Text/p-006.xhtml#toc-001"
```

Step 3 reads `label_cn` fields to auto-translate NCX, nav.xhtml, and OPF `<dc:title>`.

## Step 2: Chunk source.md for parallel translation

Book-length content must be chunked so baoyu-translate can translate in parallel:

```bash
python {baseDir}/scripts/chunk_source.py \
  --source <output_dir>/source.md \
  --output-dir <output_dir>/chunks/ \
  --max-chars 6000
```

`--max-chars` controls target chars per chunk (default 6000). All internal thresholds (flush threshold, merge floor, merge cap) scale proportionally.

**Chunking rules:**
- `<!-- FILE: ... -->` markers are atomic — never split across chunks
- Oversize FILE sections split at **blank-line-separated paragraph boundaries** (never mid-paragraph)
- `---` scene separators are standalone paragraph blocks
- If a chunk would end with an `h1` heading, the `h1` is moved to the next chunk
- Small trailing fragments (< max_chars/3) merge back into the previous chunk
- Tiny FILE sections (image-only pages, short sections) accumulate into adjacent chunks rather than creating standalone tiny blocks

**Output:** `chunk-NN.md` files + `chunk_index.json` mapping chunks to FILE ranges.

Then run baoyu-translate on the chunk directory:

```bash
# baoyu-translate will read chunks/*.md individually and translate them in parallel
# Or combine chunks back and translate as a single file:
cat chunks/chunk-*.md > source_combined.md
```

## Step 3: Rebuild EPUB

```bash
python {baseDir}/scripts/rebuild_epub.py \
  --epub <origin.epub> \
  --translation <translation.md> \
  --output <final.epub> \
  [--toc <toc_original.yaml>]
```

`--toc` auto-detects next to `translation.md` if omitted. Default language direction: ja→zh-CN, vertical→horizontal.

**What it does:**
- Copies original EPUB as base, replaces text per FILE-mapped sections
- Removes `<ruby>`, changes `xml:lang`, `class="vrtl"` → `"hltr"`
- Adds Chinese chapter title text below heading images (`<p class="chapter-title-cn">`)
- Updates CSS: vertical-rl → horizontal Chinese typography
- Updates OPF: language, title (from `book_title_cn`), writing mode
- Translates NCX + nav.xhtml from `toc_original.yaml` `label_cn` fields

## Step 4: Validate

```bash
python {baseDir}/scripts/validate_epub.py \
  --epub <final.epub> \
  --source-md <output_dir>/source.md \
  --translation-md <output_dir>/translation.md
```

**Checks: 25 items** — structure, content (Chinese text, no ruby, correct lang/class), TOC translation, image preservation, metadata. Translation verification (line count comparison) is warning-only.

## Full Pipeline

```bash
# 1. Extract
python extract_epub.py --epub book.epub --output-dir book-zh/

# 2. Chunk
python chunk_source.py --source book-zh/source.md --output-dir book-zh/chunks/ --max-chars 6000

# 3. Translate with baoyu-translate (outside this skill's scope)

# 4. Rebuild
python rebuild_epub.py --epub book.epub --translation book-zh/translation.md --output book-zh/final.epub

# 5. Validate
python validate_epub.py --epub book-zh/final.epub --source-md book-zh/source.md --translation-md book-zh/translation.md
```

## Chinese Typography CSS

When rebuilding, Chinese horizontal layout CSS is injected. See `{baseDir}/references/chinese-typography.css` for the full rule set. Key rules:

```css
p { text-indent: 2em; line-height: 1.8; text-align: justify; }
h1, h2, h3 { text-align: center; text-indent: 0; }
```

## Edge Cases

- **SVG-wrapper pages** (cover, color plates): Preserved as-is
- **Chapter heading images** (`<h1><img>`): Image kept, Chinese text title inserted below
- **Scene breaks**: `○`/`●` → `---` in markdown, restored during rebuild
- **Empty paragraphs** (`<p><br/>`): Preserved structurally; no translation.md line needed
- **`---` alignment**: Must match original scene breaks one-to-one; mismatches shift subsequent paragraphs
- **EPUB2 vs EPUB3**: Both handled (NCX and nav.xhtml)
- **Embedded fonts**: Preserved

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `extract_epub.py` | EPUB → structured markdown (`--epub INPUT --output-dir DIR`) |
| `chunk_source.py` | FILE-bounded chunking (`--source SRC --output-dir DIR [--max-chars N]`) |
| `rebuild_epub.py` | Translation → final EPUB (`--epub SRC --translation MD --output EPUB`) |
| `validate_epub.py` | Structural check + translation verification (`--epub EPUB [--source-md SRC --translation-md TGT]`) |
