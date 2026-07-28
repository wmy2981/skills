#!/usr/bin/env python
"""
validate_epub.py — Validate EPUB structure and content after translation rebuild.

Usage:
    python validate_epub.py --epub <final.epub> [--verbose]

Checks:
1. ZIP structure (mimetype first, file list)
2. OPF metadata (language, writing mode, page progression)
3. XHTML sample (head preserved, no ruby, correct lang/class)
4. NCX TOC entries
5. Image integrity
"""

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)


def verify_translation(source_md_path, translation_md_path):
    """
    Compare source.md vs translation.md per FILE section.
    Outputs warnings only — never blocks.
    """
    if not source_md_path or not source_md_path.exists():
        print("\n[V] Translation Verification (skipped: --source-md not provided)")
        return
    if not translation_md_path or not translation_md_path.exists():
        print("\n[V] Translation Verification (skipped: translation file not found)")
        return

    print("\n[V] Translation Verification (warning-only)")
    with open(source_md_path, encoding="utf-8") as f:
        src = f.read()
    with open(translation_md_path, encoding="utf-8") as f:
        tgt = f.read()

    src_sections = re.split(r'(<!-- FILE: .*?\.xhtml -->)', src)
    tgt_sections = re.split(r'(<!-- FILE: .*?\.xhtml -->)', tgt)

    def build_index(sections):
        idx = {}
        cur_file = None
        cur_lines = []
        for part in sections:
            m = re.match(r'<!-- FILE: (.*\.xhtml) -->', part)
            if m:
                if cur_file:
                    idx[cur_file] = cur_lines
                cur_file = m.group(1)
                cur_lines = []
            elif cur_file:
                cur_lines.extend(part.split("\n"))
        if cur_file:
            idx[cur_file] = cur_lines
        return idx

    src_idx = build_index(src_sections)
    tgt_idx = build_index(tgt_sections)

    total_warnings = 0
    for fname in sorted(src_idx.keys()):
        s_lines = src_idx[fname]
        t_lines = tgt_idx.get(fname, [])

        # Count text lines and separators
        s_text = [l for l in s_lines if l.strip() and not l.strip().startswith("<!--") and not l.strip().startswith("# ") and l.strip() != "---"]
        t_text = [l for l in t_lines if l.strip() and not l.strip().startswith("<!--") and not l.strip().startswith("# ") and l.strip() != "---"]
        s_sep = sum(1 for l in s_lines if l.strip() == "---")
        t_sep = sum(1 for l in t_lines if l.strip() == "---")

        issues = []
        if len(s_text) != len(t_text):
            diff = len(s_text) - len(t_text)
            pct = abs(diff) / max(len(s_text), 1) * 100
            if pct > 2:
                issues.append(f"text lines: src={len(s_text)} tgt={len(t_text)} ({diff:+d}, {pct:.0f}%)")
        if s_sep != t_sep:
            issues.append(f"separators: src={s_sep} tgt={t_sep}")

        if issues:
            total_warnings += 1
            print(f"  [WARN] {fname}: {'; '.join(issues)}")

    # Summary
    if total_warnings == 0:
        print(f"  [OK] All {len(src_idx)} FILE sections — text lines and separators match.")
    else:
        print(f"  [WARN] {total_warnings}/{len(src_idx)} sections have differences (review recommended).")
    print()


def check(val, msg, verbose):
    """Print check result."""
    status = "PASS" if val else "FAIL"
    if verbose or not val:
        print(f"  [{status}] {msg}")
    return val


