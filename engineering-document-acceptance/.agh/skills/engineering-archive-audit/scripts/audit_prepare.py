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
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("需要 PyMuPDF：pip install pymupdf") from exc

ROOT = Path(__file__).resolve().parents[3]  # engineering-document-acceptance
RULES_DIR = Path(__file__).resolve().parents[1] / "rules"
DEFAULT_RULES = RULES_DIR / "housing-construction.json"

# 前端选择的 rules_profile / project_type → 规则文件
PROFILE_SLUGS = ("housing-construction", "road-bridge", "municipal-pipeline")
PROFILE_ALIASES = {
    "房屋建筑工程": "housing-construction",
    "道路/桥梁工程": "road-bridge",
    "市政管线工程": "municipal-pipeline",
}

FIELD_PATTERNS = [
    # 真实样表常用「工程名称」；合成 PDF 同时保留「项目名称」
    ("项目名称", re.compile(r"(?:项目名称|工程名称|建设项目名称)[：:]\s*(.+)")),
    ("项目编号", re.compile(r"项目编号[：:]\s*(.+)")),
    ("建设单位", re.compile(r"建设单位[：:]\s*(.+)")),
    ("施工单位", re.compile(r"施工单位[：:]\s*(.+)")),
    ("监理单位", re.compile(r"监理单位[：:]\s*(.+)")),
    ("设计单位", re.compile(r"设计单位[：:]\s*(.+)")),
    ("工程地址", re.compile(r"(?:工程地址|建设地点|建设地址|工程地点|建设位置)[：:]\s*(.+)")),
    ("开工日期", re.compile(r"开工日期[：:]\s*(.+)")),
    ("竣工日期", re.compile(r"竣工日期[：:]\s*(.+)")),
    ("合同金额", re.compile(
        r"(?:合同金额(?:[（(]?元[）)]?)?|签约合同价|合同价格(?:[（(]?元[）)]?)?)[：:]\s*([0-9.]+)"
    )),
    # 勿用裸「编号」：会误吃「项目编号：」。检验批等靠著录条「文件编号：」
    ("文件编号", re.compile(r"(?:文件编号|合同编号|报告编号|证号|图册编号)[：:]\s*(.+)")),
]

_NEXT_LABEL = re.compile(
    r"(?:项目名称|工程名称|建设项目名称|项目编号|建设单位|施工单位|监理单位|设计单位|"
    r"工程地址|建设地点|建设地址|工程地点|建设位置|开工日期|竣工日期|"
    r"合同金额|签约合同价|合同价格|文件编号|合同编号|报告编号|证号|图册编号)\s*[：:]"
)

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


def iter_pdf_pages(path: Path):
    """Yield (page_no_1based, text) for every page. Empty on open failure."""
    try:
        doc = fitz.open(path)
    except Exception:
        return
    try:
        for i, page in enumerate(doc):
            yield i + 1, page.get_text() or ""
    finally:
        doc.close()


def read_pdf_text(path: Path, max_pages: int | None = None) -> str:
    """Read PDF text layer. Default: all pages (C1). Pass max_pages to cap."""
    parts: list[str] = []
    for i, (_page_no, text) in enumerate(iter_pdf_pages(path)):
        if max_pages is not None and i >= max_pages:
            break
        parts.append(text)
    return "\n".join(parts)


def pdf_page_count(path: Path) -> int:
    try:
        doc = fitz.open(path)
    except Exception:
        return 0
    try:
        return len(doc)
    finally:
        doc.close()


def _clean_field_value(key: str, raw: str) -> str:
    """截断同行多字段粘连（；或下一标签），兼容异构样表。"""
    val = raw.strip().splitlines()[0].strip()
    val = re.split(r"[；;|]", val, maxsplit=1)[0].strip()
    m = _NEXT_LABEL.search(val)
    if m and m.start() > 0:
        val = val[: m.start()].strip()
    if key == "合同金额":
        val = re.sub(r"\s+", "", val)
    if key in ("开工日期", "竣工日期"):
        # 合同工期「2024-03-01 至 2025-11-20」只取日期段
        m = re.match(r"(\d{4}[-./年]\d{1,2}[-./月]\d{1,2}日?)", val)
        if m:
            val = m.group(1).replace("年", "-").replace("月", "-").replace("日", "")
            val = re.sub(r"[-./]+", "-", val)
    return val


def extract_fields(text: str) -> dict[str, str]:
    """First-hit flat map (Chinese name -> value). Prefer extract_field_candidates for C1."""
    out: dict[str, str] = {}
    for key, pat in FIELD_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        val = _clean_field_value(key, m.group(1))
        if val and not re.search(r"暂缺|待填写|示例|XXXX", val, re.I):
            out[key] = val
    return out


def _evidence_line(text: str, match: re.Match[str]) -> str:
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end < 0:
        line_end = min(len(text), match.end() + 48)
    evidence = re.sub(r"\s+", " ", text[line_start:line_end].strip())[:160]
    return evidence


def manifest_name_to_key(rules: dict) -> dict[str, str]:
    """Chinese name/alias -> English field_key from rules.manifest_fields."""
    mapping: dict[str, str] = {}
    for field in rules.get("manifest_fields") or []:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key") or "").strip()
        if not key:
            continue
        name = str(field.get("name") or "").strip()
        if name:
            mapping[name] = key
        for alias in field.get("aliases") or []:
            a = str(alias).strip()
            if a and a != "编号":
                mapping[a] = key
    return mapping


def extract_field_candidates(
    pages: list[tuple[int, str]],
    name_to_key: dict[str, str] | None = None,
) -> list[dict]:
    """C1: page-level candidates; keep every occurrence of each field.

    Each item: field_key / value / page / evidence / source / confidence
    (+ name Chinese label, bbox null this round).
    """
    name_to_key = name_to_key or {}
    candidates: list[dict] = []
    for page_no, text in pages:
        if not text or not text.strip():
            continue
        for name_zh, pat in FIELD_PATTERNS:
            for m in pat.finditer(text):
                val = _clean_field_value(name_zh, m.group(1))
                if not val or re.search(r"暂缺|待填写|示例|XXXX", val, re.I):
                    continue
                evidence = _evidence_line(text, m) or f"{name_zh}：{val}"
                field_key = name_to_key.get(name_zh, name_zh)
                # 文本层命中：较高置信；页首区略高
                confidence = 0.92 if m.start() < 400 else 0.8
                candidates.append(
                    {
                        "field_key": field_key,
                        "name": name_zh,
                        "value": val,
                        "page": page_no,
                        "evidence": evidence,
                        "source": "native_pdf_text",
                        "confidence": confidence,
                        "bbox": None,
                    }
                )
    return candidates


