# -*- coding: utf-8 -*-
"""Heterogeneous PDF builders modeled on public blank forms / standards.

Layout references (public blank forms / standards, not real project archives):
- GB50300-2013 附录 E/F/G/H（检验批、分项、分部、观感）
- reference/public-pdfs/construction-permit-sample-sd.pdf（施工许可证申请表/证样）
- reference/public-pdfs/construction-contract-gf2017.pdf（GF-2017-0201 合同示范文本）
- reference/public-pdfs/unit-completion-acceptance-report.pdf（单位竣工验收报告 GD-E1）
- reference/public-pdfs/acceptance-check-forms-unified.pdf / gb50300-2013-acceptance-standard.pdf
- reference/public-pdfs/zj-unified-forms-2025.pdf（浙江统一用表目录结构）

Synthetic filled values only. Field extractors expect 「标签：值」 lines
(项目名称 / 工程名称 alias 等)；各文种版式刻意拉开视觉差异。
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


def seal(page, x=430, y=700, label="公章", color=(0.75, 0.12, 0.12)):
    page.draw_oval(fitz.Rect(x, y, x + 90, y + 90), color=color, width=1.8)
    # 短标签居中大致对齐椭圆
    ox = x + max(8, (90 - len(label) * 10) // 2)
    _text(page, ox, y + 42, label, size=10, color=color)


def save(doc, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(path, garbage=4, deflate=True)
    doc.close()


def _new_page(doc, scan_style: bool = False):
    page = doc.new_page(width=595, height=842)
    _font(page)
    if scan_style:
        page.draw_rect(page.rect, color=(0.93, 0.93, 0.9), fill=(0.93, 0.93, 0.9))
    return page


def field_lines(meta: dict) -> list[str]:
    """Canonical extractable lines for audit_prepare."""
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
    return [f"{k}：{v}" for k, v in keys if v]


def write_fields(page, meta: dict, x: float = 48, y: float = 780, size: float = 7) -> None:
    """Compact extractable strip (footer / side note), not a visual template."""
    for line in field_lines(meta):
        _text(page, x, y, line[:90], size=size, color=(0.2, 0.2, 0.2))
        y += 9
        if y > 830:
            break


def catalog_strip(page, meta: dict, y0: float = 52) -> float:
    """Compact project field strip for GB50300 builders / extractors."""
    y = y0
    for line in field_lines(meta):
        _text(page, 48, y, line[:78], size=8, color=(0.15, 0.15, 0.15))
        y += 11
    _hline(page, 42, 553, y + 2, 0.4)
    return y + 10


# ---------------------------------------------------------------------------
# GB50300 appendix-style (already distinct)
# ---------------------------------------------------------------------------


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
    page = _new_page(doc, scan_style)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 150, 48, f"{batch_name}检验批质量验收记录", size=13)
    _text(page, 420, 48, f"编号：{file_no}", size=9)
    y = catalog_strip(page, {**meta, "文件编号": file_no, "工程名称": meta.get("项目名称", "")}, 64)

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
            ("项目负责人", 100, "王建华"),
            ("施工班组长", 100, "李志强"),
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
        [("验收依据", 370, basis_ys)],
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
    seal(page, 470, 760, "质检章")
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
    page = _new_page(doc)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 180, 50, f"{title}", size=13)
    _text(page, 400, 50, f"编号：{file_no}", size=9)
    y = catalog_strip(page, {**meta, "文件编号": file_no}, 66)

    rows = [
        ("单位(子单位)工程名称", meta.get("项目名称", "")),
        ("分部(子分部)工程名称", division),
        ("分项工程名称", subitem),
        ("检验批数量", batch_count),
        ("施工单位", meta.get("施工单位", "")),
        ("项目负责人", "王建华"),
        ("项目技术负责人", "赵明远"),
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
    page = _new_page(doc)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 170, 50, title, size=13)
    _text(page, 400, 50, f"编号：{file_no}", size=9)
    y = catalog_strip(page, {**meta, "文件编号": file_no}, 66)
    rows = [
        ("单位(子单位)工程名称", meta.get("项目名称", "")),
        ("分部(子分部)工程名称", division),
        ("分项工程数量", subitem_count),
        ("施工单位", meta.get("施工单位", "")),
        ("项目负责人", "王建华"),
        ("项目技术负责人", "赵明远"),
        ("监理单位", meta.get("监理单位", "")),
        ("总监理工程师", "周海涛"),
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
    page = _new_page(doc)
    _rect(page, fitz.Rect(36, 28, 559, 814), 1.2)
    _text(page, 180, 50, "单位工程观感质量检查记录", size=13)
    _text(page, 420, 50, f"编号：{file_no}", size=9)
    y = catalog_strip(page, {**meta, "文件编号": file_no}, 66)
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


# ---------------------------------------------------------------------------
# Document-kind specific layouts (visual diversity)
# ---------------------------------------------------------------------------


def make_planning_permit(
    path: Path,
    *,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
) -> None:
    """规划许可证：竖向证照风格（红字标题 + 证号居中 + 正文条款）。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    # outer red-ish double frame
    page.draw_rect(fitz.Rect(40, 36, 555, 806), color=(0.55, 0.08, 0.08), width=2.2)
    page.draw_rect(fitz.Rect(48, 44, 547, 798), color=(0.55, 0.08, 0.08), width=0.8)

    _text(page, 145, 100, "建设工程规划许可证", size=20, color=(0.55, 0.08, 0.08))
    _text(page, 160, 150, f"证号：{meta.get('文件编号', '')}", size=12)

    y = 200
    rows = [
        ("建设单位", meta.get("建设单位", "")),
        ("建设项目名称", meta.get("项目名称", "")),
        ("建设位置", meta.get("工程地址", "")),
        ("建设规模", "地上建筑面积约18600平方米"),
        ("附图及附件", "与本证同时使用"),
    ]
    for label, val in rows:
        _text(page, 80, y, f"{label}：", size=11)
        _box_text(page, fitz.Rect(180, y - 12, 500, y + 28), val, size=11)
        _hline(page, 80, 500, y + 18, 0.4)
        y += 42

    y += 10
    for line in body_lines:
        _text(page, 80, y, line[:42], size=10)
        y += 18

    _text(page, 80, 620, "发证机关：云港市自然资源和规划局", size=10)
    _text(page, 80, 640, "发证日期：2023年12月18日", size=10)
    seal(page, 400, 600, "规划专用章", color=(0.7, 0.1, 0.1))
    write_fields(page, meta, 55, 720)
    save(doc, path)