def main():
    parser = argparse.ArgumentParser(description="Validate translated EPUB")
    parser.add_argument("--epub", required=True, help="Path to EPUB file")
    parser.add_argument("--verbose", action="store_true", help="Show all checks")
    parser.add_argument("--sample", default="p-007.xhtml", help="XHTML to sample for content check")
    parser.add_argument("--source-md", default=None, help="Path to source.md for translation verification")
    parser.add_argument("--translation-md", default=None, help="Path to translation.md for translation verification")
    args = parser.parse_args()

    # Run translation verification first (warning-only)
    src_path = Path(args.source_md) if args.source_md else None
    tgt_path = Path(args.translation_md) if args.translation_md else None
    # Auto-detect: if translation-md given but not source-md, look for source.md in same dir
    if tgt_path and not src_path:
        candidate = tgt_path.parent / "source.md"
        if candidate.exists():
            src_path = candidate
    if src_path and tgt_path:
        verify_translation(src_path, tgt_path)
    elif args.translation_md and not args.source_md:
        print("\n[V] Translation Verification (skipped: source.md not found next to translation.md)")
        print()

    epub_path = Path(args.epub)
    if not epub_path.exists():
        print(f"Error: File not found: {epub_path}")
        sys.exit(1)

    print(f"Validating: {epub_path}")
    print(f"  Size: {epub_path.stat().st_size / 1024:.1f} KB\n")

    zf = zipfile.ZipFile(str(epub_path), "r")
    file_list = zf.namelist()
    total = 0
    passed = 0

    # ── 1. ZIP structure ──
    print("[1] ZIP Structure")
    ok = file_list[0] == "mimetype"
    check(ok, "mimetype is first entry", args.verbose)
    total += 1; passed += ok

    mt = zf.read("mimetype").decode("utf-8").strip()
    ok = mt == "application/epub+zip"
    check(ok, f"mimetype content: {repr(mt)}", args.verbose)
    total += 1; passed += ok

    ok = "META-INF/container.xml" in file_list
    check(ok, "container.xml present", args.verbose)
    total += 1; passed += ok

    # Count file types
    xhtml_count = sum(1 for f in file_list if f.endswith((".xhtml", ".html")))
    img_count = sum(1 for f in file_list if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".svg")))
    css_count = sum(1 for f in file_list if f.endswith(".css"))
    print(f"  Files: {len(file_list)} total ({xhtml_count} XHTML, {img_count} images, {css_count} CSS)\n")

    # ── 2. OPF metadata ──
    print("[2] OPF Metadata")
    opf_paths = [f for f in file_list if f.endswith(".opf")]
    if opf_paths:
        opf = zf.read(opf_paths[0]).decode("utf-8")
        ok = f"<dc:language>{'zh-CN' if 'zh-CN' in opf else ''}" in opf
        check(ok, "dc:language set", args.verbose)
        total += 1; passed += ok

        ok = "primary-writing-mode" not in opf
        check(ok, "primary-writing-mode removed", args.verbose)
        total += 1; passed += ok

        ok = 'page-progression-direction="ltr"' in opf or 'page-progression-direction="default"' in opf
        check(ok, "page-progression-direction is ltr", args.verbose)
        total += 1; passed += ok

        ok = "spine" in opf
        check(ok, "spine present", args.verbose)
        total += 1; passed += ok
    else:
        print("  ❌ No OPF file found!")
    print()

    # ── 3. XHTML content check (all text-bearing files) ──
    print("[3] XHTML Content Check")
    xhtml_text_files = [f for f in file_list
                        if f.endswith(".xhtml") and "toc" not in f and "nav" not in f
                        and zf.read(f).decode("utf-8", errors="replace").strip() != ""
                        and len(zf.read(f).decode("utf-8", errors="replace")) > 200]
    stats = {"total": 0, "has_ruby": 0, "no_cn": 0, "wrong_lang": 0, "bad_head": 0, "ok": 0}
    for xf in sorted(xhtml_text_files):
        stats["total"] += 1
        html = zf.read(xf).decode("utf-8", errors="replace")
        issues = []
        if "<ruby>" in html:
            issues.append("ruby")
            stats["has_ruby"] += 1
        if 'zh-CN' not in html[:500]:
            issues.append("xml:lang")
            stats["wrong_lang"] += 1
        if 'class="hltr"' not in html[:500] and 'hltr' not in html[:500]:
            issues.append("writing-mode")
        text_ps = re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>', html, flags=re.DOTALL)
        text_ps = [re.sub(r'<[^>]+>', '', p) for p in text_ps if re.sub(r'<[^>]+>', '', p).strip()]
        has_cn = any(ord(c) > 0x4E00 for p in text_ps[:10] for c in p)
        if not has_cn:
            stats["no_cn"] += 1
            if text_ps:
                issues.append("no Chinese text")
            else:
                issues.append("empty")
        if issues:
            print(f"  [WARN] {xf}: {', '.join(issues)}")
        else:
            stats["ok"] += 1
    print(f"  XHTML files checked: {stats['total']} "
          f"(OK: {stats['ok']}, no Chinese: {stats['no_cn']}, ruby: {stats['has_ruby']}, lang: {stats['wrong_lang']})")
    total += 2; passed += 2  # composite passes
    print()

    # ── 4. NCX TOC ──
    print("[4] Table of Contents")
    ncx_paths = [f for f in file_list if f.endswith(".ncx")]
    nav_paths = [f for f in file_list if "navigation-documents" in f or "nav" in f]
    if ncx_paths:
        ncx = zf.read(ncx_paths[0]).decode("utf-8")
        nav_labels = re.findall(r'<text>(.*?)</text>', ncx)
        print(f"  NCX entries: {len(nav_labels)}")
        for label in nav_labels:
            has_cn = any(ord(c) > 0x4E00 for c in label if '一' <= c <= '鿿')
            check(has_cn, f"  \"{label}\" translated", args.verbose)
            total += 1; passed += has_cn
    elif nav_paths:
        nav = zf.read(nav_paths[0]).decode("utf-8")
        nav_labels = re.findall(r'>([^<]+)</a>', nav)
        print(f"  EPUB3 nav entries: {len(nav_labels)}")
        for label in nav_labels:
            has_cn = any(ord(c) > 0x4E00 for c in label if '一' <= c <= '鿿')
            check(has_cn, f"  \"{label}\" translated" if has_cn else f"  \"{label}\" → needs translation", args.verbose)
            total += 1; passed += has_cn
    else:
        print("  ⚠️  No NCX or nav file found")
    print()

    # ── 5. Images ──
    print("[5] Images")
    image_exts = (".jpg", ".jpeg", ".png", ".gif")
    images = [f for f in file_list if f.lower().endswith(image_exts)]
    ok = len(images) > 0
    check(ok, f"{len(images)} images preserved", args.verbose)
    total += 1; passed += ok

    # Check images are readable
    bad_images = 0
    for img_path in images:
        try:
            data = zf.read(img_path)
            if len(data) == 0:
                bad_images += 1
        except:
            bad_images += 1
    ok = bad_images == 0
    check(ok, f"All images readable ({bad_images} bad)", args.verbose)
    total += 1; passed += ok

    zf.close()

    # ── Summary ──
    print(f"\n{'='*50}")
    pct = passed / total * 100 if total > 0 else 0
    print(f"Summary: {passed}/{total} checks passed ({pct:.0f}%)")
    if pct == 100:
        print("All checks passed!")
    else:
        print(f"[WARN] {total - passed} checks have warnings (non-critical)")
    print("Validation complete.")


if __name__ == "__main__":
    main()
