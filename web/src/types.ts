/** 与 audit_prepare findings 对齐的核查状态 */
export type FindingStatus =
  | 'provided'
  | 'missing'
  | 'suspect_duplicate_or_misfiled'
  | 'needs_human_review'
  | 'unscanned'

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

export interface Project {
  id: string
  userId: string
  name: string
  code?: string
  batchLabel: string
  createdAt: string
  updatedAt: string
  auditStatus: ProjectAuditStatus
  files: ProjectFile[]
  folderMarks: FolderMark[]
  summary?: AuditSummary
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
