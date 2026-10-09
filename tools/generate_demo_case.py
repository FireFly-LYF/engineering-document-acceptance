# -*- coding: utf-8 -*-
"""Generate synthetic housing-construction demo PDF pack with GB50300-style forms."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pdf_forms import (  # noqa: E402
    make_appearance_record,
    make_division_record,
    make_inspection_batch,
    make_official_report,
    make_subitem_record,
)

CASE_ID = "demo-housing-mixed"
CASE = ROOT / "cases" / CASE_ID
FILES = CASE / "files"

P = {
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
P_FLAT = {
    "project_name": P["项目名称"],
    "project_code": P["项目编号"],
    "owner": P["建设单位"],
    "contractor": P["施工单位"],
    "supervisor": P["监理单位"],
    "designer": P["设计单位"],
    "address": P["工程地址"],
    "start_date": P["开工日期"],
    "finish_date": P["竣工日期"],
    "contract_amount": P["合同金额（元）"],
    "contract_amount_cn": "捌仟陆佰伍拾万元整",
}


def meta(**extra):
    m = dict(P)
    m.update(extra)
    return m


def main() -> None:
    if CASE.exists():
        shutil.rmtree(CASE)
    FILES.mkdir(parents=True)

    make_official_report(
        FILES / "01-准备/A-01-建设工程规划许可证.pdf",
        title="建设工程规划许可证",
        meta=meta(文件编号="建规证字〔2023〕第118号"),
        body_lines=[
            "依据城乡规划相关规定，核准本工程建设规模：地上建筑面积约18600平方米。",
            "附图及附件与本证同时使用。本证为合成演示填写。",
        ],
        form_hint="版式参考：地方规划许可证明文件常见栏目",
        doc_kind="工程准备",
    )
    make_official_report(
        FILES / "01-准备/A-02-建筑工程施工许可证.pdf",
        title="建筑工程施工许可证",
        meta=meta(文件编号="施许字〔2024〕第045号"),
        body_lines=[
            "合同工期：2024-03-01 至 2025-11-20。",
            "建设资金已落实，施工图审查合格，具备开工条件（合成）。",
        ],
        form_hint="版式参考：施工许可证明文件常见栏目",
        scan_style=True,
        doc_kind="工程准备",
    )
    make_official_report(
        FILES / "01-准备/A-03-建设工程施工合同.pdf",
        title="建设工程施工合同",
        meta=meta(文件编号="YG-XFZX-HT-2024-001"),
        body_lines=[
            f"发包人（建设单位）：{P['建设单位']}",
            f"承包人（施工单位）：{P['施工单位']}",
            f"签约合同价（人民币）：{P['合同金额（元）']} 元（{P_FLAT['contract_amount_cn']}）。",
            "工程质量标准：合格。争议解决方式：向工程所在地人民法院起诉。",
        ],
        form_hint="版式参考：施工合同首页要素（合成填写）",
        doc_kind="合同",
    )
    make_official_report(
        FILES / "01-准备/A-04-建设工程委托监理合同.pdf",
        title="建设工程委托监理合同",
        meta=meta(文件编号="YG-XFZX-JLHT-2024-001"),
        body_lines=[
            f"委托人：{P['建设单位']}",
            f"监理人：{P['监理单位']}",
            "监理服务期限：与施工工期一致。",
        ],
        doc_kind="合同",
    )

    make_official_report(
        FILES / "02-监理/B-01-监理规划.pdf",
        title="监理规划",
        meta=meta(文件编号="JL-GH-2024-01"),
        body_lines=[
            "本规划明确旁站、巡视、平行检验等监理工作制度。",
            "总监理工程师：周某某（合成署名）。",
        ],
        doc_kind="监理文件",
    )
    make_official_report(
        FILES / "02-监理/B-02-监理实施细则-主体结构.pdf",
        title="专业监理实施细则（主体结构）",
        meta=meta(文件编号="JL-XZ-2024-03"),
        body_lines=["针对钢筋、模板、混凝土分项明确控制要点与旁站范围。"],
        doc_kind="监理文件",
    )
    make_official_report(
        FILES / "02-监理/B-03-工程质量评估报告.pdf",
        title="工程质量评估报告",
        meta=meta(文件编号="JL-PG-2025-11", 项目编号="YG-XFZX-JL-2024-019"),
        body_lines=[
            "监理单位对主体及装饰装修工程质量进行评估。",
            "评估结论：同意进入竣工验收程序。",
            "备注：页眉系统导出项目编号存在误填，见上方项目编号字段。",
        ],
        form_hint="版式参考：监理质量评估报告常见栏目",
        scan_style=True,
        doc_kind="监理评估",
    )

    make_official_report(
        FILES / "03-施工/C-01-施工组织设计.pdf",
        title="施工组织设计",
        meta=meta(文件编号="SG-ZZ-2024-01"),
        body_lines=["采用装配式脚手架与分区流水施工。", "安全目标：零重大事故。"],
        doc_kind="施工文件",
    )
    make_inspection_batch(
        FILES / "03-施工/C-02-检验批质量验收记录-钢筋工程-01.pdf",
        meta=meta(文件编号="JYP-GJ-2024-011"),
        batch_name="钢筋工程",
        file_no="JYP-GJ-2024-011",
        division="主体结构",
        subitem="钢筋工程",
        location="一层梁板",
        capacity="一层梁板钢筋约12t",
        basis_sg="GB50204 / 专项施工方案",
        basis_ys="GB50204-2015",
        major_rows=[
            ("钢筋品种、规格、强度", "全/抽查", "符合设计，复试合格", "合格"),
            ("钢筋连接方式及接头", "3/3", "机械连接接头检验合格", "合格"),
            ("受力钢筋间距、排距", "10/10", "偏差在允许范围内", "合格"),
        ],
        general_rows=[
            ("钢筋表面", "10/10", "无严重锈蚀油污", "合格"),
            ("保护层厚度", "10/10", "符合设计", "合格"),
        ],
    )
    make_inspection_batch(
        FILES / "03-施工/C-02-检验批质量验收记录-钢筋工程-01B.pdf",
        meta=meta(文件编号="JYP-GJ-2024-011"),
        batch_name="钢筋工程",
        file_no="JYP-GJ-2024-011",
        division="主体结构",
        subitem="钢筋工程",
        location="一层梁板",
        capacity="一层梁板钢筋约12t",
        basis_sg="GB50204 / 专项施工方案",
        basis_ys="GB50204-2015",
        major_rows=[
            ("钢筋品种、规格、强度", "全/抽查", "符合设计，复试合格", "合格"),
            ("钢筋连接方式及接头", "3/3", "机械连接接头检验合格", "合格"),
        ],
        general_rows=[("钢筋表面", "10/10", "无严重锈蚀油污", "合格")],
        note="（与 JYP-GJ-2024-011 同编号的另一扫描件，用于测试疑似重复；文件名不含「副本」。）",
        scan_style=True,
    )
    make_inspection_batch(
        FILES / "03-施工/C-02-检验批质量验收记录-混凝土工程-02.pdf",
        meta=meta(文件编号="JYP-HNT-2024-008"),
        batch_name="混凝土工程",
        file_no="JYP-HNT-2024-008",
        division="主体结构",
        subitem="混凝土工程",
        location="一层梁板",
        capacity="约85m³",
        basis_sg="GB50204 / 混凝土专项方案",
        basis_ys="GB50204-2015",
        major_rows=[
            ("混凝土强度等级", "试块", "C30，同条件/标级试块合格", "合格"),
            ("位置、尺寸偏差", "10/10", "符合规范", "合格"),
        ],
        general_rows=[("表面质量", "全数", "无严重蜂窝孔洞", "合格")],
    )
    make_subitem_record(
        FILES / "03-施工/C-03-分项工程质量验收记录-钢筋工程.pdf",
        meta=meta(文件编号="FX-GJ-2024-01"),
        title="分项工程质量验收记录",
        file_no="FX-GJ-2024-01",
        division="主体结构",
        subitem="钢筋工程",
        batch_count="2",
        conclusion="合格",
    )
    make_division_record(
        FILES / "03-施工/C-04-分部工程质量验收记录-主体结构.pdf",
        meta=meta(文件编号="FB-ZT-2025-01"),
        title="分部工程质量验收记录",
        file_no="FB-ZT-2025-01",
        division="主体结构",
        subitem_count="6",
        conclusion="合格",
    )

    make_official_report(
        FILES / "04-检测/D-01-材料进场报审及复试报告-钢筋.pdf",
        title="材料进场报审及复试报告",
        meta=meta(文件编号="JC-GJ-2024-066"),
        body_lines=[
            "材料名称：热轧带肋钢筋 HRB400E",
            "规格：Φ12 / Φ18",
            "复试结论：合格。",
            "检测机构：云港市建设工程质量检测中心（合成）",
            "对应部位：主体结构钢筋工程。",
        ],
        form_hint="版式参考：材料进场/复试报告常见栏目",
        scan_style=True,
        doc_kind="材料检测",
    )
    make_official_report(
        FILES / "04-检测/D-01-材料进场报审及复试报告-混凝土试块.pdf",
        title="检测报告",
        meta=meta(文件编号="JC-HNT-2024-102"),
        body_lines=[
            "检测项目：混凝土抗压强度",
            "强度等级：C30",
            "结论：合格。",
            "对应分部：主体结构。",
        ],
        doc_kind="材料检测",
    )

    make_official_report(
        FILES / "05-验收/工程竣工预验收报告.pdf",
        title="工程竣工预验收报告",
        meta=meta(文件编号="YS-2025-11-05"),
        body_lines=[
            "预验收时间：2025-11-05。",
            "预验收意见：基本具备正式竣工验收条件，整改完成后组织正式验收。",
            "注意：本文为预验收，不能替代《工程竣工验收报告》。",
        ],
        form_hint="相似件：预验收 ≠ 正式竣工验收报告",
        scan_style=True,
        doc_kind="竣工验收",
    )
    make_official_report(
        FILES / "05-验收/E-02-施工单位工程竣工报告.pdf",
        title="施工单位工程竣工报告",
        meta=meta(文件编号="SG-JG-2025-01", **{"合同金额（元）": "92000000"}),
        body_lines=[
            "工程已按合同约定完成，业务质量符合设计与规范要求，申请竣工验收。",
            "自行统计完成合同价款约：92000000 元。",
        ],
        form_hint="版式参考：施工单位竣工报告常见栏目",
        doc_kind="竣工验收",
    )
    make_official_report(
        FILES / "05-验收/E-03-设计单位工程质量检查报告.pdf",
        title="设计单位工程质量检查报告",
        meta=meta(文件编号="SJ-JC-2025-01"),
        body_lines=["设计单位现场检查认为工程施工符合设计文件要求。", "同意竣工验收。"],
        doc_kind="竣工验收",
    )
    make_appearance_record(
        FILES / "05-验收/单位工程观感质量检查记录.pdf",
        meta=meta(文件编号="GG-2025-01"),
        file_no="GG-2025-01",
        grade="好",
    )

    make_official_report(
        FILES / "06-竣工图/F-01-建筑竣工图说明.pdf",
        title="工程竣工图（建筑）说明",
        meta=meta(文件编号="JG-TZ-JZ-2025"),
        body_lines=[
            "本册为建筑专业竣工图目录与变更汇总说明。",
            "设计变更：共 3 份，已在竣工图中云线标注。",
            "图纸编号：建竣-01 至 建竣-28。",
        ],
        form_hint="版式参考：公开归档指南中竣工图说明/目录要素",
        scan_style=True,
        doc_kind="竣工图",
    )
    make_official_report(
        FILES / "06-竣工图/F-01-结构竣工图说明.pdf",
        title="工程竣工图（结构）说明",
        meta=meta(文件编号="JG-TZ-JG-2025"),
        body_lines=["结构专业竣工图已按变更更新。", "图纸编号：结竣-01 至 结竣-16。"],
        doc_kind="竣工图",
    )

    make_official_report(
        FILES / "07-专项/G-02-规划核实证明.pdf",
        title="建设工程规划核实合格证",
        meta=meta(文件编号="GHHS-2025-088"),
        body_lines=["核实结论：符合规划许可要求（合成）。"],
        doc_kind="专项",
    )

    other = {
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
    }
    make_official_report(
        FILES / "01-准备/滨河路市政管廊一期-施工合同.pdf",
        title="建设工程施工合同",
        meta=other,
        body_lines=[
            "本文件属于另一项目，误放入本教学楼资料包。",
            "发包人：云港市市政公用事业中心（合成）",
            "承包人：海川市政工程有限公司（合成）",
        ],
        doc_kind="合同",
    )
    make_official_report(
        FILES / "05-验收/滨河路市政管廊一期-竣工验收报告.pdf",
        title="工程竣工验收报告",
        meta={**other, "文件编号": "SZ-GL-JGYS-2024-01"},
        body_lines=["滨河路市政管廊一期工程竣工验收报告（他项工程，不能计入本项目正式验收）。"],
        form_hint="他项工程正式竣工验收报告，不能计入本项目 E-01",
        doc_kind="竣工验收",
    )

    pdfs = sorted(p.relative_to(CASE).as_posix() for p in FILES.rglob("*.pdf"))
    manifest = {
        "project_id": CASE_ID,
        "project_type": "房屋建筑工程",
        "rules_profile": "housing-construction",
        **{k: P_FLAT[k] for k in (
            "project_name", "project_code", "owner", "contractor", "supervisor",
            "designer", "address", "start_date", "finish_date", "contract_amount",
        )},
        "data_note": "合成演示 PDF；检验批/分项/分部/观感表式参考 GB50300-2013 附录；非真实工程档案。",
        "file_count": len(pdfs),
        "file_format": "pdf",
        "form_reference": [
            "reference/public-pdfs/gb50300-2013-acceptance-standard.pdf",
            "reference/public-pdfs/acceptance-check-forms-unified.pdf",
        ],
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
            "form_style_note": "验收类表式仿 GB50300 附录；仍为合成数据",
        },
        "expected_highlights": {
            "missing_required": [
                {
                    "code": "E-01",
                    "name": "工程竣工验收报告",
                    "reason": "包内仅有《工程竣工预验收报告》，按规则不能替代正式竣工验收报告",
                    "similar_files": ["files/05-验收/工程竣工预验收报告.pdf"],
                },
                {"code": "G-01", "name": "消防验收意见或备案凭证", "reason": "包内无消防验收/备案类文件"},
            ],
            "field_conflicts": [
                {
                    "field": "项目编号",
                    "canonical": P_FLAT["project_code"],
                    "conflict_value": "YG-XFZX-JL-2024-019",
                    "source": "files/02-监理/B-03-工程质量评估报告.pdf",
                },
                {
                    "field": "合同金额",
                    "canonical": P_FLAT["contract_amount"],
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
                "A-01", "A-02", "A-03", "A-04", "B-01", "B-03", "C-01", "C-02",
                "C-03", "C-04", "D-01", "E-02", "E-03", "F-01", "G-02",
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
    print(f"pdf_count={len(pdfs)}")
    for rel in pdfs:
        print(" ", rel)


if __name__ == "__main__":
    main()
