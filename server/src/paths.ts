import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

/** engineering-document-acceptance 仓库根 */
export const EDA_ROOT = path.resolve(
  process.env.EDA_ROOT || path.join(here, '..', '..'),
)

export const CASES_DIR = path.join(EDA_ROOT, 'cases')

export const AGH_CLI = path.resolve(
  process.env.AGH_CLI ||
    path.join(EDA_ROOT, '..', 'agnes-harness', 'packages', 'cli', 'dist', 'local', 'agnes.mjs'),
)

export const AGH_WEB_ORIGIN = (process.env.AGH_WEB_ORIGIN || 'http://127.0.0.1:4177').replace(
  /\/$/,
  '',
)

export const AGNES_PROFILE = process.env.AGNES_PROFILE || 'local-dev'

export const PORT = Number(process.env.PORT || 8787)

const CASE_ID_RE = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/

export function assertCaseId(id: string): string {
  if (!CASE_ID_RE.test(id)) {
    throw Object.assign(new Error('非法工程 ID'), { status: 400 })
  }
  return id
}

/** 规范化相对路径，禁止跳出 files/；去掉多余的 files/ 前缀避免落成 files/files/… */
export function safeRelPath(raw: string): string {
  let norm = raw.replace(/\\/g, '/').replace(/^\/+/, '').replace(/\/+/g, '/')
  while (/^files\//i.test(norm)) {
    norm = norm.replace(/^files\//i, '')
  }
  if (!norm || norm.includes('\0') || norm.split('/').some((s) => s === '..' || s === '.')) {
    throw Object.assign(new Error(`非法路径: ${raw}`), { status: 400 })
  }
  return norm
}

export function caseDir(id: string) {
  return path.join(CASES_DIR, assertCaseId(id))
}

export function filesDir(id: string) {
  return path.join(caseDir(id), 'files')
}

export function workDir(id: string) {
  return path.join(caseDir(id), '_work')
}

export function resolveUnderFiles(id: string, rel: string) {
  const safe = safeRelPath(rel)
  const abs = path.resolve(filesDir(id), ...safe.split('/'))
  const root = path.resolve(filesDir(id))
  if (abs !== root && !abs.startsWith(root + path.sep)) {
    throw Object.assign(new Error('路径越界'), { status: 400 })
  }
  return { abs, rel: safe }
}
