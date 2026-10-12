import type { ProjectFile, ProjectType, UploadSource } from '../types'

export type AuditLaunch = {
  caseId: string
  sessionId: string | null
  aghUrl: string
  status: 'starting' | 'running' | 'error'
  message: string
  pid?: number
  reused?: boolean
}

export type AghClientConfig = {
  edaRoot: string
  aghCli: string
  aghWebOrigin: string
  profile: string
}

export async function apiGetConfig(): Promise<AghClientConfig> {
  const res = await fetch('/api/config')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<AghClientConfig>
}

function uid() {
  return `f_${crypto.randomUUID().slice(0, 10)}`
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { error?: string }
    if (data.error) return data.error
  } catch {
    /* ignore */
  }
  return res.statusText || `HTTP ${res.status}`
}

export async function apiCreateCase(
  id: string,
  name: string,
  projectType: ProjectType,
  batchLabel?: string,
) {
  const res = await fetch('/api/cases', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, name, projectType, batchLabel }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function apiRenameCase(id: string, name: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

function toProjectFiles(
  listed: Array<{ relativePath: string; name: string; size: number; kind: 'pdf' | 'other' }>,
  source: UploadSource,
): ProjectFile[] {
  return listed.map((f) => ({
    id: uid(),
    relativePath: f.relativePath,
    name: f.name,
    size: f.size,
    kind: f.kind,
    source,
  }))
}

/** 上传多个本地文件（PDF / 文件夹条目），保留 relativePath */
export async function apiUploadFiles(
  caseId: string,
  items: Array<{ file: File; relativePath: string }>,
  source: UploadSource,
  projectName?: string,
): Promise<ProjectFile[]> {
  if (!items.length) return []
  const form = new FormData()
  const paths: string[] = []
  for (const item of items) {
    form.append('files', item.file, item.file.name)
    paths.push(item.relativePath)
  }
  form.append('relativePaths', JSON.stringify(paths))
  if (projectName) form.append('projectName', projectName)

  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/files`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await parseError(res))
  const data = (await res.json()) as {
    files: Array<{ relativePath: string; name: string; size: number; kind: 'pdf' | 'other' }>
  }
  return toProjectFiles(data.files, source)
}

export async function apiUploadZip(
  caseId: string,
  zip: File,
  projectName?: string,
): Promise<ProjectFile[]> {
  const form = new FormData()
  form.append('zip', zip, zip.name)
  if (projectName) form.append('projectName', projectName)
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/files`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await parseError(res))
  const data = (await res.json()) as {
    files: Array<{ relativePath: string; name: string; size: number; kind: 'pdf' | 'other' }>
  }
  return toProjectFiles(data.files, 'zip')
}

export async function apiListFiles(caseId: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/files`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<{
    files: Array<{ relativePath: string; name: string; size: number; kind: 'pdf' | 'other' }>
    extraFolders: string[]
  }>
}

export async function apiCreateFolder(caseId: string, folderPath: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/folders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: folderPath }),
  })
  if (!res.ok) throw new Error(await parseError(res))
}

export async function apiRenameFile(caseId: string, from: string, to: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/files/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from, to }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return (await res.json()) as { relativePath: string }
}

export async function apiMoveFile(caseId: string, from: string, targetFolder: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/files/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from, targetFolder }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return (await res.json()) as { relativePath: string }
}

export async function apiDeleteFile(caseId: string, relativePath: string) {
  const res = await fetch(
    `/api/cases/${encodeURIComponent(caseId)}/files?path=${encodeURIComponent(relativePath)}`,
    { method: 'DELETE' },
  )
  if (!res.ok) throw new Error(await parseError(res))
}

export async function apiRenameFolder(caseId: string, from: string, to: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/folders/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from, to }),
  })
  if (!res.ok) throw new Error(await parseError(res))
}

export async function apiDeleteFolder(caseId: string, folderPath: string) {
  const res = await fetch(
    `/api/cases/${encodeURIComponent(caseId)}/folders?path=${encodeURIComponent(folderPath)}`,
    { method: 'DELETE' },
  )
  if (!res.ok) throw new Error(await parseError(res))
}

export async function apiStartAudit(
  caseId: string,
  name: string,
  projectType: ProjectType,
): Promise<AuditLaunch> {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, projectType }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<AuditLaunch>
}

export async function apiAuditStatus(caseId: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/audit/status`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<{
    caseId: string
    running: boolean
    sessionId: string | null
    aghUrl: string
    pid?: number
  }>
}

export async function apiCancelAudit(caseId: string, pid?: number) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/audit/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(pid != null ? { pid } : {}),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<{ ok: true; killed: boolean }>
}

export async function apiGetFindings(caseId: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/findings`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<{
    ready: boolean
    findings: { items?: unknown[] } | null
    sessionId?: string | null
    aghUrl?: string
  }>
}

/** 预取本仓库最近 AGH 会话（用于跳转，不启动核查） */
export async function apiLatestAghSession() {
  const res = await fetch('/api/agh/session')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<{ sessionId: string | null; aghUrl: string }>
}

export async function apiStatementStatus(caseId: string) {
  const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/statement`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<{
    ready: boolean
    generating: boolean
    fileName: string | null
    hasBody: boolean
    hasMeta: boolean
  }>
}

export function statementDownloadUrl(caseId: string) {
  return `/api/cases/${encodeURIComponent(caseId)}/statement/download`
}
