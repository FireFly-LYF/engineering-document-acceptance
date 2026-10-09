# -*- coding: utf-8 -*-
"""Form-style PDF builders modeled on GB50300-2013 appendix tables and common archive covers.

Layout references (public blank forms / standards, not real project archives):
- GB50300-2013 附录 E/F/G/H（检验批、分项、分部、观感）
- reference/public-pdfs/acceptance-check-forms-unified.pdf
- reference/public-pdfs/gb50300-2013-acceptance-standard.pdf

Synthetic filled values only. Field extractors expect 「标签：值」 lines; those are
written into table cells and a small 资料著录 strip.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import fitz

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
]


def find_font() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("未找到可用中文字体（msyh/simhei/simsun）")


FONT_PATH = find_font()


def _font(page) -> None:
    page.insert_font(fontname="cn", fontfile=str(FONT_PATH))


def _text(page, x, y, s, size=10, color=(0, 0, 0)):
    page.insert_text((x, y), s, fontname="cn", fontsize=size, color=color)


def _box_text(page, rect, s, size=9, align=0):
    page.insert_textbox(rect, s, fontname="cn", fontsize=size, align=align)


def _hline(page, x0, x1, y, w=0.6):
    page.draw_line(fitz.Point(x0, y), fitz.Point(x1, y), color=(0, 0, 0), width=w)


def _vline(page, x, y0, y1, w=0.6):
    page.draw_line(fitz.Point(x, y0), fitz.Point(x, y1), color=(0, 0, 0), width=w)


def _rect(page, r, w=1.0):
    page.draw_rect(r, color=(0, 0, 0), width=w)


def catalog_strip(page, meta: dict, y0: float = 52) -> float:
    """Compact 著录 strip so audit_prepare regex still sees 项目名称：… etc."""
    keys = [
        ("项目名称", meta.get("项目名称") or meta.get("工程名称", "")),
        ("项目编号", meta.get("项目编号", "")),
        ("建设单位", meta.get("建设单位", "")),
        ("施工单位", meta.get("施工单位", "")),
        ("监理单位", meta.get("监理单位", "")),
        ("设计单位", meta.get("设计单位", "")),
        ("工程地址", meta.get("工程地址", "")),
        ("开工日期", meta.get("开工日期", "")),
        ("竣工日期", meta.get("竣工日期", "")),
        ("合同金额（元）", meta.get("合同金额（元）") or meta.get("合同金额", "")),
        ("文件编号", meta.get("文件编号", "")),
    ]
    x, y = 48, y0
    _text(page, x, y, "【资料著录（合成填写）】", size=8, color=(0.35, 0.35, 0.35))
    y += 12
    for k, v in keys:
        if not v:
            continue
        line = f"{k}：{v}"
        _text(page, x, y, line[:78], size=8, color=(0.15, 0.15, 0.15))
        y += 11
    _hline(page, 42, 553, y + 2, 0.4)
    return y + 10


def seal(page, x=430, y=700, label="示意章"):
    page.draw_oval(fitz.Rect(x, y, x + 90, y + 90), color=(0.75, 0.12, 0.12), width=1.8)
    _text(page, x + 18, y + 42, label, size=10, color=(0.75, 0.12, 0.12))


def save(doc, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(path, garbage=4, deflate=True)
    doc.close()


def make_inspection_batch(
    path: Path,
    *,
    meta: dict,
    batch_name: str,
    file_no: str,
    division: str,
    subitem: str,
    location: str,
    capacity: str,
    basis_sg: str,
    basis_ys: str,
    major_rows: list[tuple[str, str, str, str]],
    general_rows: list[tuple[str, str, str, str]],
    scan_style: bool = False,
    note: str = "",
) -> None:
    """GB50300 附录 E 风格：检验批质量验收记录。"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    _font(page)
    if scan_style:
        page.draw_rect(page.rect, color=(0.93, 0.93, 0.9), fill=(0.93, 0.93, 0.9))

    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 150, 48, f"{batch_name}检验批质量验收记录", size=13)
    _text(page, 420, 48, f"编号：{file_no}", size=9)
    _text(page, 42, 64, "表式参考：GB50300-2013 附录E（合成填写，非真实档案）", size=7, color=(0.4, 0.4, 0.4))

    y = catalog_strip(page, {**meta, "文件编号": file_no, "工程名称": meta.get("项目名称", "")}, 78)

    # header grid 2 rows x multi cols
    x0, x1 = 42, 553
    row_h = 22
    headers = [
        [
            ("单位(子单位)工程名称", 150, meta.get("项目名称", "")),
            ("分部(子分部)工程名称", 120, division),
            ("分项工程名称", 100, subitem),
        ],
        [
            ("施工单位", 150, meta.get("施工单位", "")),
            ("项目负责人", 100, "（合成）王某某"),
            ("施工班组长", 100, "（合成）李某某"),
        ],
        [
            ("分包单位", 150, "/"),
            ("分包单位项目负责人", 120, "/"),
            ("监理单位", 100, meta.get("监理单位", "")),
        ],
        [
            ("检验批容量", 100, capacity),
            ("检验批部位", 150, location),
            ("施工依据", 120, basis_sg),
        ],
        [
            ("验收依据", 370, basis_ys),
        ],
    ]
    for row in headers:
        widths = [w for _, w, _ in row]
        total = sum(widths) or 1
        scale = (x1 - x0) / total
        x = x0
        for label, w, val in row:
            ww = w * scale
            _rect(page, fitz.Rect(x, y, x + ww, y + row_h), 0.5)
            _box_text(page, fitz.Rect(x + 2, y + 2, x + ww - 2, y + row_h - 2), f"{label}\n{val}", size=7)
            x += ww
        y += row_h

    # column titles for items
    col_w = [28, 150, 70, 160, 50]
    titles = ["序号", "验收项目 / 设计要求及规范规定", "最小/实际抽样", "检查记录", "结果"]
    y += 4
    x = x0
    for tw, title in zip(col_w, titles):
        _rect(page, fitz.Rect(x, y, x + tw, y + 18), 0.5)
        _box_text(page, fitz.Rect(x + 1, y + 3, x + tw - 1, y + 16), title, size=7, align=1)
        x += tw
    y += 18

    def draw_section(title: str, rows: list[tuple[str, str, str, str]], start_idx: int):
        nonlocal y
        _rect(page, fitz.Rect(x0, y, x1, y + 16), 0.5)
        _box_text(page, fitz.Rect(x0 + 2, y + 2, x1 - 2, y + 14), title, size=8)
        y += 16
        for i, (item, sample, record, result) in enumerate(rows, start_idx):
            h = 28
            if y + h > 720:
                break
            vals = [str(i), item, sample, record, result]
            x = x0
            for tw, val in zip(col_w, vals):
                _rect(page, fitz.Rect(x, y, x + tw, y + h), 0.4)
                _box_text(page, fitz.Rect(x + 1, y + 2, x + tw - 1, y + h - 2), val, size=7)
                x += tw
            y += h

    draw_section("主控项目", major_rows, 1)
    draw_section("一般项目", general_rows, 1)
    if note:
        _text(page, 44, y + 10, note[:70], size=8, color=(0.3, 0.3, 0.3))
        y += 18

    y = max(y + 8, 730)
    _rect(page, fitz.Rect(x0, y, 300, y + 55), 0.5)
    _box_text(
        page,
        fitz.Rect(x0 + 4, y + 4, 296, y + 52),
        "施工单位检查结果：合格\n专业工长：\n项目专业质量检查员：\n年  月  日",
        size=8,
    )
    _rect(page, fitz.Rect(300, y, x1, y + 55), 0.5)
    _box_text(
        page,
        fitz.Rect(304, y + 4, x1 - 4, y + 52),
        "监理单位验收结论：同意验收\n专业监理工程师：\n年  月  日",
        size=8,
    )
    seal(page, 470, 760)
    if scan_style:
        _text(page, 42, 820, "【扫描件示意】", size=8, color=(0.4, 0.4, 0.4))
    save(doc, path)


