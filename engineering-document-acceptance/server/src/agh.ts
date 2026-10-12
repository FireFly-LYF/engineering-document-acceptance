import { type ChildProcess, spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import path from 'node:path'
import { AGH_CLI, AGNES_PROFILE, EDA_ROOT, getAghWebOrigin, workDir } from './paths.js'
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
  error?: string
}

/** caseId → 本机 -p 进程 */
const runningAudits = new Map<
  string,
  { pid?: number; sessionId: string | null; error?: string; stderr?: string }
>()

/** 仅缓存「本轮 -p」写出的 session，禁止 sessions list 顶替 */
let cachedAuditSessionId: string | null = null

const SESSION_LINE = /agnes:\s*session\s+(\S+)/i

function isPidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

/** CLI / daemon 必须与 Web 同一 origin，否则 -p 会失败或连错实例 */
function cliEnv(): NodeJS.ProcessEnv {
  return {
    ...process.env,
    AGNES_PROFILE,
    AGNES_WEB_ORIGIN: getAghWebOrigin(),
  }
}

function launchUrl(sessionId: string | null) {
  const origin = getAghWebOrigin()
  return sessionId
    ? `${origin}/?session=${encodeURIComponent(sessionId)}`
    : `${origin}/`
}

async function cliExists(): Promise<boolean> {
  try {
    await fs.access(AGH_CLI)
    return true
  } catch {
    return false
  }
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

function remember(caseId: string, sessionId: string | null) {
  if (!sessionId) return
  cachedAuditSessionId = sessionId
  const cur = runningAudits.get(caseId)
  if (cur) runningAudits.set(caseId, { ...cur, sessionId })
  void writeSessionFile(caseId, sessionId)
}

function rememberError(caseId: string, message: string) {
  const cur = runningAudits.get(caseId)
  if (cur) runningAudits.set(caseId, { ...cur, error: message })
}

/**
 * 只认本进程 stderr 的 `agnes: session <id>`。
 * 禁止用 sessions list / 旧缓存顶替——会跳到调试留下的「只回复OK」会话。
 */
function attachChildCapture(caseId: string, child: ChildProcess): {
  waitSession: (timeoutMs: number) => Promise<string | null>
  getStderr: () => string
  waitExit: () => Promise<number | null>
} {
  let buf = ''
  let exitCode: number | null = null
  let exitWaiters: Array<(code: number | null) => void> = []

  const onData = (chunk: Buffer | string) => {
    buf += String(chunk)
    if (buf.length > 64_000) buf = buf.slice(-12_000)
    const m = buf.match(SESSION_LINE)
    if (m?.[1]) remember(caseId, m[1])
    const low = buf.toLowerCase()
    if (low.includes('web origin does not match') || low.includes('origin does not match')) {
      rememberError(caseId, 'AGH Web origin 与 daemon 不一致，请重新运行 start-dev')
    }
  }

  child.stderr?.on('data', onData)
  child.stderr?.resume()
  child.on('exit', (code) => {
    exitCode = code
    const m = buf.match(SESSION_LINE)
    if (m?.[1]) remember(caseId, m[1])
    else if (code && code !== 0 && !runningAudits.get(caseId)?.sessionId) {
      const tip = buf.trim().split(/\r?\n/).filter(Boolean).slice(-3).join(' | ')
      rememberError(caseId, tip || `AGH -p 退出码 ${code}`)
    }
    for (const w of exitWaiters) w(exitCode)
    exitWaiters = []
  })

  return {
    getStderr: () => buf,
    waitExit: () =>
      new Promise((resolve) => {
        if (exitCode !== null || (child.pid != null && !isPidAlive(child.pid) && exitCode !== null)) {
          resolve(exitCode)
          return
        }
        if (child.exitCode !== null) {
          resolve(child.exitCode)
          return
        }
        exitWaiters.push(resolve)
      }),
    waitSession: (timeoutMs) =>
      new Promise((resolve) => {
        const started = Date.now()
        const tick = () => {
          const sid = runningAudits.get(caseId)?.sessionId
          if (sid) {
            clearInterval(timer)
            resolve(sid)
            return
          }
          if (child.exitCode !== null || (child.pid != null && !isPidAlive(child.pid))) {
            const again = runningAudits.get(caseId)?.sessionId
            clearInterval(timer)
            resolve(again || null)
            return
          }
          if (Date.now() - started >= timeoutMs) {
            clearInterval(timer)
            resolve(null)
          }
        }
        const timer = setInterval(tick, 100)
        tick()
      }),
  }
}

/** 仅返回本轮核查写入的会话；不再用 sessions list（易落到「只回复OK」） */
export async function getLatestAghSession(): Promise<{ sessionId: string | null; aghUrl: string }> {
  if (cachedAuditSessionId) {
    return { sessionId: cachedAuditSessionId, aghUrl: launchUrl(cachedAuditSessionId) }
  }
  return { sessionId: null, aghUrl: launchUrl(null) }
}

/** 启动本轮 -p；prompt 走 stdin，避免 Windows 命令行截断/乱码；会话 ID 只来自本进程 stderr */
export async function startAghAudit(
  caseId: string,
  projectName: string,
  projectType?: string,
): Promise<AuditLaunch> {
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
    const sid = existing.sessionId
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

  try {
    await fs.unlink(path.join(workDir(caseId), 'agh_session.json'))
  } catch {
    /* ignore */
  }
  cachedAuditSessionId = null

  const prompt = await writeAuditPrompt(caseId, projectName, projectType)
  const origin = getAghWebOrigin()
  console.log(`[agh] start -p case=${caseId} origin=${origin}`)

  // prompt 走 argv（Windows 下比 stdin 更稳）；CLI 对同一 cwd 复用 workspace 会话
  const child = spawn(process.execPath, [AGH_CLI, '-p', prompt, '--cwd', EDA_ROOT], {
    cwd: EDA_ROOT,
    env: cliEnv(),
    stdio: ['ignore', 'ignore', 'pipe'],
    windowsHide: true,
  })

  runningAudits.set(caseId, { pid: child.pid, sessionId: null })
  const cap = attachChildCapture(caseId, child)

  const sessionId = await cap.waitSession(8_000)

  // session 行会在 prompt 之前打出；若立刻 DAEMON_CONNECTION_CLOSED，说明 workspace 会话损坏
  await new Promise((r) => setTimeout(r, 600))
  const stderr = cap.getStderr()
  const closedEarly =
    /DAEMON_CONNECTION_CLOSED/i.test(stderr) ||
    /web origin does not match/i.test(stderr)
  if (closedEarly && (child.exitCode !== null || (child.pid != null && !isPidAlive(child.pid)))) {
    runningAudits.delete(caseId)
    const hint = /DAEMON_CONNECTION_CLOSED/i.test(stderr)
      ? 'AGH workspace 会话异常（常见于历史调试会话损坏）。请重新运行 start-dev.cmd；若仍失败，停止 daemon 后删除该 cwd 的 cli:workspace 会话再试。'
      : `AGH 未连上 Web（${origin}）。请关掉多余的 serve，重新运行 start-dev.cmd`
    console.warn('[agh] -p failed early:', stderr.trim().slice(-400))
    return {
      caseId,
      sessionId: null,
      aghUrl: launchUrl(null),
      status: 'error',
      message: hint,
    }
  }

  if (sessionId) {
    return {
      caseId,
      sessionId,
      aghUrl: launchUrl(sessionId),
      status: 'running',
      message: '已启动 AGH 核查；请用下方按钮打开本轮会话（勿打开旧的「只回复OK」会话）。',
      pid: child.pid,
    }
  }

  const dead = child.pid == null || !isPidAlive(child.pid) || child.exitCode !== null
  if (dead) {
    const err =
      runningAudits.get(caseId)?.error ||
      stderr.trim().split(/\r?\n/).filter(Boolean).slice(-4).join(' | ') ||
      'AGH -p 未能创建会话'
    runningAudits.delete(caseId)
    console.warn('[agh] -p failed:', err)
    return {
      caseId,
      sessionId: null,
      aghUrl: launchUrl(null),
      status: 'error',
      message: `核查未启动：${err}`,
    }
  }

  return {
    caseId,
    sessionId: null,
    aghUrl: launchUrl(null),
    status: 'starting',
    message: '已启动 AGH 核查；会话 ID 回填中（请稍候再打开网页）。',
    pid: child.pid,
  }
}

export function getAghAuditStatus(caseId: string): AuditStatus {
  const tracked = runningAudits.get(caseId)
  if (!tracked) {
    return {
      caseId,
      running: false,
      sessionId: null,
      aghUrl: launchUrl(null),
    }
  }
  const running = tracked.pid != null ? isPidAlive(tracked.pid) : false
  return {
    caseId,
    running,
    sessionId: tracked.sessionId,
    aghUrl: launchUrl(tracked.sessionId),
    ...(tracked.pid != null ? { pid: tracked.pid } : {}),
    ...(tracked.error ? { error: tracked.error } : {}),
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
    aghWebOrigin: getAghWebOrigin(),
    profile: AGNES_PROFILE,
  }
}

/** 启动时只校验 origin，不再预热「最近会话」（避免跳到调试 OK 会话） */
export function warmAghSessionCache() {
  console.log('[agh] Web origin ->', getAghWebOrigin())
}
