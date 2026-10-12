/** 与 audit_prepare findings 对齐的核查状态 */
export type FindingStatus =
  | 'provided'
  | 'missing'
  | 'suspect_duplicate_or_misfiled'
  | 'needs_human_review'
  | 'unscanned'

/** 工程类型 slug；与 rules_profile / 规则文件名一致 */
export type ProjectType =
  | 'housing-construction'
  | 'road-bridge'
  | 'municipal-pipeline'

export type ProjectAuditStatus = 'draft' | 'ready' | 'auditing' | 'done' | 'error'

export type UploadSource = 'zip' | 'pdf' | 'folder'

export interface FileAnnotation {
  status: FindingStatus
  code?: string
  checklistName?: string
  reason?: string
  suggestion?: string
  severity?: 'info' | 'warning' | 'error'
}

export interface ProjectFile {
  id: string
  /** 相对路径，如 01-准备/A-01-xxx.pdf */
  relativePath: string
  name: string
  size: number
  kind: 'pdf' | 'other'
  source: UploadSource
  /** 核查后的标记 */
  annotation?: FileAnnotation
}

export interface FolderMark {
  path: string
  label: string
  summary: string
  tone: 'ok' | 'warn' | 'bad' | 'neutral'
  counts: Partial<Record<FindingStatus, number>>
}

export interface AuditSummary {
  provided: number
  missing: number
  misfiled: number
  review: number
  totalFiles: number
  generatedAt?: string
  note?: string
}

/** 主参考文件（manifest.primary_reference） */
export interface PrimaryReference {
  file_id: string
  file_name: string
  document_code: string
  source: 'user' | 'auto'
}

export type PrimarySelectionStatus = 'selected' | 'no_primary' | undefined

export interface PrimarySelection {
  status?: string
  reason?: string
  expected?: { code?: string; name?: string }
  candidates?: Array<{ path?: string; filename?: string; score?: number }>
  primary?: PrimaryReference | null
}

/** 字段候选（fields.json candidates[]） */
export interface FieldCandidate {
  field_key?: string
  name?: string
  value?: string | null
  page?: number | null
  evidence?: string | null
  source?: string
  confidence?: string
  bbox?: unknown
}

/** 单文件字段抽取结果 */
export interface FileFieldsEntry {
  page_count?: number
  candidates?: FieldCandidate[]
  summary?: Record<string, string>
  unreadable?: boolean
  unsupported_format?: boolean
}

export interface FieldsPayload {
  generated_by?: string
  generated_at?: string
  note?: string
  files?: Record<string, FileFieldsEntry>
}

/** 共识中各文件取值 */
export interface ConsensusValueByFile {
  file_id: string
  file_name?: string
  value?: string | null
  page?: number | null
  evidence?: string | null
  applicable: boolean
  reason?: string
  status?: string
  out_of_scope_value?: string | null
}

export interface FieldConsensusEntry {
  field_key: string
  field_name: string
  consistency?: string
  manifest_value?: string | null
  status: string
  values_by_file: ConsensusValueByFile[]
  rule_ids?: string[]
  reason?: string
  applicable_value_count?: number
  distinct_values?: string[]
}

export interface FieldConsensusPayload {
  fields?: FieldConsensusEntry[]
  rule_findings?: RuleFindingItem[]
  conflicts?: unknown[]
  excluded_misfiled?: string[]
  note?: string
  generated_by?: string
}

/** findings 中 RULE 条目 / consensus.rule_findings */
export interface RuleFindingItem {
  code?: string
  name?: string
  status?: string
  severity?: string
  reason?: string
  suggestion?: string
  field?: string
  field_name?: string
  rule_ids?: string[]
  consistency?: string
  matched_file?: string
  similar_files?: string[]
}

export interface EvidenceItem {
  file_id?: string
  field_key?: string
  name?: string
  value?: string | null
  page?: number | null
  evidence?: string | null
  source?: string
  confidence?: string
  bbox?: unknown
}

export interface EvidencePayload {
  items?: EvidenceItem[]
  generated_by?: string
}

/** Round D 字段/共识/证据 */
export interface AuditDetail {
  ready: boolean
  fields?: FieldsPayload | null
  field_consensus?: FieldConsensusPayload | null
  evidence?: EvidencePayload | null
}

export interface Project {
  id: string
  userId: string
  name: string
  /** 工程类型（任务身份）；映射 rules_profile */
  projectType: ProjectType
  code?: string
  batchLabel: string
  createdAt: string
  updatedAt: string
  auditStatus: ProjectAuditStatus
  files: ProjectFile[]
  /** 用户新建的空目录（尚无文件时仍展示） */
  extraFolders?: string[]
  folderMarks: FolderMark[]
  summary?: AuditSummary
  /** 当前主参考文件（用户指定或脚本自动选择） */
  primaryReference?: PrimaryReference | null
  /** prepare 选择结果：selected / no_primary */
  primarySelectionStatus?: PrimarySelectionStatus
  primarySelection?: PrimarySelection | null
  /** Round D：字段级 / 规则级产物 */
  auditDetail?: AuditDetail | null
  /** findings.items 缓存（规则列表兜底） */
  findingItems?: RuleFindingItem[]
  /** AGH 会话深链 */
  aghUrl?: string
  aghSessionId?: string
  aghMessage?: string
  /** 本机 AGH -p 进程，用于打断 */
  aghPid?: number
  /** 核查情况说明 Word：waiting=生成中 ready=可下载 */
  statementStatus?: 'idle' | 'waiting' | 'ready'
  statementFileName?: string
}

export interface UserProfile {
  id: string
  displayName: string
  createdAt: string
}

export interface AppState {
  user: UserProfile | null
  projects: Project[]
  activeProjectId: string | null
}
