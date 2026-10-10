# -*- coding: utf-8 -*-
"""Generate a fully complete, consistent housing demo PDF pack (no planted defects)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pdf_forms import (  # noqa: E402
    make_appearance_record,
    make_asbuilt_drawing_note,
    make_completion_pack,
    make_construction_contract,
    make_construction_permit,
    make_division_record,
    make_fire_acceptance_opinion,
    make_inspection_batch,
    make_material_test_report,
    make_planning_permit,
    make_planning_verify_cert,
    make_quality_assessment,
    make_subitem_record,
    make_supervision_contract,
    make_tech_document,
)

CASE_ID = "demo-housing-complete"
CASE = ROOT / "cases" / CASE_ID
FILES = CASE / "files"

P = {
    "项目名称": "云港新区市民活动中心图书馆工程",
    "项目编号": "YG-SQ-TSG-2024-003",
    "建设单位": "云港市文化广电和旅游局",
    "施工单位": "东海建工集团有限公司",
    "监理单位": "华信建设监理有限公司",
    "设计单位": "滨海建筑设计有限公司",
    "工程地址": "云港市海州区市民大道168号",
    "开工日期": "2024-04-15",
    "竣工日期": "2025-10-30",
    "合同金额（元）": "128600000",
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
    "contract_amount_cn": "壹亿贰仟捌佰陆拾万元整",
}


def meta(**extra):
    m = dict(P)
    m.update(extra)
    return m


def main() -> None:
    if CASE.exists():
        shutil.rmtree(CASE)
    FILES.mkdir(parents=True)

    make_planning_permit(
        FILES / "01-准备/A-01-建设工程规划许可证.pdf",
        meta=meta(文件编号="建规证字〔2023〕第206号"),
        body_lines=[
            "依据城乡规划相关规定，核准本工程建设规模：地上建筑面积约24500平方米。",
            "附图及附件名称见许可证附件清单，与本证同时使用。",
        ],
    )
    make_construction_permit(
        FILES / "01-准备/A-02-建筑工程施工许可证.pdf",
        meta=meta(文件编号="施许字〔2024〕第092号"),
        body_lines=[
            "合同工期：2024-04-15 至 2025-10-30。",
            "建设资金已落实，施工图审查合格，具备开工条件。",
        ],
        scale_note="地上约24500㎡",
    )
    make_construction_contract(
        FILES / "01-准备/A-03-建设工程施工合同.pdf",
        meta=meta(文件编号="YG-SQ-TSG-HT-2024-003"),
        body_lines=["工程质量标准：合格。争议解决方式：向工程所在地人民法院起诉。"],
        amount_cn=P_FLAT["contract_amount_cn"],
    )
    make_supervision_contract(
        FILES / "01-准备/A-04-建设工程委托监理合同.pdf",
        meta=meta(文件编号="YG-SQ-TSG-JLHT-2024-003"),
        body_lines=["监理服务内容含旁站、巡视与平行检验。"],
    )

    make_tech_document(
        FILES / "02-监理/B-01-监理规划.pdf",
        title="监理规划",
        meta=meta(文件编号="JL-GH-TSG-2024-01"),
        org_header=P["监理单位"],
        chapters=[
            ("1 工程概况", [f"项目名称：{P['项目名称']}", f"项目编号：{P['项目编号']}"]),
            ("2 监理工作内容", ["本规划明确旁站、巡视、平行检验等监理工作制度。", "总监理工程师：周海涛。"]),
            ("3 监理组织", [f"监理单位：{P['监理单位']}", f"施工单位：{P['施工单位']}"]),
        ],
    )
    make_tech_document(
        FILES / "02-监理/B-02-监理实施细则-主体结构.pdf",
        title="专业监理实施细则（主体结构）",
        meta=meta(文件编号="JL-XZ-TSG-2024-02"),
        org_header=P["监理单位"],
        chapters=[
            ("1 编制依据", ["GB50300、设计文件及监理规划。"]),
            ("2 控制要点", ["针对钢筋、模板、混凝土分项明确控制要点与旁站范围。"]),
        ],
    )
    make_quality_assessment(
        FILES / "02-监理/B-03-工程质量评估报告.pdf",
        meta=meta(文件编号="JL-PG-TSG-2025-10"),
        body_lines=[
            "监理单位对主体及装饰装修工程质量进行评估。",
            "各分部工程质量验收合格，质量控制资料齐全。",
            "评估结论：同意进入竣工验收程序。",
        ],
    )

    make_tech_document(
        FILES / "03-施工/C-01-施工组织设计.pdf",
        title="施工组织设计",
        meta=meta(文件编号="SG-ZZ-TSG-2024-01"),
        org_header=P["施工单位"],
        chapters=[
            ("1 编制说明", [f"工程地址：{P['工程地址']}", f"合同金额（元）：{P['合同金额（元）']}"]),
            ("2 施工部署", ["采用分区流水施工，重点控制大空间屋面与消防系统安装交叉作业。"]),
            ("3 进度计划", [f"开工日期：{P['开工日期']}", f"竣工日期：{P['竣工日期']}"]),
        ],
    )
    make_inspection_batch(
        FILES / "03-施工/C-02-检验批质量验收记录-钢筋工程-01.pdf",
        meta=meta(文件编号="JYP-TSG-GJ-2024-015"),
        batch_name="钢筋工程",
        file_no="JYP-TSG-GJ-2024-015",
        division="主体结构",
        subitem="钢筋工程",
        location="二层梁板",
        capacity="二层梁板钢筋约15t",
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
        FILES / "03-施工/C-02-检验批质量验收记录-混凝土工程-02.pdf",
        meta=meta(文件编号="JYP-TSG-HNT-2024-009"),
        batch_name="混凝土工程",
        file_no="JYP-TSG-HNT-2024-009",
        division="主体结构",
        subitem="混凝土工程",
        location="二层梁板",
        capacity="约96m³",
        basis_sg="GB50204 / 混凝土专项方案",
        basis_ys="GB50204-2015",
        major_rows=[
            ("混凝土强度等级", "试块", "C35，同条件/标养试块合格", "合格"),
            ("位置、尺寸偏差", "10/10", "符合规范", "合格"),
        ],
        general_rows=[("表面质量", "全数", "无严重蜂窝孔洞", "合格")],
    )
    make_subitem_record(
        FILES / "03-施工/C-03-分项工程质量验收记录-钢筋工程.pdf",
        meta=meta(文件编号="FX-TSG-GJ-2024-01"),
        title="分项工程质量验收记录",
        file_no="FX-TSG-GJ-2024-01",
        division="主体结构",
        subitem="钢筋工程",
        batch_count="4",
        conclusion="合格",
    )
    make_division_record(
        FILES / "03-施工/C-04-分部工程质量验收记录-主体结构.pdf",
        meta=meta(文件编号="FB-TSG-ZT-2025-01"),
        title="分部工程质量验收记录",
        file_no="FB-TSG-ZT-2025-01",
        division="主体结构",
        subitem_count="8",
        conclusion="合格",
    )

    make_material_test_report(
        FILES / "04-检测/D-01-材料进场报审及复试报告-钢筋.pdf",
        meta=meta(文件编号="JC-TSG-GJ-2024-088"),
        report_title="材料进场报审及复试报告",
        sample_rows=[
            ("材料名称", "热轧带肋钢筋 HRB400E"),
            ("规格", "Φ14 / Φ20"),
            ("对应部位", "主体结构钢筋工程"),
            ("复试项目", "拉伸 / 弯曲"),
        ],
        conclusion="合格",
        body_lines=["检测机构见证取样，结果符合设计与规范要求。"],
    )
    make_material_test_report(
        FILES / "04-检测/D-01-材料进场报审及复试报告-混凝土试块.pdf",
        meta=meta(文件编号="JC-TSG-HNT-2024-115"),
        report_title="检测报告",
        sample_rows=[
            ("检测项目", "混凝土抗压强度"),
            ("强度等级", "C35"),
            ("对应分部", "主体结构"),
            ("龄期", "28d"),
        ],
        conclusion="合格",
    )

    make_completion_pack(
        FILES / "05-验收/E-01-工程竣工验收报告.pdf",
        title="工程竣工验收报告",
        meta=meta(文件编号="JGYS-TSG-2025-001"),
        body_lines=[
            "建设单位组织勘察、设计、施工、监理等单位进行竣工验收。",
            "本工程已完成各分部工程施工，材料均有出厂质量证明及见证送检报告，检测结果合格。",
            "质量控制资料齐全，安全和主要使用功能检验符合要求，观感质量综合评价为好。",
            "综合评定：工程质量合格，一致同意验收。",
        ],
        form_code="GD-E1-914",
        conclusion="验收合格",
        report_date="2025年11月8日",
        five_party=True,
    )
    make_completion_pack(
        FILES / "05-验收/E-02-施工单位工程竣工报告.pdf",
        title="施工单位工程竣工报告",
        meta=meta(文件编号="SG-JG-TSG-2025-01"),
        body_lines=[
            "本工程已按施工图设计文件及合同约定完成全部施工内容。",
            "工程质量控制资料完整，安全和主要使用功能检验资料齐全，观感质量综合评价为好。",
            f"合同金额（元）：{P['合同金额（元）']}。施工单位自评工程质量合格，申请组织竣工验收。",
        ],
        form_code="施工单位竣工报告",
        conclusion="本工程达到竣工验收条件，申请组织竣工验收",
        report_date="2025年11月2日",
        five_party=False,
    )
    make_completion_pack(
        FILES / "05-验收/E-03-设计单位工程质量检查报告.pdf",
        title="设计单位工程质量检查报告",
        meta=meta(文件编号="SJ-JC-TSG-2025-01"),
        body_lines=[
            "设计单位对工程实体与设计文件符合性进行现场检查。",
            "检查意见：施工质量符合设计文件要求，同意竣工验收。",
        ],
        form_code="设计单位质量检查报告",
        conclusion="同意竣工验收",
        report_date="2025年11月3日",
        five_party=False,
    )
    make_appearance_record(
        FILES / "05-验收/单位工程观感质量检查记录.pdf",
        meta=meta(文件编号="GG-TSG-2025-01"),
        file_no="GG-TSG-2025-01",
        grade="好",
    )

    make_asbuilt_drawing_note(
        FILES / "06-竣工图/F-01-建筑竣工图说明.pdf",
        meta=meta(文件编号="JG-TZ-TSG-JZ-2025"),
        specialty="建筑",
        drawing_nos="建竣-01 至 建竣-36",
        body_lines=[
            "本册为建筑专业竣工图目录与变更汇总说明。",
            "设计变更：共 2 份，已在竣工图中云线标注。",
        ],
    )
    make_asbuilt_drawing_note(
        FILES / "06-竣工图/F-01-结构竣工图说明.pdf",
        meta=meta(文件编号="JG-TZ-TSG-JG-2025"),
        specialty="结构",
        drawing_nos="结竣-01 至 结竣-20",
        body_lines=["结构专业竣工图已按变更更新。"],
    )

    make_fire_acceptance_opinion(
        FILES / "07-专项/G-01-消防验收意见书.pdf",
        meta=meta(文件编号="XFYS-TSG-2025-046"),
        opinion_no="云消验字〔2025〕第046号",
        body_lines=["消防设施联动试验合格，消防控制室值班制度落实。"],
        conclusion="同意投入使用",
    )
    make_planning_verify_cert(
        FILES / "07-专项/G-02-规划核实证明.pdf",
        meta=meta(文件编号="GHHS-TSG-2025-031"),
        body_lines=["经现场核实，本工程平面位置、建筑规模符合规划许可要求，准予规划核实合格。"],
    )

    pdfs = sorted(p.relative_to(CASE).as_posix() for p in FILES.rglob("*.pdf"))
    manifest = {
        "project_id": CASE_ID,
        "project_type": "房屋建筑工程",
        "rules_profile": "housing-construction",
        **{
            k: P_FLAT[k]
            for k in (
                "project_name",
                "project_code",
                "owner",
                "contractor",
                "supervisor",
                "designer",
                "address",
                "start_date",
                "finish_date",
                "contract_amount",
            )
        },
        "data_note": (
            "完全正确对照包：齐套全部必需项（含正式竣工验收与消防验收），"
            "字段与 manifest 一致，无错传/冲突/重复/不可读页。"
        ),
        "file_count": len(pdfs),
        "file_format": "pdf",
        "form_reference": [
            "reference/public-pdfs/gb50300-2013-acceptance-standard.pdf",
            "reference/public-pdfs/acceptance-check-forms-unified.pdf",
            "reference/public-pdfs/construction-permit-sample-sd.pdf",
            "reference/public-pdfs/construction-contract-gf2017.pdf",
            "reference/public-pdfs/unit-completion-acceptance-report.pdf",
        ],
    }
    (CASE / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ground_truth = {
        "project_id": CASE_ID,
        "rules_profile": "housing-construction",
        "scoring_notes": {
            "contrast_with": ["demo-housing-mixed", "demo-housing-near-miss"],
            "difference": "本包为全量齐套、字段一致的正确对照；不应出现缺失/错传/冲突/重复/不可读",
            "expected_field_conflict_count": 0,
            "expected_missing_required_count": 0,
            "optional_codes_included": ["B-02", "G-02"],
            "form_style_note": "文种异构版式；专业文书表述；无演示性标注",
        },
        "expected_highlights": {
            "missing_required": [],
            "field_conflicts": [],
            "suspect_misfiled": [],
            "suspect_duplicate": [],
            "should_be_provided_examples": [
                "A-01",
                "A-02",
                "A-03",
                "A-04",
                "B-01",
                "B-02",
                "B-03",
                "C-01",
                "C-02",
                "C-03",
                "C-04",
                "D-01",
                "E-01",
                "E-02",
                "E-03",
                "F-01",
                "G-01",
                "G-02",
            ],
        },
        "agh_success_criteria": [
            "加载 housing-construction 规则",
            "全部 required 文档 status=provided（含 E-01 正式竣工验收、G-01 消防验收）",
            "无 FIELD / MISFILE / DUP / UNREADABLE / missing(error)",
            "可选：再跑 engineering-doc-generator，情况说明结论为资料齐套、无明显一致性问题",
        ],
    }
    (CASE / "ground_truth.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    prompt = f"""请使用 engineering-archive-audit 对 cases/{CASE_ID} 做竣工资料齐套与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

本包为完全正确对照包：预期全部必需资料已提供，字段一致，无错传、冲突、重复与不可读页。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。
文书结论应反映资料齐套、无明显一致性问题；勿编造缺失或冲突。
"""
    (CASE / "TEST_PROMPT.txt").write_text(prompt.strip() + "\n", encoding="utf-8")
    print(f"Generated {CASE}")
    print(f"pdf_count={len(pdfs)}")
    for rel in pdfs:
        print(" ", rel)


if __name__ == "__main__":
    main()
