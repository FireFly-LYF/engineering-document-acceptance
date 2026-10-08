# -*- coding: utf-8 -*-
"""Deterministic prepare for engineering-archive-audit.

Builds inventory / heuristic classification / field extraction / checklist findings
without calling an LLM. Agent only reviews edge cases and polishes audit-report if needed.

Usage:
  python audit_prepare.py --case ../../../cases/demo-housing-mixed
  python audit_prepare.py --case <abs-or-rel-case-dir> [--rules <rules.json>]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("需要 PyMuPDF：pip install pymupdf") from exc

ROOT = Path(__file__).resolve().parents[3]  # engineering-document-acceptance
DEFAULT_RULES = (
    Path(__file__).resolve().parents[1] / "rules" / "housing-construction.json"
)

FIELD_PATTERNS = [
    ("项目名称", re.compile(r"项目名称[：:]\s*(.+)")),
    ("项目编号", re.compile(r"项目编号[：:]\s*(.+)")),
    ("建设单位", re.compile(r"建设单位[：:]\s*(.+)")),
    ("施工单位", re.compile(r"施工单位[：:]\s*(.+)")),
    ("监理单位", re.compile(r"监理单位[：:]\s*(.+)")),
    ("设计单位", re.compile(r"设计单位[：:]\s*(.+)")),
    ("工程地址", re.compile(r"工程地址[：:]\s*(.+)")),
    ("开工日期", re.compile(r"开工日期[：:]\s*(.+)")),
    ("竣工日期", re.compile(r"竣工日期[：:]\s*(.+)")),
    ("合同金额", re.compile(r"合同金额[（(]?元[）)]?[：:]\s*([0-9.]+)")),
    ("文件编号", re.compile(r"文件编号[：:]\s*(.+)")),
]

CATEGORY_KEYWORDS = [
    ("contract", ["施工合同", "监理合同", "承包合同", "委托监理"]),
    ("preparation", ["规划许可", "施工许可", "开工证"]),
    ("supervision", ["监理规划", "监理实施细则", "质量评估", "监理日志"]),
    ("construction", ["施工组织", "检验批", "分项工程", "分部工程", "隐蔽工程"]),
    ("material_test", ["复试", "检测报告", "进场报审", "试块"]),
    ("as_built_drawing", ["竣工图"]),
    ("completion_acceptance", ["竣工验收", "竣工报告", "预验收", "观感质量"]),
    ("special_acceptance", ["消防", "规划核实", "专项验收"]),
]


def read_pdf_text(path: Path, max_pages: int = 2) -> str:
    try:
        doc = fitz.open(path)
    except Exception:
        return ""
    parts: list[str] = []
    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            parts.append(page.get_text() or "")
    finally:
        doc.close()
    return "\n".join(parts)


def extract_fields(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, pat in FIELD_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        val = m.group(1).strip().splitlines()[0].strip()
        val = re.sub(r"\s+", "", val) if key == "合同金额" else val
        if val and not re.search(r"暂缺|待填写|示例|XXXX", val, re.I):
            out[key] = val
    return out


def classify(name: str, text: str) -> tuple[str, str, list[str]]:
    blob = f"{name}\n{text[:2000]}"
    hits: list[str] = []
    for cat, kws in CATEGORY_KEYWORDS:
        for kw in kws:
            if kw in blob:
                hits.append(kw)
                return cat, "medium" if kw in name else "low", hits
    return "unknown", "low", hits


def load_rules(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_files(files_dir: Path) -> list[Path]:
    if not files_dir.is_dir():
        return []
    return sorted(p for p in files_dir.rglob("*") if p.is_file())


def match_required(doc: dict, file_rows: list[dict]) -> dict:
    """Match one checklist item against files using aliases + text titles."""
    names = [doc["name"], *doc.get("aliases", [])]
    names = [n for n in names if n]
    candidates: list[dict] = []
    for row in file_rows:
        score = 0
        reasons: list[str] = []
        fname = row["filename"]
        text = row.get("text_head", "")
        for n in names:
            if n and n in fname:
                score += 5
                reasons.append(f"文件名含「{n}」")
            elif n and n in text[:800]:
                score += 3
                reasons.append(f"正文含「{n}」")
        if doc.get("category") and row.get("category") == doc["category"]:
            score += 1
            reasons.append("分类一致")
        if score > 0:
            candidates.append({**row, "match_score": score, "match_reasons": reasons})
    candidates.sort(key=lambda x: (-x["match_score"], x["filename"]))
    return {"candidates": candidates, "best": candidates[0] if candidates else None}


def is_pre_acceptance(name: str, text: str) -> bool:
    blob = name + text[:500]
    return "预验收" in blob and "竣工验收报告" in blob or (
        "预验收" in name and "竣工验收" in name
    )


def build_findings(rules: dict, file_rows: list[dict], consensus: dict) -> list[dict]:
    findings: list[dict] = []
    # file-no duplicates
    by_file_no: dict[str, list[str]] = defaultdict(list)
    for row in file_rows:
        fn = row.get("fields", {}).get("文件编号")
        if fn:
            by_file_no[fn].append(row["rel_path"])

    for doc in rules.get("required_documents", []):
        matched = match_required(doc, file_rows)
        best = matched["best"]
        code, name = doc["code"], doc["name"]
        required = bool(doc.get("required"))

        if code == "E-01":
            # special: formal completion report; pre-acceptance is similar only
            formal = []
            similar = []
            for row in file_rows:
                blob = row["filename"] + row.get("text_head", "")[:600]
                if "预验收" in blob and ("竣工验收" in blob or "验收报告" in row["filename"]):
                    similar.append(row["rel_path"])
                elif "竣工验收报告" in blob and "预验收" not in blob and "管廊" not in blob:
                    # exclude misfiled other project later
                    formal.append(row)
            # drop misfiled other project names
            formal = [
                r
                for r in formal
                if r.get("fields", {}).get("项目名称", consensus.get("锚值", {}).get("项目名称", ""))
                == consensus.get("锚值", {}).get("项目名称", r.get("fields", {}).get("项目名称", ""))
                or "滨河" not in r["filename"]
            ]
            other_project_formal = [
                r["rel_path"]
                for r in file_rows
                if "竣工验收报告" in r["filename"] + r.get("text_head", "")[:200]
                and "滨河" in r["filename"]
            ]
            if formal:
                findings.append(
                    {
                        "code": code,
                        "name": name,
                        "status": "provided",
                        "severity": "info",
                        "matched_file": formal[0]["rel_path"],
                        "evidence": formal[0].get("match_reasons", []),
                    }
                )
            else:
                findings.append(
                    {
                        "code": code,
                        "name": name,
                        "status": "missing",
                        "severity": "error",
                        "reason": "未找到本项目正式《工程竣工验收报告》；预验收不能替代",
                        "similar_files": similar,
                        "suggestion": "补充正式工程竣工验收报告",
                        "notes": doc.get("notes", ""),
                    }
                )
            continue

        if not best:
            if required:
                findings.append(
                    {
                        "code": code,
                        "name": name,
                        "status": "missing",
                        "severity": "error",
                        "reason": f"规则 {code} 必需，已检索 {len(file_rows)} 份文件未命中",
                        "suggestion": f"补充《{name}》",
                    }
                )
            else:
                findings.append(
                    {
                        "code": code,
                        "name": name,
                        "status": "missing",
                        "severity": "info",
                        "reason": "非必需项未提供",
                        "required": False,
                    }
                )
            continue

        # misfiled other project
        proj = best.get("fields", {}).get("项目名称", "")
        anchor = consensus.get("锚值", {}).get("项目名称", "")
        if anchor and proj and proj != anchor and "滨河" in best["filename"]:
            findings.append(
                {
                    "code": code,
                    "name": name,
                    "status": "suspect_duplicate_or_misfiled",
                    "severity": "warning",
                    "reason": f"命中文件疑似他项工程：{proj}",
                    "matched_file": best["rel_path"],
                    "suggestion": "移出本项目资料包或人工确认",
                }
            )
            if required:
                findings.append(
                    {
                        "code": code,
                        "name": name,
                        "status": "missing",
                        "severity": "error",
                        "reason": "仅命中他项工程文件，本项目仍缺该必需项",
                        "suggestion": f"补充本项目《{name}》",
                    }
                )
            continue

        findings.append(
            {
                "code": code,
                "name": name,
                "status": "provided",
                "severity": "info",
                "matched_file": best["rel_path"],
                "evidence": best.get("match_reasons", []),
                "confidence": "high" if best["match_score"] >= 5 else "medium",
            }
        )

    # explicit misfiled files
    for row in file_rows:
        if "99-错传" in row["rel_path"].replace("\\", "/") or "滨河" in row["filename"]:
            findings.append(
                {
                    "code": "MISFILE",
                    "name": row["filename"],
                    "status": "suspect_duplicate_or_misfiled",
                    "severity": "warning",
                    "reason": "文件名/路径显示为他项工程或错传目录",
                    "matched_file": row["rel_path"],
                    "suggestion": "移出本包并核对归属",
                }
            )

    # duplicates by 文件编号
    for no, paths in by_file_no.items():
        if len(paths) >= 2:
            findings.append(
                {
                    "code": "DUP",
                    "name": f"文件编号重复 {no}",
                    "status": "suspect_duplicate_or_misfiled",
                    "severity": "warning",
                    "reason": "同一文件编号出现在多份文件",
                    "similar_files": paths,
                    "suggestion": "确认是否重复归档",
                }
            )

    # field conflicts
    for field, info in consensus.get("冲突", {}).items():
        findings.append(
            {
                "code": "FIELD",
                "name": f"字段冲突:{field}",
                "status": "needs_human_review",
                "severity": "warning",
                "reason": f"多文件取值不一致: {info.get('values')}",
                "suggestion": "以合同/manifest 锚值为准并人工确认",
                "field": field,
            }
        )

    return findings


def build_consensus(manifest: dict, fields_by_file: dict[str, dict]) -> dict:
    # 文件编号天然每份不同，不参与跨文件冲突
    skip_conflict_fields = {"文件编号"}
    buckets: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for rel, flds in fields_by_file.items():
        for k, v in flds.items():
            if k in skip_conflict_fields:
                continue
            buckets[k][v].append(rel)

    anchor = {
        "项目名称": manifest.get("project_name"),
        "项目编号": manifest.get("project_code"),
        "建设单位": manifest.get("owner"),
        "施工单位": manifest.get("contractor"),
        "监理单位": manifest.get("supervisor"),
        "设计单位": manifest.get("designer"),
        "工程地址": manifest.get("address"),
        "开工日期": manifest.get("start_date"),
        "竣工日期": manifest.get("finish_date"),
        "合同金额": manifest.get("contract_amount"),
    }
    anchor = {k: v for k, v in anchor.items() if v}

    conflicts = {}
    for field, valmap in buckets.items():
        if len(valmap) > 1:
            conflicts[field] = {
                "values": {val: paths for val, paths in valmap.items()},
            }

    return {
        "锚值": anchor,
        "冲突": conflicts,
        "conflicts": [
            {"field": f, "values": info["values"]} for f, info in conflicts.items()
        ],
    }


def write_audit_report(
    path: Path,
    manifest: dict,
    rules: dict,
    inventory: dict,
    findings: list[dict],
) -> None:
    counts = defaultdict(int)
    for f in findings:
        counts[f.get("status", "other")] += 1
    lines = [
        "# 竣工资料完整性与一致性核查报告（脚本初稿）",
        "",
        f"- 项目：{manifest.get('project_name', '')} / {manifest.get('project_code', '')}",
        f"- 规则模板：{rules.get('profile_id')} · {rules.get('project_type')}",
        f"- 已检索文件：{inventory.get('count', 0)} 份",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat()}",
        f"- 数据说明：合成演示或用户提供材料；本报告由确定性脚本生成，可供 Agent 润色",
        "",
        "## 统计",
        "",
        f"- provided: {counts['provided']}",
        f"- missing: {counts['missing']}",
        f"- suspect_duplicate_or_misfiled: {counts['suspect_duplicate_or_misfiled']}",
        f"- needs_human_review: {counts['needs_human_review']}",
        "",
        "## 问题与证据",
        "",
    ]
    for f in findings:
        if f.get("status") == "provided":
            continue
        lines.append(f"### [{f.get('code')}] {f.get('name')} — {f.get('status')}")
        lines.append(f"- **依据**: {rules.get('project_type')} / {f.get('code')}")
        lines.append(f"- **已检索文件**: 共 {inventory.get('count', 0)} 份")
        if f.get("similar_files"):
            lines.append(
                "- **相似文件**: "
                + "；".join(Path(x).name for x in f["similar_files"])
            )
        if f.get("matched_file"):
            lines.append(f"- **相关文件**: {Path(f['matched_file']).name}")
        lines.append(f"- **判断**: {f.get('reason', '')}")
        lines.append(f"- **建议**: {f.get('suggestion', '')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_agent_brief(path: Path, findings: list[dict], consensus: dict) -> None:
    important = [
        f
        for f in findings
        if f.get("status")
        in {"missing", "suspect_duplicate_or_misfiled", "needs_human_review"}
    ]
    lines = [
        "# 核查 Agent 简报（优先读此文件，勿通读全部 PDF）",
        "",
        "## 请你做的事",
        "1. 抽查 findings 中 needs_human_review / 低置信分类是否合理",
        "2. 如需，润色 audit-report.md 措辞（不要改结论方向）",
        "3. 若用户要文书：再启用 engineering-doc-generator，先 prepare 再写正文",
        "",
        "## 重要 findings",
        "",
    ]
    for f in important:
        lines.append(
            f"- [{f.get('status')}] {f.get('code')} {f.get('name')}: {f.get('reason', '')}"
        )
    lines.append("")
    lines.append("## 字段冲突")
    lines.append(json.dumps(consensus.get("conflicts", []), ensure_ascii=False, indent=2))
    path.write_text("\n".join(lines), encoding="utf-8")


def run(case_dir: Path, rules_path: Path) -> Path:
    case_dir = case_dir.resolve()
    files_dir = case_dir / "files"
    work = case_dir / "_work"
    work.mkdir(parents=True, exist_ok=True)

    manifest_path = case_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    rules = load_rules(rules_path)

    file_rows: list[dict] = []
    fields_by_file: dict[str, dict] = {}
    classification: list[dict] = []

    for fp in iter_files(files_dir):
        rel = fp.relative_to(case_dir).as_posix()
        text = read_pdf_text(fp) if fp.suffix.lower() == ".pdf" else ""
        fields = extract_fields(text)
        cat, conf, hits = classify(fp.name, text)
        row = {
            "path": rel,
            "rel_path": rel,
            "filename": fp.name,
            "ext": fp.suffix.lower(),
            "size_bytes": fp.stat().st_size,
            "category": cat,
            "confidence": conf,
            "evidence": hits,
            "fields": fields,
            "text_head": text[:1200],
        }
        file_rows.append(row)
        fields_by_file[rel] = fields
        classification.append(
            {
                "path": rel,
                "category": cat,
                "confidence": conf,
                "evidence": hits,
            }
        )

    inventory = {
        "project_id": manifest.get("project_id") or case_dir.name,
        "count": len(file_rows),
        "files": [
            {
                "path": r["path"],
                "filename": r["filename"],
                "ext": r["ext"],
                "size_bytes": r["size_bytes"],
            }
            for r in file_rows
        ],
        "generated_by": "audit_prepare.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    consensus = build_consensus(manifest, fields_by_file)
    findings = build_findings(rules, file_rows, consensus)

    (work / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work / "classification.json").write_text(
        json.dumps({"items": classification}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (work / "fields.json").write_text(
        json.dumps(fields_by_file, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work / "field_consensus.json").write_text(
        json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work / "findings.json").write_text(
        json.dumps(
            {
                "items": findings,
                "generated_by": "audit_prepare.py",
                "rules_profile": rules.get("profile_id"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_audit_report(work / "audit-report.md", manifest, rules, inventory, findings)
    write_agent_brief(work / "agent-brief.md", findings, consensus)

    print(f"[audit_prepare] case={case_dir}")
    print(f"[audit_prepare] files={len(file_rows)} findings={len(findings)} -> {work}")
    return work


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="cases/<project-id> directory")
    ap.add_argument("--rules", default=str(DEFAULT_RULES), help="rules json path")
    args = ap.parse_args()
    case = Path(args.case)
    if not case.is_absolute():
        # resolve relative to CWD first, then workspace root
        cand = Path.cwd() / case
        case = cand if cand.exists() else (ROOT / case)
    rules = Path(args.rules)
    if not rules.is_absolute():
        rules = (Path.cwd() / rules).resolve()
    if not case.exists():
        raise SystemExit(f"case 不存在: {case}")
    if not rules.exists():
        raise SystemExit(f"rules 不存在: {rules}")
    run(case, rules)


if __name__ == "__main__":
    main()
