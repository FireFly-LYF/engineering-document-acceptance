import type { AppState, Project, UserProfile } from './types'

const KEY = 'eda-archive-check-v1'

export const UNNAMED_PROJECT = '未命名工程'

export function isUnnamedProject(name: string) {
  return !name.trim() || name.trim() === UNNAMED_PROJECT
}

function empty(): AppState {
  return { user: null, projects: [], activeProjectId: null }
}

/** 刷新/重启后 in-flight 核查已中断，不能继续显示「核查中」 */
function reviveProject(p: Project): Project {
  if (p.auditStatus !== 'auditing') return p
  return {
    ...p,
    auditStatus: p.files?.length ? 'ready' : 'draft',
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

export function createUser(displayName: string): UserProfile {
  const name = displayName.trim() || '核查员'
  return {
    id: `u_${crypto.randomUUID().slice(0, 8)}`,
    displayName: name,
    createdAt: new Date().toISOString(),
  }
}

/** 目录名安全片段：去掉路径非法字符，保留中文 */
function sanitizeUserForCaseId(displayName: string): string {
  const s = displayName
    .trim()
    .replace(/[\\/:*?"<>|\s]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 32)
  return s || '未命名'
}

function formatCaseTime(d = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

/** 工程目录 ID：用户名-YYYYMMDD-HHmmss */
export function makeCaseId(displayName: string, at = new Date()): string {
  return `${sanitizeUserForCaseId(displayName)}-${formatCaseTime(at)}`
}

export function createProject(
  userId: string,
  displayName: string,
  name: string,
  batchLabel?: string,
  takenIds?: Iterable<string>,
): Project {
  const now = new Date().toISOString()
  const batch =
    batchLabel?.trim() ||
    `批次 ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
  const taken = new Set(takenIds)
  let id = makeCaseId(displayName)
  if (taken.has(id)) id = `${id}-${crypto.randomUUID().slice(0, 4)}`
  return {
    id,
    userId,
    name: name.trim() || UNNAMED_PROJECT,
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
