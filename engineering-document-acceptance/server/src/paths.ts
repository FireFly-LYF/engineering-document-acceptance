import fs from 'node:fs'
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

/**
 * start-dev 写入 .dev-logs/agh-web-origin.txt（含 4177→4178 回退）。
 * 优先读文件：API 进程里残留的 AGNES_WEB_ORIGIN 常比真实 serve 端口旧。
 */
export function getAghWebOrigin(): string {
  try {
    const p = path.join(EDA_ROOT, '.dev-logs', 'agh-web-origin.txt')
    const raw = fs.readFileSync(p, 'utf8').trim()
    if (/^https?:\/\/127\.0\.0\.1:\d+\/?$/i.test(raw)) return raw.replace(/\/$/, '')
  } catch {
    /* ignore */
  }
  const fromEnv = process.env.AGNES_WEB_ORIGIN?.trim()
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  return 'http://127.0.0.1:4177'
}

/** @deprecated 用 getAghWebOrigin()；保留常量兼容旧 import（进程启动时快照） */
export const AGH_WEB_ORIGIN = getAghWebOrigin()

export const AGNES_PROFILE = process.env.AGNES_PROFILE || 'local-dev'

export const PORT = Number(process.env.PORT || 8787)

/** 允许日期型目录名（如 2026_10_12_121230）及既有 demo id；禁止路径穿越与非法字符 */
export function assertCaseId(id: string): string {
  const s = String(id || '').trim()
  if (!s || s.length > 96) {
    throw Object.assign(new Error('非法工程 ID'), { status: 400 })
  }
  if (s === '.' || s === '..' || s.includes('..') || /[\\/:*?"<>|\0]/.test(s)) {
    throw Object.assign(new Error('非法工程 ID'), { status: 400 })
  }
  return s
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