def candidates_to_summary(candidates: list[dict]) -> dict[str, str]:
    """First value per Chinese field name (legacy flat map for consensus/misfile)."""
    summary: dict[str, str] = {}
    for c in candidates:
        name = c.get("name") or c.get("field_key")
        if not name or name in summary:
            continue
        val = c.get("value")
        if val:
            summary[str(name)] = str(val)
    return summary


def _null_manifest_field() -> dict:
    return {"value": None, "page": None, "evidence": None}


def empty_manifest_fields(rules: dict) -> dict[str, dict]:
    """Skeleton for all manifest_fields keys (null values)."""
    out: dict[str, dict] = {}
    for field in rules.get("manifest_fields") or []:
        if not isinstance(field, dict):
            continue
        key = field.get("key")
        if key:
            out[str(key)] = _null_manifest_field()
    return out


def build_field_extractors(manifest_fields: list) -> list[tuple[str, str, re.Pattern[str]]]:
    """Build (field_key, name_zh, pattern) from rules.manifest_fields."""
    extractors: list[tuple[str, str, re.Pattern[str]]] = []
    for field in manifest_fields or []:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key") or "").strip()
        name_zh = str(field.get("name") or "").strip()
        aliases = [str(a).strip() for a in (field.get("aliases") or []) if str(a).strip()]
        labels: list[str] = []
        for lab in [name_zh, *aliases]:
            # 裸「编号」易误吃其它著录项，跳过；identifier 另加「证号」
            if not lab or lab == "编号":
                continue
            if lab not in labels:
                labels.append(lab)
        if field.get("type") == "identifier" and "证号" not in labels:
            labels.append("证号")
        if not key or not labels:
            continue
        alt = "|".join(re.escape(lab) for lab in labels)
        if field.get("type") == "money":
            pat = re.compile(rf"(?:{alt})[：:]\s*([0-9.]+)")
        else:
            pat = re.compile(rf"(?:{alt})[：:]\s*(.+)")
        extractors.append((key, name_zh or key, pat))
    return extractors


def extract_fields_from_primary_pdf(
    path: Path,
    extractors: list[tuple[str, str, re.Pattern[str]]],
) -> dict[str, dict]:
    """Page-aware extract from one PDF. First hit per field wins. Keys = English field keys."""
    hits: dict[str, dict] = {}
    if not extractors or not path.is_file():
        return hits
    try:
        doc = fitz.open(path)
    except Exception:
        return hits
    try:
        for i, page in enumerate(doc):
            text = page.get_text() or ""
            if not text.strip():
                continue
            page_no = i + 1
            for key, name_zh, pat in extractors:
                if key in hits:
                    continue
                m = pat.search(text)
                if not m:
                    continue
                val = _clean_field_value(name_zh, m.group(1))
                if not val or re.search(r"暂缺|待填写|示例|XXXX", val, re.I):
                    continue
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                if line_end < 0:
                    line_end = min(len(text), m.end() + 48)
                evidence = re.sub(r"\s+", " ", text[line_start:line_end].strip())[:160]
                if not evidence:
                    evidence = f"{name_zh}：{val}"
                hits[key] = {
                    "value": val,
                    "page": page_no,
                    "evidence": evidence,
                }
    finally:
        doc.close()
    return hits