def make_construction_permit(
    path: Path,
    *,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
    scale_note: str = "地上约18600㎡",
) -> None:
    """施工许可证：仿住建部证照密表（非双框报告）。参考 construction-permit-sample-sd.pdf。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    _text(page, 170, 48, "建筑工程施工许可证", size=16)
    _text(page, 48, 78, f"编号：{meta.get('文件编号', '')}", size=11)

    y = 100
    x0, x1 = 48, 547
    pairs = [
        ("建设单位", meta.get("建设单位", "")),
        ("工程名称", meta.get("项目名称", "")),
        ("建设地址", meta.get("工程地址", "")),
        ("建设规模", scale_note),
        ("合同价格（元）", meta.get("合同金额（元）") or meta.get("合同金额", "")),
        ("勘察单位", "云港地质勘察院"),
        ("设计单位", meta.get("设计单位", "")),
        ("施工单位", meta.get("施工单位", "")),
        ("监理单位", meta.get("监理单位", "")),
        ("合同工期", f"{meta.get('开工日期', '')} 至 {meta.get('竣工日期', '')}"),
        ("施工单位项目负责人", "王建华"),
        ("总监理工程师", "周海涛"),
    ]
    for label, val in pairs:
        _rect(page, fitz.Rect(x0, y, 170, y + 28), 0.6)
        _rect(page, fitz.Rect(170, y, x1, y + 28), 0.6)
        _box_text(page, fitz.Rect(x0 + 4, y + 6, 166, y + 24), label, size=9)
        _box_text(page, fitz.Rect(174, y + 6, x1 - 4, y + 24), val, size=9)
        y += 28

    y += 12
    _rect(page, fitz.Rect(x0, y, x1, y + 90), 0.6)
    body = "根据《建筑法》第八条规定，经审查，本建筑工程符合施工条件，准予施工。\n"
    body += "\n".join(body_lines)
    _box_text(page, fitz.Rect(x0 + 6, y + 8, x1 - 6, y + 84), body, size=9)

    y += 105
    _text(page, x0, y, "发证机关：云港市住房和城乡建设局", size=9)
    _text(page, x0, y + 18, "备注：变更事项另行记载。", size=8, color=(0.35, 0.35, 0.35))
    seal(page, 430, y - 10, "许可专用章")
    write_fields(page, {**meta, "项目名称": meta.get("项目名称", "")}, 48, 760)
    save(doc, path)


def make_construction_contract(
    path: Path,
    *,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
    amount_cn: str = "",
) -> None:
    """施工合同：GF-2017 示范文本封面 + 协议书首页。参考 construction-contract-gf2017.pdf。"""
    doc = fitz.open()
    # Cover
    page = _new_page(doc, scan_style)
    _text(page, 210, 100, "GF—2017—0201", size=12, color=(0.3, 0.3, 0.3))
    _text(page, 160, 220, "建设工程施工合同", size=22)
    _text(page, 220, 260, "（示范文本）", size=12)
    _text(page, 100, 360, f"工程名称：{meta.get('项目名称', '')}", size=11)
    _text(page, 100, 390, f"工程地点：{meta.get('工程地址', '')}", size=11)
    _text(page, 100, 420, f"发包人：{meta.get('建设单位', '')}", size=11)
    _text(page, 100, 450, f"承包人：{meta.get('施工单位', '')}", size=11)
    _text(page, 100, 500, f"合同编号：{meta.get('文件编号', '')}", size=11)
    _text(page, 160, 620, "住房城乡建设部", size=11)
    _text(page, 160, 640, "国家工商行政管理总局", size=11)
    _text(page, 220, 670, "制定", size=9, color=(0.4, 0.4, 0.4))
    write_fields(page, meta, 48, 720)

    # Protocol page
    page = _new_page(doc, scan_style)
    _text(page, 200, 50, "第一部分  合同协议书", size=14)
    _hline(page, 48, 547, 62, 0.8)
    y = 90
    lines = [
        f"发包人（全称）：{meta.get('建设单位', '')}",
        f"承包人（全称）：{meta.get('施工单位', '')}",
        "",
        f"一、工程概况",
        f"工程名称：{meta.get('项目名称', '')}",
        f"工程地点：{meta.get('工程地址', '')}",
        f"项目编号：{meta.get('项目编号', '')}",
        "",
        f"二、合同工期",
        f"开工日期：{meta.get('开工日期', '')}",
        f"竣工日期：{meta.get('竣工日期', '')}",
        "",
        f"三、质量标准：合格",
        f"四、签约合同价（人民币）：{meta.get('合同金额（元）') or meta.get('合同金额', '')} 元"
        + (f"（{amount_cn}）" if amount_cn else ""),
        f"合同金额（元）：{meta.get('合同金额（元）') or meta.get('合同金额', '')}",
        "",
        "五、项目经理：王建华",
        f"监理单位：{meta.get('监理单位', '')}",
        f"设计单位：{meta.get('设计单位', '')}",
    ]
    for line in list(lines) + list(body_lines):
        _text(page, 56, y, line[:48], size=10)
        y += 18
        if y > 760:
            break
    _text(page, 56, 780, "发包人（公章）                    承包人（公章）", size=9)
    seal(page, 450, 700, "合同专用章")
    save(doc, path)


def make_supervision_contract(
    path: Path,
    *,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
) -> None:
    """监理合同：横条题头 + 甲乙方对照表（与施工合同封面明显不同）。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    page.draw_rect(fitz.Rect(0, 0, 595, 70), color=(0.15, 0.25, 0.45), fill=(0.15, 0.25, 0.45))
    _text(page, 160, 42, "建设工程委托监理合同", size=16, color=(1, 1, 1))
    _text(page, 48, 90, f"合同编号：{meta.get('文件编号', '')}", size=10)

    y = 120
    _rect(page, fitz.Rect(48, y, 290, y + 160), 1.0)
    _rect(page, fitz.Rect(305, y, 547, y + 160), 1.0)
    _box_text(
        page,
        fitz.Rect(56, y + 10, 282, y + 150),
        f"委托人（甲方）\n\n单位名称：{meta.get('建设单位', '')}\n\n项目名称：{meta.get('项目名称', '')}\n\n工程地址：{meta.get('工程地址', '')}",
        size=10,
    )
    _box_text(
        page,
        fitz.Rect(313, y + 10, 539, y + 150),
        f"监理人（乙方）\n\n单位名称：{meta.get('监理单位', '')}\n\n总监理工程师：周海涛\n\n服务期限：与施工工期一致",
        size=10,
    )
    y += 180
    _text(page, 48, y, "主要约定", size=12)
    y += 20
    defaults = [
        "监理范围：本工程施工阶段质量、进度、投资与安全监理。",
        f"开工日期：{meta.get('开工日期', '')}",
        f"竣工日期：{meta.get('竣工日期', '')}",
        f"设计单位：{meta.get('设计单位', '')}",
        f"施工单位：{meta.get('施工单位', '')}",
        f"项目编号：{meta.get('项目编号', '')}",
        (
            f"合同金额（元）：本监理酬金另计（施工合同价 "
            f"{meta.get('合同金额（元）') or meta.get('合同金额', '')} 元）。"
        ),
    ]
    for line in defaults + list(body_lines):
        _text(page, 48, y, line[:52], size=10)
        y += 18
    _text(page, 48, 720, "委托人（盖章）                 监理人（盖章）", size=10)
    seal(page, 430, 680, "监理专用章", color=(0.2, 0.3, 0.55))
    write_fields(page, meta, 48, 750)
    save(doc, path)


