# -*- coding: utf-8 -*-
"""Generate synthetic housing-construction demo PDF pack with heterogeneous form layouts."""
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
    make_inspection_batch,
    make_material_test_report,
    make_planning_permit,
    make_planning_verify_cert,
    make_quality_assessment,
    make_subitem_record,
    make_supervision_contract,
    make_tech_document,
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

    make_planning_permit(
        FILES / "01-准备/A-01-建设工程规划许可证.pdf",
        meta=meta(文件编号="建规证字〔2023〕第118号"),
        body_lines=[
            "依据城乡规划相关规定，核准本工程建设规模：地上建筑面积约18600平方米。",
            "附图及附件名称见许可证附件清单，与本证同时使用。",
        ],
    )
    make_construction_permit(
        FILES / "01-准备/A-02-建筑工程施工许可证.pdf",
        meta=meta(文件编号="施许字〔2024〕第045号"),
        body_lines=[
            "合同工期：2024-03-01 至 2025-11-20。",
            "建设资金已落实，施工图审查合格，具备开工条件。",
        ],
        scan_style=True,
    )
    make_construction_contract(
        FILES / "01-准备/A-03-建设工程施工合同.pdf",
        meta=meta(文件编号="YG-XFZX-HT-2024-001"),
        body_lines=["工程质量标准：合格。争议解决方式：向工程所在地人民法院起诉。"],
        amount_cn=P_FLAT["contract_amount_cn"],
    )
    make_supervision_contract(
        FILES / "01-准备/A-04-建设工程委托监理合同.pdf",
        meta=meta(文件编号="YG-XFZX-JLHT-2024-001"),
        body_lines=["监理服务内容含旁站、巡视与平行检验。"],
    )

    make_tech_document(
        FILES / "02-监理/B-01-监理规划.pdf",
        title="监理规划",
        meta=meta(文件编号="JL-GH-2024-01"),
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
        meta=meta(文件编号="JL-XZ-2024-03"),
        org_header=P["监理单位"],
        chapters=[
            ("1 编制依据", ["GB50300、设计文件及监理规划。"]),
            ("2 控制要点", ["针对钢筋、模板、混凝土分项明确控制要点与旁站范围。"]),
        ],
    )
    make_quality_assessment(
        FILES / "02-监理/B-03-工程质量评估报告.pdf",
        meta=meta(文件编号="JL-PG-2025-11", 项目编号="YG-XFZX-JL-2024-019"),
        body_lines=[
            "监理单位对主体及装饰装修工程质量进行评估。",
            "各分部工程质量验收合格，质量控制资料基本齐全。",
            "评估结论：同意进入竣工验收程序。",
        ],
        scan_style=True,
    )

    make_tech_document(
        FILES / "03-施工/C-01-施工组织设计.pdf",
        title="施工组织设计",
        meta=meta(文件编号="SG-ZZ-2024-01"),
        org_header=P["施工单位"],
        chapters=[
            ("1 编制说明", [f"工程地址：{P['工程地址']}", f"合同金额（元）：{P['合同金额（元）']}"]),
            ("2 施工部署", ["采用装配式脚手架与分区流水施工。", "安全目标：零重大事故。"]),
            ("3 进度计划", [f"开工日期：{P['开工日期']}；竣工日期：{P['竣工日期']}"]),
        ],
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
        note="",
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

    make_material_test_report(
        FILES / "04-检测/D-01-材料进场报审及复试报告-钢筋.pdf",
        meta=meta(文件编号="JC-GJ-2024-066"),
        report_title="材料进场报审及复试报告",
        sample_rows=[
            ("材料名称", "热轧带肋钢筋 HRB400E"),
            ("规格", "Φ12 / Φ18"),
            ("对应部位", "主体结构钢筋工程"),
            ("复试项目", "拉伸 / 弯曲"),
        ],
        conclusion="合格",
        body_lines=["检测机构见证取样，结果符合设计与规范要求。"],
        scan_style=True,
    )
    make_material_test_report(
        FILES / "04-检测/D-01-材料进场报审及复试报告-混凝土试块.pdf",
        meta=meta(文件编号="JC-HNT-2024-102"),
        report_title="检测报告",
        sample_rows=[
            ("检测项目", "混凝土抗压强度"),
            ("强度等级", "C30"),
            ("对应分部", "主体结构"),
            ("龄期", "28d"),
        ],
        conclusion="合格",
    )

    make_completion_pack(
        FILES / "05-验收/工程竣工预验收报告.pdf",
        title="工程竣工预验收报告",
        meta=meta(文件编号="YS-2025-11-05"),
        body_lines=[
            "建设单位组织施工、监理等单位于2025年11月5日进行竣工预验收。",
            "查验分部工程验收记录、质量控制资料及安全和主要使用功能抽查记录。",
            "预验收意见：工程质量基本符合设计要求，局部整改完成后组织正式竣工验收。",
        ],
        form_code="预验收记录表",
        conclusion="预验收结论：基本具备正式竣工验收条件",
        report_date="2025年11月5日",
        scan_style=True,
        five_party=False,
    )
    make_completion_pack(
        FILES / "05-验收/E-02-施工单位工程竣工报告.pdf",
        title="施工单位工程竣工报告",
        meta=meta(文件编号="SG-JG-2025-01", **{"合同金额（元）": "92000000"}),
        body_lines=[
            "本工程已按施工图设计文件及合同约定完成全部施工内容。",
            "工程质量控制资料完整，安全和主要使用功能检验资料齐全，观感质量综合评价为好。",
            "合同金额（元）：92000000。施工单位自评工程质量合格，申请组织竣工验收。",
        ],
        form_code="施工单位竣工报告",
        conclusion="本工程达到竣工验收条件，申请组织竣工验收",
        report_date="2025年11月18日",
        five_party=False,
    )
    make_completion_pack(
        FILES / "05-验收/E-03-设计单位工程质量检查报告.pdf",
        title="设计单位工程质量检查报告",
        meta=meta(文件编号="SJ-JC-2025-01"),
        body_lines=[
            "设计单位对工程实体与设计文件符合性进行现场检查。",
            "检查意见：施工质量符合设计文件要求，同意竣工验收。",
        ],
        form_code="设计单位质量检查报告",
        conclusion="同意竣工验收",
        report_date="2025年11月18日",
        five_party=False,
    )
    make_appearance_record(
        FILES / "05-验收/单位工程观感质量检查记录.pdf",
        meta=meta(文件编号="GG-2025-01"),
        file_no="GG-2025-01",
        grade="好",
    )

    make_asbuilt_drawing_note(
        FILES / "06-竣工图/F-01-建筑竣工图说明.pdf",
        meta=meta(文件编号="JG-TZ-JZ-2025"),
        specialty="建筑",
        drawing_nos="建竣-01 至 建竣-28",
        body_lines=[
            "本册为建筑专业竣工图目录与变更汇总说明。",
            "设计变更：共 3 份，已在竣工图中云线标注。",
        ],
        scan_style=True,
    )
    make_asbuilt_drawing_note(
        FILES / "06-竣工图/F-01-结构竣工图说明.pdf",
        meta=meta(文件编号="JG-TZ-JG-2025"),
        specialty="结构",
        drawing_nos="结竣-01 至 结竣-16",
        body_lines=["结构专业竣工图已按变更更新。"],
    )

    make_planning_verify_cert(
        FILES / "07-专项/G-02-规划核实证明.pdf",
        meta=meta(文件编号="GHHS-2025-088"),
        body_lines=["经现场核实，本工程平面位置、建筑规模符合规划许可要求，准予规划核实合格。"],
    )

    other = {
        "项目名称": "滨河路市政管廊一期工程",
        "项目编号": "YG-SZ-GL-2023-007",
        "建设单位": "云港市市政公用事业中心",
        "施工单位": "海川市政工程有限公司",
        "监理单位": "蓝桥工程监理有限公司",
        "设计单位": "云港市政设计研究院有限公司",
        "工程地址": "云港市滨河路沿线",
        "开工日期": "2023-05-10",
        "竣工日期": "2024-08-30",
        "合同金额（元）": "120000000",
        "文件编号": "SZ-GL-HT-2023-001",
    }
    make_construction_contract(
        FILES / "01-准备/滨河路市政管廊一期-施工合同.pdf",
        meta=other,
        body_lines=[
            "工程质量标准：合格。",
            "承包范围：滨河路市政综合管廊土建及附属工程。",
        ],
        amount_cn="壹亿贰仟万元整",
    )
    make_completion_pack(
        FILES / "05-验收/滨河路市政管廊一期-竣工验收报告.pdf",
        title="工程竣工验收报告",
        meta={**other, "文件编号": "SZ-GL-JGYS-2024-01"},
        body_lines=[
            "本工程已完成各分部工程施工，材料均有出厂质量证明及见证送检报告，检测结果合格。",
            "质量控制资料齐全，安全和主要使用功能检验符合要求，观感质量综合评价为一般。",
            "综合评定：工程质量合格，一致同意验收。",
        ],
        form_code="GD-E1-914",
        conclusion="验收合格",
        report_date="2024年9月5日",
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
        "data_note": (
            "合成演示 PDF；按文种异构版式（规划/施工许可证、GF合同、监理/施组技术文件、"
            "检测报告、竣工验收封面表、竣工图目录、GB50300附录验收表）；非真实工程档案。"
        ),
        "file_count": len(pdfs),
        "file_format": "pdf",
        "form_reference": [
            "reference/public-pdfs/gb50300-2013-acceptance-standard.pdf",
            "reference/public-pdfs/acceptance-check-forms-unified.pdf",
            "reference/public-pdfs/construction-permit-sample-sd.pdf",
            "reference/public-pdfs/construction-contract-gf2017.pdf",
            "reference/public-pdfs/unit-completion-acceptance-report.pdf",
            "reference/public-pdfs/zj-unified-forms-2025.pdf",
        ],
    }
    (CASE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ground_truth = {
        "project_id": CASE_ID,
        "rules_profile": "housing-construction",
        "scoring_notes": {
            "misfiled_excluded_from_presence": "错传/他项文件不得计入本项目材料齐全 provided",
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
            "scan_style_pdfs_note": "说明性字段，不作为材料齐全成败标准",
            "form_style_note": (
                "文种异构：许可证/合同/技术文件/检测报告/竣工验收封面/竣工图目录/GB50300附录；"
                "仍为合成数据"
            ),
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
    prompt = f"""请使用 engineering-archive-audit 对 cases/{CASE_ID} 做竣工资料材料齐全与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

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
