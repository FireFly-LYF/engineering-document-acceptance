import type { AppState, Project, UserProfile } from './types'

const KEY = 'eda-archive-check-v1'

function empty(): AppState {
  return { user: null, projects: [], activeProjectId: null }
}

export function loadState(): AppState {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return empty()
    const parsed = JSON.parse(raw) as AppState
    if (!parsed || typeof parsed !== 'object') return empty()
    return {
      user: parsed.user ?? null,
      projects: Array.isArray(parsed.projects) ? parsed.projects : [],
      activeProjectId: parsed.activeProjectId ?? null,
    }
  } catch {
    return empty()
  }
}

export function saveState(state: AppState) {
  localStorage.setItem(KEY, JSON.stringify(state))
}

export function createUser(displayName: string): UserProfile {
  const name = displayName.trim() || '核查员'
  return {
    id: `u_${crypto.randomUUID().slice(0, 8)}`,
    displayName: name,
    createdAt: new Date().toISOString(),
  }
}

export function createProject(userId: string, name: string, batchLabel?: string): Project {
  const now = new Date().toISOString()
  const batch =
    batchLabel?.trim() ||
    `批次 ${new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
  return {
    id: `p_${crypto.randomUUID().slice(0, 10)}`,
    userId,
    name: name.trim() || '未命名工程',
    batchLabel: batch,
    createdAt: now,
    updatedAt: now,
    auditStatus: 'draft',
    files: [],
    folderMarks: [],
  }
}

export function touchProject(p: Project): Project {
  return { ...p, updatedAt: new Date().toISOString() }
}
