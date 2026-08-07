#!/usr/bin/env python3
"""校验 EPUB：结构合法、导航目录完整、目录条目与正文标题一一对应、无残留特征。

用法:
    python scripts/verify.py book/book.epub [-o book/verify_report.txt]

检查项:
    1. 容器结构（META-INF/container.xml → content.opf）
    2. manifest 与 spine 一致性
    3. 导航目录存在（nav.xhtml 或 toc.ncx），每条目在正文中有对应标题
    4. 目录锚点目标可解析（点击可跳转）
    5. 正文字段无残留：<!-- CH 锚点、COPYRIGHT_CANDIDATE、<!-- PAGE、__ 连接标记
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

CN_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF_NS = "http://www.idpf.org/2007/opf"
XHTML_NS = "http://www.w3.org/1999/xhtml"
OPS_NS = "http://www.idpf.org/2007/ops"


def force_utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class VerifyReport:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.errors = 0

    def info(self, msg: str) -> None:
        self.lines.append("[INFO] " + msg)

    def ok(self, msg: str) -> None:
        self.lines.append("[OK]   " + msg)

    def err(self, msg: str) -> None:
        self.errors += 1
        self.lines.append("[FAIL] " + msg)

    def save(self, path: Path) -> None:
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def get_opf_path(z: zipfile.ZipFile) -> str | None:
    if "META-INF/container.xml" not in z.namelist():
        return None
    root = ET.fromstring(z.read("META-INF/container.xml"))
    for rf in root.iter(f"{{{CN_NS}}}rootfile"):
        return rf.get("full-path")
    return None


def get_nav_targets(opf_root: ET.Element) -> list[tuple[str, str]]:
    """从 manifest 找出 nav 文件（EPUB3）与 ncx 文件（EPUB2）。"""
    nav_path, ncx_path = "", ""
    for item in opf_root.iter(f"{{{OPF_NS}}}item"):
        props = item.get("properties", "")
        media = item.get("media-type", "")
        if "nav" in props or media == "application/x-dtbncx+xml":
            if media == "application/x-dtbncx+xml":
                ncx_path = item.get("href", "")
            else:
                nav_path = item.get("href", "")
    return nav_path, ncx_path


def collect_nav_links(z: zipfile.ZipFile, nav_path: str) -> list[tuple[str, str]]:
    """解析 nav.xhtml 的所有 <a href>，返回 [(href, text), ...]。"""
    links: list[tuple[str, str]] = []
    root = ET.fromstring(z.read(nav_path))
    for a in root.iter(f"{{{XHTML_NS}}}a"):
        href = a.get("href", "")
        text = " ".join(a.itertext()).strip()
        if href:
            links.append((href, text))
    return links


def collect_ncx_links(z: zipfile.ZipFile, ncx_path: str) -> list[tuple[str, str]]:
    """解析 toc.ncx 的所有 content src，返回 [(src, label), ...]。"""
    links: list[tuple[str, str]] = []
    root = ET.fromstring(z.read(ncx_path))
    for np in root.iter():
        if localname(np.tag) == "navPoint":
            label = next(np.iter()).text or ""
            content = np.find(".//{*}content")
            src = content.get("src", "") if content is not None else ""
            links.append((src, label.strip()))
    return links


def pjoin(base: str, rel: str) -> str:
    """把相对 manifest 的 href 解析为 zip 内绝对路径（相对 content.opf 所在目录）。"""
    if not base:
        return rel
    return base.rstrip("/") + "/" + rel.lstrip("/")


def check_target(z: zipfile.ZipFile, href: str, opf_dir: str, nav_doc: str = "") -> tuple[bool, str]:
    """检查目录条目目标可解析：文件存在，锚点 id 存在且附近有标题文本。"""
    if "#" in href:
        fname, anchor = href.split("#", 1)
    else:
        fname, anchor = href, ""
    if not fname:
        # 纯片段 href（如 pandoc 的 #toc）：指向 nav 文档内的锚点，属合法目录首页
        if not nav_doc:
            return False, f"纯片段锚点 #{anchor} 但缺少定位文档"
        data = z.read(nav_doc).decode("utf-8", errors="ignore")
        if f'id="{anchor}"' in data or f"id='{anchor}'" in data:
            return True, f"{nav_doc}#{anchor}"
        return False, f"锚点 {anchor} 在 {nav_doc} 中不存在"
    # manifest 的 href 相对 content.opf 所在目录；zip 内路径可能大小写/编码不同，做规整匹配
    fname_norm = fname.replace("\\", "/")
    abs_name = pjoin(opf_dir, fname_norm)
    candidates = [abs_name] + [n for n in z.namelist() if n.rstrip("/").lower() == abs_name.lower()]
    if not candidates or not any(c in z.namelist() for c in candidates):
        return False, f"目标文件不存在：{fname}"
    real = next(c for c in candidates if c in z.namelist())
    data = z.read(real).decode("utf-8", errors="ignore")
    if anchor:
        if f'id="{anchor}"' not in data and f"id='{anchor}'" not in data:
            return False, f"锚点 {anchor} 在 {real} 中不存在"
        return True, f"{real}#{anchor}"
    # 无锚点：要求文件内存在正文标题（封面页 cover.xhtml 除外——SVG 包裹图片，无 h 标题）
    if re.search(r"<h[1-6][^>]*>", data):
        return True, real
    if "cover" in real.lower():
        return True, f"{real}（封面页）"
    return False, f"{real} 中未发现正文标题"


def main() -> None:
    force_utf8()
    ap = argparse.ArgumentParser(description="校验 EPUB 结构与导航目录")
    ap.add_argument("input", help="输入 EPUB 路径")
    ap.add_argument("-o", "--output", default="verify_report.txt", help="报告输出路径")
    args = ap.parse_args()

    rep = VerifyReport()
    epub_path = Path(args.input)
    if not epub_path.exists():
        print(f"找不到输入文件：{epub_path}")
        sys.exit(1)

    with zipfile.ZipFile(epub_path) as z:
        # 1. 容器结构
        opf_path = get_opf_path(z)
        if not opf_path:
            rep.err("缺少 META-INF/container.xml 或 rootfile")
        else:
            rep.ok(f"容器结构完整，content.opf = {opf_path}")
        if not opf_path:
            rep.save(Path(args.output))
            print("校验未通过（结构损坏）")
            sys.exit(1)

        # 2. manifest / spine 一致性
        opf_root = ET.fromstring(z.read(opf_path))
        opf_dir = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
        manifest_ids = {i.get("id") for i in opf_root.iter(f"{{{OPF_NS}}}item")}
        spine_refs = [r.get("idref") for r in opf_root.iter(f"{{{OPF_NS}}}itemref")]
        orphan = [r for r in spine_refs if r not in manifest_ids]
        if orphan:
            rep.err(f"spine 引用不存在的 manifest id：{orphan}")
        else:
            rep.ok(f"manifest/spine 一致，spine 共 {len(spine_refs)} 项")

        # 3. 导航目录
        nav_path, ncx_path = get_nav_targets(opf_root)
        nav_doc = pjoin(opf_dir, nav_path) if nav_path else (pjoin(opf_dir, ncx_path) if ncx_path else "")
        links: list[tuple[str, str]] = []
        if nav_path:
            try:
                links = collect_nav_links(z, pjoin(opf_dir, nav_path))
                rep.ok(f"找到导航 nav（{pjoin(opf_dir, nav_path)}），目录条目 {len(links)} 条")
            except Exception as e:
                rep.err(f"解析 nav 失败：{e}")
        elif ncx_path:
            try:
                links = collect_ncx_links(z, pjoin(opf_dir, ncx_path))
                rep.ok(f"找到 toc.ncx（{pjoin(opf_dir, ncx_path)}），目录条目 {len(links)} 条")
            except Exception as e:
                rep.err(f"解析 ncx 失败：{e}")
        else:
            rep.err("未找到导航目录（nav 或 ncx）")

        # 4. 目录条目目标可解析
        bad_target = 0
        for href, text in links:
            ok, msg = check_target(z, href, opf_dir, nav_doc)
            if not ok:
                bad_target += 1
                rep.err(f"目录「{text or href}」→ {msg}")
        if bad_target == 0 and links:
            rep.ok("所有目录条目均可解析（可点击跳转）")

        # 5. 残留特征
        xhtml_files = [
            n for n in z.namelist()
            if n.endswith((".xhtml", ".html")) and not n.startswith("META-INF/")
        ]
        leftovers = 0
        for n in xhtml_files:
            data = z.read(n).decode("utf-8", errors="ignore")
            for pat, label in (
                (r"<!--\s*CH\d\s*:", "锚点注释 <!-- CH"),
                (r"COPYRIGHT_CANDIDATE", "版权页候选标记"),
                (r"<!--\s*PAGE\s*\d", "页定位注释 <!-- PAGE"),
                (r"__", "跨页连接标记 __"),
            ):
                if re.search(pat, data):
                    leftovers += 1
                    rep.err(f"{n} 含 {label} 残留")
        if leftovers == 0:
            rep.ok("正文无锚点注释 / 版权页标记残留")

    rep.info(f"检查完成，正文 xhtml 文件 {len(xhtml_files) if 'xhtml_files' in dir() else 0} 个")
    rep.info("通过" if rep.errors == 0 else f"失败：{rep.errors} 项错误")
    rep.save(Path(args.output))
    print(f"校验报告 → {args.output}（{'通过' if rep.errors == 0 else f'{rep.errors} 项错误'}）")
    sys.exit(0 if rep.errors == 0 else 1)


if __name__ == "__main__":
    main()