def make_tech_document(
    path: Path,
    *,
    title: str,
    meta: dict,
    chapters: list[tuple[str, list[str]]],
    scan_style: bool = False,
    org_header: str = "",
) -> None:
    """技术文件：章条结构（监理规划 / 细则 / 施组）。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    if org_header:
        _text(page, 48, 40, org_header, size=9, color=(0.25, 0.25, 0.25))
        _hline(page, 48, 547, 48, 0.5)
    _text(page, 48, 70, title, size=16)
    _text(page, 48, 92, f"文件编号：{meta.get('文件编号', '')}", size=9)
    _text(page, 300, 92, f"项目名称：{meta.get('项目名称', '')}", size=9)
    write_fields(page, meta, 48, 118, size=7)

    y = 230
    for ch_title, paras in chapters:
        if y > 720:
            page = _new_page(doc, scan_style)
            y = 50
        _text(page, 48, y, ch_title, size=12)
        y += 20
        for para in paras:
            while len(para) > 44:
                _text(page, 56, y, para[:44], size=10)
                para = para[44:]
                y += 16
                if y > 780:
                    page = _new_page(doc, scan_style)
                    y = 50
            _text(page, 56, y, para, size=10)
            y += 18
        y += 10
    seal(page, 430, 720, "文件专用章", color=(0.25, 0.35, 0.45))
    save(doc, path)


def make_quality_assessment(
    path: Path,
    *,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
) -> None:
    """工程质量评估报告：单位抬头信纸风格。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    org = meta.get("监理单位", "监理单位")
    _text(page, 150, 50, org, size=14)
    _hline(page, 80, 515, 62, 1.2)
    _text(page, 200, 90, "工程质量评估报告", size=16)
    _text(page, 420, 110, f"编号：{meta.get('文件编号', '')}", size=9)

    y = 140
    for line in field_lines(meta):
        _text(page, 70, y, line[:70], size=9)
        y += 14
    y += 10
    _hline(page, 70, 525, y, 0.5)
    y += 20
    _text(page, 70, y, "评估意见", size=12)
    y += 22
    defaults = [
        "根据有关法律法规、工程建设强制性标准及设计文件，对本工程质量进行评估。",
    ]
    for line in defaults + list(body_lines):
        while len(line) > 42:
            _text(page, 70, y, line[:42], size=10)
            line = line[42:]
            y += 16
        _text(page, 70, y, line, size=10)
        y += 18
    y = max(y + 30, 620)
    _text(page, 70, y, "总监理工程师：周海涛", size=10)
    _text(page, 70, y + 20, f"监理单位：{org}（盖章）", size=10)
    _text(page, 70, y + 40, "日期：2025年11月18日", size=10)
    seal(page, 420, y - 20, "评估专用章", color=(0.55, 0.15, 0.15))
    save(doc, path)


