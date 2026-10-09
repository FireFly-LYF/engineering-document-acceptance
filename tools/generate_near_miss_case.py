# -*- coding: utf-8 -*-
"""Near-miss housing demo pack with GB50300-style forms."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pdf_forms import (  # noqa: E402
    make_division_record,
    make_inspection_batch,
    make_official_report,
    make_subitem_record,
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

    make_official_report(
        FILES / "01-准备/A-01-建设工程规划许可证.pdf",
        title="建设工程规划许可证",
        meta=meta(文件编号="建规证字〔2023〕第156号"),
        body_lines=["核准建设规模：实验楼加固约6400平方米。"],
        doc_kind="工程准备",
    )
    make_official_report(
        FILES / "01-准备/A-02-建筑工程施工许可证.pdf",
        title="建筑工程施工许可证",
        meta=meta(文件编号="施许字〔2024〕第078号", 开工日期="2024-04-01"),
        body_lines=[
            "许可证编号：施许字〔2024〕第078号。",
            "备注：证载开工日期与合同/manifest 不一致，用于本工程字段冲突测试。",
        ],
        scan_style=True,
        doc_kind="工程准备",
    )
    make_official_report(
        FILES / "01-准备/A-03-建设工程施工合同.pdf",
        title="建设工程施工合同",
        meta=meta(文件编号="YG-XFZX-SY-HT-2024-001"),
        body_lines=[
            f"发包人：{P['建设单位']}",
            f"承包人：{P['施工单位']}",
            f"签约合同价：{P['合同金额（元）']} 元（{P_FLAT['contract_amount_cn']}）。",
            f"合同工期：{P['开工日期']} 至 {P['竣工日期']}。",
        ],
        doc_kind="合同",
    )
    make_official_report(
        FILES / "01-准备/A-04-建设工程委托监理合同.pdf",
        title="建设工程委托监理合同",
        meta=meta(文件编号="YG-XFZX-SY-JLHT-2024-001"),
        body_lines=[f"委托人：{P['建设单位']}", f"监理人：{P['监理单位']}"],
        doc_kind="合同",
    )

    make_official_report(
        FILES / "02-监理/B-01-监理规划.pdf",
        title="监理规划",
        meta=meta(文件编号="JL-GH-SY-2024-01"),
        body_lines=["针对加固改造工程明确旁站与平行检验制度。"],
        doc_kind="监理文件",
    )
    make_official_report(
        FILES / "02-监理/B-03-工程质量评估报告.pdf",
        title="工程质量评估报告",
        meta=meta(文件编号="JL-PG-SY-2025-12"),
        body_lines=["加固部位质量评估结论：同意竣工验收。"],
        doc_kind="监理评估",
    )

    make_official_report(
        FILES / "03-施工/C-01-施工组织设计.pdf",
        title="施工组织设计",
        meta=meta(文件编号="SG-ZZ-SY-2024-01"),
        body_lines=["采用分段加固、夜间浇筑控制裂缝。"],
        doc_kind="施工文件",
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

    make_official_report(
        FILES / "05-验收/工程竣工预验收报告.pdf",
        title="工程竣工预验收报告",
        meta=meta(文件编号="YS-SY-2025-12-01"),
        body_lines=[
            "预验收时间：2025-12-01。",
            "预验收意见：整改完成后组织正式验收。",
            "注意：本文为预验收，不能替代《工程竣工验收报告》。",
        ],
        scan_style=True,
        doc_kind="竣工验收",
    )
    make_official_report(
        FILES / "05-验收/E-02-施工单位工程竣工报告.pdf",
        title="施工单位工程竣工报告",
        meta=meta(文件编号="SG-JG-SY-2025-01"),
        body_lines=["加固改造已按合同完成，申请竣工验收。"],
        doc_kind="竣工验收",
    )
    make_official_report(
        FILES / "05-验收/E-03-设计单位工程质量检查报告.pdf",
        title="设计单位工程质量检查报告",
        meta=meta(文件编号="SJ-JC-SY-2025-01"),
        body_lines=["设计单位检查认为符合加固设计文件要求。"],
        doc_kind="竣工验收",
    )
    make_official_report(
        FILES / "06-竣工图/F-01-结构竣工图说明.pdf",
        title="工程竣工图（结构）说明",
        meta=meta(文件编号="JG-TZ-SY-2025"),
        body_lines=["结构加固竣工图已按变更更新。", "图纸编号：结竣-SY-01 至 结竣-SY-12。"],
        scan_style=True,
        doc_kind="竣工图",
    )
    make_official_report(
        FILES / "07-专项/G-02-规划核实证明.pdf",
        title="建设工程规划核实合格证",
        meta=meta(文件编号="GHHS-SY-2025-021"),
        body_lines=["核实结论：符合规划许可要求（合成）。"],
        doc_kind="专项",
    )

    make_official_report(
        FILES / "01-准备/建设工程施工合同-教学楼单体.pdf",
        title="建设工程施工合同",
        meta=NEAR_CAMPUS,
        body_lines=[
            "本文件属于同校区另一单体（教学楼改扩建），误归入实验楼加固资料包。",
            "请按项目名称/编号区分，不得计入本实验楼齐套。",
        ],
        form_hint="近邻：同校区、同建设方、编号前缀相近",
        doc_kind="合同",
    )
    make_official_report(
        FILES / "05-验收/工程竣工验收报告-学府路小学.pdf",
        title="工程竣工验收报告",
        meta=NEAR_ROAD,
        body_lines=[
            "云港新区学府路小学教学楼工程竣工验收报告。",
            "同学府路、同学段近似工程，不能计入本实验楼正式验收（E-01）。",
        ],
        form_hint="近邻：同学府路小学正式验收，文件名含竣工验收报告",
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
        "data_note": "近邻混淆演示包；表式参考 GB50300 附录与公开空白样表；非真实档案。",
        "file_count": len(pdfs),
        "file_format": "pdf",
        "focus": ["near_miss_misfile", "start_date_conflict", "missing_material_test", "unreadable_scan"],
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
            "contrast_with": "demo-housing-mixed",
            "difference": "本包侧重近邻工程名/编号混淆；另测开工日期冲突、缺材料检测、不可读扫描",
            "misfiled_excluded_from_presence": "他项文件不得计入本项目齐套 provided；小学正式验收不得计为本项目 E-01",
            "field_conflicts_in_project_only": "仅统计本工程真冲突；他项级联不得计为多条 FIELD",
            "expected_field_conflict_count": 1,
            "optional_codes": ["B-02", "G-02"],
            "no_duplicate_file_no_test": "本包不测同编号重复（见 demo-housing-mixed）",
            "form_style_note": "验收类表式仿 GB50300 附录；仍为合成数据",
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
    prompt = f"""请使用 engineering-archive-audit 对 cases/{CASE_ID} 做竣工资料齐套与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。

本包重点：近邻工程混淆（同校区教学楼、同学府路小学）、缺材料检测、预验收不可替代正式验收、本工程开工日期冲突、不可读扫描页。

核查完成后，使用 engineering-doc-generator 生成《竣工资料核查情况说明》并导出 Word。
文书勿把近邻他项写成「本工程已提供正式竣工验收报告」；不可读页保留读取不足，不判为已齐套。
"""
    (CASE / "TEST_PROMPT.txt").write_text(prompt.strip() + "\n", encoding="utf-8")
    print(f"Generated {CASE}")
    print(f"pdf_count={len(pdfs)}")
    for rel in pdfs:
        print(" ", rel)


if __name__ == "__main__":
    main()
