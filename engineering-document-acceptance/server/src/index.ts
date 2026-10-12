import cors from 'cors'
import express from 'express'
import JSZip from 'jszip'
import multer from 'multer'
import {
  assertFormalAuditIdentity,
  createFolder,
  deleteFolder,
  deletePath,
  ensureCase,
  findStatementDocx,
  getStatementStatus,
  listCaseFiles,
  listExtraFolders,
  moveFileToFolder,
  readFindings,
  readManifest,
  readPrimarySelection,
  renameFolder,
  renamePath,
  setPrimaryReference,
  updateCaseName,
  writeUpload,
} from './cases.js'
import {
  aghConfig,
  cancelAghAudit,
  getAghAuditStatus,
  getLatestAghSession,
  readSessionFile,
  startAghAudit,
  warmAghSessionCache,
} from './agh.js'
import { PORT, assertCaseId, safeRelPath } from './paths.js'

const app = express()
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 80 * 1024 * 1024, files: 200 },
})

app.use(cors())
app.use(express.json({ limit: '2mb' }))

function sendError(res: express.Response, err: unknown) {
  const status = typeof err === 'object' && err && 'status' in err ? Number((err as { status: number }).status) : 500
  const message = err instanceof Error ? err.message : String(err)
  res.status(status || 500).json({ error: message })
}

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, ...aghConfig() })
})

app.get('/api/config', (_req, res) => {
  res.json(aghConfig())
})

app.post('/api/cases', async (req, res) => {
  try {
    const id = assertCaseId(String(req.body?.id || ''))
    const name = req.body?.name ?? req.body?.project_name
    const projectType = req.body?.projectType ?? req.body?.project_type
    const manifest = await ensureCase(id, {
      name: name != null ? String(name) : undefined,
      projectType: projectType != null ? String(projectType) : undefined,
      batchLabel: req.body?.batchLabel != null ? String(req.body.batchLabel) : undefined,
      requireIdentity: true,
    })
    res.json({ ok: true, manifest })
  } catch (e) {
    sendError(res, e)
  }
})

app.patch('/api/cases/:id', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const manifest = await updateCaseName(id, String(req.body?.name || ''))
    res.json({ ok: true, manifest })
  } catch (e) {
    sendError(res, e)
  }
})

/** 用户设定/清空主参考文件；body: { relativePath: string | null } */
app.put('/api/cases/:id/primary-reference', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const raw = req.body?.relativePath ?? req.body?.relative_path
    const relativePath =
      raw === null || raw === undefined || raw === ''
        ? null
        : String(raw)
    const manifest = await setPrimaryReference(id, relativePath)
    res.json({ ok: true, manifest, primary_reference: manifest.primary_reference ?? null })
  } catch (e) {
    sendError(res, e)
  }
})

app.get('/api/cases/:id/manifest', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const manifest = await readManifest(id)
    const primarySelection = await readPrimarySelection(id)
    res.json({
      ok: true,
      manifest,
      project_name: manifest.project_name || '',
      project_name_source: manifest.project_name_source || null,
      primary_reference: manifest.primary_reference ?? null,
      primarySelection,
    })
  } catch (e) {
    sendError(res, e)
  }
})

app.get('/api/cases/:id/files', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const [files, extraFolders] = await Promise.all([listCaseFiles(id), listExtraFolders(id)])
    res.json({ files, extraFolders })
  } catch (e) {
    sendError(res, e)
  }
})

/** multipart: files[] + relativePaths[]（与 files 一一对应）；或单文件 field file + relativePath */
app.post('/api/cases/:id/files', upload.any(), async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    await ensureCase(id, { name: req.body?.projectName })
    const files = (req.files as Express.Multer.File[]) || []
    const saved = []

    // ZIP：field 名 zip
    const zipFile = files.find((f) => f.fieldname === 'zip')
    if (zipFile) {
      const zip = await JSZip.loadAsync(zipFile.buffer)
      for (const [name, entry] of Object.entries(zip.files)) {
        if (entry.dir) continue
        const rel = name.replace(/\\/g, '/')
        if (rel.split('/').some((s) => s.startsWith('.') || s === '__MACOSX')) continue
        const buf = Buffer.from(await entry.async('uint8array'))
        saved.push(await writeUpload(id, rel, buf))
      }
      res.json({ files: saved })
      return
    }

    const pathsRaw = req.body?.relativePaths
    const paths: string[] = Array.isArray(pathsRaw)
      ? pathsRaw
      : typeof pathsRaw === 'string'
        ? (() => {
            try {
              const parsed = JSON.parse(pathsRaw) as string[]
              return Array.isArray(parsed) ? parsed : [pathsRaw]
            } catch {
              return [pathsRaw]
            }
          })()
        : []

    const uploads = files.filter((f) => f.fieldname === 'files' || f.fieldname === 'file')
    for (let i = 0; i < uploads.length; i++) {
      const f = uploads[i]
      const rel =
        paths[i] ||
        (typeof req.body?.relativePath === 'string' ? req.body.relativePath : '') ||
        f.originalname
      saved.push(await writeUpload(id, rel, f.buffer))
    }

    res.json({ files: saved })
  } catch (e) {
    sendError(res, e)
  }
})

