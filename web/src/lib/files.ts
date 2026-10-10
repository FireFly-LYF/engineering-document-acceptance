import JSZip from 'jszip'
import type { ProjectFile, UploadSource } from '../types'

function uid() {
  return `f_${crypto.randomUUID().slice(0, 10)}`
}

function normalizePath(p: string) {
  return p.replace(/\\/g, '/').replace(/^\.?\//, '')
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

export function groupByFolder(files: ProjectFile[]) {
  const groups = new Map<string, ProjectFile[]>()
  for (const f of files) {
    const parts = f.relativePath.split('/')
    const folder = parts.length > 1 ? parts.slice(0, -1).join('/') : '（根目录）'
    const list = groups.get(folder) || []
    list.push(f)
    groups.set(folder, list)
  }
  return groups
}
