import fs from 'node:fs/promises'
import path from 'node:path'
import {
  caseDir,
  filesDir,
  resolveUnderFiles,
  safeRelPath,
  workDir,
} from './paths.js'

const KEEP = '.keep'

/** 工程类型 slug；与 rules_profile / 规则文件名一致（V2.0 任务身份） */
export const PROJECT_TYPES = [
  'housing-construction',
  'road-bridge',
  'municipal-pipeline',
] as const

export type ProjectTypeId = (typeof PROJECT_TYPES)[number]

const PROJECT_TYPE_SET = new Set<string>(PROJECT_TYPES)

export function isProjectTypeId(value: unknown): value is ProjectTypeId {
  return typeof value === 'string' && PROJECT_TYPE_SET.has(value)
}

export const PROJECT_TYPE_LABELS: Record<ProjectTypeId, string> = {
  'housing-construction': '房屋建筑工程',
  'road-bridge': '道路/桥梁工程',
  'municipal-pipeline': '市政管线工程',
}

/** 规范化前端传入或 manifest 中的工程类型 slug */
export function resolveRulesProfile(raw?: string | null): ProjectTypeId {
  const s = String(raw || '').trim()
  if (isProjectTypeId(s)) return s
  const byLabel = (Object.entries(PROJECT_TYPE_LABELS) as Array<[ProjectTypeId, string]>).find(
    ([, label]) => label === s,
  )
  if (byLabel) return byLabel[0]
  return 'housing-construction'
}

export type PrimaryReference = {
  file_id: string
  file_name: string
  document_code: string
  source: 'user' | 'auto'
}

export type CaseManifest = {
  project_id: string
  project_type: ProjectTypeId | string
  rules_profile: string
  project_name: string
  /** user=任务创建填写；file_consensus=脚本由多数文件共识回写 */
  project_name_source?: 'user' | 'file_consensus' | string
  batch_label?: string
  created_at?: string
  updated_at?: string
  source?: string
  /** 主参考文件；无主文件时为 null */
  primary_reference?: PrimaryReference | null
  fields?: Record<string, unknown>
}

export type ListedFile = {
  relativePath: string
  name: string
  size: number
  kind: 'pdf' | 'other'
}

async function ensureDir(dir: string) {
  await fs.mkdir(dir, { recursive: true })
}

export type EnsureCaseOpts = {
  name?: string
  batchLabel?: string
  projectType?: string
  /** 为 true 时要求名称与类型齐全（新建正式任务） */
  requireIdentity?: boolean
}

export async function ensureCase(id: string, opts: EnsureCaseOpts = {}): Promise<CaseManifest> {
  const root = caseDir(id)
  await ensureDir(filesDir(id))
  await ensureDir(workDir(id))

  const manifestPath = path.join(root, 'manifest.json')
  let manifest: CaseManifest
  let created = false
  try {
    const raw = await fs.readFile(manifestPath, 'utf8')
    manifest = JSON.parse(raw) as CaseManifest
  } catch {
    created = true
    const projectType = opts.projectType
    const projectName = auditProjectName(opts.name)
    if (opts.requireIdentity) {
      if (!isProjectTypeId(projectType)) {
        const err = new Error('请选择有效的工程类型') as Error & { status?: number }
        err.status = 400
        throw err
      }
      if (!projectName) {
        const err = new Error('请填写项目名称') as Error & { status?: number }
        err.status = 400
        throw err
      }
    }
    const typeId: ProjectTypeId = isProjectTypeId(projectType)
      ? projectType
      : 'housing-construction'
    // 任务身份最小结构：不预填施工单位/合同金额等核查字段
    manifest = {
      project_id: id,
      project_type: typeId,
      rules_profile: typeId,
      project_name: projectName,
      project_name_source: 'user',
      created_at: new Date().toISOString(),
      source: 'archive-check-web',
    }
    if (opts.batchLabel !== undefined) manifest.batch_label = opts.batchLabel
  }

  if (!created) {
    if (opts.name !== undefined) {
      manifest.project_name = auditProjectName(opts.name)
      manifest.project_name_source = 'user'
    }
    if (opts.batchLabel !== undefined) manifest.batch_label = opts.batchLabel
    if (opts.projectType !== undefined) {
      if (!isProjectTypeId(opts.projectType)) {
        const err = new Error('请选择有效的工程类型') as Error & { status?: number }
        err.status = 400
        throw err
      }
      manifest.project_type = opts.projectType
      manifest.rules_profile = opts.projectType
    }
  }

  manifest.updated_at = new Date().toISOString()
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
  return manifest
}

/** 未命名 / 空名写入空串，禁止作为正式核查的项目名称 */
function auditProjectName(name?: string) {
  const n = (name || '').trim()
  if (!n || n === '未命名工程') return ''
  return n
}

export function assertFormalAuditIdentity(manifest: CaseManifest) {
  if (!auditProjectName(manifest.project_name)) {
    const err = new Error('请先填写项目名称后再开始核查') as Error & { status?: number }
    err.status = 400
    throw err
  }
  const typeOk =
    isProjectTypeId(manifest.project_type) || isProjectTypeId(manifest.rules_profile)
  if (!typeOk) {
    const err = new Error('请先选择工程类型后再开始核查') as Error & { status?: number }
    err.status = 400
    throw err
  }
}

