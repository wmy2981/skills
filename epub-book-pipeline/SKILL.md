---
name: epub-book-pipeline
description: >-
  EPUB book processing pipeline — extract, chunk, rebuild, and validate EPUB
  files. Use this whenever you need to programmatically manipulate the content
  of an EPUB book: extract structured text, split into manageable chunks,
  apply batch modifications, rebuild a valid EPUB from modified content, or
  validate structural integrity. Triggered by any request involving EPUB
  extraction ("extract epub", "unpack epub"), chunking ("split epub",
  "chunk epub"), rebuilding ("rebuild epub", "repackage epub", "pack epub"),
  or validation ("validate epub", "check epub"). Also triggered when the user
  needs to batch-edit EPUB content (replace text, reformat, inject styles,
  modify structure) and then rebuild a valid EPUB from the edited files.
  Does NOT handle content-level operations like AI translation or text
  rewriting — only the EPUB mechanical pipeline.
---

# EPUB Book Pipeline

Provides the EPUB-specific mechanical operations for extracting, chunking, rebuilding, and validating EPUB files. It handles the structural EPUB work so you can focus on whatever content transformation you need to apply in between.

## Pipeline Overview

```
origin.epub → [Step 1: Extract] → source.md + toc_original.yaml + terminology_candidates.md
              → [Step 2: Chunk] → chunk-*.md files (for parallel processing)
              → [** your content modifications here **]
              → [Step 3: Rebuild] → modified.epub
              → [Step 4: Validate]
```

## Execution Rule

Run the requested pipeline step directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the scripts will fail with clear errors — check and fix only then.

## Requirements

```bash
pip install ebooklib beautifulsoup4 lxml
```

Scripts at `{baseDir}/scripts/`.

## Step 1: Extract EPUB → Structured Markdown

```bash
python {baseDir}/scripts/extract_epub.py --epub <input.epub> --output-dir <output_dir>
```

**What it does:**
- Parses EPUB structure (OPF, NCX, CSS, spine)
- Extracts text-bearing XHTML into a single merged markdown file
- Adds structural markers: `<!-- FILE: ... -->`, `<!-- CHAPTER-HEADING-IMAGE: ... -->`, `<!-- IMAGE: ... -->`
- Extracts NCX navLabel entries into `toc_original.yaml` (for later TOC rebuilding)
- Scans katakana sequences into `terminology_candidates.md` (proper noun candidates for review)

**Output:**

| File | Description |
|------|-------------|
| `source.md` | Merged markdown with all text + structural markers |
| `toc_original.yaml` | NCX/EPUB3 TOC entries (play_order, label, src) |
| `terminology_candidates.md` | Auto-detected proper noun candidates (katakana sequences) for review |

**Critical:** `<!-- FILE: ... -->` markers map each section to its original XHTML file. **Never remove or modify them** — the rebuild step relies on them to place modified content back into the correct XHTML files.

## Step 2: Chunk source.md for Parallel Processing

When an EPUB is large, chunking lets you process sections independently (e.g., in parallel subagents, or one section at a time):

```bash
python {baseDir}/scripts/chunk_source.py \
  --source <output_dir>/source.md \
  --output-dir <output_dir>/chunks/ \
  --max-chars 12000
```

`--max-chars` controls target chars per chunk (default 6000). All internal thresholds (flush threshold, merge floor, merge cap) scale proportionally.

**Chunking rules:**
- `<!-- FILE: ... -->` markers are atomic — never split across chunks
- Oversize FILE sections split at **blank-line-separated paragraph boundaries** (never mid-paragraph)
- `---` scene separators are standalone paragraph blocks
- If a chunk would end with an `h1` heading, the `h1` is moved to the next chunk
- Small trailing fragments (< max_chars/3) merge back into the previous chunk
- Tiny FILE sections (image-only pages, short sections) accumulate into adjacent chunks rather than creating standalone tiny blocks

**Output:** `chunk-NN.md` files + `chunk_index.json` mapping chunk numbers to `<!-- FILE: ... -->` ranges.

After you've modified the chunk content, concatenate them back into a single markdown file (in order) for the rebuild step:

```bash
cat chunks/chunk-*.md > ../modified.md
```

Or if processing sequentially, you can edit `source.md` directly and skip Step 2 entirely.

## Step 3: Rebuild EPUB

