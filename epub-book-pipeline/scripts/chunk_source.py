#!/usr/bin/env python
"""
Split source.md into paragraph-safe chunks for parallel translation.

The source FILE markers are treated as immutable metadata. They are copied
from the source exactly once and are never generated during chunk assembly.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILE_MARKER_RE = re.compile(r"^\s*<!-- FILE: .*? -->\s*$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
H1_RE = re.compile(r"^#\s+")


@dataclass
class FileSection:
    name: str
    marker: str
    lines: list[str]


@dataclass
class Block:
    lines: list[str]

    @property
    def text(self):
        return "\n".join(self.lines)

    @property
    def chars(self):
        return count_text_chars(self.text)

    @property
    def is_h1(self):
        meaningful_lines = [
            line.strip()
            for line in self.lines
            if line.strip() and not re.fullmatch(r"<!--.*?-->", line.strip())
        ]
        return len(meaningful_lines) == 1 and bool(H1_RE.match(meaningful_lines[0]))


@dataclass
class Unit:
    file_name: str
    text: str
    chars: int
    is_h1: bool


@dataclass
class Segment:
    units: list[Unit]

    @property
    def chars(self):
        return sum(unit.chars for unit in self.units)

    @property
    def ends_with_h1(self):
        return bool(self.units) and self.units[-1].is_h1


@dataclass
class Chunk:
    segments: list[Segment]

    @property
    def chars(self):
        return sum(segment.chars for segment in self.segments)

    @property
    def ends_with_h1(self):
        return bool(self.segments) and self.segments[-1].ends_with_h1


def parse_source_sections(source_path):
    """Parse source.md into FILE sections without changing marker text."""
    with open(source_path, encoding="utf-8", newline=None) as source_file:
        lines = source_file.read().splitlines()

    sections = []
    current = None
    preamble = []

    for line in lines:
        if FILE_MARKER_RE.match(line):
            if current is not None:
                sections.append(current)
            file_name = re.match(r"^\s*<!-- FILE: (.*?) -->\s*$", line).group(1)
            current = FileSection(name=file_name, marker=line, lines=[])
        elif current is None:
            if line.strip():
                preamble.append(line)
        else:
            current.lines.append(line)

    if current is not None:
        sections.append(current)

    if preamble:
        raise ValueError("source.md contains non-empty content before the first FILE marker")
    if not sections:
        raise ValueError("source.md contains no FILE markers")

    markers = [section.marker for section in sections]
    if len(markers) != len(set(markers)):
        raise ValueError("source.md contains duplicate FILE markers")

    return sections


def split_section_into_blocks(lines):
    """Split a FILE body at blank lines, keeping --- as its own block."""
    blocks = []
    current = []

    def flush_current():
        nonlocal current
        if current:
            blocks.append(Block(current))
            current = []

    for line in lines:
        if not line.strip():
            flush_current()
        elif line.strip() == "---":
            flush_current()
            blocks.append(Block([line]))
        else:
            current.append(line)
    flush_current()
    return blocks


def count_text_chars(text):
    """Count content characters while ignoring metadata comments and h1 lines."""
    cleaned = HTML_COMMENT_RE.sub("", text)
    cleaned = re.sub(r"^\s*#\s+.*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s", "", cleaned)
    return len(cleaned)


def section_units(section):
    """Create units with the FILE marker attached to the first body block."""
    blocks = split_section_into_blocks(section.lines)
    if not blocks:
        return [Unit(section.name, section.marker, 0, False)]

    units = []
    for index, block in enumerate(blocks):
        if index == 0:
            text = f"{section.marker}\n\n{block.text}"
        else:
            text = block.text
        units.append(Unit(section.name, text, block.chars, block.is_h1))
    return units


def pack_units(units, max_chars):
    """Pack paragraph units, moving a trailing h1 to the next segment."""
    segments = []
    current = []
    current_chars = 0

    def flush_current():
        nonlocal current, current_chars
        if current:
            segments.append(Segment(current))
            current = []
            current_chars = 0

    for unit in units:
        if not current:
            current = [unit]
            current_chars = unit.chars
            continue

        if current_chars + unit.chars <= max_chars:
            current.append(unit)
            current_chars += unit.chars
            continue

        if current[-1].is_h1:
            heading = current.pop()
            current_chars -= heading.chars
            flush_current()
            current = [heading, unit]
            current_chars = heading.chars + unit.chars
        else:
            flush_current()
            current = [unit]
            current_chars = unit.chars

    flush_current()
    return segments


def section_segments(section, max_chars):
    """Keep normal FILE sections intact; split only oversized sections."""
    units = section_units(section)
    if sum(unit.chars for unit in units) <= max_chars:
        return [Segment(units)]
    return pack_units(units, max_chars)


def pop_trailing_h1(segments):
    """Remove a trailing h1 unit so it can begin the next chunk."""
    if not segments or not segments[-1].ends_with_h1:
        return None

    last_segment = segments[-1]
    heading = last_segment.units.pop()
    if not last_segment.units:
        segments.pop()
    return heading


def group_segments(segments, max_chars):
    """Group FILE segments and keep chunk boundaries away from h1 headings."""
    chunks = []
    current = []
    current_chars = 0

    def flush_current():
        nonlocal current, current_chars
        if current:
            chunks.append(Chunk(current))
            current = []
            current_chars = 0

    for segment in segments:
        if not current:
            current = [segment]
            current_chars = segment.chars
            continue

        if current_chars + segment.chars <= max_chars:
            current.append(segment)
            current_chars += segment.chars
            continue

        heading = pop_trailing_h1(current)
        if heading is not None:
            flush_current()
            current = [Segment([heading]), segment]
            current_chars = heading.chars + segment.chars
        else:
            flush_current()
            current = [segment]
            current_chars = segment.chars

    flush_current()
    return chunks


def merge_chunks(left, right):
    return Chunk(left.segments + right.segments)


def merge_small_chunks(chunks, max_chars):
    """Merge fragments smaller than max_chars/3 into an adjacent chunk."""
    threshold = max_chars / 3
    merged = []

    index = 0
    while index < len(chunks):
        if chunks[index].chars >= threshold:
            merged.append(chunks[index])
            index += 1
            continue

        small_run = []
        while index < len(chunks) and chunks[index].chars < threshold:
            small_run.append(chunks[index])
            index += 1
        small_chunk = small_run[0]
        for following_small in small_run[1:]:
            small_chunk = merge_chunks(small_chunk, following_small)

        if not merged:
            if index < len(chunks):
                merged.append(merge_chunks(small_chunk, chunks[index]))
                index += 1
            else:
                merged.append(small_chunk)
        elif small_chunk.ends_with_h1 and index < len(chunks):
            # Keep a trailing h1 at the beginning of the next destination.
            merged.append(merge_chunks(small_chunk, chunks[index]))
            index += 1
        else:
            merged[-1] = merge_chunks(merged[-1], small_chunk)

    return merged


def flatten_units(chunk):
    for segment in chunk.segments:
        yield from segment.units


def render_chunk(chunk):
    return "\n\n".join(unit.text for unit in flatten_units(chunk)) + "\n"


def extract_file_markers(text):
    return [line for line in text.splitlines() if FILE_MARKER_RE.match(line)]


def validate_marker_integrity(sections, chunks):
    """Ensure the output marker sequence exactly matches the source sequence."""
    expected = [section.marker for section in sections]
    actual = []
    for chunk in chunks:
        actual.extend(extract_file_markers(render_chunk(chunk)))
    if actual != expected:
        raise ValueError(
            "FILE marker integrity check failed: output markers differ from source"
        )


def chunk_file_labels(chunk, occurrence_counts):
    """List source files represented by a chunk, adding part labels only to the index."""
    labels = []
    seen = set()
    for unit in flatten_units(chunk):
        if unit.file_name in seen:
            continue
        seen.add(unit.file_name)
        occurrence_counts[unit.file_name] = occurrence_counts.get(unit.file_name, 0) + 1
        occurrence = occurrence_counts[unit.file_name]
        labels.append(
            unit.file_name if occurrence == 1 else f"{unit.file_name} (part {occurrence})"
        )
    return labels


def main():
    parser = argparse.ArgumentParser(
        description="Split source.md into FILE-bounded chunks for parallel translation."
    )
    parser.add_argument("--source", required=True, help="Path to source.md")
    parser.add_argument("--output-dir", required=True, help="Output directory for chunks")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=6000,
        help="Target chars per chunk (default: 6000)",
    )
    args = parser.parse_args()

    if args.max_chars <= 0:
        parser.error("--max-chars must be greater than zero")

    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    if not source_path.exists():
        print(f"Error: source.md not found: {source_path}")
        sys.exit(1)

    sections = parse_source_sections(source_path)
    segments = []
    for section in sections:
        segments.extend(section_segments(section, args.max_chars))

    chunks = group_segments(segments, args.max_chars)
    chunks = merge_small_chunks(chunks, args.max_chars)
    validate_marker_integrity(sections, chunks)

    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_index = {}
    occurrence_counts = {}

    for index, chunk in enumerate(chunks, start=1):
        chunk_name = f"chunk-{index:02d}"
        chunk_path = output_dir / f"{chunk_name}.md"
        content = render_chunk(chunk)
        with open(chunk_path, "w", encoding="utf-8", newline="\n") as chunk_file:
            chunk_file.write(content)

        chunk_index[chunk_name] = {
            "files": chunk_file_labels(chunk, occurrence_counts),
            "chars": chunk.chars,
        }
        print(f"  {chunk_name}: {', '.join(chunk_index[chunk_name]['files'])} ({chunk.chars} chars)")

    index_path = output_dir / "chunk_index.json"
    with open(index_path, "w", encoding="utf-8", newline="\n") as index_file:
        json.dump(chunk_index, index_file, ensure_ascii=False, indent=2)
        index_file.write("\n")

    print(f"Found {len(sections)} FILE sections in {source_path.name}")
    print(f"\nDone! {len(chunks)} chunks in {output_dir}")
    print(f"Index: {index_path}")


if __name__ == "__main__":
    main()