export async function updateCaseName(id: string, name: string) {
  const n = auditProjectName(name)
  if (!n) {
    const err = new Error('项目名称不能为空') as Error & { status?: number }
    err.status = 400
    throw err
  }
  return ensureCase(id, { name: n })
}

/** 读取 case manifest（不存在则创建最小身份后返回） */
export async function readManifest(id: string): Promise<CaseManifest> {
  return ensureCase(id)
}

/**
 * 用户设定/清空主参考文件。
 * relativePath 为相对 files/ 的路径，或带 files/ 前缀的 case 相对路径；null 清空。
 */
export async function setPrimaryReference(
  id: string,
  relativePath: string | null,
): Promise<CaseManifest> {
  const manifest = await ensureCase(id)
  if (relativePath == null || String(relativePath).trim() === '') {
    manifest.primary_reference = null
    manifest.updated_at = new Date().toISOString()
    await fs.writeFile(
      path.join(caseDir(id), 'manifest.json'),
      `${JSON.stringify(manifest, null, 2)}\n`,
      'utf8',
    )
    return manifest
  }

  let rel = String(relativePath).replace(/\\/g, '/').replace(/^\/+/, '')
  if (rel.startsWith('files/')) {
    rel = rel.slice('files/'.length)
  }
  const resolved = resolveUnderFiles(id, rel)
  try {
    const st = await fs.stat(resolved.abs)
    if (!st.isFile()) {
      const err = new Error('主参考路径不是文件') as Error & { status?: number }
      err.status = 400
      throw err
    }
  } catch (e) {
    if (e instanceof Error && 'status' in e) throw e
    const err = new Error('主参考文件不存在，请先上传') as Error & { status?: number }
    err.status = 400
    throw err
  }

  const fileId = `files/${resolved.rel}`
  manifest.primary_reference = {
    file_id: fileId,
    file_name: path.posix.basename(resolved.rel),
    document_code: '',
    source: 'user',
  }
  if (!manifest.fields || typeof manifest.fields !== 'object') {
    manifest.fields = {}
  }
  manifest.updated_at = new Date().toISOString()
  await fs.writeFile(
    path.join(caseDir(id), 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
    'utf8',
  )
  return manifest
}

export type PrimarySelectionWork = {
  status?: string
  reason?: string
  expected?: { code?: string; name?: string }
  candidates?: Array<{ path?: string; filename?: string; score?: number; reasons?: string[] }>
  primary?: PrimaryReference | null
}

export async function readPrimarySelection(id: string): Promise<PrimarySelectionWork | null> {
  try {
    const raw = await fs.readFile(path.join(workDir(id), 'primary_selection.json'), 'utf8')
    return JSON.parse(raw) as PrimarySelectionWork
  } catch {
    return null
  }
}

async function walkFiles(dir: string, prefix = ''): Promise<ListedFile[]> {
  let entries
  try {
    entries = await fs.readdir(dir, { withFileTypes: true })
  } catch {
    return []
  }
  const out: ListedFile[] = []
  for (const ent of entries) {
    if (ent.name.startsWith('.') && ent.name !== KEEP) continue
    const rel = prefix ? `${prefix}/${ent.name}` : ent.name
    const abs = path.join(dir, ent.name)
    if (ent.isDirectory()) {
      out.push(...(await walkFiles(abs, rel)))
      continue
    }
    if (ent.name === KEEP) continue
    const st = await fs.stat(abs)
    out.push({
      relativePath: rel.replace(/\\/g, '/'),
      name: ent.name,
      size: st.size,
      kind: ent.name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'other',
    })
  }
  return out.sort((a, b) => a.relativePath.localeCompare(b.relativePath, 'zh-CN'))
}

export async function listCaseFiles(id: string): Promise<ListedFile[]> {
  await ensureCase(id)
  return walkFiles(filesDir(id))
}

export async function listExtraFolders(id: string): Promise<string[]> {
  const root = filesDir(id)
  const folders = new Set<string>()

  async function walk(dir: string, prefix = '') {
    let entries
    try {
      entries = await fs.readdir(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const ent of entries) {
      if (!ent.isDirectory()) continue
      if (ent.name.startsWith('.')) continue
      const rel = prefix ? `${prefix}/${ent.name}` : ent.name
      folders.add(rel.replace(/\\/g, '/'))
      await walk(path.join(dir, ent.name), rel)
    }
  }

  await walk(root)

  // 仅含 .keep 的空目录也计入
  for (const folder of [...folders]) {
    const abs = path.join(root, ...folder.split('/'))
    const ents = await fs.readdir(abs)
    const real = ents.filter((n) => n !== KEEP && !n.startsWith('.'))
    if (real.length === 0) folders.add(folder)
  }

  return [...folders].sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export async function writeUpload(
  id: string,
  relativePath: string,
  data: Buffer,
): Promise<ListedFile> {
  await ensureCase(id)
  const { abs, rel } = resolveUnderFiles(id, relativePath)
  await ensureDir(path.dirname(abs))
  await fs.writeFile(abs, data)
  const name = path.basename(rel)
  return {
    relativePath: rel,
    name,
    size: data.length,
    kind: name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'other',
  }
}

export async function createFolder(id: string, folder: string) {
  await ensureCase(id)
  const rel = safeRelPath(folder)
  const { abs } = resolveUnderFiles(id, path.posix.join(rel, KEEP))
  await ensureDir(path.dirname(abs))
  try {
    await fs.access(abs)
  } catch {
    await fs.writeFile(abs, '', 'utf8')
  }
  return rel
}

export async function renamePath(id: string, from: string, to: string) {
  await ensureCase(id)
  const src = resolveUnderFiles(id, from)
  const dst = resolveUnderFiles(id, to)
  await ensureDir(path.dirname(dst.abs))
  await fs.rename(src.abs, dst.abs)
  return dst.rel
}

export async function moveFileToFolder(id: string, from: string, targetFolder: string) {
  const srcRel = safeRelPath(from)
  const name = path.posix.basename(srcRel)
  const dest =
    !targetFolder || targetFolder === '（根目录）'
      ? name
      : `${safeRelPath(targetFolder)}/${name}`
  return renamePath(id, srcRel, dest)
}

export async function deletePath(id: string, relativePath: string) {
  await ensureCase(id)
  const { abs } = resolveUnderFiles(id, relativePath)
  await fs.rm(abs, { recursive: true, force: true })
}

export async function renameFolder(id: string, from: string, to: string) {
  return renamePath(id, from, to)
}

export async function deleteFolder(id: string, folder: string) {
  await deletePath(id, folder)
}

export async function readFindings(id: string) {
  const p = path.join(workDir(id), 'findings.json')
  try {
    const raw = await fs.readFile(p, 'utf8')
    return JSON.parse(raw) as {
      items?: unknown[]
      generated_by?: string
      primary_status?: string
      primary_reference?: PrimaryReference | null
      task_status?: string
      formal_conclusion?: boolean
    }
  } catch {
    return null
  }
}

export async function writeAuditPrompt(
  id: string,
  projectName: string,
  projectType?: string,
) {
  const manifest = await ensureCase(id, {
    name: projectName,
    projectType: projectType ? resolveRulesProfile(projectType) : undefined,
    requireIdentity: false,
  })
  const profile = resolveRulesProfile(manifest.rules_profile || manifest.project_type)
  const typeLabel = PROJECT_TYPE_LABELS[profile]
  const text = [
    `工程名称：${manifest.project_name || projectName || id}`,
    `工程类型：${typeLabel}`,
    `rules_profile：${profile}`,
    '',
    `请使用 engineering-archive-audit 对 cases/${id} 做工程验收资料材料齐全与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。`,
    '',
    '有主文件且核查完成后，请使用 engineering-doc-generator 生成情况说明 word 文件。',
  ].join('\n')
  const promptPath = path.join(caseDir(id), 'TEST_PROMPT.txt')
  await fs.writeFile(promptPath, `${text}\n`, 'utf8')
  return text
}

async function pathExists(p: string) {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

async function listDocxIn(dir: string): Promise<Array<{ abs: string; name: string; mtimeMs: number }>> {
  if (!(await pathExists(dir))) return []
  const names = await fs.readdir(dir)
  const out: Array<{ abs: string; name: string; mtimeMs: number }> = []
  for (const name of names) {
    if (!name.toLowerCase().endsWith('.docx')) continue
    const abs = path.join(dir, name)
    try {
      const st = await fs.stat(abs)
      if (st.isFile()) out.push({ abs, name, mtimeMs: st.mtimeMs })
    } catch {
      /* skip */
    }
  }
  return out.sort((a, b) => b.mtimeMs - a.mtimeMs)
}

/** 查找本工程说明 Word：仅 cases/<id>/doc/（不读仓库根或其他 case） */
export async function findStatementDocx(
  id: string,
): Promise<{ abs: string; fileName: string } | null> {
  const local = await listDocxIn(path.join(caseDir(id), 'doc'))
  if (local[0]) return { abs: local[0].abs, fileName: local[0].name }
  return null
}

export type StatementStatus = {
  ready: boolean
  generating: boolean
  fileName: string | null
  hasBody: boolean
  hasMeta: boolean
}

export async function getStatementStatus(id: string): Promise<StatementStatus> {
  const found = await findStatementDocx(id)
  if (found) {
    return {
      ready: true,
      generating: false,
      fileName: found.fileName,
      hasBody: true,
      hasMeta: true,
    }
  }
  const hasBody = await pathExists(path.join(workDir(id), '正文.md'))
  const hasMeta = await pathExists(path.join(workDir(id), 'statement-meta.json'))
  const hasFindings = await pathExists(path.join(workDir(id), 'findings.json'))
  return {
    ready: false,
    generating: hasFindings || hasBody || hasMeta,
    fileName: null,
    hasBody,
    hasMeta,
  }
}
