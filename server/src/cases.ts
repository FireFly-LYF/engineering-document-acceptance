import fs from 'node:fs/promises'
import path from 'node:path'
import {
  EDA_ROOT,
  caseDir,
  filesDir,
  resolveUnderFiles,
  safeRelPath,
  workDir,
} from './paths.js'

const KEEP = '.keep'

export type CaseManifest = {
  project_id: string
  project_type: string
  rules_profile: string
  project_name: string
  batch_label?: string
  created_at?: string
  updated_at?: string
  source?: string
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

export async function ensureCase(
  id: string,
  opts: { name?: string; batchLabel?: string } = {},
): Promise<CaseManifest> {
  const root = caseDir(id)
  await ensureDir(filesDir(id))
  await ensureDir(workDir(id))

  const manifestPath = path.join(root, 'manifest.json')
  let manifest: CaseManifest
  try {
    const raw = await fs.readFile(manifestPath, 'utf8')
    manifest = JSON.parse(raw) as CaseManifest
  } catch {
    manifest = {
      project_id: id,
      project_type: '房屋建筑工程',
      rules_profile: 'housing-construction',
      // 未命名时不要写占位工程名，否则 audit_prepare 会把全文判成错传
      project_name: auditProjectName(opts.name),
      batch_label: opts.batchLabel,
      created_at: new Date().toISOString(),
      source: 'archive-check-web',
    }
  }

  if (opts.name !== undefined) manifest.project_name = auditProjectName(opts.name)
  if (opts.batchLabel !== undefined) manifest.batch_label = opts.batchLabel
  manifest.updated_at = new Date().toISOString()
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
  return manifest
}

/** UI 可显示「未命名工程」；写入 manifest 时留空，交给脚本用文载共识推断 */
function auditProjectName(name?: string) {
  const n = (name || '').trim()
  if (!n || n === '未命名工程') return ''
  return n
}

export async function updateCaseName(id: string, name: string) {
  return ensureCase(id, { name })
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
    return JSON.parse(raw) as { items?: unknown[]; generated_by?: string }
  } catch {
    return null
  }
}

export async function writeAuditPrompt(id: string, projectName: string) {
  await ensureCase(id, { name: projectName })
  const text = [
    `请使用 engineering-archive-audit 对 cases/${id} 做工程验收资料材料齐全与一致性核查；脚本能做的步骤优先用脚本，不要通读全部 PDF。`,
    '',
    '核查完成后，必须使用 engineering-doc-generator：prepare → 撰写 `_work/正文.md` → build 导出 Word。',
    `build 时不要加 --out，使 docx 输出到 cases/${id}/生成结果/。`,
    '',
    '结论需覆盖：缺失文件、错传文件、文件中冲突字段、重复文件。',
    '',
    `工程名称：${projectName || id}`,
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

async function readStatementMetaTitle(id: string): Promise<string | null> {
  try {
    const raw = await fs.readFile(path.join(workDir(id), 'statement-meta.json'), 'utf8')
    const meta = JSON.parse(raw) as { title?: string }
    return meta.title?.trim() || null
  } catch {
    return null
  }
}

/** 查找本工程说明 Word：优先 cases/<id>/生成结果，其次仓库根 生成结果 */
export async function findStatementDocx(
  id: string,
): Promise<{ abs: string; fileName: string } | null> {
  const local = await listDocxIn(path.join(caseDir(id), '生成结果'))
  if (local[0]) return { abs: local[0].abs, fileName: local[0].name }

  const title = await readStatementMetaTitle(id)
  const rootDocs = await listDocxIn(path.join(EDA_ROOT, '生成结果'))
  if (title) {
    const safe = title.replace(/[\\/:*?"<>|]/g, '_')
    const hit = rootDocs.find((d) => d.name === title || d.name === safe)
    if (hit) return { abs: hit.abs, fileName: hit.name }
  }
  if (title && rootDocs[0]) {
    const body = path.join(workDir(id), '正文.md')
    if (await pathExists(body)) {
      try {
        const bst = await fs.stat(body)
        if (rootDocs[0].mtimeMs >= bst.mtimeMs - 60_000) {
          return { abs: rootDocs[0].abs, fileName: rootDocs[0].name }
        }
      } catch {
        /* ignore */
      }
    }
  }
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
