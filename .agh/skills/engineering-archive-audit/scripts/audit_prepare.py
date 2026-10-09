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


def short_names(paths: list[str], limit: int = 3) -> str:
    names = [Path(p).name for p in paths[:limit]]
    text = "、".join(names)
    extra = len(paths) - len(names)
    if extra > 0:
        text += f" 等共{len(paths)}份"
    return text


def format_value_map(valmap: dict[str, list[str]], limit: int = 3) -> str:
    parts = []
    for val, paths in valmap.items():
        parts.append(f"「{val}」← {short_names(paths, limit)}")
    return "；".join(parts)


def anchor_from_manifest(manifest: dict) -> dict[str, str]:
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
    return {k: str(v) for k, v in anchor.items() if v}


def is_misfiled_row(row: dict, anchor_name: str) -> bool:
    """Other-project materials: path label, filename cue, or project_name ≠ anchor."""
    rel = row["rel_path"].replace("\\", "/")
    fname = row["filename"]
    proj = (row.get("fields") or {}).get("项目名称", "")
    if "错传" in rel or "错传" in fname:
        return True
    if anchor_name and proj and proj != anchor_name:
        return True
    if anchor_name and "滨河" not in anchor_name and "滨河" in fname:
        return True
    return False


def mark_misfiled(file_rows: list[dict], anchor_name: str) -> list[dict]:
    for row in file_rows:
        row["misfiled"] = is_misfiled_row(row, anchor_name)
    return file_rows


def in_project_rows(file_rows: list[dict]) -> list[dict]:
    return [r for r in file_rows if not r.get("misfiled")]


