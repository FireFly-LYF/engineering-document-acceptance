import { type ChildProcess, spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import path from 'node:path'
import { AGH_CLI, AGH_WEB_ORIGIN, AGNES_PROFILE, EDA_ROOT, workDir } from './paths.js'
import { writeAuditPrompt } from './cases.js'

export type AuditLaunch = {
  caseId: string
  sessionId: string | null
  aghUrl: string
  status: 'starting' | 'running' | 'error'
  message: string
  pid?: number
  reused?: boolean
}

export type AuditStatus = {
  caseId: string
  running: boolean
  sessionId: string | null
  aghUrl: string
  pid?: number
}

/** caseId → 本机 -p 进程 */
const runningAudits = new Map<string, { pid?: number; sessionId: string | null }>()

/** 进程内缓存：同一 cwd 的 workspace 会话可立刻用于跳转 */
let cachedCwdSessionId: string | null = null

const SESSION_LINE = /agnes:\s*session\s+(\S+)/i

type SessionItem = {
  sessionId: string
  cwd?: string
  archived?: boolean
}

function isPidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

function launchUrl(sessionId: string | null) {
  return sessionId
    ? `${AGH_WEB_ORIGIN}/?session=${encodeURIComponent(sessionId)}`
    : `${AGH_WEB_ORIGIN}/`
}

function sameCwd(a?: string, b?: string) {
  if (!a || !b) return false
  try {
    return path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase()
  } catch {
    return false
  }
}

async function cliExists(): Promise<boolean> {
  try {
    await fs.access(AGH_CLI)
    return true
  } catch {
    return false
  }
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms))
}

async function writeSessionFile(caseId: string, sessionId: string) {
  try {
    const dir = workDir(caseId)
    await fs.mkdir(dir, { recursive: true })
    await fs.writeFile(
      path.join(dir, 'agh_session.json'),
      JSON.stringify({ sessionId, aghUrl: launchUrl(sessionId), at: new Date().toISOString() }, null, 2),
      'utf8',
    )
  } catch (e) {
    console.warn('[agh] write session file failed:', e instanceof Error ? e.message : e)
  }
}

export async function readSessionFile(caseId: string): Promise<string | null> {
  try {
    const raw = await fs.readFile(path.join(workDir(caseId), 'agh_session.json'), 'utf8')
    const data = JSON.parse(raw) as { sessionId?: string }
    return data.sessionId || null
  } catch {
    return null
  }
}

function runAgnes(args: string[], timeoutMs = 8_000): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [AGH_CLI, ...args], {
      cwd: EDA_ROOT,
      env: { ...process.env, AGNES_PROFILE },
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    const timer = setTimeout(() => {
      child.kill()
      reject(new Error(`AGH CLI 超时: ${args.join(' ')}`))
    }, timeoutMs)
    child.stdout.on('data', (d) => {
      stdout += String(d)
    })
    child.stderr.on('data', (d) => {
      stderr += String(d)
    })
    child.on('error', (err) => {
      clearTimeout(timer)
      reject(err)
    })
    child.on('close', (code) => {
      clearTimeout(timer)
      resolve({ code: code ?? 1, stdout, stderr })
    })
  })
}

async function latestCwdSession(): Promise<string | null> {
  try {
    const { code, stdout, stderr } = await runAgnes(
      ['sessions', 'list', '--cwd', EDA_ROOT, '--json'],
      8_000,
    )
    if (code !== 0) {
      console.warn('[agh] sessions list failed:', stderr.trim() || stdout.trim())
      return null
    }
    const page = JSON.parse(stdout) as { items?: SessionItem[] }
    const items = Array.isArray(page.items) ? page.items : []
    const hit = items.find((it) => !it.archived && sameCwd(it.cwd, EDA_ROOT))
    const id = hit?.sessionId ?? null
    if (id) cachedCwdSessionId = id
    return id
  } catch (e) {
    console.warn('[agh] sessions list error:', e instanceof Error ? e.message : e)
    return null
  }
}

function remember(caseId: string, sessionId: string | null) {
  if (!sessionId) return
  cachedCwdSessionId = sessionId
  const cur = runningAudits.get(caseId)
  if (cur) runningAudits.set(caseId, { ...cur, sessionId })
  void writeSessionFile(caseId, sessionId)
}

function bindSessionCapture(caseId: string, pid: number | undefined, child: ChildProcess) {
  let buf = ''
  const onData = (chunk: Buffer | string) => {
    buf += String(chunk)
    if (buf.length > 64_000) buf = buf.slice(-8_000)
    const m = buf.match(SESSION_LINE)
    if (m?.[1]) {
      remember(caseId, m[1])
      child.stderr?.off('data', onData)
    }
  }
  if (!child.stderr) return
  child.stderr.on('data', onData)
  child.stderr.resume()
  child.on('exit', () => {
    const m = buf.match(SESSION_LINE)
    if (m?.[1]) remember(caseId, m[1])
  })
}