def make_subitem_record(
    path: Path,
    *,
    meta: dict,
    title: str,
    file_no: str,
    division: str,
    subitem: str,
    batch_count: str,
    conclusion: str,
) -> None:
    """GB50300 附录 F 风格：分项工程质量验收记录。"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    _font(page)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 180, 50, f"{title}", size=13)
    _text(page, 400, 50, f"编号：{file_no}", size=9)
    _text(page, 42, 66, "表式参考：GB50300-2013 附录F（合成填写）", size=7, color=(0.4, 0.4, 0.4))
    y = catalog_strip(page, {**meta, "文件编号": file_no}, 80)

    rows = [
        ("单位(子单位)工程名称", meta.get("项目名称", "")),
        ("分部(子分部)工程名称", division),
        ("分项工程名称", subitem),
        ("检验批数量", batch_count),
        ("施工单位", meta.get("施工单位", "")),
        ("项目负责人", "（合成）王某某"),
        ("项目技术负责人", "（合成）赵某某"),
        ("监理单位", meta.get("监理单位", "")),
    ]
    x0, x1 = 42, 553
    for label, val in rows:
        _rect(page, fitz.Rect(x0, y, 200, y + 24), 0.5)
        _rect(page, fitz.Rect(200, y, x1, y + 24), 0.5)
        _box_text(page, fitz.Rect(x0 + 4, y + 5, 196, y + 20), label, size=9)
        _box_text(page, fitz.Rect(204, y + 5, x1 - 4, y + 20), val, size=9)
        y += 24

    y += 10
    _rect(page, fitz.Rect(x0, y, x1, y + 80), 0.5)
    _box_text(
        page,
        fitz.Rect(x0 + 6, y + 8, x1 - 6, y + 74),
        f"验收记录：所含检验批质量均已验收合格，质量控制资料完整。\n验收结论：{conclusion}",
        size=10,
    )
    y += 100
    _rect(page, fitz.Rect(x0, y, 297, y + 70), 0.5)
    _box_text(page, fitz.Rect(x0 + 4, y + 6, 293, y + 66), "施工单位\n项目专业技术负责人：\n年  月  日", size=9)
    _rect(page, fitz.Rect(297, y, x1, y + 70), 0.5)
    _box_text(page, fitz.Rect(301, y + 6, x1 - 4, y + 66), "监理单位\n专业监理工程师：\n年  月  日", size=9)
    seal(page)
    save(doc, path)


def make_division_record(
    path: Path,
    *,
    meta: dict,
    title: str,
    file_no: str,
    division: str,
    subitem_count: str,
    conclusion: str,
) -> None:
    """GB50300 附录 G 风格：分部工程质量验收记录。"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    _font(page)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 170, 50, title, size=13)
    _text(page, 400, 50, f"编号：{file_no}", size=9)
    _text(page, 42, 66, "表式参考：GB50300-2013 附录G（合成填写）", size=7, color=(0.4, 0.4, 0.4))
    y = catalog_strip(page, {**meta, "文件编号": file_no}, 80)
    rows = [
        ("单位(子单位)工程名称", meta.get("项目名称", "")),
        ("分部(子分部)工程名称", division),
        ("分项工程数量", subitem_count),
        ("施工单位", meta.get("施工单位", "")),
        ("项目负责人", "（合成）王某某"),
        ("项目技术负责人", "（合成）赵某某"),
        ("监理单位", meta.get("监理单位", "")),
        ("总监理工程师", "（合成）周某某"),
    ]
    x0, x1 = 42, 553
    for label, val in rows:
        _rect(page, fitz.Rect(x0, y, 200, y + 24), 0.5)
        _rect(page, fitz.Rect(200, y, x1, y + 24), 0.5)
        _box_text(page, fitz.Rect(x0 + 4, y + 5, 196, y + 20), label, size=9)
        _box_text(page, fitz.Rect(204, y + 5, x1 - 4, y + 20), val, size=9)
        y += 24
    y += 8
    _rect(page, fitz.Rect(x0, y, x1, y + 90), 0.5)
    _box_text(
        page,
        fitz.Rect(x0 + 6, y + 8, x1 - 6, y + 84),
        "质量控制资料：完整\n安全和功能检验（检测）报告：符合要求\n观感质量验收：好\n"
        f"验收结论：{conclusion}",
        size=10,
    )
    y += 110
    for i, lab in enumerate(["施工单位", "勘察单位", "设计单位", "监理单位", "建设单位"]):
        xx = 42 + i * 102
        _rect(page, fitz.Rect(xx, y, xx + 100, y + 70), 0.5)
        _box_text(page, fitz.Rect(xx + 3, y + 6, xx + 97, y + 66), f"{lab}\n（公章）\n年  月  日", size=7, align=1)
    save(doc, path)