def make_material_test_report(
    path: Path,
    *,
    meta: dict,
    report_title: str,
    sample_rows: list[tuple[str, str]],
    conclusion: str,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
    lab_name: str = "云港市建设工程质量检测中心",
) -> None:
    """检测/复试报告：实验室抬头 + 结果表。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    _text(page, 120, 42, lab_name, size=12)
    _text(page, 200, 68, report_title, size=15)
    _text(page, 48, 90, f"报告编号：{meta.get('文件编号', '')}", size=9)
    _text(page, 320, 90, "CMA", size=9, color=(0.5, 0.2, 0.2))
    _hline(page, 48, 547, 100, 1.0)

    y = 120
    for line in field_lines(meta):
        _text(page, 48, y, line[:80], size=8)
        y += 11
    y += 8

    x0, x1 = 48, 547
    _rect(page, fitz.Rect(x0, y, 180, y + 24), 0.5)
    _rect(page, fitz.Rect(180, y, x1, y + 24), 0.5)
    _box_text(page, fitz.Rect(x0 + 2, y + 5, 178, y + 20), "检测项目 / 参数", size=9, align=1)
    _box_text(page, fitz.Rect(182, y + 5, x1 - 2, y + 20), "结果 / 说明", size=9, align=1)
    y += 24
    for k, v in sample_rows:
        _rect(page, fitz.Rect(x0, y, 180, y + 26), 0.4)
        _rect(page, fitz.Rect(180, y, x1, y + 26), 0.4)
        _box_text(page, fitz.Rect(x0 + 3, y + 5, 177, y + 22), k, size=9)
        _box_text(page, fitz.Rect(183, y + 5, x1 - 3, y + 22), v, size=9)
        y += 26

    y += 12
    for line in body_lines:
        _text(page, 48, y, line[:50], size=10)
        y += 16
    y += 8
    _rect(page, fitz.Rect(x0, y, x1, y + 50), 0.6)
    _box_text(page, fitz.Rect(x0 + 6, y + 10, x1 - 6, y + 44), f"检测结论：{conclusion}", size=11)
    _text(page, 48, y + 70, "主检：钱伟    审核：孙丽    批准：李建国", size=9)
    seal(page, 430, y + 40, "检测专用章", color=(0.1, 0.35, 0.55))
    save(doc, path)


def make_completion_pack(
    path: Path,
    *,
    title: str,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
    form_code: str = "GD-E1-914",
    conclusion: str = "",
    five_party: bool = True,
    report_date: str = "2025年11月20日",
) -> None:
    """竣工类：封面 + 工程概况表（仿单位竣工验收报告）。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    _text(page, 48, 60, form_code, size=9, color=(0.35, 0.35, 0.35))
    _text(page, 150, 200, title, size=18)
    _text(page, 80, 280, f"工程名称：{meta.get('项目名称', '')}", size=12)
    _text(page, 80, 310, f"验收/报告日期：{report_date}", size=11)
    _text(page, 80, 340, f"建设单位：{meta.get('建设单位', '')}", size=11)
    write_fields(page, meta, 48, 720)

    # Profile page
    page = _new_page(doc, scan_style)
    _text(page, 48, 48, "一、工程概况", size=13)
    y = 70
    rows = [
        ("工程名称", meta.get("项目名称", "")),
        ("工程地点", meta.get("工程地址", "")),
        ("项目编号", meta.get("项目编号", "")),
        ("文件编号", meta.get("文件编号", "")),
        ("建设单位", meta.get("建设单位", "")),
        ("施工单位", meta.get("施工单位", "")),
        ("监理单位", meta.get("监理单位", "")),
        ("设计单位", meta.get("设计单位", "")),
        ("开工日期", meta.get("开工日期", "")),
        ("竣工日期", meta.get("竣工日期", "")),
        ("合同金额（元）", meta.get("合同金额（元）") or meta.get("合同金额", "")),
    ]
    x0, x1 = 48, 547
    for label, val in rows:
        _rect(page, fitz.Rect(x0, y, 160, y + 24), 0.5)
        _rect(page, fitz.Rect(160, y, x1, y + 24), 0.5)
        _box_text(page, fitz.Rect(x0 + 4, y + 5, 156, y + 20), label, size=9)
        _box_text(page, fitz.Rect(164, y + 5, x1 - 4, y + 20), val, size=9)
        y += 24

    y += 16
    _text(page, 48, y, "二、说明与结论", size=13)
    y += 22
    for line in body_lines:
        while len(line) > 44:
            _text(page, 56, y, line[:44], size=10)
            line = line[44:]
            y += 16
        _text(page, 56, y, line, size=10)
        y += 18
    if conclusion:
        y += 8
        _rect(page, fitz.Rect(48, y, 547, y + 40), 0.6)
        _box_text(page, fitz.Rect(54, y + 8, 541, y + 34), conclusion, size=11)

    if five_party:
        y = max(y + 60, 620)
        for i, lab in enumerate(["建设单位", "勘察单位", "设计单位", "监理单位", "施工单位"]):
            xx = 48 + i * 100
            _rect(page, fitz.Rect(xx, y, xx + 96, y + 70), 0.5)
            _box_text(page, fitz.Rect(xx + 2, y + 8, xx + 94, y + 64), f"{lab}\n同意\n（公章）", size=8, align=1)
    save(doc, path)


