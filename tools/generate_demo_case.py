# -*- coding: utf-8 -*-
"""Generate synthetic housing-construction demo PDF pack for AGH Skill testing."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "demo-housing-mixed"
CASE = ROOT / "cases" / CASE_ID
FILES = CASE / "files"

# Prefer smaller single-face TTF; full CJK fonts are 10–20MB and must be subset.
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
]

P = {
    "project_name": "云港新区示范中学教学楼改扩建工程",
    "project_code": "YG-XFZX-JL-2024-018",
    "owner": "云港市教育发展建设中心",
    "contractor": "江海建工集团有限公司",
    "supervisor": "远洲建设监理有限公司",
    "designer": "青城建筑设计研究院有限公司",
    "address": "云港市海州区学府路88号",
    "start_date": "2024-03-01",
    "finish_date": "2025-11-20",
    "contract_amount": "86500000",
    "contract_amount_cn": "捌仟陆佰伍拾万元整",
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
) -> None:
    path = FILES / rel
    path.parent.mkdir(parents=True, exist_ok=True)

    meta = {
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
    if extra:
        meta.update(extra)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    if scan_style:
        page.draw_rect(page.rect, color=(0.92, 0.92, 0.88), fill=(0.92, 0.92, 0.88))
    page.draw_rect(fitz.Rect(36, 36, 559, 806), color=(0.2, 0.2, 0.2), width=1.2)

    y = 64
    page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
    page.insert_text((48, y), title, fontname="cn", fontsize=16, color=(0, 0, 0))
    y += 28
    if form_hint:
        page.insert_text(
            (48, y),
            form_hint,
            fontname="cn",
            fontsize=9,
            color=(0.35, 0.35, 0.35),
        )
        y += 18
    page.insert_text(
        (48, y),
        "（合成演示数据; 表头结构参考公开归档目录与验收空白表; 非真实工程档案）",
        fontname="cn",
        fontsize=8,
        color=(0.45, 0.45, 0.45),
    )
    y += 22
    page.draw_line(fitz.Point(48, y), fitz.Point(547, y), color=(0.5, 0.5, 0.5), width=0.6)
    y += 16

    for key, value in meta.items():
        page.insert_text((48, y), f"{key}：{value}", fontname="cn", fontsize=11, color=(0, 0, 0))
        y += 16
        if y > 720:
            page = doc.new_page(width=595, height=842)
            page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
            y = 64

    y += 8
    page.draw_line(fitz.Point(48, y), fitz.Point(547, y), color=(0.5, 0.5, 0.5), width=0.6)
    y += 18

    for line in body_lines:
        # simple wrap
        while len(line) > 42:
            chunk, line = line[:42], line[42:]
            page.insert_text((48, y), chunk, fontname="cn", fontsize=11, color=(0, 0, 0))
            y += 16
            if y > 760:
                page = doc.new_page(width=595, height=842)
                page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
                y = 64
        page.insert_text((48, y), line, fontname="cn", fontsize=11, color=(0, 0, 0))
        y += 16
        if y > 760:
            page = doc.new_page(width=595, height=842)
            page.insert_font(fontname="cn", fontfile=str(FONT_PATH))
            y = 64

    # signature / seal area
    y = max(y + 24, 680)
    page.insert_text((48, y), "签署栏（合成示意）：建设单位 / 施工单位 / 监理单位", fontname="cn", fontsize=10)
    y += 20
    page.draw_oval(fitz.Rect(420, y - 10, 520, y + 90), color=(0.7, 0.15, 0.15), width=2)
    page.insert_text((445, y + 40), "示意章", fontname="cn", fontsize=11, color=(0.7, 0.15, 0.15))
    if scan_style:
        page.insert_text((48, 790), "【扫描件示意 PDF】", fontname="cn", fontsize=9, color=(0.4, 0.4, 0.4))

    # Subset embedded CJK fonts (otherwise each PDF is ~10–20MB of unused glyphs).
    doc.subset_fonts()
    doc.save(path, garbage=4, deflate=True)
    doc.close()


def main() -> None:
    if CASE.exists():
        shutil.rmtree(CASE)
    FILES.mkdir(parents=True)

    # 工程准备
    make_pdf(
        "01-准备/A-01-建设工程规划许可证.pdf",
        "建设工程规划许可证",
        ["许可证编号：建规证字〔2023〕第118号", "建设规模：地上建筑面积约18600平方米。", "签发机关：云港市自然资源和规划局（合成）。"],
        extra={"文件编号": "建规证字〔2023〕第118号"},
        form_hint="版式参考：地方规划许可证明文件常见栏目",
    )
    make_pdf(
        "01-准备/A-02-建筑工程施工许可证.pdf",
        "建筑工程施工许可证",
        ["许可证编号：施许字〔2024〕第045号", "合同工期：2024-03-01 至 2025-11-20。"],
        extra={"文件编号": "施许字〔2024〕第045号"},
        form_hint="版式参考：施工许可证明文件常见栏目",
        scan_style=True,
    )
    make_pdf(
        "01-准备/A-03-建设工程施工合同.pdf",
        "建设工程施工合同",
        [
            f"发包人（建设单位）：{P['owner']}",
            f"承包人（施工单位）：{P['contractor']}",
            f"签约合同价（人民币）：{P['contract_amount']} 元（{P['contract_amount_cn']}）。",
            "工程质量标准：合格。",
        ],
        extra={"文件编号": "YG-XFZX-HT-2024-001"},
        form_hint="版式参考：施工合同首页要素（合成填写）",
    )
    make_pdf(
        "01-准备/A-04-建设工程委托监理合同.pdf",
        "建设工程委托监理合同",
        [f"委托人：{P['owner']}", f"监理人：{P['supervisor']}", "监理服务期限：与施工工期一致。"],
        extra={"文件编号": "YG-XFZX-JLHT-2024-001"},
    )

    # 监理
    make_pdf(
        "02-监理/B-01-监理规划.pdf",
        "监理规划",
        ["本规划明确旁站、巡视、平行检验等监理工作制度。", "总监理工程师：周某某（合成署名）。"],
        extra={"文件编号": "JL-GH-2024-01"},
    )
    make_pdf(
        "02-监理/B-02-监理实施细则-主体结构.pdf",
        "专业监理实施细则（主体结构）",
        ["针对钢筋、模板、混凝土分项明确控制要点与旁站范围。"],
        extra={"文件编号": "JL-XZ-2024-03"},
    )
    make_pdf(
        "02-监理/B-03-工程质量评估报告.pdf",
        "工程质量评估报告",
        [
            "监理单位对主体及装饰装修工程质量进行评估。",
            "评估结论：同意进入竣工验收程序。",
            "备注：页眉系统导出项目编号存在误填，见上方项目编号字段。",
        ],
        extra={"文件编号": "JL-PG-2025-11", "项目编号": "YG-XFZX-JL-2024-019"},
        form_hint="版式参考：监理质量评估报告常见栏目",
        scan_style=True,
    )

    # 施工 / 验收记录（对齐 GB50300 附录表名）
    make_pdf(
        "03-施工/C-01-施工组织设计.pdf",
        "施工组织设计",
        ["采用装配式脚手架与分区流水施工。", "安全目标：零重大事故。"],
        extra={"文件编号": "SG-ZZ-2024-01"},
    )
    make_pdf(
        "03-施工/C-02-检验批质量验收记录-钢筋工程-01.pdf",
        "检验批质量验收记录",
        [
            "部位：一层梁板钢筋工程",
            "主控项目检查结果：合格",
            "一般项目检查结果：合格",
            "施工单位检查结果：合格；监理单位验收结论：同意验收。",
        ],
        extra={
            "文件编号": "JYP-GJ-2024-011",
            "分部（子分部）工程名称": "主体结构",
            "分项工程名称": "钢筋工程",
            "检验批部位": "一层梁板",
        },
        form_hint="表名对齐：GB50300 附录E 检验批质量验收记录（合成填写）",
    )
    make_pdf(
        "03-施工/C-02-检验批质量验收记录-钢筋工程-01B.pdf",
        "检验批质量验收记录",
        [
            "部位：一层梁板钢筋工程",
            "主控项目检查结果：合格",
            "（与 JYP-GJ-2024-011 同编号的另一扫描件，用于测试疑似重复；文件名不含「副本」。）",
        ],
        extra={
            "文件编号": "JYP-GJ-2024-011",
            "分部（子分部）工程名称": "主体结构",
            "分项工程名称": "钢筋工程",
            "检验批部位": "一层梁板",
        },
        form_hint="表名对齐：GB50300 附录E（同编号重复件）",
    )
    make_pdf(
        "03-施工/C-02-检验批质量验收记录-混凝土工程-02.pdf",
        "检验批质量验收记录",
        ["部位：一层梁板混凝土", "验收结论：合格。"],
        extra={
            "文件编号": "JYP-HNT-2024-008",
            "分部（子分部）工程名称": "主体结构",
            "分项工程名称": "混凝土工程",
        },
        form_hint="表名对齐：GB50300 附录E 检验批质量验收记录（合成填写）",
    )
    make_pdf(
        "03-施工/C-03-分项工程质量验收记录-钢筋工程.pdf",
        "分项工程质量验收记录",
        ["分项工程名称：钢筋工程", "验收结论：合格。"],
        extra={"文件编号": "FX-GJ-2024-01"},
        form_hint="表名对齐：GB50300 附录F 分项工程质量验收记录（合成填写）",
    )
    make_pdf(
        "03-施工/C-04-分部工程质量验收记录-主体结构.pdf",
        "分部工程质量验收记录",
        ["分部工程名称：主体结构", "验收结论：合格。"],
        extra={"文件编号": "FB-ZT-2025-01"},
        form_hint="表名对齐：GB50300 附录G 分部工程质量验收记录（合成填写）",
    )

    # 检测
    make_pdf(
        "04-检测/D-01-材料进场报审及复试报告-钢筋.pdf",
        "材料进场报审及复试报告",
        [
            "材料名称：热轧带肋钢筋 HRB400E",
            "规格：Φ12 / Φ18",
            "复试结论：合格。",
            "对应部位：主体结构钢筋工程。",
        ],
        extra={"文件编号": "JC-GJ-2024-066", "检测机构": "云港市建设工程质量检测中心（合成）"},
        form_hint="版式参考：材料进场/复试报告常见栏目",
        scan_style=True,
    )
    make_pdf(
        "04-检测/D-01-材料进场报审及复试报告-混凝土试块.pdf",
        "检测报告",
        ["检测项目：混凝土抗压强度", "强度等级：C30", "结论：合格。", "对应分部：主体结构。"],
        extra={"文件编号": "JC-HNT-2024-102"},
    )

    # 验收（故意缺正式竣工验收报告，仅预验收；文件名不带规则 code）
    make_pdf(
        "05-验收/工程竣工预验收报告.pdf",
        "工程竣工预验收报告",
        [
            "预验收时间：2025-11-05。",
            "预验收意见：基本具备正式竣工验收条件，整改完成后组织正式验收。",
            "注意：本文为预验收，不能替代《工程竣工验收报告》。",
        ],
        extra={"文件编号": "YS-2025-11-05"},
        form_hint="相似件：预验收 ≠ 正式竣工验收报告",
        scan_style=True,
    )
    make_pdf(
        "05-验收/E-02-施工单位工程竣工报告.pdf",
        "施工单位工程竣工报告",
        [
            "工程已按合同约定完成，质量符合设计与规范要求，申请竣工验收。",
            "自行统计完成合同价款约：92000000 元。",
        ],
        extra={"文件编号": "SG-JG-2025-01", "合同金额（元）": "92000000"},
        form_hint="版式参考：施工单位竣工报告常见栏目",
    )
    make_pdf(
        "05-验收/E-03-设计单位工程质量检查报告.pdf",
        "设计单位工程质量检查报告",
        ["设计单位现场检查认为工程施工符合设计文件要求。", "同意竣工验收。"],
        extra={"文件编号": "SJ-JC-2025-01"},
    )
    make_pdf(
        "05-验收/单位工程观感质量检查记录.pdf",
        "单位工程观感质量检查记录",
        ["观感质量评价：好。"],
        extra={"文件编号": "GG-2025-01"},
        form_hint="表名对齐：GB50300 附录H 观感质量检查记录（合成填写）",
    )

    # 竣工图
    make_pdf(
        "06-竣工图/F-01-建筑竣工图说明.pdf",
        "工程竣工图（建筑）说明",
        [
            "本册为建筑专业竣工图目录与变更汇总说明。",
            "设计变更：共 3 份，已在竣工图中云线标注。",
            "图纸编号：建竣-01 至 建竣-28。",
        ],
        extra={"文件编号": "JG-TZ-JZ-2025"},
        form_hint="版式参考：公开归档指南中竣工图说明/目录要素",
        scan_style=True,
    )
    make_pdf(
        "06-竣工图/F-01-结构竣工图说明.pdf",
        "工程竣工图（结构）说明",
        ["结构专业竣工图已按变更更新。", "图纸编号：结竣-01 至 结竣-16。"],
        extra={"文件编号": "JG-TZ-JG-2025"},
    )

    # 专项（故意缺 G-01 消防）
    make_pdf(
        "07-专项/G-02-规划核实证明.pdf",
        "建设工程规划核实合格证",
        ["核实结论：符合规划许可要求（合成）。"],
        extra={"文件编号": "GHHS-2025-088"},
    )

    # 错传他项：混入正常阶段目录，不设「错传」路径标签
    make_pdf(
        "01-准备/滨河路市政管廊一期-施工合同.pdf",
        "建设工程施工合同",
        [
            "本文件属于另一项目，误放入本教学楼资料包。",
            "发包人：云港市市政公用事业中心（合成）",
            "承包人：海川市政工程有限公司（合成）",
        ],
        extra={
            "项目名称": "滨河路市政管廊一期工程",
            "项目编号": "YG-SZ-GL-2023-007",
            "建设单位": "云港市市政公用事业中心",
            "施工单位": "海川市政工程有限公司",
            "监理单位": "（本文件未载明）",
            "设计单位": "（本文件未载明）",
            "工程地址": "云港市滨河路沿线",
            "开工日期": "2023-05-10",
            "竣工日期": "2024-08-30",
            "合同金额（元）": "120000000",
            "文件编号": "SZ-GL-HT-2023-001",
        },
    )
    make_pdf(
        "05-验收/滨河路市政管廊一期-竣工验收报告.pdf",
        "工程竣工验收报告",
        ["滨河路市政管廊一期工程竣工验收报告（他项工程，不能计入本项目正式验收）。"],
        extra={
            "项目名称": "滨河路市政管廊一期工程",
            "项目编号": "YG-SZ-GL-2023-007",
            "建设单位": "云港市市政公用事业中心",
            "施工单位": "海川市政工程有限公司",
            "文件编号": "SZ-GL-JGYS-2024-01",
        },
        form_hint="他项工程正式竣工验收报告，不能计入本项目 E-01",
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
        "data_note": "全部为合成演示 PDF，表头参考公开归档目录与验收空白表结构；非真实工程档案。",
        "file_count": len(pdfs),
        "file_format": "pdf",
    }
    (CASE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ground_truth = {
        "project_id": CASE_ID,
        "rules_profile": "housing-construction",
        "scoring_notes": {
            "misfiled_excluded_from_presence": "错传/他项文件不得计入本项目齐套 provided",
            "field_conflicts_in_project_only": "仅统计本工程真冲突（相对 manifest 锚值）；错传级联不得计为多条 FIELD",
            "expected_field_conflict_count": 2,
            "out_of_scope_files": [
                {
                    "path": "files/05-验收/单位工程观感质量检查记录.pdf",
                    "policy": "ignore",
                    "reason": "规则清单未要求观感记录；有则可忽略，不判 missing/provided",
                }
            ],
            "optional_codes": ["B-02", "G-02"],
            "scan_style_pdfs_note": "说明性字段，不作为齐套成败标准",
        },
        "expected_highlights": {
            "missing_required": [
                {
                    "code": "E-01",
                    "name": "工程竣工验收报告",
                    "reason": "包内仅有《工程竣工预验收报告》，按规则不能替代正式竣工验收报告",
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
                    "field": "项目编号",
                    "canonical": P["project_code"],
                    "conflict_value": "YG-XFZX-JL-2024-019",
                    "source": "files/02-监理/B-03-工程质量评估报告.pdf",
                },
                {
                    "field": "合同金额",
                    "canonical": P["contract_amount"],
                    "conflict_value": "92000000",
                    "source": "files/05-验收/E-02-施工单位工程竣工报告.pdf",
                },
            ],
            "suspect_misfiled": [
                "files/01-准备/滨河路市政管廊一期-施工合同.pdf",
                "files/05-验收/滨河路市政管廊一期-竣工验收报告.pdf",
            ],
            "suspect_duplicate": [
                {
                    "files": [
                        "files/03-施工/C-02-检验批质量验收记录-钢筋工程-01.pdf",
                        "files/03-施工/C-02-检验批质量验收记录-钢筋工程-01B.pdf",
                    ],
                    "shared_file_no": "JYP-GJ-2024-011",
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
                "D-01",
                "E-02",
                "E-03",
                "F-01",
                "G-02",
            ],
            "scan_style_pdfs": [
                "files/01-准备/A-02-建筑工程施工许可证.pdf",
                "files/02-监理/B-03-工程质量评估报告.pdf",
                "files/04-检测/D-01-材料进场报审及复试报告-钢筋.pdf",
                "files/05-验收/工程竣工预验收报告.pdf",
                "files/06-竣工图/F-01-建筑竣工图说明.pdf",
            ],
        },
        "agh_success_criteria": [
            "加载 housing-construction 规则",
            "枚举并为 PDF 写出 _work 产物",
            "E-01 判 missing 且指出预验收不可替代",
            "G-01 判 missing",
            "标出滨河路管廊错传文件（不依赖「错传」目录名）",
            "标出本工程项目编号与合同金额冲突（恰好 2 条 FIELD，不含错传级联）",
            "标出检验批同编号重复",
            "可选：再跑 engineering-doc-generator（prepare→正文→build）生成情况说明 docx",
        ],
    }
    (CASE / "ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    prompt = f"""请使用 engineering-archive-audit 对 cases/{CASE_ID} 做竣工资料齐套与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。

结论需覆盖：缺失项、错传（他项工程）、本工程字段冲突、重复件。
文书勿把错传级联字段写成多条本工程冲突；预验收不能替代正式竣工验收报告。
"""
    (CASE / "TEST_PROMPT.txt").write_text(prompt.strip() + "\n", encoding="utf-8")

    print(f"Generated {CASE}")
    print(f"pdf_count={len(pdfs)} font={FONT_PATH}")
    for rel in pdfs:
        print(" ", rel)


if __name__ == "__main__":
    main()
