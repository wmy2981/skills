#!/usr/bin/env python
"""
chunk_source.py — Split source.md into FILE-bounded chunks for parallel translation.

FILE markers are NEVER split across chunks. If a single FILE section exceeds
the threshold, it is split by blank-line-separated paragraphs (not word count).

Usage:
    python chunk_source.py --source <source.md> --output-dir <chunks_dir> [--max-chars 6000]

Output (in output_dir):
    chunk-01.md, chunk-02.md, ...   — Source chunk files
    chunk_index.json                 — Mapping: chunk -> [FILE names]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_source_sections(source_path):
    """Split source.md by FILE markers, return list of (file_marker, content_lines)."""
    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections_raw = re.split(r'(<!-- FILE: .*?\.xhtml -->)', content)
    sections = []
    cur_file = None
    cur_lines = []
    for part in sections_raw:
        m = re.match(r'<!-- FILE: (.*\.xhtml) -->', part)
        if m:
            if cur_file:
                sections.append((cur_file, cur_lines))
            cur_file = m.group(1)
            cur_lines = []
        elif cur_file is not None:
            cur_lines.append(part)
    if cur_file:
        sections.append((cur_file, cur_lines))
    return sections


def split_section_by_paragraphs(lines, max_chars, file_name):
    """
    Split a FILE section into sub-chunks at paragraph boundaries.

    Rules:
    1. Split only at blank-line-separated paragraph boundaries (atomic blocks)
    2. Merge tiny trailing sub-chunks (< max_chars/3) into previous

    Returns list of (name, paragraph_list).
    """
    full_text = "".join(lines)
    all_lines = full_text.split("\n")

    # Step 1: Split into paragraph blocks by blank lines
    blocks = []
    current_block = []
    for line in all_lines:
        stripped = line.strip()
        if stripped == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
        elif stripped == "---":
            if current_block:
                blocks.append(current_block)
                current_block = []
            blocks.append(["---"])
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    # Step 2: Convert blocks to paragraph text strings
    para_texts = []
    for block in blocks:
        if block == ["---"]:
            para_texts.append("---")
        else:
            para_texts.append("\n".join(block))

    # Step 3: Group paragraphs into chunks (target: up to max_chars each)
    sub_chunks = []  # list of list-of-paragraphs
    current_paras = []
    current_chars = 0

    def is_h1(t):
        return t.lstrip().startswith("# ")

    def flush():
        nonlocal current_paras, current_chars
        if not current_paras:
            return
        sub_chunks.append(current_paras)
        current_paras = []
        current_chars = 0

    for pt in para_texts:
        pt_chars = count_text_chars(pt)

        # Skip truly empty paragraphs
        if pt_chars == 0 and not pt.strip():
            continue

        # Single paragraph larger than max_chars: keep with any accumulated prefix
        if pt_chars > max_chars:
            current_paras.append(pt)
            current_chars += pt_chars
            flush()
            continue

        if not current_paras:
            current_paras = [pt]
            current_chars = pt_chars
            continue

        # Check if adding this paragraph would exceed max_chars
        if current_chars + pt_chars > max_chars:
            # If h1 is at end, move it to next chunk
            if is_h1(current_paras[-1]):
                h1 = current_paras.pop()
                current_chars -= count_text_chars(h1)
                flush()
                current_paras = [h1, pt]
                current_chars = count_text_chars(h1) + pt_chars
            else:
                flush()
                current_paras = [pt]
                current_chars = pt_chars
        else:
            current_paras.append(pt)
            current_chars += pt_chars
    flush()

    # Step 4: Merge tiny trailing chunks ( < max_chars/3 ) into previous
    TINY_THRESH = max(int(max_chars / 3), 1)
    if len(sub_chunks) > 1:
        merged = [sub_chunks[0]]
        for chunk in sub_chunks[1:]:
            c_chars = sum(count_text_chars(p) for p in chunk)
            if c_chars < TINY_THRESH:
                merged[-1] = merged[-1] + chunk
            else:
                merged.append(chunk)
        sub_chunks = merged

    return [(f"{file_name} (part {i + 1})", paras) for i, paras in enumerate(sub_chunks)]


def count_text_chars(text):
    """Count meaningful text characters (exclude comments, headings, whitespace)."""
    cleaned = re.sub(r'<!--.*?-->', '', text)
    cleaned = re.sub(r'^# .*\n?', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s', '', cleaned)
    return len(cleaned)


def main():
    parser = argparse.ArgumentParser(
        description="Split source.md into FILE-bounded chunks for parallel translation."
    )
    parser.add_argument("--source", required=True, help="Path to source.md")
    parser.add_argument("--output-dir", required=True, help="Output directory for chunks")
    parser.add_argument("--max-chars", type=int, default=6000,
                        help="Target chars per chunk (default: 6000). All thresholds scale proportionally.")
    args = parser.parse_args()

    source_path = Path(args.source)
    output_dir = Path(args.output_dir)

    if not source_path.exists():
        print(f"Error: source.md not found: {source_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    sections = parse_source_sections(source_path)
    print(f"Found {len(sections)} FILE sections in {source_path.name}")

    # Derived thresholds (all proportional to max_chars)
    MC = args.max_chars
    MIN_FLUSH = int(MC * 0.6)      # flush accumulated only if >= this
    MIN_CHUNK = int(MC * 0.83)     # safety net: merge chunks below this
    MAX_MERGE = int(MC * 1.33)     # safety net: don't merge if result exceeds this

    # Group sections into chunks, splitting oversize ones
    chunks = []
    current_chunk = []
    current_file_list = []
    current_chars = 0

    def flush_current_chunk():
        nonlocal current_chunk, current_file_list, current_chars
        if not current_chunk:
            return
        chunk_name = f"chunk-{len(chunks) + 1:02d}"
        content = "".join(current_chunk)
        chunks.append((chunk_name, current_file_list, content))
        print(f"  chunk {chunk_name}: {', '.join(current_file_list)} ({current_chars} chars)")
        current_chunk = []
        current_file_list = []
        current_chars = 0

    for file_name, lines in sections:
        section_text = "".join(lines)
        section_chars = count_text_chars(section_text)
        file_marker = f"<!-- FILE: {file_name} -->"

        # Skip image-only empty pages — they just need the FILE marker
        if section_chars == 0:
            current_chunk.append(f"{file_marker}\n\n")
            current_file_list.append(file_name)
            continue

        # Oversize section: merge small accumulated content, then split
        if section_chars > MC:
            prefix = ""
            if current_chars < MIN_FLUSH and current_chunk:
                prefix = "".join(current_chunk)
                current_chunk = []
                current_file_list = []
                current_chars = 0
            else:
                flush_current_chunk()
            sub_chunks = split_section_by_paragraphs(lines, MC, file_name)
            for i, (sub_name, sub_paras) in enumerate(sub_chunks):
                chunk_name = f"chunk-{len(chunks) + 1:02d}"
                # Only first sub-chunk gets the file_marker (matches source — no new markers)
                body = "\n\n".join(sub_paras) + "\n"
                if i == 0:
                    body = f"{file_marker}\n" + body
                    if prefix:
                        body = prefix + body
                chunks.append((chunk_name, [sub_name], body))
                sc = count_text_chars(body)
                print(f"  chunk {chunk_name}: {sub_name} ({sc} chars, split)")
            continue

        # Normal section: flush only if accumulated enough; otherwise let overflow
        if current_chars + section_chars > MC and current_chunk:
            if current_chars >= MIN_FLUSH:
                flush_current_chunk()

        content_part = f"{file_marker}\n\n{''.join(lines)}\n"
        current_chunk.append(content_part)
        current_file_list.append(file_name)
        current_chars += section_chars

    flush_current_chunk()

    # Merge final 0-char chunk (FILE markers only) into previous
    if len(chunks) >= 2 and chunks[-1][2].strip() == "":
        _, empty_files, _ = chunks.pop()
        prev_name, prev_files, prev_content = chunks[-1]
        chunks[-1] = (prev_name, prev_files + empty_files, prev_content)

    # Safety net: merge chunks below MIN_CHUNK into previous (if result fits MAX_MERGE)
    if len(chunks) >= 2:
        merged = [chunks[0]]
        for i in range(1, len(chunks)):
            c_name, c_files, c_content = chunks[i]
            c_chars = count_text_chars(c_content)
            p_name, p_files, p_content = merged[-1]
            p_chars = count_text_chars(p_content)
            cap = 99999 if i == len(chunks) - 1 else MAX_MERGE
            if c_chars < MIN_CHUNK and c_chars > 0 and (p_chars + c_chars) <= cap:
                # Deduplicate FILE markers: strip any marker from c_content whose
                # file already appears (including as "foo (part N)") in p_files
                deduped = c_content
                for p_file in p_files:
                    p_base = re.sub(r' \(part \d+\)$', '', p_file)
                    for c_file_str in c_files:
                        c_base = re.sub(r' \(part \d+\)$', '', c_file_str)
                        if p_base == c_base:
                            marker = f"<!-- FILE: {p_base} -->"
                            deduped = deduped.replace(marker + "\n", "", 1)
                merged[-1] = (p_name, p_files + c_files, p_content + deduped)
            else:
                merged.append((c_name, c_files, c_content))
        chunks = merged

    # Write chunks
    chunk_index = {}
    for chunk_name, file_list, content in chunks:
        chunk_path = output_dir / f"{chunk_name}.md"
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(content)
        chunk_index[chunk_name] = {
            "files": file_list,
            "chars": count_text_chars(content),
        }

    # Write index
    index_path = output_dir / "chunk_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(chunk_index, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(chunks)} chunks in {output_dir}")
    print(f"Index: {index_path}")


if __name__ == "__main__":
    main()
