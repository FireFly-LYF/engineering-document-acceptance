# -*- coding: utf-8 -*-
"""Near-miss housing demo pack with heterogeneous form layouts."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pdf_forms import (  # noqa: E402
    make_asbuilt_drawing_note,
    make_completion_pack,
    make_construction_contract,
    make_construction_permit,
    make_division_record,
    make_inspection_batch,
    make_planning_permit,
    make_planning_verify_cert,
    make_quality_assessment,
    make_subitem_record,
    make_supervision_contract,
    make_tech_document,
    make_unreadable,
)

CASE_ID = "demo-housing-near-miss"
CASE = ROOT / "cases" / CASE_ID
FILES = CASE / "files"

P = {
    "项目名称": "云港新区示范中学实验楼加固改造工程",
    "项目编号": "YG-XFZX-SY-2024-021",
    "建设单位": "云港市教育发展建设中心",
    "施工单位": "江海建工集团有限公司",
    "监理单位": "远洲建设监理有限公司",
    "设计单位": "青城建筑设计研究院有限公司",
    "工程地址": "云港市海州区学府路92号",
    "开工日期": "2024-05-08",
    "竣工日期": "2025-12-15",
    "合同金额（元）": "42800000",
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
    "contract_amount_cn": "肆仟贰佰捌拾万元整",
}

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
    "文件编号": "YG-XFZX-HT-2024-001",
}
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
    "文件编号": "XFL-XX-JGYS-2024-01",
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
        meta=meta(文件编号="建规证字〔2023〕第156号"),
        body_lines=["核准建设规模：实验楼加固约6400平方米。"],
    )
    make_construction_permit(
        FILES / "01-准备/A-02-建筑工程施工许可证.pdf",
        meta=meta(文件编号="施许字〔2024〕第078号", 开工日期="2024-04-01"),
        body_lines=[
            "建设资金已落实，施工图审查合格，具备开工条件。",
            "合同工期按证载开工日期至竣工日期执行。",
        ],
        scan_style=True,
        scale_note="加固约6400㎡",
    )
    make_construction_contract(
        FILES / "01-准备/A-03-建设工程施工合同.pdf",
        meta=meta(文件编号="YG-XFZX-SY-HT-2024-001"),
        body_lines=[f"合同工期：{P['开工日期']} 至 {P['竣工日期']}。"],
        amount_cn=P_FLAT["contract_amount_cn"],
    )
    make_supervision_contract(
        FILES / "01-准备/A-04-建设工程委托监理合同.pdf",
        meta=meta(文件编号="YG-XFZX-SY-JLHT-2024-001"),
        body_lines=["针对加固改造明确旁站范围。"],
    )

    make_tech_document(
        FILES / "02-监理/B-01-监理规划.pdf",
        title="监理规划",
        meta=meta(文件编号="JL-GH-SY-2024-01"),
        org_header=P["监理单位"],
        chapters=[
            ("1 工程概况", [f"项目名称：{P['项目名称']}"]),
            ("2 监理工作内容", ["针对加固改造工程明确旁站与平行检验制度。"]),
        ],
    )
    make_quality_assessment(
        FILES / "02-监理/B-03-工程质量评估报告.pdf",
        meta=meta(文件编号="JL-PG-SY-2025-12"),
        body_lines=["加固部位质量评估结论：同意竣工验收。"],
    )

    make_tech_document(
        FILES / "03-施工/C-01-施工组织设计.pdf",
        title="施工组织设计",
        meta=meta(文件编号="SG-ZZ-SY-2024-01"),
        org_header=P["施工单位"],
        chapters=[
            ("1 编制说明", [f"项目编号：{P['项目编号']}"]),
            ("2 施工部署", ["采用分段加固、夜间浇筑控制裂缝。"]),
        ],
    )
    make_inspection_batch(
        FILES / "03-施工/C-02-检验批质量验收记录-混凝土加固-01.pdf",
        meta=meta(文件编号="JYP-JG-2024-021"),
        batch_name="混凝土加固",
        file_no="JYP-JG-2024-021",
        division="主体结构",
        subitem="混凝土加固",
        location="实验楼二层梁",
        capacity="加固梁段约18m",
        basis_sg="加固专项方案",
        basis_ys="GB50367 / GB50204",
        major_rows=[
            ("加固材料性能", "复试", "碳纤维/植筋胶复试合格", "合格"),
            ("截面尺寸与植筋深度", "10/10", "符合设计", "合格"),
        ],
        general_rows=[("外观质量", "全数", "无空鼓脱落", "合格")],
    )
    make_subitem_record(
        FILES / "03-施工/C-03-分项工程质量验收记录-混凝土加固.pdf",
        meta=meta(文件编号="FX-JG-2024-01"),
        title="分项工程质量验收记录",
        file_no="FX-JG-2024-01",
        division="主体结构",
        subitem="混凝土加固",
        batch_count="1",
        conclusion="合格",
    )
    make_division_record(
        FILES / "03-施工/C-04-分部工程质量验收记录-主体结构.pdf",
        meta=meta(文件编号="FB-ZT-SY-2025-01"),
        title="分部工程质量验收记录",
        file_no="FB-ZT-SY-2025-01",
        division="主体结构",
        subitem_count="4",
        conclusion="合格",
    )

    make_unreadable(FILES / "04-检测/扫描件-页面损坏.pdf")

    make_completion_pack(
        FILES / "05-验收/工程竣工预验收报告.pdf",
        title="工程竣工预验收报告",
        meta=meta(文件编号="YS-SY-2025-12-01"),
        body_lines=[
            "建设单位组织施工、监理等单位于2025年12月1日进行竣工预验收。",
            "查验加固分部验收记录、质量控制资料及主要使用功能抽查情况。",
            "预验收意见：局部整改完成后组织正式竣工验收。",
        ],
        form_code="预验收记录表",
        conclusion="预验收结论：基本具备正式竣工验收条件",
        report_date="2025年12月1日",
        scan_style=True,
        five_party=False,
    )
    make_completion_pack(
        FILES / "05-验收/E-02-施工单位工程竣工报告.pdf",
        title="施工单位工程竣工报告",
        meta=meta(文件编号="SG-JG-SY-2025-01"),
        body_lines=[
            "本工程加固改造内容已按设计文件及合同约定完成。",
            "工程质量控制资料完整，安全和主要使用功能检验符合要求。",
            "施工单位自评工程质量合格，申请组织竣工验收。",
        ],
        form_code="施工单位竣工报告",
        conclusion="本工程达到竣工验收条件，申请组织竣工验收",
        report_date="2025年12月10日",
        five_party=False,
    )
    make_completion_pack(
        FILES / "05-验收/E-03-设计单位工程质量检查报告.pdf",
        title="设计单位工程质量检查报告",
        meta=meta(文件编号="SJ-JC-SY-2025-01"),
        body_lines=[
            "设计单位对加固部位实体与加固设计文件符合性进行现场检查。",
            "检查意见：施工质量符合加固设计文件要求，同意竣工验收。",
        ],
        form_code="设计单位质量检查报告",
        conclusion="同意竣工验收",
        report_date="2025年12月10日",
        five_party=False,
    )
    make_asbuilt_drawing_note(
        FILES / "06-竣工图/F-01-结构竣工图说明.pdf",
        meta=meta(文件编号="JG-TZ-SY-2025"),
        specialty="结构",
        drawing_nos="结竣-SY-01 至 结竣-SY-12",
        body_lines=["结构加固竣工图已按变更更新。"],
        scan_style=True,
    )
    make_planning_verify_cert(
        FILES / "07-专项/G-02-规划核实证明.pdf",
        meta=meta(文件编号="GHHS-SY-2025-021"),
        body_lines=["经现场核实，本工程平面位置、建筑规模符合规划许可要求，准予规划核实合格。"],
    )

    make_construction_contract(
        FILES / "01-准备/建设工程施工合同-教学楼单体.pdf",
        meta=NEAR_CAMPUS,
        body_lines=[
            "工程质量标准：合格。",
            "承包范围：教学楼改扩建土建、装饰及安装工程。",
        ],
        amount_cn="捌仟陆佰伍拾万元整",
    )
    make_completion_pack(
        FILES / "05-验收/工程竣工验收报告-学府路小学.pdf",
        title="工程竣工验收报告",
        meta=NEAR_ROAD,
        body_lines=[
            "本工程已完成各分部工程施工，材料均有出厂质量证明及见证送检报告，检测结果合格。",
            "质量控制资料齐全，安全和主要使用功能检验符合要求，观感质量综合评价为好。",
            "综合评定：工程质量合格，一致同意验收。",
        ],
        form_code="GD-E1-914",
        conclusion="验收合格",
        report_date="2024年7月8日",
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
        "data_note": "近邻混淆演示包；文种异构版式参考公开空白样表与 GB50300 附录；非真实档案。",
        "file_count": len(pdfs),
        "file_format": "pdf",
        "focus": ["near_miss_misfile", "start_date_conflict", "missing_material_test", "unreadable_scan"],
        "form_reference": [
            "reference/public-pdfs/gb50300-2013-acceptance-standard.pdf",
            "reference/public-pdfs/acceptance-check-forms-unified.pdf",
            "reference/public-pdfs/construction-permit-sample-sd.pdf",
            "reference/public-pdfs/construction-contract-gf2017.pdf",
            "reference/public-pdfs/unit-completion-acceptance-report.pdf",
        ],
    }
    (CASE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ground_truth = {
        "project_id": CASE_ID,
        "rules_profile": "housing-construction",
        "scoring_notes": {
            "contrast_with": "demo-housing-mixed",
            "difference": "本包侧重近邻工程名/编号混淆；另测开工日期冲突、缺材料检测、不可读扫描",
            "misfiled_excluded_from_presence": "他项文件不得计入本项目材料齐全 provided；小学正式验收不得计为本项目 E-01",
            "field_conflicts_in_project_only": "仅统计本工程真冲突；他项级联不得计为多条 FIELD",
            "expected_field_conflict_count": 1,
            "optional_codes": ["B-02", "G-02"],
            "no_duplicate_file_no_test": "本包不测同编号重复（见 demo-housing-mixed）",
            "form_style_note": "文种异构版式 + GB50300 附录；仍为合成数据",
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
                {"code": "G-01", "name": "消防验收意见或备案凭证", "reason": "包内无消防验收/备案类文件"},
            ],
            "field_conflicts": [
                {
                    "field": "开工日期",
                    "canonical": P_FLAT["start_date"],
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
                "A-01", "A-02", "A-03", "A-04", "B-01", "B-03", "C-01", "C-02",
                "C-03", "C-04", "E-02", "E-03", "F-01", "G-02",
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
    prompt = f"""请使用 engineering-archive-audit 对 cases/{CASE_ID} 做竣工资料材料齐全与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

本包重点：近邻工程混淆（同校区教学楼、同学府路小学）、缺材料检测、预验收不可替代正式验收、本工程开工日期冲突、不可读扫描页。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。
文书勿把近邻他项写成「本工程已提供正式竣工验收报告」；不可读页保留读取不足，不判为已材料齐全。
"""
    (CASE / "TEST_PROMPT.txt").write_text(prompt.strip() + "\n", encoding="utf-8")
    print(f"Generated {CASE}")
    print(f"pdf_count={len(pdfs)}")
    for rel in pdfs:
        print(" ", rel)


if __name__ == "__main__":
    main()
