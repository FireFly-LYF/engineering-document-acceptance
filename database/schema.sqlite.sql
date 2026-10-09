-- Local executable schema. Every extracted fact is tied to one immutable audit run.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_migration (
  version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS registry_bundle (
  id TEXT PRIMARY KEY, version TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE,
  reference_markdown TEXT NOT NULL, snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tag_definition (
  bundle_id TEXT NOT NULL REFERENCES registry_bundle(id), code TEXT NOT NULL,
  name TEXT NOT NULL, stage TEXT NOT NULL, definition_json TEXT NOT NULL CHECK(json_valid(definition_json)),
  PRIMARY KEY(bundle_id, code)
);
CREATE TABLE IF NOT EXISTS label_definition (
  bundle_id TEXT NOT NULL REFERENCES registry_bundle(id), code TEXT NOT NULL,
  name TEXT NOT NULL, value_type TEXT NOT NULL, comparison_scope TEXT NOT NULL,
  definition_json TEXT NOT NULL CHECK(json_valid(definition_json)), PRIMARY KEY(bundle_id, code)
);
CREATE TABLE IF NOT EXISTS tag_label_binding (
  bundle_id TEXT NOT NULL, tag_code TEXT NOT NULL, label_code TEXT NOT NULL,
  extraction_enabled INTEGER NOT NULL DEFAULT 1 CHECK(extraction_enabled IN (0,1)),
  PRIMARY KEY(bundle_id, tag_code, label_code),
  FOREIGN KEY(bundle_id, tag_code) REFERENCES tag_definition(bundle_id, code),
  FOREIGN KEY(bundle_id, label_code) REFERENCES label_definition(bundle_id, code)
);
CREATE TABLE IF NOT EXISTS rule_definition (
  bundle_id TEXT NOT NULL REFERENCES registry_bundle(id), code TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('presence','identity','consistency','chronology','duplicate','coverage','content')),
  name TEXT NOT NULL, definition_json TEXT NOT NULL CHECK(json_valid(definition_json)),
  PRIMARY KEY(bundle_id, code)
);
CREATE TABLE IF NOT EXISTS project (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, external_code TEXT,
  region_code TEXT, use_type TEXT, fire_category TEXT CHECK(fire_category IN ('special','other','not_applicable','unknown')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS project_scope (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES project(id), parent_id TEXT,
  kind TEXT NOT NULL CHECK(kind IN ('project','unit','discipline','location','contract','sample','event','drawing')),
  name TEXT NOT NULL, attributes_json TEXT NOT NULL CHECK(json_valid(attributes_json)),
  UNIQUE(id, project_id), FOREIGN KEY(parent_id, project_id) REFERENCES project_scope(id, project_id)
);
CREATE TABLE IF NOT EXISTS project_reference_value (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES project(id), scope_id TEXT,
  bundle_id TEXT NOT NULL, label_code TEXT NOT NULL, raw_value TEXT NOT NULL, normalized_value TEXT,
  source_type TEXT NOT NULL CHECK(source_type IN ('manifest','approved_document','review_decision')),
  source_reference TEXT NOT NULL, valid_from TEXT, valid_to TEXT,
  FOREIGN KEY(scope_id, project_id) REFERENCES project_scope(id, project_id),
  FOREIGN KEY(bundle_id, label_code) REFERENCES label_definition(bundle_id, code)
);
CREATE TABLE IF NOT EXISTS audit_run (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES project(id), bundle_id TEXT NOT NULL REFERENCES registry_bundle(id),
  run_no INTEGER NOT NULL CHECK(run_no > 0), audit_stage TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','running','succeeded','partial','failed')),
  input_sha256 TEXT NOT NULL, config_sha256 TEXT NOT NULL,
  context_snapshot_json TEXT NOT NULL CHECK(json_valid(context_snapshot_json)),
  coverage_snapshot_json TEXT NOT NULL CHECK(json_valid(coverage_snapshot_json)),
  engine_version TEXT NOT NULL, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at TEXT,
  UNIQUE(project_id, run_no), UNIQUE(id, project_id), UNIQUE(id, bundle_id)
);
CREATE TABLE IF NOT EXISTS source_file (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_run(id), relative_path TEXT NOT NULL,
  original_name TEXT NOT NULL, storage_path TEXT NOT NULL, mime_type TEXT NOT NULL,
  sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0), physical_page_count INTEGER,
  parse_status TEXT NOT NULL CHECK(parse_status IN ('pending','readable','partial','unreadable','unsupported')),
  parse_error_code TEXT, UNIQUE(run_id, relative_path), UNIQUE(id, run_id)
);
CREATE INDEX IF NOT EXISTS idx_source_file_hash ON source_file(run_id, sha256);
CREATE TABLE IF NOT EXISTS document_unit (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, project_id TEXT NOT NULL, source_file_id TEXT NOT NULL, bundle_id TEXT NOT NULL,
  unit_no INTEGER NOT NULL CHECK(unit_no > 0), tag_code TEXT NOT NULL,
  tag_origin TEXT NOT NULL CHECK(tag_origin IN ('upload','title_rule','agnes','review')),
  tag_status TEXT NOT NULL CHECK(tag_status IN ('proposed','verified','unknown','rejected')),
  identity_status TEXT NOT NULL CHECK(identity_status IN ('target_project','other_project','unresolved')),
  scope_id TEXT, scope_status TEXT NOT NULL CHECK(scope_status IN ('confirmed','unresolved')),
  classification_json TEXT NOT NULL CHECK(json_valid(classification_json)),
  UNIQUE(source_file_id, unit_no), UNIQUE(id, source_file_id, run_id), UNIQUE(id, run_id), UNIQUE(id, run_id, bundle_id),
  FOREIGN KEY(source_file_id, run_id) REFERENCES source_file(id, run_id),
  FOREIGN KEY(run_id, bundle_id) REFERENCES audit_run(id, bundle_id),
  FOREIGN KEY(run_id, project_id) REFERENCES audit_run(id, project_id),
  FOREIGN KEY(bundle_id, tag_code) REFERENCES tag_definition(bundle_id, code),
  FOREIGN KEY(scope_id, project_id) REFERENCES project_scope(id, project_id)
);
CREATE TABLE IF NOT EXISTS markdown_unit (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, source_file_id TEXT NOT NULL, unit_no INTEGER NOT NULL CHECK(unit_no > 0),
  physical_page_no INTEGER CHECK(physical_page_no > 0), logical_locator TEXT,
  source_type TEXT NOT NULL CHECK(source_type IN ('native_pdf','native_word','native_excel','native_csv','ocr','image_ocr')),
  markdown_path TEXT NOT NULL, source_map_path TEXT NOT NULL, text_sha256 TEXT NOT NULL,
  read_status TEXT NOT NULL CHECK(read_status IN ('readable','partial','unreadable')),
  UNIQUE(source_file_id, unit_no), UNIQUE(id, source_file_id, run_id), UNIQUE(id, run_id),
  FOREIGN KEY(source_file_id, run_id) REFERENCES source_file(id, run_id)
);
CREATE TABLE IF NOT EXISTS document_markdown (
  document_unit_id TEXT NOT NULL, markdown_unit_id TEXT NOT NULL, source_file_id TEXT NOT NULL, run_id TEXT NOT NULL,
  PRIMARY KEY(document_unit_id, markdown_unit_id),
  FOREIGN KEY(document_unit_id, source_file_id, run_id) REFERENCES document_unit(id, source_file_id, run_id),
  FOREIGN KEY(markdown_unit_id, source_file_id, run_id) REFERENCES markdown_unit(id, source_file_id, run_id)
);
CREATE TABLE IF NOT EXISTS source_fragment (
  id TEXT PRIMARY KEY, markdown_unit_id TEXT NOT NULL REFERENCES markdown_unit(id),
  fragment_no INTEGER NOT NULL CHECK(fragment_no > 0), text TEXT NOT NULL,
  source TEXT NOT NULL, bbox_json TEXT CHECK(bbox_json IS NULL OR json_valid(bbox_json)),
  table_id TEXT, row_index INTEGER CHECK(row_index >= 0), column_index INTEGER CHECK(column_index >= 0),
  logical_locator TEXT, UNIQUE(markdown_unit_id, fragment_no), UNIQUE(id, markdown_unit_id)
);
CREATE TABLE IF NOT EXISTS evidence_span (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, markdown_unit_id TEXT NOT NULL, fragment_id TEXT,
  quote_text TEXT NOT NULL, span_start INTEGER CHECK(span_start >= 0), span_end INTEGER,
  grounding_status TEXT NOT NULL CHECK(grounding_status IN ('verified_text','vision_transcription','unverified','rejected')),
  UNIQUE(id, markdown_unit_id), UNIQUE(id, run_id),
  CHECK(span_end IS NULL OR (span_start IS NOT NULL AND span_end >= span_start)),
  FOREIGN KEY(markdown_unit_id, run_id) REFERENCES markdown_unit(id, run_id),
  FOREIGN KEY(fragment_id, markdown_unit_id) REFERENCES source_fragment(id, markdown_unit_id)
);
CREATE TABLE IF NOT EXISTS field_candidate (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, source_file_id TEXT NOT NULL, document_unit_id TEXT NOT NULL,
  markdown_unit_id TEXT NOT NULL, bundle_id TEXT NOT NULL, label_code TEXT NOT NULL, evidence_id TEXT NOT NULL,
  raw_value TEXT NOT NULL, normalized_value TEXT, value_unit TEXT, source_label TEXT,
  value_role TEXT NOT NULL CHECK(value_role IN ('subject','reference','historical','aggregate','detail','unknown')),
  source TEXT NOT NULL CHECK(source IN ('native_rule','reference_search','agnes','review')),
  confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
  validation_status TEXT NOT NULL CHECK(validation_status IN ('accepted','needs_review','rejected')),
  rejection_reason TEXT, UNIQUE(id, document_unit_id, label_code), UNIQUE(id, run_id),
  FOREIGN KEY(document_unit_id, source_file_id, run_id) REFERENCES document_unit(id, source_file_id, run_id),
  FOREIGN KEY(markdown_unit_id, source_file_id, run_id) REFERENCES markdown_unit(id, source_file_id, run_id),
  FOREIGN KEY(document_unit_id, markdown_unit_id) REFERENCES document_markdown(document_unit_id, markdown_unit_id),
  FOREIGN KEY(document_unit_id, run_id, bundle_id) REFERENCES document_unit(id, run_id, bundle_id),
  FOREIGN KEY(bundle_id, label_code) REFERENCES label_definition(bundle_id, code),
  FOREIGN KEY(evidence_id, markdown_unit_id) REFERENCES evidence_span(id, markdown_unit_id)
);
CREATE INDEX IF NOT EXISTS idx_candidate_lookup ON field_candidate(run_id, label_code, validation_status);
CREATE TABLE IF NOT EXISTS field_selection (
  document_unit_id TEXT NOT NULL, label_code TEXT NOT NULL, candidate_id TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK(purpose IN ('display','identity')), rule_code TEXT NOT NULL DEFAULT '' CHECK(rule_code=''),
  selection_reason TEXT NOT NULL, PRIMARY KEY(document_unit_id, label_code, purpose, rule_code),
  FOREIGN KEY(candidate_id, document_unit_id, label_code) REFERENCES field_candidate(id, document_unit_id, label_code)
);
CREATE TABLE IF NOT EXISTS rule_evaluation (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL, bundle_id TEXT NOT NULL, rule_code TEXT NOT NULL,
  scope_key TEXT NOT NULL, applicability TEXT NOT NULL CHECK(applicability IN ('applicable','not_applicable','unknown')),
  result TEXT NOT NULL CHECK(result IN ('pass','fail','needs_review','not_applicable','not_evaluated')),
  reason_code TEXT NOT NULL, details_json TEXT NOT NULL CHECK(json_valid(details_json)),
  UNIQUE(run_id, rule_code, scope_key), UNIQUE(id, run_id),
  FOREIGN KEY(run_id, bundle_id) REFERENCES audit_run(id, bundle_id),
  FOREIGN KEY(bundle_id, rule_code) REFERENCES rule_definition(bundle_id, code),
  CHECK((applicability='not_applicable' AND result='not_applicable') OR
        (applicability='unknown' AND result='not_evaluated') OR
        (applicability='applicable' AND result IN ('pass','fail','needs_review')))
);
CREATE TABLE IF NOT EXISTS rule_document (
  evaluation_id TEXT NOT NULL, document_unit_id TEXT NOT NULL, run_id TEXT NOT NULL,
  relation TEXT NOT NULL CHECK(relation IN ('accepted','rejected','similar','needs_review')),
  reason_code TEXT NOT NULL, PRIMARY KEY(evaluation_id, document_unit_id),
  FOREIGN KEY(evaluation_id, run_id) REFERENCES rule_evaluation(id, run_id),
  FOREIGN KEY(document_unit_id, run_id) REFERENCES document_unit(id, run_id)
);
CREATE TABLE IF NOT EXISTS rule_candidate (
  evaluation_id TEXT NOT NULL, candidate_id TEXT NOT NULL, run_id TEXT NOT NULL,
  relation TEXT NOT NULL CHECK(relation IN ('selected','conflicting','reference','rejected')),
  PRIMARY KEY(evaluation_id, candidate_id, relation),
  FOREIGN KEY(evaluation_id, run_id) REFERENCES rule_evaluation(id, run_id),
  FOREIGN KEY(candidate_id, run_id) REFERENCES field_candidate(id, run_id)
);
CREATE TABLE IF NOT EXISTS audit_finding (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_run(id), evaluation_id TEXT,
  finding_type TEXT NOT NULL CHECK(finding_type IN ('missing','misfiled','field_conflict','duplicate','version_conflict','unreadable','rule_gap','coverage_gap','content_gap')),
  severity TEXT NOT NULL CHECK(severity IN ('info','warning','error')),
  status TEXT NOT NULL CHECK(status IN ('open','resolved','disputed')),
  title TEXT NOT NULL, reason_code TEXT NOT NULL, suggestion TEXT NOT NULL,
  details_json TEXT NOT NULL CHECK(json_valid(details_json)), UNIQUE(id, run_id),
  FOREIGN KEY(evaluation_id, run_id) REFERENCES rule_evaluation(id, run_id)
);
CREATE INDEX IF NOT EXISTS idx_finding_review ON audit_finding(run_id, status, finding_type);
CREATE TABLE IF NOT EXISTS finding_evidence (
  finding_id TEXT NOT NULL, evidence_id TEXT NOT NULL, run_id TEXT NOT NULL,
  relation TEXT NOT NULL CHECK(relation IN ('supports','contradicts','similar')),
  PRIMARY KEY(finding_id, evidence_id, relation),
  FOREIGN KEY(finding_id, run_id) REFERENCES audit_finding(id, run_id),
  FOREIGN KEY(evidence_id, run_id) REFERENCES evidence_span(id, run_id)
);
CREATE TABLE IF NOT EXISTS review_decision (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_run(id), finding_id TEXT,
  decision TEXT NOT NULL CHECK(decision IN ('confirm','dismiss','correct','request_more')),
  reviewer_ref TEXT NOT NULL, reason TEXT NOT NULL, evidence_ids_json TEXT NOT NULL CHECK(json_valid(evidence_ids_json)),
  before_json TEXT NOT NULL CHECK(json_valid(before_json)), after_json TEXT NOT NULL CHECK(json_valid(after_json)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(id, run_id),
  FOREIGN KEY(finding_id, run_id) REFERENCES audit_finding(id, run_id)
);
CREATE TABLE IF NOT EXISTS review_evidence (
  decision_id TEXT NOT NULL, evidence_id TEXT NOT NULL, run_id TEXT NOT NULL,
  PRIMARY KEY(decision_id, evidence_id),
  FOREIGN KEY(decision_id, run_id) REFERENCES review_decision(id, run_id),
  FOREIGN KEY(evidence_id, run_id) REFERENCES evidence_span(id, run_id)
);
CREATE TABLE IF NOT EXISTS model_call (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_run(id), purpose TEXT NOT NULL,
  model_name TEXT NOT NULL, prompt_sha256 TEXT NOT NULL, input_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('succeeded','failed','rejected')),
  latency_ms INTEGER NOT NULL CHECK(latency_ms >= 0), usage_json TEXT NOT NULL CHECK(json_valid(usage_json)),
  error_code TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS report_artifact (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES audit_run(id),
  kind TEXT NOT NULL CHECK(kind IN ('audit_json','audit_markdown','statement_markdown','statement_docx','evidence_index','test_report')),
  revision_no INTEGER NOT NULL CHECK(revision_no > 0), path TEXT NOT NULL, sha256 TEXT NOT NULL,
  validation_status TEXT NOT NULL CHECK(validation_status IN ('pending','passed','needs_review','failed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(run_id, kind, revision_no)
);
INSERT OR IGNORE INTO schema_migration(version) VALUES(1);
