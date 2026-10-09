# -*- coding: utf-8 -*-
"""Generate near-miss housing demo pack: same campus/road neighbor misfiles, date conflict, unreadables."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "demo-housing-near-miss"
CASE = ROOT / "cases" / CASE_ID
FILES = CASE / "files"

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
]

# Distinct from demo-housing-mixed (教学楼改扩建 / 018)，考点侧重近邻混淆 + 开工日期冲突 + 缺材料检测 + 不可读页
P = {
    "project_name": "云港新区示范中学实验楼加固改造工程",
    "project_code": "YG-XFZX-SY-2024-021",
    "owner": "云港市教育发展建设中心",
    "contractor": "江海建工集团有限公司",
    "supervisor": "远洲建设监理有限公司",
    "designer": "青城建筑设计研究院有限公司",
    "address": "云港市海州区学府路92号",
    "start_date": "2024-05-08",
    "finish_date": "2025-12-15",
    "contract_amount": "42800000",
    "contract_amount_cn": "肆仟贰佰捌拾万元整",
}

# 同校区另一单体（教学楼改扩建）——名称/编号近似，混入正常目录
NEAR_CAMPUS = {
    "项目名称": "云港新区示范中学教学楼改扩建工程",
    "项目编号": "YG-XFZX-JL-2024-018",
    "建设单位": "云港市教育发展建设中心",
    "施工单位": "江海建工集团有限公司",
    "监理单位": "远洲建设监理有限公司",
    "设计单位": "青城建筑设计研究院有限公司",
    "工程地址": "云港市海州区学府路88号",
    "开工日期": "2024-03-01",
    "竣工日期": "2025-11-20",
    "合同金额（元）": "86500000",
}

# 同学府路小学——路名与学段相近
NEAR_ROAD = {
    "项目名称": "云港新区学府路小学教学楼工程",
    "项目编号": "YG-XFL-XX-2023-012",
    "建设单位": "云港市教育发展建设中心",
    "施工单位": "海州区建安工程有限公司",
    "监理单位": "蓝桥工程监理有限公司",
    "设计单位": "青城建筑设计研究院有限公司",
    "工程地址": "云港市海州区学府路66号",
    "开工日期": "2023-02-15",
    "竣工日期": "2024-06-30",
    "合同金额（元）": "35600000",
}


def find_font() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("未找到可用中文字体（msyh/simhei/simsun）")


FONT_PATH = find_font()


def make_pdf(
    rel: str,
    title: str,
    body_lines: list[str],
    *,
    extra: dict | None = None,
    scan_style: bool = False,
    form_hint: str = "",
    project: dict | None = None,
) -> None:
    path = FILES / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    base = project or {
        "项目名称": P["project_name"],
        "项目编号": P["project_code"],
        "建设单位": P["owner"],
        "施工单位": P["contractor"],
        "监理单位": P["supervisor"],
        "设计单位": P["designer"],
        "工程地址": P["address"],
        "开工日期": P["start_date"],
        "竣工日期": P["finish_date"],
        "合同金额（元）": P["contract_amount"],
    }
    meta = dict(base)
    if extra:
        meta.update(extra)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    if scan_style:
        page.draw_rect(page.rect, color=(0.92, 0.92, 0.88), fill=(0.92, 0.92, 0.88))
    page.draw_rect(fitz.Rect(36, 36, 559, 806), color=(0.2, 0.2, 0.2), width=1.2)
    page.insert_font(fontname="cn", fontfile=str(FONT_PATH))

    y = 64
    page.insert_text((48, y), title, fontname="cn", fontsize=16)
    y += 28
    if form_hint:
        page.insert_text((48, y), form_hint, fontname="cn", fontsize=9, color=(0.35, 0.35, 0.35))
        y += 18
    page.insert_text(
        (48, y),
        "（合成演示数据; 近邻混淆用例; 非真实工程档案）",
        fontname="cn",
        fontsize=8,
        color=(0.45, 0.45, 0.45),
    )
    y += 22
    page.draw_line(fitz.Point(48, y), fitz.Point(547, y), color=(0.5, 0.5, 0.5), width=0.6)
    y += 16
    for key, value in meta.items():
        page.insert_text((48, y), f"{key}：{value}", fontname="cn", fontsize=11)
        y += 16
        if y > 720:
            page = doc.new_page(width=595, height=842)
            page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
            y = 64
    y += 8
    page.draw_line(fitz.Point(48, y), fitz.Point(547, y), color=(0.5, 0.5, 0.5), width=0.6)
    y += 18
    for line in body_lines:
        while len(line) > 42:
            chunk, line = line[:42], line[42:]
            page.insert_text((48, y), chunk, fontname="cn", fontsize=11)
            y += 16
            if y > 760:
                page = doc.new_page(width=595, height=842)
                page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
                y = 64
        page.insert_text((48, y), line, fontname="cn", fontsize=11)
        y += 16
        if y > 760:
            page = doc.new_page(width=595, height=842)
            page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
            y = 64
    y = max(y + 24, 680)
    page.insert_text((48, y), "签署栏（合成示意）", fontname="cn", fontsize=10)
    doc.subset_fonts()
    doc.save(path, garbage=4, deflate=True)
    doc.close()


def make_unreadable_pdf(rel: str) -> None:
    """Image-only page with no text layer — script should mark UNREADABLE."""
    path = FILES / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # noise rectangle only; no insert_text / no fonts → empty get_text()
    page.draw_rect(page.rect, color=(0.85, 0.85, 0.85), fill=(0.85, 0.85, 0.85))
    for i in range(40):
        page.draw_line(
            fitz.Point(40 + i * 3, 80),
            fitz.Point(100 + i * 5, 760),
            color=(0.7, 0.7, 0.7),
            width=0.4,
        )
    doc.save(path, garbage=4, deflate=True)
    doc.close()


def main() -> None:
    if CASE.exists():
        shutil.rmtree(CASE)
    FILES.mkdir(parents=True)

    make_pdf(
        "01-准备/A-01-建设工程规划许可证.pdf",
        "建设工程规划许可证",
        ["许可证编号：建规证字〔2023〕第156号", "建设规模：实验楼加固约6400平方米。"],
        extra={"文件编号": "建规证字〔2023〕第156号"},
    )
    make_pdf(
        "01-准备/A-02-建筑工程施工许可证.pdf",
        "建筑工程施工许可证",
        [
            "许可证编号：施许字〔2024〕第078号",
            "备注：证载开工日期与合同/manifest 不一致，用于本工程字段冲突测试。",
        ],
        extra={"文件编号": "施许字〔2024〕第078号", "开工日期": "2024-04-01"},
        scan_style=True,
    )
    make_pdf(
        "01-准备/A-03-建设工程施工合同.pdf",
        "建设工程施工合同",
        [
            f"发包人：{P['owner']}",
            f"承包人：{P['contractor']}",
            f"签约合同价：{P['contract_amount']} 元（{P['contract_amount_cn']}）。",
            f"合同工期：{P['start_date']} 至 {P['finish_date']}。",
        ],
        extra={"文件编号": "YG-XFZX-SY-HT-2024-001"},
    )
    make_pdf(
        "01-准备/A-04-建设工程委托监理合同.pdf",
        "建设工程委托监理合同",
        [f"委托人：{P['owner']}", f"监理人：{P['supervisor']}"],
        extra={"文件编号": "YG-XFZX-SY-JLHT-2024-001"},
    )

    make_pdf(
        "02-监理/B-01-监理规划.pdf",
        "监理规划",
        ["针对加固改造工程明确旁站与平行检验制度。"],
        extra={"文件编号": "JL-GH-SY-2024-01"},
    )
    make_pdf(
        "02-监理/B-03-工程质量评估报告.pdf",
        "工程质量评估报告",
        ["加固部位质量评估结论：同意竣工验收。"],
        extra={"文件编号": "JL-PG-SY-2025-12"},
    )

    make_pdf(
        "03-施工/C-01-施工组织设计.pdf",
        "施工组织设计",
        ["采用分段加固、夜间浇筑控制裂缝。"],
        extra={"文件编号": "SG-ZZ-SY-2024-01"},
    )
    make_pdf(
        "03-施工/C-02-检验批质量验收记录-混凝土加固-01.pdf",
        "检验批质量验收记录",
        ["部位：实验楼二层梁加固", "验收结论：合格。"],
        extra={
            "文件编号": "JYP-JG-2024-021",
            "分部（子分部）工程名称": "主体结构",
            "分项工程名称": "混凝土加固",
        },
    )
    make_pdf(
        "03-施工/C-03-分项工程质量验收记录-混凝土加固.pdf",
        "分项工程质量验收记录",
        ["分项工程名称：混凝土加固", "验收结论：合格。"],
        extra={"文件编号": "FX-JG-2024-01"},
    )
    make_pdf(
        "03-施工/C-04-分部工程质量验收记录-主体结构.pdf",
        "分部工程质量验收记录",
        ["分部工程名称：主体结构", "验收结论：合格。"],
        extra={"文件编号": "FB-ZT-SY-2025-01"},
    )

    # 故意缺 D-01：不生成材料复试正文；仅放无文本层扫描占位（文件名避开资料别名）
    make_unreadable_pdf("04-检测/扫描件-页面损坏.pdf")

    make_pdf(
        "05-验收/工程竣工预验收报告.pdf",
        "工程竣工预验收报告",
        [
            "预验收时间：2025-12-01。",
            "预验收意见：整改完成后组织正式验收。",
            "注意：本文为预验收，不能替代《工程竣工验收报告》。",
        ],
        extra={"文件编号": "YS-SY-2025-12-01"},
        scan_style=True,
    )
    make_pdf(
        "05-验收/E-02-施工单位工程竣工报告.pdf",
        "施工单位工程竣工报告",
        ["加固改造已按合同完成，申请竣工验收。"],
        extra={"文件编号": "SG-JG-SY-2025-01"},
    )
    make_pdf(
        "05-验收/E-03-设计单位工程质量检查报告.pdf",
        "设计单位工程质量检查报告",
        ["设计单位检查认为符合加固设计文件要求。"],
        extra={"文件编号": "SJ-JC-SY-2025-01"},
    )

    make_pdf(
        "06-竣工图/F-01-结构竣工图说明.pdf",
        "工程竣工图（结构）说明",
        ["结构加固竣工图已按变更更新。", "图纸编号：结竣-SY-01 至 结竣-SY-12。"],
        extra={"文件编号": "JG-TZ-SY-2025"},
        scan_style=True,
    )

    make_pdf(
        "07-专项/G-02-规划核实证明.pdf",
        "建设工程规划核实合格证",
        ["核实结论：符合规划许可要求（合成）。"],
        extra={"文件编号": "GHHS-SY-2025-021"},
    )

    # 近邻混淆：同校区教学楼资料混入准备目录（无「错传」路径）
    make_pdf(
        "01-准备/建设工程施工合同-教学楼单体.pdf",
        "建设工程施工合同",
        [
            "本文件属于同校区另一单体（教学楼改扩建），误归入实验楼加固资料包。",
            "请按项目名称/编号区分，不得计入本实验楼齐套。",
        ],
        project=NEAR_CAMPUS,
        extra={"文件编号": "YG-XFZX-HT-2024-001"},
        form_hint="近邻：同校区、同建设方、编号前缀相近",
    )
    # 近邻混淆：同学府路小学验收报告混入验收目录
    make_pdf(
        "05-验收/工程竣工验收报告-学府路小学.pdf",
        "工程竣工验收报告",
        [
            "云港新区学府路小学教学楼工程竣工验收报告。",
            "同学府路、同学段近似工程，不能计入本实验楼正式验收（E-01）。",
        ],
        project=NEAR_ROAD,
        extra={"文件编号": "XFL-XX-JGYS-2024-01"},
        form_hint="近邻：同学府路小学正式验收，文件名含竣工验收报告",
    )

    pdfs = sorted(p.relative_to(CASE).as_posix() for p in FILES.rglob("*.pdf"))
    manifest = {
        "project_id": CASE_ID,
        "project_type": "房屋建筑工程",
        "rules_profile": "housing-construction",
        "project_name": P["project_name"],
        "project_code": P["project_code"],
        "owner": P["owner"],
        "contractor": P["contractor"],
        "supervisor": P["supervisor"],
        "designer": P["designer"],
        "address": P["address"],
        "start_date": P["start_date"],
        "finish_date": P["finish_date"],
        "contract_amount": P["contract_amount"],
        "data_note": "近邻混淆演示包：同校区/同学府路他项混入正常目录；缺 D-01/E-01/G-01；本工程开工日期冲突；含不可读扫描页。",
        "file_count": len(pdfs),
        "file_format": "pdf",
        "focus": ["near_miss_misfile", "start_date_conflict", "missing_material_test", "unreadable_scan"],
    }
    (CASE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ground_truth = {
        "project_id": CASE_ID,
        "rules_profile": "housing-construction",
        "scoring_notes": {
            "contrast_with": "demo-housing-mixed",
            "difference": "本包侧重近邻工程名/编号混淆，而非市政管廊远域错传；另测开工日期冲突、缺材料检测、不可读扫描",
            "misfiled_excluded_from_presence": "他项文件不得计入本项目齐套 provided；小学正式验收不得计为本项目 E-01",
            "field_conflicts_in_project_only": "仅统计本工程真冲突；他项级联不得计为多条 FIELD",
            "expected_field_conflict_count": 1,
            "optional_codes": ["B-02", "G-02"],
            "no_duplicate_file_no_test": "本包不测同编号重复（见 demo-housing-mixed）",
        },
        "expected_highlights": {
            "missing_required": [
                {
                    "code": "D-01",
                    "name": "材料进场报审及复试报告",
                    "reason": "包内无可用材料复试正文；仅有不可读扫描占位",
                },
                {
                    "code": "E-01",
                    "name": "工程竣工验收报告",
                    "reason": "仅有预验收；小学正式验收属他项，不能替代",
                    "similar_files": ["files/05-验收/工程竣工预验收报告.pdf"],
                },
                {
                    "code": "G-01",
                    "name": "消防验收意见或备案凭证",
                    "reason": "包内无消防验收/备案类文件",
                },
            ],
            "field_conflicts": [
                {
                    "field": "开工日期",
                    "canonical": P["start_date"],
                    "conflict_value": "2024-04-01",
                    "source": "files/01-准备/A-02-建筑工程施工许可证.pdf",
                }
            ],
            "suspect_misfiled": [
                "files/01-准备/建设工程施工合同-教学楼单体.pdf",
                "files/05-验收/工程竣工验收报告-学府路小学.pdf",
            ],
            "unreadable": [
                {
                    "path": "files/04-检测/扫描件-页面损坏.pdf",
                    "status": "needs_human_review",
                    "reason": "无文本层/无法抽取正文",
                }
            ],
            "should_be_provided_examples": [
                "A-01",
                "A-02",
                "A-03",
                "A-04",
                "B-01",
                "B-03",
                "C-01",
                "C-02",
                "C-03",
                "C-04",
                "E-02",
                "E-03",
                "F-01",
                "G-02",
            ],
        },
        "agh_success_criteria": [
            "加载 housing-construction 规则",
            "写出 _work 产物",
            "D-01 / E-01 / G-01 判 missing",
            "E-01 不被学府路小学正式验收报告假阳性 provided",
            "标出同校区教学楼合同与学府路小学验收为错传（靠项目名称，不靠错传目录）",
            "标出本工程开工日期冲突（恰好 1 条 FIELD）",
            "标出不可读扫描为 needs_human_review",
            "可选：文书 prepare→正文→build",
        ],
    }
    (CASE / "ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    prompt = f"""请使用 engineering-archive-audit 对 cases/{CASE_ID} 做竣工资料齐套与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

本包重点：近邻工程混淆（同校区教学楼、同学府路小学）、缺材料检测、预验收不可替代正式验收、本工程开工日期冲突、不可读扫描页。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。
文书勿把近邻他项写成「本工程已提供正式竣工验收报告」；不可读页保留读取不足，不判为已齐套。
"""
    (CASE / "TEST_PROMPT.txt").write_text(prompt.strip() + "\n", encoding="utf-8")

    print(f"Generated {CASE}")
    print(f"pdf_count={len(pdfs)} font={FONT_PATH}")
    for rel in pdfs:
        print(" ", rel)


if __name__ == "__main__":
    main()