/** 后台解析会话，绝不阻塞 HTTP */
function resolveSessionInBackground(caseId: string, pid: number | undefined, child: ChildProcess) {
  bindSessionCapture(caseId, pid, child)
  void (async () => {
    // 若 stderr 已写入则跳过；否则偶发 list 一次（不做高频轮询）
    for (const delay of [300, 800, 1500]) {
      await sleep(delay)
      const cur = runningAudits.get(caseId)
      if (!cur || (pid != null && cur.pid !== pid)) return
      if (cur.sessionId) return
      const id = await latestCwdSession()
      if (id) {
        remember(caseId, id)
        return
      }
    }
  })()
}

/** 供前端预取跳转链接；不启动核查 */
export async function getLatestAghSession(): Promise<{ sessionId: string | null; aghUrl: string }> {
  if (cachedCwdSessionId) {
    return { sessionId: cachedCwdSessionId, aghUrl: launchUrl(cachedCwdSessionId) }
  }
  const id = await latestCwdSession()
  return { sessionId: id, aghUrl: launchUrl(id) }
}

/** HTTP 立即返回；会话 ID 后台回填 + 写入 _work/agh_session.json */
export async function startAghAudit(caseId: string, projectName: string): Promise<AuditLaunch> {
  if (!(await cliExists())) {
    return {
      caseId,
      sessionId: null,
      aghUrl: launchUrl(null),
      status: 'error',
      message: `未找到 AGH CLI: ${AGH_CLI}。请先在 agnes-harness 执行 build:local。`,
    }
  }

  const existing = runningAudits.get(caseId)
  if (existing?.pid && isPidAlive(existing.pid)) {
    const sid = existing.sessionId || cachedCwdSessionId
    return {
      caseId,
      sessionId: sid,
      aghUrl: launchUrl(sid),
      status: sid ? 'running' : 'starting',
      message: '核查已在进行中，未重复启动。',
      pid: existing.pid,
      reused: true,
    }
  }
  if (existing) runningAudits.delete(caseId)

  const prompt = await writeAuditPrompt(caseId, projectName)

  // 跳转目标：内存缓存 → 本案落盘 → 最多等 3s 查一次 sessions list（不做高频轮询）
  let hint =
    cachedCwdSessionId ||
    (await readSessionFile(caseId).catch(() => null)) ||
    null
  if (!hint) {
    hint = await Promise.race([
      latestCwdSession(),
      sleep(3_000).then(() => null as string | null),
    ])
  }

  const child = spawn(
    process.execPath,
    [AGH_CLI, '-p', prompt, '--cwd', EDA_ROOT],
    {
      cwd: EDA_ROOT,
      env: { ...process.env, AGNES_PROFILE },
      stdio: ['ignore', 'ignore', 'pipe'],
      windowsHide: true,
    },
  )

  runningAudits.set(caseId, { pid: child.pid, sessionId: hint })
  if (hint) {
    cachedCwdSessionId = hint
    void writeSessionFile(caseId, hint)
  }
  resolveSessionInBackground(caseId, child.pid, child)

  return {
    caseId,
    sessionId: hint,
    aghUrl: launchUrl(hint),
    status: hint ? 'running' : 'starting',
    message: hint
      ? '已启动 AGH 核查；可跳转会话。'
      : '已启动 AGH 核查；会话 ID 回填中。',
    pid: child.pid,
  }
}

export function getAghAuditStatus(caseId: string): AuditStatus {
  const tracked = runningAudits.get(caseId)
  if (!tracked) {
    const sid = cachedCwdSessionId
    return {
      caseId,
      running: false,
      sessionId: sid,
      aghUrl: launchUrl(sid),
    }
  }
  const running = tracked.pid != null ? isPidAlive(tracked.pid) : false
  const sessionId = tracked.sessionId || cachedCwdSessionId
  return {
    caseId,
    running,
    sessionId,
    aghUrl: launchUrl(sessionId),
    ...(tracked.pid != null ? { pid: tracked.pid } : {}),
  }
}

function killProcessTree(pid: number) {
  return new Promise<void>((resolve) => {
    const killer =
      process.platform === 'win32'
        ? spawn('taskkill.exe', ['/PID', String(pid), '/T', '/F'], {
            windowsHide: true,
            stdio: 'ignore',
          })
        : spawn('kill', ['-TERM', String(pid)], { stdio: 'ignore' })
    killer.on('close', () => resolve())
    killer.on('error', () => resolve())
  })
}

export async function cancelAghAudit(
  caseId: string,
  opts: { pid?: number } = {},
): Promise<{ ok: true; killed: boolean }> {
  const tracked = runningAudits.get(caseId)
  runningAudits.delete(caseId)
  const pid = opts.pid || tracked?.pid
  if (!pid) return { ok: true, killed: false }
  await killProcessTree(pid)
  return { ok: true, killed: true }
}

export function aghConfig() {
  return {
    edaRoot: EDA_ROOT,
    aghCli: AGH_CLI,
    aghWebOrigin: AGH_WEB_ORIGIN,
    profile: AGNES_PROFILE,
  }
}

/** 服务启动时预热 cwd 会话缓存 */
export function warmAghSessionCache() {
  void latestCwdSession().then((id) => {
    if (id) console.log('[agh] warmed session cache:', id)
  })
}