After modifying the markdown content, rebuild it into a valid EPUB:

```bash
python {baseDir}/scripts/rebuild_epub.py \
  --epub <origin.epub> \
  --translation <modified.md> \
  --output <final.epub> \
  [--toc <toc_original.yaml>]
```

**Arguments:**
- `--epub`: Original EPUB file (used as structural template)
- `--translation`: Modified markdown with content changes
- `--output`: Output EPUB path
- `--toc`: YAML file for TOC label customization (auto-detects next to `--translation` if omitted)
- `--from-lang` / `--to-lang`: Source/target language codes (defaults: `ja` → `zh-CN`); only needed if the script's built-in language-specific transformations (ruby removal, writing mode, typography CSS) apply to your use case

**What it does:**
- Copies original EPUB as base, replaces text per `<!-- FILE: ... -->` mapped sections
- Rebuilds NCX/EPUB3 TOC from `toc_original.yaml` (if provided)
- Preserves all non-text assets (images, fonts, stylesheets) from the original
- Handles both EPUB2 and EPUB3 formats
- Handles SVG-wrapper pages (cover, color plates) — preserved as-is

**TOC customization:** Create a YAML file (based on `toc_original.yaml`) to customize TOC labels when rebuilding:

```yaml
book_title: The Original Title
toc:
  - play_order: 1
    label: "Custom Chapter Title"
    src: "Text/p-006.xhtml#toc-001"
```

Fields not specified fall back to the original EPUB's values.

## Step 4: Validate

Verify the rebuilt EPUB is structurally sound:

```bash
python {baseDir}/scripts/validate_epub.py \
  --epub <final.epub> \
  --source-md <output_dir>/source.md \
  --translation-md <output_dir>/modified.md
```

**Checks:** ZIP structure, OPF metadata integrity, all text-bearing XHTML files present and well-formed, image integrity, TOC consistency across NCX and nav.xhtml, structural marker alignment between source and modified content.

**Output format:**
- Each XHTML file is scanned individually; issues reported as `[WARN]` per file
- Summary line: `XHTML files checked: N (OK: M, no Chinese: ..., ruby: ..., lang: ...)`
- Overall result: `Summary: X/Y checks passed (Z%)` — exits 0 unless a critical structural error prevents verification

**Optional:**
- `--sample`: XHTML filename to sample for content validation (default: `p-007.xhtml`)
- `--verbose`: Show all checks including passing ones

## Full Pipeline Example

```bash
BASE=book-work

# 1. Extract
python scripts/extract_epub.py --epub book.epub --output-dir $BASE/

# 2. (Optional) Chunk for parallel processing
python scripts/chunk_source.py --source $BASE/source.md --output-dir $BASE/chunks/ --max-chars 12000

# 3. Apply your content modifications to chunk-*.md or source.md
#    (this is where you edit text, replace content, reformat, etc.)

# 4. Rebuild
python scripts/rebuild_epub.py --epub book.epub --translation $BASE/modified.md --output $BASE/final.epub

# 5. Validate
python scripts/validate_epub.py --epub $BASE/final.epub --source-md $BASE/source.md --translation-md $BASE/modified.md
```

## Edge Cases

- **SVG-wrapper pages** (cover, color plates): Preserved as-is
- **Chapter heading images** (`<h1><img>`): Image kept, additional text can be inserted via the markdown
- **Scene breaks**: `○`/`●` → `---` in markdown, restored during rebuild — `---` alignment must match original one-to-one; mismatches shift subsequent paragraphs
- **Empty paragraphs** (`<p><br/>`): Preserved structurally
- **EPUB2 vs EPUB3**: Both handled (NCX and nav.xhtml)
- **Embedded fonts**: Preserved automatically
- **Right-to-left / vertical writing mode CSS**: Removed during rebuild (controlled by `--from-lang`/`--to-lang`); skipped if the generated CSS doesn't apply to your direction

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `extract_epub.py` | EPUB → structured markdown (`--epub INPUT --output-dir DIR`) |
| `chunk_source.py` | FILE-bounded chunking (`--source SRC --output-dir DIR [--max-chars N]`) |
| `rebuild_epub.py` | Modified markdown → final EPUB (`--epub SRC --translation MD --output EPUB [--toc YAML]`) |
| `validate_epub.py` | Structural check + content alignment (`--epub EPUB [--source-md SRC --translation-md TGT]`) |