def make_appearance_record(path: Path, *, meta: dict, file_no: str, grade: str = "好") -> None:
    """GB50300 附录 H 观感质量检查记录风格。"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    _font(page)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 180, 50, "单位工程观感质量检查记录", size=13)
    _text(page, 420, 50, f"编号：{file_no}", size=9)
    _text(page, 42, 66, "表式参考：GB50300-2013 附录H（合成填写）", size=7, color=(0.4, 0.4, 0.4))
    y = catalog_strip(page, {**meta, "文件编号": file_no}, 80)
    items = [
        ("室外墙面", grade),
        ("变形缝、水落管", grade),
        ("室内墙面", grade),
        ("室内顶棚", grade),
        ("室内地面", grade),
        ("门窗安装", grade),
        ("楼梯、踏步", grade),
        ("屋面", grade),
    ]
    x0, x1 = 42, 553
    _rect(page, fitz.Rect(x0, y, 80, y + 20), 0.5)
    _rect(page, fitz.Rect(80, y, 300, y + 20), 0.5)
    _rect(page, fitz.Rect(300, y, x1, y + 20), 0.5)
    _box_text(page, fitz.Rect(x0, y + 4, 80, y + 18), "序号", size=9, align=1)
    _box_text(page, fitz.Rect(80, y + 4, 300, y + 18), "项目", size=9, align=1)
    _box_text(page, fitz.Rect(300, y + 4, x1, y + 18), "质量评价", size=9, align=1)
    y += 20
    for i, (name, g) in enumerate(items, 1):
        _rect(page, fitz.Rect(x0, y, 80, y + 22), 0.4)
        _rect(page, fitz.Rect(80, y, 300, y + 22), 0.4)
        _rect(page, fitz.Rect(300, y, x1, y + 22), 0.4)
        _box_text(page, fitz.Rect(x0, y + 5, 80, y + 18), str(i), size=9, align=1)
        _box_text(page, fitz.Rect(84, y + 5, 296, y + 18), name, size=9)
        _box_text(page, fitz.Rect(304, y + 5, x1 - 4, y + 18), g, size=9, align=1)
        y += 22
    y += 12
    _rect(page, fitz.Rect(x0, y, x1, y + 50), 0.5)
    _box_text(page, fitz.Rect(x0 + 6, y + 10, x1 - 6, y + 44), f"观感质量综合评价：{grade}", size=11)
    seal(page)
    save(doc, path)


def make_official_report(
    path: Path,
    *,
    title: str,
    meta: dict,
    body_lines: Iterable[str],
    form_hint: str = "",
    scan_style: bool = False,
    doc_kind: str = "报告",
) -> None:
    """Cover + meta table + body + signature block for permits/contracts/reports."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    _font(page)
    if scan_style:
        page.draw_rect(page.rect, color=(0.93, 0.93, 0.9), fill=(0.93, 0.93, 0.9))
    _rect(page, fitz.Rect(32, 28, 563, 814), 1.6)
    _rect(page, fitz.Rect(38, 34, 557, 808), 0.7)

    _text(page, 48, 58, f"文号：{meta.get('文件编号', '（合成）')}", size=9)
    _text(page, 400, 58, f"资料类别：{doc_kind}", size=9)
    _text(page, 160, 88, title, size=16)
    if form_hint:
        _text(page, 48, 108, form_hint[:70], size=7, color=(0.4, 0.4, 0.4))
    _text(page, 48, 122, "（合成演示；表头结构参考公开归档目录/空白样表；非真实工程档案）", size=7, color=(0.45, 0.45, 0.45))

    y = catalog_strip(page, meta, 138)
    y += 6
    # two-column meta table for visual density
    pairs = [
        ("工程名称", meta.get("项目名称", "")),
        ("工程编号", meta.get("项目编号", "")),
        ("建设单位", meta.get("建设单位", "")),
        ("施工单位", meta.get("施工单位", "")),
        ("监理单位", meta.get("监理单位", "")),
        ("设计单位", meta.get("设计单位", "")),
        ("工程地点", meta.get("工程地址", "")),
        ("合同价款(元)", meta.get("合同金额（元）") or meta.get("合同金额", "")),
        ("开工日期", meta.get("开工日期", "")),
        ("竣工日期", meta.get("竣工日期", "")),
    ]
    x0, mid, x1 = 48, 300, 547
    for i in range(0, len(pairs), 2):
        left = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        h = 26
        _rect(page, fitz.Rect(x0, y, 130, y + h), 0.5)
        _rect(page, fitz.Rect(130, y, mid, y + h), 0.5)
        _box_text(page, fitz.Rect(x0 + 2, y + 6, 128, y + h - 4), left[0], size=8)
        _box_text(page, fitz.Rect(132, y + 6, mid - 2, y + h - 4), left[1], size=8)
        if right[0]:
            _rect(page, fitz.Rect(mid, y, mid + 90, y + h), 0.5)
            _rect(page, fitz.Rect(mid + 90, y, x1, y + h), 0.5)
            _box_text(page, fitz.Rect(mid + 2, y + 6, mid + 88, y + h - 4), right[0], size=8)
            _box_text(page, fitz.Rect(mid + 92, y + 6, x1 - 2, y + h - 4), right[1], size=8)
        y += h

    y += 12
    _text(page, 48, y, "正文", size=11)
    y += 14
    _hline(page, 48, 547, y, 0.5)
    y += 14
    for line in body_lines:
        while len(line) > 40:
            chunk, line = line[:40], line[40:]
            _text(page, 48, y, chunk, size=10)
            y += 15
            if y > 700:
                page = doc.new_page(width=595, height=842)
                _font(page)
                y = 60
        _text(page, 48, y, line, size=10)
        y += 15
        if y > 700:
            page = doc.new_page(width=595, height=842)
            _font(page)
            y = 60

    y = max(y + 20, 720)
    _rect(page, fitz.Rect(48, y, 280, y + 70), 0.5)
    _box_text(page, fitz.Rect(52, y + 8, 276, y + 66), "编制/填报单位（盖章）\n负责人：\n年  月  日", size=9)
    _rect(page, fitz.Rect(290, y, 547, y + 70), 0.5)
    _box_text(page, fitz.Rect(294, y + 8, 543, y + 66), "审核/签收单位（盖章）\n负责人：\n年  月  日", size=9)
    seal(page, 455, y - 10)
    if scan_style:
        _text(page, 48, 825, "【扫描件示意 PDF】", size=8, color=(0.4, 0.4, 0.4))
    save(doc, path)


def make_unreadable(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(page.rect, color=(0.86, 0.86, 0.86), fill=(0.86, 0.86, 0.86))
    for i in range(50):
        page.draw_line(
            fitz.Point(30 + i * 4, 60),
            fitz.Point(80 + i * 6, 780),
            color=(0.72, 0.72, 0.72),
            width=0.5,
        )
    # intentionally no text / fonts
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path, garbage=4, deflate=True)
    doc.close()
