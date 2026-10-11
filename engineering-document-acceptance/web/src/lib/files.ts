import JSZip from 'jszip'
import type { ProjectFile, UploadSource } from '../types'

export const ROOT_FOLDER = '（根目录）'

function uid() {
  return `f_${crypto.randomUUID().slice(0, 10)}`
}

export function normalizePath(p: string) {
  return p
    .replace(/\\/g, '/')
    .replace(/^\.?\//, '')
    .replace(/\/+/g, '/')
    .replace(/\/$/, '')
}

function isPdf(name: string) {
  return name.toLowerCase().endsWith('.pdf')
}

function toProjectFile(
  relativePath: string,
  size: number,
  source: UploadSource,
): ProjectFile {
  const path = normalizePath(relativePath)
  const name = path.split('/').pop() || path
  return {
    id: uid(),
    relativePath: path,
    name,
    size,
    kind: isPdf(name) ? 'pdf' : 'other',
    source,
  }
}

/** 去掉扩展名，用作工程默认名称 */
export function stemFromFileName(name: string) {
  const base = name.split('/').pop() || name
  const stem = base.replace(/\.[^.]+$/, '').trim()
  return stem || base.trim()
}

/** 清单文件名 / 阶段目录，不能当工程名（否则 audit_prepare 会把真项目 PDF 全判错传） */
const DOC_LIKE_NAME =
  /^[A-G]-\d{2}\b|[许可合同报告证明记录细则报审验收竣工图]|建设工程|监理规划|施工组织/
const STAGE_DIR = /^\d{2}-/

function looksLikeDocumentName(name: string) {
  return DOC_LIKE_NAME.test(name.trim())
}

/**
 * 未命名工程的自动命名：优先用有意义的包名目录；
 * 绝不使用 A-01/G-02 这类资料文件名（会导致「全文错传」误判）。
 */
export function suggestProjectName(files: ProjectFile[]): string | null {
  if (!files.length) return null
  for (const f of files) {
    const parts = normalizePath(f.relativePath)
      .replace(/^files\//i, '')
      .split('/')
      .filter(Boolean)
    if (parts.length >= 2) {
      const top = parts[0]
      if (top && !STAGE_DIR.test(top) && !looksLikeDocumentName(top) && top.length >= 4) {
        return top
      }
    }
  }
  const stem = stemFromFileName(files[0].name)
  if (!stem || looksLikeDocumentName(stem)) return null
  return stem
}

/** @deprecated 使用 suggestProjectName；保留以免外部引用断裂 */
export function nameFromFirstFile(files: ProjectFile[]): string | null {
  return suggestProjectName(files)
}

/** 多选 PDF */
export async function ingestPdfs(fileList: FileList | File[]): Promise<ProjectFile[]> {
  const files = Array.from(fileList).filter((f) => isPdf(f.name) || f.type === 'application/pdf')
  return files.map((f) => toProjectFile(f.name, f.size, 'pdf'))
}

/** 本地文件夹（webkitdirectory / showDirectoryPicker） */
export async function ingestFolder(fileList: FileList | File[]): Promise<ProjectFile[]> {
  const out: ProjectFile[] = []
  for (const f of Array.from(fileList)) {
    const rel =
      (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name
    if (!rel || rel.endsWith('/')) continue
    // 跳过隐藏与系统垃圾
    if (rel.split('/').some((seg) => seg.startsWith('.') || seg === '__MACOSX')) continue
    out.push(toProjectFile(rel, f.size, 'folder'))
  }
  return out
}

/** ZIP 包：展开为相对路径列表（框架阶段不落盘二进制） */
export async function ingestZip(file: File): Promise<ProjectFile[]> {
  const zip = await JSZip.loadAsync(file)
  const out: ProjectFile[] = []
  const entries = Object.values(zip.files)
  for (const entry of entries) {
    if (entry.dir) continue
    const path = normalizePath(entry.name)
    if (path.split('/').some((seg) => seg.startsWith('.') || seg === '__MACOSX')) continue
    // 估算大小：框架阶段用 uncompressedSize 或 0
    const size = (entry as JSZip.JSZipObject & { _data?: { uncompressedSize?: number } })._data
      ?.uncompressedSize
    out.push(toProjectFile(path, typeof size === 'number' ? size : 0, 'zip'))
  }
  return out
}

export function mergeFiles(existing: ProjectFile[], incoming: ProjectFile[]): ProjectFile[] {
  const map = new Map(existing.map((f) => [f.relativePath.toLowerCase(), f]))
  for (const f of incoming) {
    map.set(f.relativePath.toLowerCase(), f)
  }
  return Array.from(map.values()).sort((a, b) =>
    a.relativePath.localeCompare(b.relativePath, 'zh-CN'),
  )
}

export function formatBytes(n: number) {
  if (!n || n < 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function parentFolder(relativePath: string): string {
  const parts = normalizePath(relativePath).split('/')
  return parts.length > 1 ? parts.slice(0, -1).join('/') : ROOT_FOLDER
}

export function groupByFolder(files: ProjectFile[]) {
  const groups = new Map<string, ProjectFile[]>()
  for (const f of files) {
    const folder = parentFolder(f.relativePath)
    const list = groups.get(folder) || []
    list.push(f)
    groups.set(folder, list)
  }
  return groups
}

/** 从文件路径 + 额外空目录汇总全部目录 */
export function listFolders(files: ProjectFile[], extraFolders: string[] = []): string[] {
  const set = new Set<string>()
  for (const f of files) {
    const parts = normalizePath(f.relativePath).split('/')
    for (let i = 1; i < parts.length; i++) {
      set.add(parts.slice(0, i).join('/'))
    }
  }
  for (const folder of extraFolders) {
    const path = normalizePath(folder)
    if (path) set.add(path)
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

function pathTaken(files: ProjectFile[], relativePath: string, exceptId?: string) {
  const key = normalizePath(relativePath).toLowerCase()
  return files.some((f) => f.id !== exceptId && f.relativePath.toLowerCase() === key)
}

function uniquePath(files: ProjectFile[], desired: string, exceptId?: string): string {
  let path = normalizePath(desired)
  if (!pathTaken(files, path, exceptId)) return path
  const parts = path.split('/')
  const fileName = parts.pop() || path
  const dir = parts.join('/')
  const dot = fileName.lastIndexOf('.')
  const stem = dot > 0 ? fileName.slice(0, dot) : fileName
  const ext = dot > 0 ? fileName.slice(dot) : ''
  let i = 2
  while (true) {
    const candidate = normalizePath(`${dir ? `${dir}/` : ''}${stem} (${i})${ext}`)
    if (!pathTaken(files, candidate, exceptId)) return candidate
    i += 1
  }
}

function applyPath(file: ProjectFile, relativePath: string): ProjectFile {
  const path = normalizePath(relativePath)
  const name = path.split('/').pop() || path
  return {
    ...file,
    relativePath: path,
    name,
    kind: isPdf(name) ? 'pdf' : 'other',
    annotation: undefined,
  }
}

export function deleteFile(files: ProjectFile[], fileId: string): ProjectFile[] {
  return files.filter((f) => f.id !== fileId)
}

export function renameFile(
  files: ProjectFile[],
  fileId: string,
  newName: string,
): ProjectFile[] {
  const file = files.find((f) => f.id === fileId)
  if (!file) return files
  const clean = newName.trim().replace(/[\\/]/g, '')
  if (!clean) return files
  const folder = parentFolder(file.relativePath)
  const nextPath =
    folder === ROOT_FOLDER ? clean : `${folder}/${clean}`
  const path = uniquePath(files, nextPath, fileId)
  return files
    .map((f) => (f.id === fileId ? applyPath(f, path) : f))
    .sort((a, b) => a.relativePath.localeCompare(b.relativePath, 'zh-CN'))
}

/** targetFolder 为 ROOT_FOLDER 或相对目录路径 */
export function moveFile(
  files: ProjectFile[],
  fileId: string,
  targetFolder: string,
): ProjectFile[] {
  const file = files.find((f) => f.id === fileId)
  if (!file) return files
  const folder = targetFolder === ROOT_FOLDER ? '' : normalizePath(targetFolder)
  const nextPath = folder ? `${folder}/${file.name}` : file.name
  const path = uniquePath(files, nextPath, fileId)
  return files
    .map((f) => (f.id === fileId ? applyPath(f, path) : f))
    .sort((a, b) => a.relativePath.localeCompare(b.relativePath, 'zh-CN'))
}

export function renameFolder(
  files: ProjectFile[],
  fromFolder: string,
  toFolder: string,
): ProjectFile[] {
  const from = normalizePath(fromFolder)
  const to = normalizePath(toFolder)
  if (!from || !to || from === to) return files

  const outsiders = files.filter(
    (f) => f.relativePath !== from && !f.relativePath.startsWith(`${from}/`),
  )
  let working = [...outsiders]
  const moved: ProjectFile[] = []
  for (const f of files) {
    if (f.relativePath !== from && !f.relativePath.startsWith(`${from}/`)) continue
    const next = to + f.relativePath.slice(from.length)
    const path = uniquePath(working, next)
    const updated = applyPath(f, path)
    moved.push(updated)
    working = [...working, updated]
  }
  return [...outsiders, ...moved].sort((a, b) =>
    a.relativePath.localeCompare(b.relativePath, 'zh-CN'),
  )
}

export function deleteFolder(files: ProjectFile[], folder: string): ProjectFile[] {
  const prefix = normalizePath(folder)
  if (!prefix) return files
  return files.filter((f) => f.relativePath !== prefix && !f.relativePath.startsWith(`${prefix}/`))
}

export function remapExtraFolders(
  extraFolders: string[],
  fromFolder: string,
  toFolder: string | null,
): string[] {
  const from = normalizePath(fromFolder)
  if (!from) return extraFolders
  const next: string[] = []
  for (const folder of extraFolders) {
    const path = normalizePath(folder)
    if (path === from || path.startsWith(`${from}/`)) {
      if (toFolder == null) continue
      const mapped = normalizePath(toFolder) + path.slice(from.length)
      if (mapped) next.push(mapped)
    } else {
      next.push(path)
    }
  }
  return Array.from(new Set(next)).sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export function addExtraFolder(extraFolders: string[], folder: string): string[] {
  const path = normalizePath(folder)
  if (!path) return extraFolders
  const set = new Set(extraFolders.map(normalizePath))
  set.add(path)
  // 同时记下父路径，便于树状展示
  const parts = path.split('/')
  for (let i = 1; i < parts.length; i++) {
    set.add(parts.slice(0, i).join('/'))
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'))
}