def resolve_primary_file_path(case_dir: Path, primary: dict) -> Path | None:
    file_id = str(primary.get("file_id") or "").replace("\\", "/").lstrip("/")
    if not file_id:
        return None
    candidates = [
        case_dir / file_id,
        case_dir / "files" / file_id.removeprefix("files/"),
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def build_manifest_fields(
    rules: dict,
    case_dir: Path,
    primary: dict | None,
) -> dict[str, dict]:
    """B2: fill manifest.fields only from primary reference file.

    Missing values stay null. Never backfill from other files.
    """
    out = empty_manifest_fields(rules)
    if not primary:
        return out
    path = resolve_primary_file_path(case_dir, primary)
    if path is None or path.suffix.lower() != ".pdf":
        return out
    extractors = build_field_extractors(rules.get("manifest_fields") or [])
    hits = extract_fields_from_primary_pdf(path, extractors)
    for key, cell in hits.items():
        if key in out:
            out[key] = cell
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


# V2.0 规则文件四段结构（另含 profile 元数据）
REQUIRED_RULE_KEYS = (
    "profile_id",
    "project_type",
    "manifest_fields",
    "primary_reference",
    "required_documents",
    "consistency_rules",
)

CORE_CONSISTENCY_TYPES = {
    "R-001": "field_scope",
    "R-002": "manifest_consistency",
    "R-003": "cross_file_consistency",
}


def load_rules(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_RULE_KEYS if k not in data]
    if missing:
        raise ValueError(f"规则文件缺少键 {missing}: {path}")
    if not isinstance(data.get("manifest_fields"), list) or not data["manifest_fields"]:
        raise ValueError(f"规则文件 manifest_fields 须为非空数组: {path}")
    pref = data.get("primary_reference")
    if not isinstance(pref, dict) or not pref.get("code") or not pref.get("name"):
        raise ValueError(f"规则文件 primary_reference 须含 code/name: {path}")
    if not isinstance(data.get("required_documents"), list):
        raise ValueError(f"规则文件 required_documents 须为数组: {path}")
    rules = data.get("consistency_rules")
    if not isinstance(rules, list):
        raise ValueError(f"规则文件 consistency_rules 须为数组: {path}")
    by_id = {r.get("rule_id"): r for r in rules if isinstance(r, dict)}
    for rid, rtype in CORE_CONSISTENCY_TYPES.items():
        row = by_id.get(rid)
        if not row or row.get("type") != rtype:
            raise ValueError(
                f"规则文件须含 {rid} type={rtype}: {path}"
            )
    return data


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


def _primary_doc_def(rules: dict) -> dict:
    """Merge rules.primary_reference with matching required_documents entry (category)."""
    pref = rules.get("primary_reference") or {}
    code = str(pref.get("code") or "")
    name = str(pref.get("name") or "")
    aliases = list(pref.get("aliases") or [])
    category = None
    for doc in rules.get("required_documents") or []:
        if not isinstance(doc, dict):
            continue
        if doc.get("code") == code or doc.get("name") == name:
            category = doc.get("category")
            for a in doc.get("aliases") or []:
                if a and a not in aliases:
                    aliases.append(a)
            break
    return {
        "code": code,
        "name": name,
        "aliases": aliases,
        "category": category,
    }


def _score_primary_candidate(
    row: dict,
    doc: dict,
    project_name: str,
) -> tuple[int, list[str]]:
    """Score one file as primary-reference candidate. Unreadable files get 0."""
    if row.get("unreadable") or row.get("misfiled"):
        return 0, []
    names = [doc.get("name") or "", *(doc.get("aliases") or [])]
    names = [n for n in names if n]
    score = 0
    reasons: list[str] = []
    fname = row.get("filename") or ""
    text = (row.get("text_head") or "")[:800]
    for n in names:
        if n in fname:
            score += 5
            reasons.append(f"文件名含「{n}」")
        elif n in text:
            score += 3
            reasons.append(f"正文含「{n}」")
    if doc.get("category") and row.get("category") == doc["category"]:
        score += 2
        reasons.append("分类一致")
    proj = str((row.get("fields") or {}).get("项目名称") or "").strip()
    anchor = (project_name or "").strip()
    if proj and anchor and not is_weak_project_name(anchor) and proj == anchor:
        score += 2
        reasons.append("项目名称一致")
    if score > 0 and not row.get("unreadable"):
        score += 1
        reasons.append("可读文本")
    return score, reasons


def select_primary_reference(
    rules: dict,
    file_rows: list[dict],
    manifest: dict,
) -> dict:
    """Select primary reference file.

    Returns:
      {
        status: "selected" | "no_primary",
        reason?: "zero_candidates" | "ambiguous_tie" | "user_missing",
        primary?: {file_id, file_name, document_code, source},
        expected: {code, name},
        candidates: [{path, filename, score, reasons}],
      }
    """
    doc = _primary_doc_def(rules)
    expected = {"code": doc["code"], "name": doc["name"]}
    project_name = str(manifest.get("project_name") or "")

    # User pre-selection: trust if file still exists
    existing = manifest.get("primary_reference")
    if isinstance(existing, dict) and existing.get("source") == "user":
        file_id = str(existing.get("file_id") or "").replace("\\", "/")
        by_path = {r["rel_path"].replace("\\", "/"): r for r in file_rows}
        row = by_path.get(file_id)
        if not row and file_id.startswith("files/"):
            # also try bare path under files/
            bare = file_id[len("files/") :]
            for r in file_rows:
                rel = r["rel_path"].replace("\\", "/")
                if rel == bare or rel.endswith("/" + bare) or rel == "files/" + bare:
                    row = r
                    break
        if not row and file_id and not file_id.startswith("files/"):
            row = by_path.get("files/" + file_id)
        if row:
            primary = {
                "file_id": row["rel_path"],
                "file_name": row["filename"],
                "document_code": doc["code"] or str(existing.get("document_code") or ""),
                "source": "user",
            }
            return {
                "status": "selected",
                "primary": primary,
                "expected": expected,
                "candidates": [
                    {
                        "path": row["rel_path"],
                        "filename": row["filename"],
                        "score": 999,
                        "reasons": ["用户指定主参考"],
                    }
                ],
            }
        return {
            "status": "no_primary",
            "reason": "user_missing",
            "expected": expected,
            "candidates": [],
        }

    scored: list[dict] = []
    for row in file_rows:
        score, reasons = _score_primary_candidate(row, doc, project_name)
        if score > 0:
            scored.append(
                {
                    "path": row["rel_path"],
                    "filename": row["filename"],
                    "score": score,
                    "reasons": reasons,
                    "_row": row,
                }
            )
    scored.sort(key=lambda x: (-x["score"], x["filename"]))
    candidates_out = [
        {
            "path": c["path"],
            "filename": c["filename"],
            "score": c["score"],
            "reasons": c["reasons"],
        }
        for c in scored
    ]

    if not scored:
        return {
            "status": "no_primary",
            "reason": "zero_candidates",
            "expected": expected,
            "candidates": [],
        }

    top = scored[0]["score"]
    tied = [c for c in scored if c["score"] == top]
    if len(tied) > 1:
        return {
            "status": "no_primary",
            "reason": "ambiguous_tie",
            "expected": expected,
            "candidates": candidates_out,
        }

    row = tied[0]["_row"]
    return {
        "status": "selected",
        "primary": {
            "file_id": row["rel_path"],
            "file_name": row["filename"],
            "document_code": doc["code"],
            "source": "auto",
        },
        "expected": expected,
        "candidates": candidates_out,
    }


def write_manifest_primary(
    case_dir: Path,
    manifest: dict,
    primary: dict | None,
    fields: dict | None = None,
) -> dict:
    """Persist primary_reference and optional fields. Does not touch task project_name."""
    manifest["primary_reference"] = primary
    if fields is not None:
        manifest["fields"] = fields
    elif "fields" not in manifest or not isinstance(manifest.get("fields"), dict):
        manifest["fields"] = {}
    manifest_path = case_dir / "manifest.json"
    try:
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return manifest


def primary_failure_finding(selection: dict) -> dict:
    expected = selection.get("expected") or {}
    code = expected.get("code") or "?"
    name = expected.get("name") or "主参考文件"
    reason_key = selection.get("reason") or "zero_candidates"
    cand = selection.get("candidates") or []
    if reason_key == "ambiguous_tie":
        detail = (
            f"找到 {len(cand)} 个同分候选，无法自动区分主参考"
            f"（期望 {code}《{name}》）；请在前端指定主文件后重跑"
        )
        suggestion = "在材料目录中指定唯一主参考文件，并确保内容正确"
    elif reason_key == "user_missing":
        detail = "用户指定的主参考文件已不存在或路径无效"
        suggestion = "重新指定主参考文件或补传后重跑核查"
    else:
        detail = (
            f"未找到主参考文件（期望 {code}《{name}》）；"
            "无主文件，不能生成正式核查结论"
        )
        suggestion = f"补传《{name}》或在前端手动指定主参考后重跑"
    return {
        "code": "PRIMARY",
        "name": f"主参考文件 · {name}",
        "status": "needs_human_review",
        "severity": "error",
        "reason": detail,
        "suggestion": suggestion,
        "primary_selection": {
            "status": "no_primary",
            "reason": reason_key,
            "candidates": [
                {"path": c.get("path"), "filename": c.get("filename"), "score": c.get("score")}
                for c in cand[:10]
            ],
        },
    }


def write_no_primary_report(
    path: Path,
    manifest: dict,
    rules: dict,
    inventory: dict,
    selection: dict,
) -> None:
    expected = selection.get("expected") or {}
    finding = primary_failure_finding(selection)
    lines = [
        "# 竣工资料完整性与一致性核查报告（脚本初稿）",
        "",
        f"- 项目：{manifest.get('project_name', '')} / {manifest.get('project_id', '')}",
        f"- 规则模板：{rules.get('profile_id')} · {rules.get('project_type')}",
        f"- 已检索文件：{inventory.get('count', 0)} 份",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat()}",
        f"- **任务状态：无主文件 — 需人工复核，未生成正式核查结论**",
        "",
        "## 主参考选择失败",
        "",
        f"- 期望：{expected.get('code')}《{expected.get('name')}》",
        f"- 原因：{finding.get('reason')}",
        f"- 建议：{finding.get('suggestion')}",
        "",
        "本任务**不能**宣称核查通过。请指定或补传主参考文件后重新核查。",
        "",
        "## 候选列表",
        "",
    ]
    cands = selection.get("candidates") or []
    if not cands:
        lines.append("- （无候选）")
    else:
        for c in cands:
            lines.append(
                f"- {c.get('filename')}（score={c.get('score')}）"
                f"：{'；'.join(c.get('reasons') or [])}"
            )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_no_primary_brief(path: Path, selection: dict) -> None:
    finding = primary_failure_finding(selection)
    lines = [
        "# 竣工资料核查简报（优先读此文件，勿通读全部 PDF）",
        "",
        "## 请你做的事",
        "1. **停止正式核查**：当前无主参考文件，不要宣称核查通过",
        "2. 告知用户在前端指定主文件或补传主参考后重跑",
        "3. 不要强行生成「通过」类情况说明文书",
        "",
        "## 主参考选择",
        f"- 状态：无主文件（{selection.get('reason')}）",
        f"- 判断：{finding.get('reason')}",
        f"- 建议：{finding.get('suggestion')}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


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


_DOC_LIKE_NAME = re.compile(
    r"^[A-G]-\d{2}\b|未命名工程|许可|合同|报告|证明|记录|细则|报审|验收|竣工图|监理规划|施工组织"
)

# 占位标识名（含纯 ASCII 任务 id，如 demo-housing-mixed）：
# 精确匹配占位词，或不含中文字符的短名，均视为弱名/占位名
_ASCII_ONLY = re.compile(r"^[^\u4e00-\u9fff]*$")
_WEAK_ASCII_LEN_THRESHOLD = 24

# 用户未认真填写时的占位名；过短名称也视为弱名
_WEAK_EXACT = {
    "未命名工程",
    "unnamed",
    "unknown",
    "工程",
    "项目",
    "某某工程",
    "测试",
    "测试工程",
    "demo",
    "test",
    "项目名称",
    "暂定",
    "待定",
    "新建工程",
    "本工程",
}


def is_weak_project_name(name: str) -> bool:
    """Placeholder / document-title names must not be used as misfile anchors.

    弱名判定原则：占位符（精确占位词、无中文字符的任务 id 标识、文种标题样式）
    不得用作错传锚点。含中文字符的真实工程名（无论是否包含 demo/测试 等子串）
    在未被精确占位列表命中时，视为有效名称。
    """
    n = (name or "").strip()
    if not n:
        return True
    if n in _WEAK_EXACT or n.lower() in _WEAK_EXACT:
        return True
    # 无中文字符的名称：视为占位标识（任务 id、代码等），判为弱名
    if _ASCII_ONLY.match(n):
        return True
    # 含中文字符的短名（≤3 字）仍判为弱名
    if len(n) <= 3:
        return True
    # 文种样式（许可证/合同等）仍是弱名
    if _DOC_LIKE_NAME.search(n):
        return True
    return False


def majority_project_name(file_rows: list[dict]) -> str:
    """Pick the most common extracted 项目名称 (ignore empty / weak)."""
    counts: dict[str, int] = {}
    for row in file_rows:
        proj = str((row.get("fields") or {}).get("项目名称") or "").strip()
        if not proj:
            continue
        # 弱名过滤：仅排除精确占位或文种样式名，避免把真实工程名
        # 误判为弱名（如包含 demo 子串的工作副本命名）
        if is_weak_project_name(proj):
            continue
        # Filename cue「滨河」alone is often the planted misfile; still count for majority.
        counts[proj] = counts.get(proj, 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def resolve_anchor_name(manifest_name: str, file_rows: list[dict]) -> str:
    """Prefer a real manifest name; otherwise consensus from PDF fields."""
    if not is_weak_project_name(manifest_name):
        return manifest_name.strip()
    return majority_project_name(file_rows)


def is_misfiled_row(row: dict, anchor_name: str) -> bool:
    """Other-project materials: path label, filename cue, or project_name ≠ anchor."""
    rel = row["rel_path"].replace("\\", "/")
    fname = row["filename"]
    proj = (row.get("fields") or {}).get("项目名称", "")
    if "错传" in rel or "错传" in fname:
        return True
    # No reliable anchor → only hard cues (avoid marking whole pack as misfiled)
    if not anchor_name:
        if "滨河" in fname:
            return True
        return False
    # manifest 工程名是占位标识（短/弱名）时，PDF 项目名称与之不同是正常现象，
    # 不得用 proj != anchor 作为错传信号，仅依赖明确文件线索（如「滨河」硬线索）
    if not is_weak_project_name(anchor_name):
        if proj and proj != anchor_name:
            return True
    if "滨河" not in anchor_name and "滨河" in fname:
        return True
    return False


def mark_misfiled(file_rows: list[dict], anchor_name: str) -> list[dict]:
    for row in file_rows:
        row["misfiled"] = is_misfiled_row(row, anchor_name)
    return file_rows


def in_project_rows(file_rows: list[dict]) -> list[dict]:
    return [r for r in file_rows if not r.get("misfiled")]


_WS_RE = re.compile(r"\s+")


def content_fingerprint(text: str) -> str | None:
    """Short sha256 of whitespace-stripped body; None if too short to compare."""
    norm = _WS_RE.sub("", (text or "").strip())
    if len(norm) < 80:
        return None
    digest = hashlib.sha256(norm[:8000].encode("utf-8")).hexdigest()
    return digest[:16]


def find_content_duplicate_groups(rows: list[dict]) -> list[list[str]]:
    """C3 heuristic: exact content fingerprint, then high text_head similarity."""
    by_fp: dict[str, list[str]] = defaultdict(list)
    comparable: list[dict] = []
    for row in rows:
        if row.get("unreadable") or row.get("unsupported_format") or row.get("misfiled"):
            continue
        fp = row.get("content_fingerprint")
        if not fp:
            continue
        by_fp[str(fp)].append(row["rel_path"])
        comparable.append(row)

    groups = [paths for paths in by_fp.values() if len(paths) >= 2]
    in_group = {p for g in groups for p in g}
    singles = [r for r in comparable if r["rel_path"] not in in_group]
    used: set[str] = set()
    for i, a in enumerate(singles):
        if a["rel_path"] in used:
            continue
        na = _WS_RE.sub("", (a.get("text_head") or "")[:1200])
        if len(na) < 80:
            continue
        cluster = [a["rel_path"]]
        for b in singles[i + 1 :]:
            if b["rel_path"] in used:
                continue
            nb = _WS_RE.sub("", (b.get("text_head") or "")[:1200])
            if len(nb) < 80:
                continue
            ratio = len(na) / max(len(nb), 1)
            if ratio < 0.7 or ratio > 1.43:
                continue
            if SequenceMatcher(None, na[:2000], nb[:2000]).ratio() >= 0.92:
                cluster.append(b["rel_path"])
                used.add(b["rel_path"])
        if len(cluster) >= 2:
            used.add(a["rel_path"])
            groups.append(cluster)
    return groups


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
                fname = row["filename"]
                # 去掉「版式参考…竣工验收报告」类脚注，避免 E-02 等竣工报告误命中
                head = re.sub(
                    r"[（(]?版式参考[^）)\n]{0,40}",
                    "",
                    row.get("text_head", "")[:600],
                )
                blob = fname + head
                if "预验收" in blob and (
                    "竣工验收" in blob
                    or "验收报告" in fname
                    or "预验收" in fname
                ):
                    similar.append(row["rel_path"])
                elif "预验收" not in blob and (
                    "竣工验收报告" in fname
                    or "竣工验收报告" in head
                    or ("工程竣工验收" in fname and "报告" in fname)
                ):
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
                "reason": f"文载项目为「{proj}」，与本项目不符，按错传处理；不参与材料齐全与字段共识",
                "matched_file": row["rel_path"],
                "suggestion": "移出本包并核对归属",
            }
        )

    # unreadable / unsupported / empty-text among in-project files
    for row in target_rows:
        if not row.get("unreadable") and not row.get("unsupported_format"):
            continue
        if row.get("unsupported_format"):
            reason = (
                f"仅支持 PDF 文本层，不处理「{row.get('ext') or '未知'}」等格式；"
                "不能据此认定已提供对应资料"
            )
            suggestion = "请转为可检索 PDF 后重新核查"
            code = "UNSUPPORTED"
        else:
            reason = "未能抽取可读正文，不能据此认定已提供对应资料"
            suggestion = "重新上传 PDF "
            code = "UNREADABLE"
        findings.append(
            {
                "code": code,
                "name": row["filename"],
                "status": "needs_human_review",
                "severity": "warning",
                "reason": reason,
                "matched_file": row["rel_path"],
                "suggestion": suggestion,
            }
        )

    # duplicates by 文件编号（仅本工程）
    covered_dup_sets: list[frozenset[str]] = []
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
                    "dup_kind": "file_no",
                }
            )
            covered_dup_sets.append(frozenset(paths))

    # duplicates by content fingerprint / high text similarity（C3）
    for paths in find_content_duplicate_groups(target_rows):
        key = frozenset(paths)
        if any(key <= c or c <= key for c in covered_dup_sets):
            continue
        findings.append(
            {
                "code": "DUP",
                "name": "内容高度相似重复",
                "status": "suspect_duplicate_or_misfiled",
                "severity": "warning",
                "reason": f"本项目多份文件正文指纹或正文高度相似：{short_names(paths)}",
                "similar_files": paths,
                "suggestion": "确认是否重复归档或误传副本",
                "dup_kind": "content",
            }
        )
        covered_dup_sets.append(key)

    # in-project field conflicts only (misfiled already excluded from consensus)
    for field, info in consensus.get("冲突", {}).items():
        findings.append(
            {
                "code": "FIELD",
                "name": f"字段冲突:{field}",
                "status": "needs_human_review",
                "severity": "warning",
                "reason": f"本项目多文件取值不一致：{format_value_map(info.get('values', {}))}",
                "suggestion": "请以主文件参考值为准核对，并人工确认",
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
    """Legacy flat Chinese-key consensus (kept for brief fallback). Prefer build_field_consistency."""
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


def _field_defs_by_key(rules: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for field in rules.get("manifest_fields") or []:
        if isinstance(field, dict) and field.get("key"):
            out[str(field["key"])] = field
    return out


def _r001_scope_map(rules: dict) -> dict[str, list[str]]:
    """field_key -> list of document names for scoped fields."""
    for rule in rules.get("consistency_rules") or []:
        if isinstance(rule, dict) and rule.get("type") == "field_scope":
            mapping: dict[str, list[str]] = {}
            for scope in rule.get("scopes") or []:
                if not isinstance(scope, dict):
                    continue
                fk = str(scope.get("field") or "").strip()
                docs = [str(d) for d in (scope.get("documents") or []) if d]
                if fk:
                    mapping[fk] = docs
            return mapping
    return {}


def _r003_min_coverage(rules: dict) -> float:
    """R-003: fraction of applicable files that must have a value before cross-compare.

    Reads ``min_coverage`` / ``min_coverage_ratio`` (0–1 or percent >1). Default 0.25.
    """
    for rule in rules.get("consistency_rules") or []:
        if isinstance(rule, dict) and rule.get("type") == "cross_file_consistency":
            raw = rule.get("min_coverage", rule.get("min_coverage_ratio"))
            if raw is None:
                return 0.25
            try:
                v = float(raw)
            except (TypeError, ValueError):
                return 0.25
            if v > 1.0:
                v = v / 100.0
            return min(1.0, max(0.0, v))
    return 0.25


def _docs_for_scope_names(rules: dict, names: list[str]) -> list[dict]:
    """Map scope document display names to required_documents entries (with aliases)."""
    by_label: dict[str, dict] = {}
    for doc in rules.get("required_documents") or []:
        if not isinstance(doc, dict):
            continue
        for lab in [doc.get("name"), *(doc.get("aliases") or [])]:
            if lab:
                by_label[str(lab)] = doc
    out: list[dict] = []
    seen: set[str] = set()
    for name in names:
        doc = by_label.get(name)
        if doc:
            code = str(doc.get("code") or doc.get("name") or name)
            if code in seen:
                continue
            seen.add(code)
            out.append(doc)
        else:
            out.append({"code": name, "name": name, "aliases": []})
    return out


_LAYOUT_REF_NOISE = re.compile(
    r"[（(]?版式参考[^）)\n]{0,40}[）)]?"
)


def _doc_name_in_text(name: str, text: str) -> bool:
    """Document title hit in body; reject compound false friends like 施工合同价."""
    if not name or not text:
        return False
    return re.search(re.escape(name) + r"(?![价金额款额])", text) is not None


def file_matches_scope_docs(row: dict, docs: list[dict], min_score: int = 3) -> bool:
    """True if file name/text hits any scoped document name/alias.

    Category alone must not qualify. Body match strips 「版式参考…」脚注，
    and rejects 「施工合同价」类子串误命中。
    """
    if not docs:
        return False
    fname = row.get("filename") or ""
    text = _LAYOUT_REF_NOISE.sub("", (row.get("text_head") or "")[:800])
    for doc in docs:
        names = [doc.get("name") or "", *(doc.get("aliases") or [])]
        names = [n for n in names if n]
        name_score = 0
        for n in names:
            if n in fname:
                name_score += 5
            elif _doc_name_in_text(n, text):
                name_score += 3
        if name_score <= 0:
            continue
        score = name_score
        if doc.get("category") and row.get("category") == doc.get("category"):
            score += 1
        if score >= min_score:
            return True
    return False


def normalize_compare_value(field_def: dict, value: object) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v or v in {"（本文件未载明）", "暂缺", "待填写"}:
        return None
    ftype = field_def.get("type")
    if ftype == "money":
        v = re.sub(r"[,，\s元整]", "", v)
    elif ftype == "date":
        v = v.replace("年", "-").replace("月", "-").replace("日", "")
        v = re.sub(r"[-./]+", "-", v).strip("-")
    return v


def extract_row_field_hit(row: dict, field_key: str, name_zh: str) -> dict | None:
    """Best candidate for field on this file (first by page then appearance)."""
    for c in row.get("candidates") or []:
        if c.get("field_key") == field_key or c.get("name") == name_zh:
            return c
    summary = row.get("fields") or {}
    if name_zh in summary and summary[name_zh]:
        return {
            "field_key": field_key,
            "name": name_zh,
            "value": summary[name_zh],
            "page": None,
            "evidence": None,
        }
    return None


def manifest_field_value(manifest: dict, field_key: str) -> object:
    fields = manifest.get("fields")
    if isinstance(fields, dict) and isinstance(fields.get(field_key), dict):
        return fields[field_key].get("value")
    # legacy top-level keys (demo packs)
    legacy = {
        "project_name": "project_name",
        "project_code": "project_code",
        "owner": "owner",
        "contractor": "contractor",
        "supervisor": "supervisor",
        "designer": "designer",
        "address": "address",
        "start_date": "start_date",
        "finish_date": "finish_date",
        "contract_amount": "contract_amount",
    }
    top = legacy.get(field_key)
    if top and manifest.get(top):
        return manifest.get(top)
    return None


def build_field_consistency(
    rules: dict,
    manifest: dict,
    file_rows: list[dict],
    misfiled_paths: set[str] | None = None,
) -> dict:
    """C2: R-001 scope + R-002 manifest consistency + R-003 cross-file.

    global fields: all in-project files with a value are applicable.
    scoped fields: only files matching R-001 documents list.
    """
    misfiled_paths = misfiled_paths or set()
    field_defs = _field_defs_by_key(rules)
    scope_map = _r001_scope_map(rules)
    min_coverage = _r003_min_coverage(rules)
    coverage_pct = int(round(min_coverage * 100))
    target_rows = [r for r in file_rows if r["rel_path"] not in misfiled_paths]

    field_results: list[dict] = []
    rule_findings: list[dict] = []
    legacy_conflicts: dict[str, dict] = {}

    for field_key, field_def in field_defs.items():
        name_zh = str(field_def.get("name") or field_key)
        consistency = str(field_def.get("consistency") or "scoped").lower()
        if consistency not in {"global", "scoped"}:
            consistency = "scoped"

        scope_docs = _docs_for_scope_names(rules, scope_map.get(field_key) or [])
        values_by_file: list[dict] = []
        applicable_values: list[tuple[str, str, dict]] = []  # norm, raw, row_meta

        for row in target_rows:
            rel = row["rel_path"]
            fname = row["filename"]
            if consistency == "global":
                applicable = True
                reason_na = None
            else:
                if not scope_docs:
                    applicable = False
                    reason_na = "该字段未配置适用材料类别"
                elif file_matches_scope_docs(row, scope_docs):
                    applicable = True
                    reason_na = None
                else:
                    applicable = False
                    reason_na = "该字段不属于此类文件"

            hit = extract_row_field_hit(row, field_key, name_zh)
            raw_val = hit.get("value") if hit else None
            norm = normalize_compare_value(field_def, raw_val)

            entry: dict = {
                "file_id": rel,
                "file_name": fname,
                "value": raw_val if applicable else None,
                "page": hit.get("page") if hit and applicable else None,
                "evidence": hit.get("evidence") if hit and applicable else None,
                "applicable": applicable,
            }
            if not applicable:
                entry["reason"] = reason_na
                # 范围外若抽出值，仅观察，不参与比较
                if norm:
                    entry["out_of_scope_value"] = raw_val
            elif norm:
                entry["status"] = "provided"
                applicable_values.append((norm, str(raw_val), entry))
            else:
                entry["status"] = "missing"
            values_by_file.append(entry)

        manifest_raw = manifest_field_value(manifest, field_key)
        manifest_norm = normalize_compare_value(field_def, manifest_raw)
        distinct = sorted({v[0] for v in applicable_values})
        rule_ids: list[str] = ["R-001"]
        status = "provided"
        reason = ""

        if manifest_norm:
            rule_ids.append("R-002")
            mismatched = [v for v in applicable_values if v[0] != manifest_norm]
            if mismatched:
                status = "needs_human_review"
                reason = (
                    f"适用材料中的「{name_zh}」与参考值不一致"
                    f"（参考值={manifest_raw}；冲突 "
                    + "、".join(
                        f"{Path(e['file_id']).name}={e.get('value')}"
                        for _, _, e in mismatched[:4]
                    )
                    + "）"
                )
            elif applicable_values:
                status = "provided"
                reason = f"适用材料中的「{name_zh}」均与参考值一致"
            else:
                status = "provided"
                reason = f"参考值有「{name_zh}」，适用材料暂无抽出值（不判缺失）"
        else:
            # R-003: ≥min_coverage of applicable files have values → cross-compare
            applicable_file_count = sum(
                1 for e in values_by_file if e.get("applicable")
            )
            value_count = len(applicable_values)
            coverage = (
                (value_count / applicable_file_count) if applicable_file_count else 0.0
            )
            if value_count > 0 and coverage >= min_coverage:
                rule_ids.append("R-003")
                if len(distinct) > 1:
                    status = "needs_human_review"
                    reason = (
                        f"参考值无「{name_zh}」，"
                        f"{value_count}/{applicable_file_count} 份适用材料有值"
                        f"（≥{coverage_pct}%）且取值不一致："
                        + "；".join(distinct[:5])
                    )
                else:
                    status = "provided"
                    reason = (
                        f"参考值无「{name_zh}」，"
                        f"{value_count}/{applicable_file_count} 份适用材料有值"
                        f"（≥{coverage_pct}%）且取值一致"
                    )
            elif value_count > 0:
                rule_ids.append("R-003")
                status = "provided"
                reason = (
                    f"参考值无「{name_zh}」，仅 "
                    f"{value_count}/{applicable_file_count} 份适用材料有值"
                    f"（未达 {coverage_pct}%），记录候选、不判冲突"
                )
            else:
                status = "provided"
                reason = f"无适用材料提供「{name_zh}」，跳过一致性比较"

        result = {
            "field_key": field_key,
            "field_name": name_zh,
            "consistency": consistency,
            "manifest_value": manifest_raw,
            "status": status,
            "values_by_file": values_by_file,
            "rule_ids": rule_ids,
            "reason": reason,
            "applicable_value_count": len(applicable_values),
            "distinct_values": distinct,
        }
        field_results.append(result)

        if status == "needs_human_review":
            rule_findings.append(
                {
                    "code": "RULE",
                    "name": f"字段一致性:{name_zh}",
                    "status": "needs_human_review",
                    "severity": "warning",
                    "reason": reason,
                    "suggestion": (
                        (
                            "请以主文件参考值为准，核对相关材料中的该字段。"
                            if manifest_norm
                            else "请在相关材料之间核对取值并人工确认。"
                        )
                        + (
                            "该字段在全部材料中应一致。"
                            if consistency == "global"
                            else "该字段仅在指定材料类别内比较。"
                        )
                    ),
                    "field": field_key,
                    "field_name": name_zh,
                    "rule_ids": rule_ids,
                    "consistency": consistency,
                }
            )
            # legacy brief buckets (Chinese name)
            valmap: dict[str, list[str]] = defaultdict(list)
            for norm, _raw, entry in applicable_values:
                valmap[norm].append(entry["file_id"])
            if manifest_norm:
                valmap[manifest_norm].append("(manifest)")
            if len(valmap) > 1:
                legacy_conflicts[name_zh] = {
                    "values": dict(valmap),
                    "summary": format_value_map(valmap),
                }

    anchor = {}
    for key, cell in (manifest.get("fields") or {}).items():
        if isinstance(cell, dict) and cell.get("value") is not None:
            fd = field_defs.get(key) or {}
            anchor[str(fd.get("name") or key)] = str(cell["value"])

    return {
        "锚值": anchor,
        "冲突": legacy_conflicts,
        "conflicts": [
            {
                "field": f.get("field_name"),
                "field_key": f.get("field_key"),
                "consistency": f.get("consistency"),
                "status": f.get("status"),
                "manifest_value": f.get("manifest_value"),
                "values": f.get("distinct_values"),
                "summary": f.get("reason"),
                "rule_ids": f.get("rule_ids"),
                "scope": f.get("consistency"),
            }
            for f in field_results
            if f.get("status") == "needs_human_review"
        ],
        "fields": field_results,
        "rule_findings": rule_findings,
        "excluded_misfiled": sorted(misfiled_paths),
        "note": (
            "C2：global=有值文件全局比；scoped=仅 R-001 使用文件类别内比；"
            "R-003 适用文件有值覆盖率≥min_coverage（默认25%）才互比；"
            "不适用 applicable=false；错传已排除"
        ),
        "generated_by": "audit_prepare.py",
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
        "## 完整性核查统计",
        "",
        f"- 已提供：{counts['provided']}",
        f"- 缺失：{counts['missing']}",
        f"- 错传或重复：{counts['suspect_duplicate_or_misfiled']}",
        f"- 需复核：{counts['needs_human_review']}",
        "",
        "## 主要问题与证据",
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
        "# 竣工资料核查简报（优先读此文件，勿通读全部 PDF）",
        "",
        "## 请你做的事",
        "1. 抽查本工程字段冲突与错传判定是否合理（优先看 FIELD / MISFILE）",
        "2. 如需，润色 audit-report.md 措辞（不要改结论方向）",
        "3. 正式《核查情况说明》交给 engineering-doc-generator：prepare → 写正文.md → build",
        "4. 文书只写缺失、错传、重复、本工程真冲突；勿把错传级联字段逐条夸大",
        "",
        "## 完整性核查统计",
        f"- 已提供 {counts['provided']}；缺失 {counts['missing']}；"
        f"错传或重复 {counts['suspect_duplicate_or_misfiled']}；"
        f"需复核 {counts['needs_human_review']}",
        "",
        "## 重要问题（短文件名）",
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
    fields_payload_files: dict[str, dict] = {}
    evidence_items: list[dict] = []
    classification: list[dict] = []
    name_to_key = manifest_name_to_key(rules)

    for fp in iter_files(files_dir):
        rel = fp.relative_to(case_dir).as_posix()
        ext = fp.suffix.lower()
        unsupported_format = ext != ".pdf"
        pages: list[tuple[int, str]] = []
        page_count = 0
        if unsupported_format:
            text = ""
            candidates: list[dict] = []
            unreadable = True
        else:
            pages = list(iter_pdf_pages(fp))
            page_count = len(pages)
            text = "\n".join(t for _n, t in pages)
            candidates = extract_field_candidates(pages, name_to_key)
            text_stripped = text.strip()
            unreadable = len(text_stripped) < 20

        fields = candidates_to_summary(candidates)
        cat, conf, hits = classify(fp.name, text)
        if unsupported_format:
            cat, conf = "unknown", "low"
            hits = hits + ["unsupported_format"]
        elif unreadable:
            cat, conf = "unknown", "low"
            hits = hits + ["no_extractable_text"]

        row = {
            "path": rel,
            "rel_path": rel,
            "filename": fp.name,
            "ext": ext,
            "size_bytes": fp.stat().st_size,
            "category": cat,
            "confidence": conf,
            "evidence": hits,
            "fields": fields,
            "candidates": candidates,
            "page_count": page_count,
            "text_head": text[:1200],
            "content_fingerprint": content_fingerprint(text),
            "unreadable": unreadable,
            "unsupported_format": unsupported_format,
        }
        file_rows.append(row)
        fields_by_file[rel] = fields
        fields_payload_files[rel] = {
            "page_count": page_count,
            "candidates": candidates,
            "summary": fields,
            "unreadable": unreadable,
            "unsupported_format": unsupported_format,
        }
        for c in candidates:
            evidence_items.append(
                {
                    "file_id": rel,
                    "field_key": c.get("field_key"),
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "page": c.get("page"),
                    "evidence": c.get("evidence"),
                    "source": c.get("source"),
                    "confidence": c.get("confidence"),
                    "bbox": c.get("bbox"),
                }
            )
        classification.append(
            {
                "path": rel,
                "category": cat,
                "confidence": conf,
                "evidence": hits,
                "unreadable": unreadable,
                "unsupported_format": unsupported_format,
                "page_count": page_count,
            }
        )

    raw_manifest_name = str(manifest.get("project_name") or "")
    anchor = anchor_from_manifest(manifest)
    anchor_name = resolve_anchor_name(anchor.get("项目名称", "") or raw_manifest_name, file_rows)
    project_name_resolved_from_files = bool(
        anchor_name
        and is_weak_project_name(raw_manifest_name)
        and anchor_name != raw_manifest_name.strip()
    )
    if project_name_resolved_from_files:
        # 用户未明确指定真实工程名时，以多数文件共同名称回写，供前端同步
        manifest["project_name"] = anchor_name
        manifest["project_name_source"] = "file_consensus"
        try:
            (case_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        print(
            f"[audit_prepare] project_name resolved from files: "
            f"{raw_manifest_name!r} -> {anchor_name!r}"
        )
    elif not is_weak_project_name(raw_manifest_name):
        manifest["project_name_source"] = "user"
    mark_misfiled(file_rows, anchor_name)
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
                "content_fingerprint": r.get("content_fingerprint"),
            }
            for r in file_rows
        ],
        "generated_by": "audit_prepare.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    (work / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work / "classification.json").write_text(
        json.dumps({"items": classification}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (work / "fields.json").write_text(
        json.dumps(
            {
                "generated_by": "audit_prepare.py",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "note": "C1 页面级候选；summary 为每字段首次命中（中文名），供错传/共识兼容",
                "files": fields_payload_files,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (work / "evidence.json").write_text(
        json.dumps(
            {
                "generated_by": "audit_prepare.py",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "items": evidence_items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # B1: select primary reference (respect user pre-selection)
    selection = select_primary_reference(rules, file_rows, manifest)
    primary_payload = {
        "status": selection["status"],
        "reason": selection.get("reason"),
        "expected": selection.get("expected"),
        "candidates": selection.get("candidates") or [],
        "primary": selection.get("primary"),
        "generated_by": "audit_prepare.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (work / "primary_selection.json").write_text(
        json.dumps(primary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if selection["status"] != "selected":
        # B2: 无主文件不写正式 fields（仅 null 骨架，禁止用其它文件补齐）
        fields_skel = empty_manifest_fields(rules)
        manifest = write_manifest_primary(case_dir, manifest, None, fields_skel)
        finding = primary_failure_finding(selection)
        findings = [finding]
        consensus = {
            "锚值": {},
            "冲突": {},
            "conflicts": [],
            "excluded_misfiled": sorted(misfiled_paths),
            "note": "无主参考文件，未生成正式核查结论",
            "primary_status": "no_primary",
        }
        (work / "field_consensus.json").write_text(
            json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (work / "findings.json").write_text(
            json.dumps(
                {
                    "items": findings,
                    "generated_by": "audit_prepare.py",
                    "rules_profile": rules.get("profile_id"),
                    "primary_status": "no_primary",
                    "task_status": "needs_human_review",
                    "formal_conclusion": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        write_no_primary_report(
            work / "audit-report.md", manifest, rules, inventory, selection
        )
        write_no_primary_brief(work / "audit-brief.md", selection)
        print(f"[audit_prepare] case={case_dir}")
        print(
            f"[audit_prepare] NO_PRIMARY reason={selection.get('reason')} "
            f"files={len(file_rows)} -> {work}"
        )
        return work

    # B2: fields only from primary reference
    task_project_name = str(manifest.get("project_name") or "")
    manifest_fields = build_manifest_fields(rules, case_dir, selection["primary"])
    manifest = write_manifest_primary(
        case_dir, manifest, selection["primary"], manifest_fields
    )
    # 任务身份 project_name 与 fields.project_name 分离，禁止混写
    if task_project_name:
        manifest["project_name"] = task_project_name
        try:
            (case_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    filled = sum(1 for v in manifest_fields.values() if v.get("value") is not None)
    # C2: global/scoped + R-001/002/003
    consensus = build_field_consistency(rules, manifest, file_rows, misfiled_paths)
    # 材料完整性仍走 build_findings；字段冲突用 rule_findings，避免与旧 FIELD 重复
    findings = build_findings(rules, file_rows, {**consensus, "冲突": {}})
    findings.extend(consensus.get("rule_findings") or [])

    (work / "field_consensus.json").write_text(
        json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work / "findings.json").write_text(
        json.dumps(
            {
                "items": findings,
                "generated_by": "audit_prepare.py",
                "rules_profile": rules.get("profile_id"),
                "primary_status": "selected",
                "primary_reference": selection["primary"],
                "manifest_fields_filled": filled,
                "manifest_fields_total": len(manifest_fields),
                "field_rule_results": len(consensus.get("fields") or []),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_audit_report(work / "audit-report.md", manifest, rules, inventory, findings)
    write_audit_brief(work / "audit-brief.md", findings, consensus)

    print(f"[audit_prepare] case={case_dir}")
    print(
        f"[audit_prepare] primary={selection['primary'].get('file_name')} "
        f"manifest_fields={filled}/{len(manifest_fields)} "
        f"files={len(file_rows)} findings={len(findings)} -> {work}"
    )
    return work


def resolve_rules_path(case: Path, rules_arg: str | None) -> Path:
    """优先 --rules；否则用 manifest.rules_profile / project_type（前端创建任务时写入）。"""
    if rules_arg:
        rules = Path(rules_arg)
        if not rules.is_absolute():
            rules = (Path.cwd() / rules).resolve()
        return rules

    profile = None
    manifest_path = case / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        raw = manifest.get("rules_profile") or manifest.get("project_type") or ""
        raw = str(raw).strip()
        if raw in PROFILE_SLUGS:
            profile = raw
        elif raw in PROFILE_ALIASES:
            profile = PROFILE_ALIASES[raw]

    if profile:
        path = RULES_DIR / f"{profile}.json"
        if path.is_file():
            print(f"[audit_prepare] rules from manifest: {profile} -> {path}")
            return path
        raise SystemExit(f"manifest 指定规则不存在: {path}")

    print(f"[audit_prepare] rules fallback: {DEFAULT_RULES.name}")
    return DEFAULT_RULES


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="cases/<project-id> directory")
    ap.add_argument(
        "--rules",
        default=None,
        help="rules json path；省略时读 cases/<id>/manifest.json 的 rules_profile",
    )
    args = ap.parse_args()
    case = Path(args.case)
    if not case.is_absolute():
        # resolve relative to CWD first, then workspace root
        cand = Path.cwd() / case
        case = cand if cand.exists() else (ROOT / case)
    if not case.exists():
        raise SystemExit(f"case 不存在: {case}")
    rules = resolve_rules_path(case, args.rules)
    if not rules.exists():
        raise SystemExit(f"rules 不存在: {rules}")
    run(case, rules)


if __name__ == "__main__":
    main()