def build_findings(rules: dict, file_rows: list[dict], consensus: dict) -> list[dict]:
    findings: list[dict] = []
    target_rows = in_project_rows(file_rows)
    misfiled_rows = [r for r in file_rows if r.get("misfiled")]

    # file-no duplicates among in-project files only
    by_file_no: dict[str, list[str]] = defaultdict(list)
    for row in target_rows:
        fn = row.get("fields", {}).get("文件编号")
        if fn:
            by_file_no[fn].append(row["rel_path"])

    for doc in rules.get("required_documents", []):
        matched = match_required(doc, target_rows)
        best = matched["best"]
        code, name = doc["code"], doc["name"]
        required = bool(doc.get("required"))

        if code == "E-01":
            formal = []
            similar = []
            for row in target_rows:
                blob = row["filename"] + row.get("text_head", "")[:600]
                if "预验收" in blob and ("竣工验收" in blob or "验收报告" in row["filename"] or "预验收" in row["filename"]):
                    similar.append(row["rel_path"])
                elif "竣工验收报告" in blob and "预验收" not in blob:
                    formal.append(row)
            if formal:
                findings.append(
                    {
                        "code": code,
                        "name": name,
                        "status": "provided",
                        "severity": "info",
                        "matched_file": formal[0]["rel_path"],
                        "evidence": ["正文/文件名命中正式竣工验收报告"],
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
                        "reason": f"规则 {code} 必需，已检索本项目 {len(target_rows)} 份文件未命中",
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

    # explicit misfiled files (one finding each)
    for row in misfiled_rows:
        proj = (row.get("fields") or {}).get("项目名称") or "他项工程"
        findings.append(
            {
                "code": "MISFILE",
                "name": row["filename"],
                "status": "suspect_duplicate_or_misfiled",
                "severity": "warning",
                "reason": f"文载项目为「{proj}」，与本项目不符，按错传处理；不参与齐套与字段共识",
                "matched_file": row["rel_path"],
                "suggestion": "移出本包并核对归属",
            }
        )

    # unreadable / empty-text PDFs among in-project files
    for row in target_rows:
        if not row.get("unreadable"):
            continue
        findings.append(
            {
                "code": "UNREADABLE",
                "name": row["filename"],
                "status": "needs_human_review",
                "severity": "warning",
                "reason": "未能抽取可读正文（空文本层或损坏扫描），读取不足，不能据此认定已提供对应资料",
                "matched_file": row["rel_path"],
                "suggestion": "补传可检索文本版或清晰扫描后重跑核查",
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
                    "reason": f"同一文件编号出现在多份本项目文件：{short_names(paths)}",
                    "similar_files": paths,
                    "suggestion": "确认是否重复归档",
                }
            )

    # in-project field conflicts only (misfiled already excluded from consensus)
    for field, info in consensus.get("冲突", {}).items():
        findings.append(
            {
                "code": "FIELD",
                "name": f"字段冲突:{field}",
                "status": "needs_human_review",
                "severity": "warning",
                "reason": f"本项目多文件取值不一致：{format_value_map(info.get('values', {}))}",
                "suggestion": "以合同/manifest 锚值为准并人工确认",
                "field": field,
                "scope": "in_project",
            }
        )

    return findings


def build_consensus(
    manifest: dict,
    fields_by_file: dict[str, dict],
    misfiled_paths: set[str] | None = None,
) -> dict:
    # 文件编号天然每份不同；错传文件不参与本工程字段共识
    skip_conflict_fields = {"文件编号"}
    misfiled_paths = misfiled_paths or set()
    buckets: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for rel, flds in fields_by_file.items():
        if rel in misfiled_paths:
            continue
        for k, v in flds.items():
            if k in skip_conflict_fields:
                continue
            if not v or v in {"（本文件未载明）", "暂缺", "待填写"}:
                continue
            buckets[k][v].append(rel)

    anchor = anchor_from_manifest(manifest)

    conflicts = {}
    for field, valmap in buckets.items():
        if len(valmap) > 1:
            conflicts[field] = {
                "values": {val: paths for val, paths in valmap.items()},
                "summary": format_value_map(valmap),
            }

    return {
        "锚值": anchor,
        "冲突": conflicts,
        "conflicts": [
            {
                "field": f,
                "values": {
                    val: [Path(p).name for p in paths[:3]]
                    + ([f"…共{len(paths)}份"] if len(paths) > 3 else [])
                    for val, paths in info["values"].items()
                },
                "summary": info.get("summary") or format_value_map(info["values"]),
                "scope": "in_project",
            }
            for f, info in conflicts.items()
        ],
        "excluded_misfiled": sorted(misfiled_paths),
        "note": "错传/他项文件已排除出字段共识；级联差异不计入本工程 FIELD",
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
        f"- 已提供：{counts['provided']}",
        f"- 缺失：{counts['missing']}",
        f"- 疑似错传或重复：{counts['suspect_duplicate_or_misfiled']}",
        f"- 需人工复核（本工程字段冲突）：{counts['needs_human_review']}",
        "",
        "## 问题与证据",
        "",
    ]
    for f in findings:
        if f.get("status") == "provided":
            continue
        lines.append(f"### [{f.get('code')}] {f.get('name')} — {f.get('status')}")
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


def write_audit_brief(path: Path, findings: list[dict], consensus: dict) -> None:
    """Audit-oriented brief. Document drafting brief is written by doc-generator prepare."""
    important = [
        f
        for f in findings
        if f.get("status")
        in {"missing", "suspect_duplicate_or_misfiled", "needs_human_review"}
    ]
    counts = defaultdict(int)
    for f in findings:
        counts[f.get("status", "other")] += 1
    lines = [
        "# 核查 Agent 简报（优先读此文件，勿通读全部 PDF）",
        "",
        "## 请你做的事",
        "1. 抽查本工程字段冲突与错传判定是否合理（优先看 FIELD / MISFILE）",
        "2. 如需，润色 audit-report.md 措辞（不要改结论方向）",
        "3. 文书请启用 engineering-doc-generator：prepare → 写正文.md → build",
        "4. 情况说明只写缺失、错传、重复、本工程真冲突；勿把错传级联字段逐条夸大",
        "",
        "## 四态统计",
        f"- 已提供 {counts['provided']}；缺失 {counts['missing']}；"
        f"错传/重复 {counts['suspect_duplicate_or_misfiled']}；"
        f"本工程字段复核 {counts['needs_human_review']}",
        "",
        "## 重要 findings（短文件名）",
        "",
    ]
    for f in important:
        extra = ""
        if f.get("similar_files"):
            extra = " | 相似: " + "；".join(Path(x).name for x in f["similar_files"])
        elif f.get("matched_file"):
            extra = " | 文件: " + Path(f["matched_file"]).name
        lines.append(
            f"- [{f.get('status')}] {f.get('code')} {f.get('name')}: {f.get('reason', '')}{extra}"
        )
    lines.append("")
    lines.append("## 本工程字段冲突（已排除错传）")
    conflicts = consensus.get("conflicts") or []
    if not conflicts:
        lines.append("- 无")
    else:
        for c in conflicts:
            lines.append(f"- {c.get('field')}: {c.get('summary') or c.get('values')}")
    if consensus.get("note"):
        lines.append("")
        lines.append(f"> {consensus['note']}")
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
        text_stripped = text.strip()
        unreadable = fp.suffix.lower() == ".pdf" and len(text_stripped) < 20
        fields = extract_fields(text)
        cat, conf, hits = classify(fp.name, text)
        if unreadable:
            cat, conf = "unknown", "low"
            hits = hits + ["no_extractable_text"]
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
            "unreadable": unreadable,
        }
        file_rows.append(row)
        fields_by_file[rel] = fields
        classification.append(
            {
                "path": rel,
                "category": cat,
                "confidence": conf,
                "evidence": hits,
                "unreadable": unreadable,
            }
        )

    anchor = anchor_from_manifest(manifest)
    mark_misfiled(file_rows, anchor.get("项目名称", ""))
    misfiled_paths = {r["rel_path"] for r in file_rows if r.get("misfiled")}

    inventory = {
        "project_id": manifest.get("project_id") or case_dir.name,
        "count": len(file_rows),
        "files": [
            {
                "path": r["path"],
                "filename": r["filename"],
                "ext": r["ext"],
                "size_bytes": r["size_bytes"],
                "misfiled": bool(r.get("misfiled")),
                "unreadable": bool(r.get("unreadable")),
            }
            for r in file_rows
        ],
        "generated_by": "audit_prepare.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    consensus = build_consensus(manifest, fields_by_file, misfiled_paths)
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
    write_audit_brief(work / "audit-brief.md", findings, consensus)

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