app.post('/api/cases/:id/folders', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const folder = await createFolder(id, String(req.body?.path || ''))
    res.json({ ok: true, folder })
  } catch (e) {
    sendError(res, e)
  }
})

app.post('/api/cases/:id/files/rename', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const from = safeRelPath(String(req.body?.from || ''))
    const to = safeRelPath(String(req.body?.to || ''))
    const rel = await renamePath(id, from, to)
    res.json({ ok: true, relativePath: rel })
  } catch (e) {
    sendError(res, e)
  }
})

app.post('/api/cases/:id/files/move', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const from = safeRelPath(String(req.body?.from || ''))
    const targetFolder = String(req.body?.targetFolder || '（根目录）')
    const rel = await moveFileToFolder(id, from, targetFolder)
    res.json({ ok: true, relativePath: rel })
  } catch (e) {
    sendError(res, e)
  }
})

app.delete('/api/cases/:id/files', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const pathRel = safeRelPath(String(req.query.path || req.body?.path || ''))
    await deletePath(id, pathRel)
    res.json({ ok: true })
  } catch (e) {
    sendError(res, e)
  }
})

app.post('/api/cases/:id/folders/rename', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const rel = await renameFolder(
      id,
      String(req.body?.from || ''),
      String(req.body?.to || ''),
    )
    res.json({ ok: true, folder: rel })
  } catch (e) {
    sendError(res, e)
  }
})

app.delete('/api/cases/:id/folders', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    await deleteFolder(id, String(req.query.path || req.body?.path || ''))
    res.json({ ok: true })
  } catch (e) {
    sendError(res, e)
  }
})

app.post('/api/cases/:id/audit', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const name = String(req.body?.name || '')
    const projectTypeRaw = req.body?.projectType ?? req.body?.project_type
    const files = await listCaseFiles(id)
    if (!files.length) {
      res.status(400).json({ error: '请先上传文件到本工程' })
      return
    }
    const manifest = await ensureCase(id, {
      name: name || undefined,
      projectType: projectTypeRaw != null ? String(projectTypeRaw) : undefined,
      requireIdentity: false,
    })
    assertFormalAuditIdentity(manifest)
    const launch = await startAghAudit(
      id,
      manifest.project_name || name || id,
      String(manifest.rules_profile || manifest.project_type || ''),
    )
    res.json(launch)
  } catch (e) {
    sendError(res, e)
  }
})

app.post('/api/cases/:id/audit/cancel', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const pid = req.body?.pid != null ? Number(req.body.pid) : undefined
    const result = await cancelAghAudit(id, {
      ...(Number.isFinite(pid) ? { pid } : {}),
    })
    res.json(result)
  } catch (e) {
    sendError(res, e)
  }
})

app.get('/api/cases/:id/audit/status', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    res.json(getAghAuditStatus(id))
  } catch (e) {
    sendError(res, e)
  }
})

app.get('/api/cases/:id/findings', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const [findings, sessionId, manifest, primarySelection] = await Promise.all([
      readFindings(id),
      readSessionFile(id),
      readManifest(id),
      readPrimarySelection(id),
    ])
    res.json({
      ready: Boolean(findings?.items),
      findings,
      sessionId,
      aghUrl: sessionId
        ? `${aghConfig().aghWebOrigin}/?session=${encodeURIComponent(sessionId)}`
        : aghConfig().aghWebOrigin + '/',
      project_name: manifest.project_name || '',
      project_name_source: manifest.project_name_source || null,
      primary_reference: manifest.primary_reference ?? null,
      primarySelection,
      primary_status:
        findings?.primary_status ||
        primarySelection?.status ||
        (manifest.primary_reference ? 'selected' : undefined),
    })
  } catch (e) {
    sendError(res, e)
  }
})

/** 说明 Word 生成状态（AGH 核查后自动生成） */
app.get('/api/cases/:id/statement', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    res.json(await getStatementStatus(id))
  } catch (e) {
    sendError(res, e)
  }
})

/** 下载说明 Word */
app.get('/api/cases/:id/statement/download', async (req, res) => {
  try {
    const id = assertCaseId(req.params.id)
    const found = await findStatementDocx(id)
    if (!found) {
      res.status(404).json({ error: '说明文件尚未生成' })
      return
    }
    res.download(found.abs, found.fileName)
  } catch (e) {
    sendError(res, e)
  }
})

/** 预取本仓库 AGH 会话，供跳转按钮使用（不启动核查） */
app.get('/api/agh/session', async (_req, res) => {
  try {
    res.json(await getLatestAghSession())
  } catch (e) {
    sendError(res, e)
  }
})

app.listen(PORT, '127.0.0.1', () => {
  const cfg = aghConfig()
  console.log(`[archive-check-server] http://127.0.0.1:${PORT}`)
  console.log(`[archive-check-server] cases → ${cfg.edaRoot}\\cases`)
  console.log(`[archive-check-server] AGH CLI → ${cfg.aghCli}`)
  console.log(`[archive-check-server] AGH Web → ${cfg.aghWebOrigin}`)
  warmAghSessionCache()
})
