import type { AppState, Project, ProjectType, UserProfile } from './types'

const KEY = 'eda-archive-check-v1'

export const UNNAMED_PROJECT = '未命名工程'

export const PROJECT_TYPE_OPTIONS: Array<{ value: ProjectType; label: string }> = [
  { value: 'housing-construction', label: '房屋建筑工程' },
  { value: 'road-bridge', label: '道路/桥梁工程' },
  { value: 'municipal-pipeline', label: '市政管线工程' },
]

const PROJECT_TYPE_SET = new Set<string>(PROJECT_TYPE_OPTIONS.map((o) => o.value))

export function isProjectType(value: unknown): value is ProjectType {
  return typeof value === 'string' && PROJECT_TYPE_SET.has(value)
}

export function projectTypeLabel(type: ProjectType): string {
  return PROJECT_TYPE_OPTIONS.find((o) => o.value === type)?.label ?? type
}

export function isUnnamedProject(name: string) {
  return !name.trim() || name.trim() === UNNAMED_PROJECT
}

/** 正式核查要求：已选工程类型 + 已填项目名称 */
export function canStartFormalAudit(p: Pick<Project, 'name' | 'projectType' | 'files'>) {
  return Boolean(p.files.length) && isProjectType(p.projectType) && !isUnnamedProject(p.name)
}

function empty(): AppState {
  return { user: null, projects: [], activeProjectId: null }
}

/** 刷新/重启后 in-flight 核查已中断，不能继续显示「核查中」 */
function reviveProject(p: Project): Project {
  const projectType: ProjectType = isProjectType(p.projectType)
    ? p.projectType
    : 'housing-construction'
  const base: Project = { ...p, projectType }
  if (base.auditStatus !== 'auditing') return base
  return {
    ...base,
    auditStatus: base.files?.length ? 'ready' : 'draft',
    aghMessage: undefined,
  }
}

export function loadState(): AppState {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return empty()
    const parsed = JSON.parse(raw) as AppState
    if (!parsed || typeof parsed !== 'object') return empty()
    const projects = Array.isArray(parsed.projects)
      ? parsed.projects.map((p) => reviveProject(p as Project))
      : []
    return {
      user: parsed.user ?? null,
      projects,
      activeProjectId: parsed.activeProjectId ?? null,
    }
  } catch {
    return empty()
  }
}

export function saveState(state: AppState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state))
  } catch {
    // 配额或隐私模式失败时不拖垮整页（读取文件夹后白屏的常见原因）
    try {
      const slim: AppState = {
        ...state,
        projects: state.projects.map((p) => ({
          ...p,
          files: p.files.slice(0, 200),
          folderMarks: [],
          summary: undefined,
        })),
      }
      localStorage.setItem(KEY, JSON.stringify(slim))
    } catch {
      /* ignore */
    }
  }
}

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

/** 用户未填名称时的 ID：精确到分钟，如 2026_10_12_1212 */
export function formatUserIdTime(d = new Date()): string {
  return `${d.getFullYear()}_${pad2(d.getMonth() + 1)}_${pad2(d.getDate())}_${pad2(d.getHours())}${pad2(d.getMinutes())}`
}

/** case 目录名：仅日期时间，精确到秒，如 2026_10_12_121230 */
export function formatCaseIdTime(d = new Date()): string {
  return `${d.getFullYear()}_${pad2(d.getMonth() + 1)}_${pad2(d.getDate())}_${pad2(d.getHours())}${pad2(d.getMinutes())}${pad2(d.getSeconds())}`
}

export function createUser(displayName: string): UserProfile {
  const name = displayName.trim()
  const minuteId = formatUserIdTime()
  return {
    id: name ? `u_${crypto.randomUUID().slice(0, 8)}` : minuteId,
    displayName: name || minuteId,
    createdAt: new Date().toISOString(),
  }
}

/** 工程目录 ID：仅 YYYY_MM_DD_HHMMSS（不含用户名） */
export function makeCaseId(at = new Date()): string {
  return formatCaseIdTime(at)
}

export function createProject(
  userId: string,
  name: string,
  projectType: ProjectType,
  batchLabel?: string,
  takenIds?: Iterable<string>,
): Project {
  const trimmed = name.trim()
  if (!trimmed || trimmed === UNNAMED_PROJECT) {
    throw new Error('请填写项目名称')
  }
  if (!isProjectType(projectType)) {
    throw new Error('请选择工程类型')
  }
  const now = new Date().toISOString()
  const batch =
    batchLabel?.trim() ||
    `批次 ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
  const taken = new Set(takenIds)
  let id = makeCaseId()
  // 同一秒内冲突时顺延一秒，尽量保持「纯日期时间」目录名
  let guard = 0
  while (taken.has(id) && guard < 60) {
    guard += 1
    id = formatCaseIdTime(new Date(Date.now() + guard * 1000))
  }
  if (taken.has(id)) id = `${makeCaseId()}_${crypto.randomUUID().slice(0, 4)}`
  return {
    id,
    userId,
    name: trimmed,
    projectType,
    batchLabel: batch,
    createdAt: now,
    updatedAt: now,
    auditStatus: 'draft',
    files: [],
    extraFolders: [],
    folderMarks: [],
  }
}

export function touchProject(p: Project): Project {
  return { ...p, updatedAt: new Date().toISOString() }
}