def make_asbuilt_drawing_note(
    path: Path,
    *,
    meta: dict,
    specialty: str,
    drawing_nos: str,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
) -> None:
    """竣工图说明：图纸目录表风格。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    _text(page, 48, 48, f"工程竣工图（{specialty}）说明及目录", size=14)
    _text(page, 48, 70, f"图册编号：{meta.get('文件编号', '')}", size=9)

    y = 95
    for line in field_lines(meta):
        _text(page, 48, y, line[:80], size=8)
        y += 11
    y += 10

    # title block like drawing sheet
    _rect(page, fitz.Rect(48, y, 547, y + 60), 1.0)
    _box_text(
        page,
        fitz.Rect(56, y + 8, 539, y + 52),
        f"项目名称：{meta.get('项目名称', '')}\n专业：{specialty}    图纸编号范围：{drawing_nos}\n设计单位：{meta.get('设计单位', '')}",
        size=10,
    )
    y += 80

    cols = [("序号", 40), ("图号", 100), ("图名", 220), ("备注", 139)]
    x = 48
    for name, w in cols:
        _rect(page, fitz.Rect(x, y, x + w, y + 22), 0.5)
        _box_text(page, fitz.Rect(x, y + 4, x + w, y + 18), name, size=9, align=1)
        x += w
    y += 22
    sample = [
        ("1", drawing_nos.split("至")[0].strip() if "至" in drawing_nos else "竣-01", f"{specialty}平面图", "已改"),
        ("2", "—", f"{specialty}变更汇总", "云线标注"),
        ("3", "—", "设计变更单索引", "共3份" if specialty == "建筑" else "已更新"),
    ]
    for row in sample:
        x = 48
        for val, (_, w) in zip(row, cols):
            _rect(page, fitz.Rect(x, y, x + w, y + 22), 0.4)
            _box_text(page, fitz.Rect(x + 2, y + 4, x + w - 2, y + 18), val, size=8)
            x += w
        y += 22

    y += 16
    for line in body_lines:
        _text(page, 48, y, line[:50], size=10)
        y += 16
    seal(page, 430, 700, "竣工图章", color=(0.2, 0.4, 0.3))
    save(doc, path)


def make_planning_verify_cert(
    path: Path,
    *,
    meta: dict,
    body_lines: Iterable[str] = (),
    scan_style: bool = False,
) -> None:
    """规划核实合格证：横版证头 + 结论栏（区别于规划许可证竖向证照）。"""
    doc = fitz.open()
    page = _new_page(doc, scan_style)
    page.draw_rect(fitz.Rect(36, 40, 559, 120), color=(0.1, 0.35, 0.25), fill=(0.1, 0.35, 0.25))
    _text(page, 150, 75, "建设工程规划核实合格证", size=16, color=(1, 1, 1))

    _text(page, 48, 150, f"证号：{meta.get('文件编号', '')}", size=12)
    y = 180
    for label, key in [
        ("项目名称", "项目名称"),
        ("建设单位", "建设单位"),
        ("工程地址", "工程地址"),
        ("项目编号", "项目编号"),
    ]:
        _text(page, 60, y, f"{label}：{meta.get(key, '')}", size=11)
        y += 28

    _rect(page, fitz.Rect(48, y + 10, 547, y + 120), 1.0)
    text = "核实结论：\n" + "\n".join(
        body_lines or ["经现场核实，本工程的平面位置、建筑规模符合规划许可要求，准予规划核实合格。"]
    )
    _box_text(page, fitz.Rect(60, y + 20, 535, y + 110), text, size=11)

    _text(page, 60, 620, "核实机关：云港市自然资源和规划局", size=10)
    seal(page, 420, 580, "核实专用章", color=(0.1, 0.4, 0.3))
    write_fields(page, meta, 48, 700)
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
    """Fallback generic report (prefer kind-specific builders)."""
    make_completion_pack(
        path,
        title=title,
        meta=meta,
        body_lines=list(body_lines) + ([form_hint] if form_hint else []),
        scan_style=scan_style,
        form_code=f"资料类别：{doc_kind}",
        five_party=False,
    )


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
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path, garbage=4, deflate=True)
    doc.close()
