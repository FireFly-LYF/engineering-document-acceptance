# -*- coding: utf-8 -*-
"""Fetch classified public archive-catalog PDFs into reference/."""
from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "reference"
SHARED = ROOT / "archive-catalogs"
ROAD = ROOT / "road-bridge"
PIPE = ROOT / "municipal-pipeline"
PUBLIC = ROOT / "public-pdfs"

for d in (SHARED, ROAD, PIPE):
    d.mkdir(parents=True, exist_ok=True)

DOWNLOADS: list[tuple[Path, str]] = [
    (
        SHARED / "sg-archive-guide-2025.pdf",
        "https://www.sg.gov.cn/attachment/0/286/286198/2779605.pdf",
    ),
    (
        SHARED / "jm-archive-unified-catalog.pdf",
        "http://www.jiangmen.gov.cn/attachment/0/341/341760/3304209.pdf",
    ),
    (
        SHARED / "sz-archive-guide-2025.pdf",
        "https://zjj.sz.gov.cn/attachment/1/1628/1628043/12250554.pdf",
    ),
    (
        SHARED / "gbt-50328-2014-archive-code.pdf",
        "http://www.sxmtjl.com/uploads/files/2015/05/431200c9521bc4592dd3e9cb7fb22896.pdf",
    ),
    (
        PIPE / "underground-pipeline-data-management.pdf",
        "https://www.csgpc.org/ueditor/php/upload/file/20260609/1780990079295399.pdf",
    ),
    (
        ROAD / "highway-project-data-management.pdf",
        "https://qxb-img-osscache.qixin.com/standards/300fbe9b3a94f899fa56a4e520456c2a.pdf",
    ),
]

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}


def fetch(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        out.write_bytes(resp.read())


def main() -> None:
    # Prefer copy from public-pdfs when identical files already fetched
    for name in ("jm-archive-unified-catalog.pdf", "sz-archive-guide-2025.pdf"):
        src, dst = PUBLIC / name, SHARED / name
        if src.exists() and src.stat().st_size > 1000:
            if not dst.exists() or dst.stat().st_size < 1000:
                shutil.copy2(src, dst)
                print(f"COPIED {name} -> archive-catalogs/")

    for out, url in DOWNLOADS:
        if out.exists() and out.stat().st_size > 1000:
            print(f"SKIP exists {out.relative_to(ROOT)} ({out.stat().st_size})")
            continue
        print(f"GET {url}")
        try:
            fetch(url, out)
            head = out.read_bytes()[:5]
            print(f"OK {out.stat().st_size} magic={head!r} -> {out.relative_to(ROOT)}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {out.name}: {exc}")

    print("files:")
    for p in sorted(ROOT.rglob("*.pdf")):
        print(f"  {p.relative_to(ROOT)}\t{p.stat().st_size}")


if __name__ == "__main__":
    main()
