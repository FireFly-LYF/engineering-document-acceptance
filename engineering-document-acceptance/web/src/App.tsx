import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ClipboardCheck,
  FolderPlus,
  LogOut,
  Pencil,
  Plus,
} from 'lucide-react'
import { AuditPanel } from './components/AuditPanel'
import { FileTree } from './components/FileTree'
import { IdentityGate } from './components/IdentityGate'
import { NewProjectModal } from './components/NewProjectModal'
import { UploadPanel } from './components/UploadPanel'
import { auditStatusLabel } from './components/StatusBadge'
import {
  apiAuditStatus,
  apiCancelAudit,
  apiCreateCase,
  apiCreateFolder,
  apiDeleteFile,
  apiDeleteFolder,
  apiGetConfig,
  apiGetFindings,
  apiGetManifest,
  apiListFiles,
  apiMoveFile,
  apiRenameCase,
  apiRenameFile,
  apiRenameFolder,
  apiSetPrimaryReference,
  apiStartAudit,
  apiStatementStatus,
} from './lib/api'
import { annotateFromFindings, type WorkFinding } from './lib/auditMock'
import {
  ROOT_FOLDER,
  mergeFiles,
  normalizePath,
  parentFolder,
  suggestProjectName,
} from './lib/files'
import {
  canStartFormalAudit,
  createProject,
  createUser,
  isUnnamedProject,
  loadState,
  projectTypeLabel,
  saveState,
  touchProject,
} from './store'
import type {
  AppState,
  PrimaryReference,
  PrimarySelection,
  Project,
  ProjectFile,
  ProjectType,
} from './types'

function listedToProjectFiles(
  listed: Array<{ relativePath: string; name: string; size: number; kind: 'pdf' | 'other' }>,
  existing: ProjectFile[],
  keepAnnotations = false,
): ProjectFile[] {
  const byPath = new Map(existing.map((f) => [f.relativePath.toLowerCase(), f]))
  return listed.map((f) => {
    const prev = byPath.get(f.relativePath.toLowerCase())
    return {
      id: prev?.id || `f_${crypto.randomUUID().slice(0, 10)}`,
      relativePath: f.relativePath,
      name: f.name,
      size: f.size,
      kind: f.kind,
      source: prev?.source || 'folder',
      annotation: keepAnnotations ? prev?.annotation : undefined,
    }
  })
}

function App() {
  const [state, setState] = useState<AppState>(() => loadState())
  const [showNew, setShowNew] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [renameDraft, setRenameDraft] = useState('')
  const [toast, setToast] = useState<string | null>(null)
  const [findingsHint, setFindingsHint] = useState<string | null>(null)
  const [aghWebOrigin, setAghWebOrigin] = useState('http://127.0.0.1:4177')
  const [sharedAghSessionId, setSharedAghSessionId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem('eda-agh-session-id')
    } catch {
      return null
    }
  })
  const [sharedAghUrl, setSharedAghUrl] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem('eda-agh-session-url')
    } catch {
      return null
    }
  })
  const cancelRenameRef = useRef(false)
  const pollRef = useRef<number | null>(null)
  const sessionPollRef = useRef<number | null>(null)
  const statementPollRef = useRef<number | null>(null)
  /** 防止连点「开始核查」重复发起 */
  const auditLockRef = useRef(false)

  function rememberSharedSession(sessionId: string | null | undefined, aghUrl?: string | null) {
    if (!sessionId) return
    setSharedAghSessionId(sessionId)
    const url =
      aghUrl ||
      `${aghWebOrigin.replace(/\/$/, '')}/?session=${encodeURIComponent(sessionId)}`
    setSharedAghUrl(url)
    try {
      sessionStorage.setItem('eda-agh-session-id', sessionId)
      sessionStorage.setItem('eda-agh-session-url', url)
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    saveState(state)
  }, [state])

  useEffect(() => {
    void apiGetConfig()
      .then((cfg) => {
        if (cfg.aghWebOrigin) setAghWebOrigin(cfg.aghWebOrigin.replace(/\/$/, ''))
      })
      .catch(() => undefined)
    // 不再进页预取「最近会话」——sessions list / 旧缓存常落到调试「只回复OK」
  }, [])

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
      if (sessionPollRef.current) window.clearInterval(sessionPollRef.current)
      if (statementPollRef.current) window.clearInterval(statementPollRef.current)
    }
  }, [])

  const myProjects = useMemo(
    () =>
      state.projects
        .filter((p) => p.userId === state.user?.id)
        // 固定：从上到下为从新到旧（按创建时间），选择/编辑不改变顺序
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    [state.projects, state.user?.id],
  )

  const active = myProjects.find((p) => p.id === state.activeProjectId) || null

  function showError(message: string) {
    setToast(message)
    window.setTimeout(() => setToast(null), 5000)
  }

  function updateProject(id: string, updater: (p: Project) => Project) {
    setState((s) => ({
      ...s,
      projects: s.projects.map((p) => (p.id === id ? touchProject(updater(p)) : p)),
    }))
  }

  async function syncFromDisk(projectId: string, opts?: { keepAnnotations?: boolean }) {
    const [data, manifestPack] = await Promise.all([
      apiListFiles(projectId),
      apiGetManifest(projectId).catch(() => null),
    ])
    const keep = Boolean(opts?.keepAnnotations)
    updateProject(projectId, (p) => {
      const files = listedToProjectFiles(data.files, p.files, keep)
      const next: Project = {
        ...p,
        files,
        extraFolders: data.extraFolders,
        auditStatus: files.length
          ? p.auditStatus === 'auditing' || p.auditStatus === 'done'
            ? p.auditStatus
            : 'ready'
          : 'draft',
      }
      if (manifestPack) {
        const resolvedName = (
          manifestPack.project_name ||
          manifestPack.manifest?.project_name ||
          ''
        ).trim()
        if (resolvedName && resolvedName !== p.name) {
          next.name = resolvedName
        }
        next.primaryReference = manifestPack.primary_reference ?? null
        if (manifestPack.primarySelection?.status === 'no_primary') {
          next.primarySelectionStatus = 'no_primary'
          next.primarySelection = manifestPack.primarySelection
        } else if (manifestPack.primary_reference) {
          next.primarySelectionStatus = 'selected'
          next.primarySelection = manifestPack.primarySelection
        }
      }
      if (!keep) {
        next.folderMarks = []
        next.summary = undefined
        if (next.auditStatus === 'done') next.auditStatus = files.length ? 'ready' : 'draft'
      }
      return next
    })
    return data
  }

  function enter(name: string) {
    const trimmed = name.trim()
    const prev = loadState()
    const reuse =
      trimmed && prev.user && prev.user.displayName === trimmed
        ? prev.user
        : createUser(trimmed)
    setState({
      user: reuse,
      projects: prev.projects,
      activeProjectId: null,
    })
  }

  function logout() {
    setState({ user: null, projects: state.projects, activeProjectId: null })
  }

  async function addProject(name: string, projectType: ProjectType, batchLabel: string) {
    if (!state.user) return
    let p: Project
    try {
      p = createProject(
        state.user.id,
        name,
        projectType,
        batchLabel,
        state.projects.map((x) => x.id),
      )
    } catch (e) {
      showError(e instanceof Error ? e.message : String(e))
      return
    }
    try {
      await apiCreateCase(p.id, p.name, p.projectType, p.batchLabel)
    } catch (e) {
      showError(e instanceof Error ? e.message : String(e))
      return
    }
    setState((s) => ({
      ...s,
      projects: [p, ...s.projects],
      activeProjectId: p.id,
    }))
    setShowNew(false)
  }

  function startRenameProject() {
    if (!active) return
    cancelRenameRef.current = false
    setRenameDraft(isUnnamedProject(active.name) ? '' : active.name)
    setRenaming(true)
  }

  async function commitRenameProject() {
    if (!active) return
    if (cancelRenameRef.current) {
      cancelRenameRef.current = false
      setRenaming(false)
      return
    }
    const next = renameDraft.trim()
    setRenaming(false)
    if (!next) {
      showError('项目名称不能为空')
      return
    }
    if (next === active.name) return
    try {
      await apiRenameCase(active.id, next)
      updateProject(active.id, (p) => ({ ...p, name: next }))
    } catch (e) {
      showError(e instanceof Error ? e.message : String(e))
    }
  }

  function onFilesUploaded(incoming: ProjectFile[]) {
    if (!active) return
    updateProject(active.id, (p) => {
      const wasEmpty = p.files.length === 0
      const files = mergeFiles(p.files, incoming)
      let name = p.name
      if (isUnnamedProject(name) && wasEmpty && incoming.length) {
        const suggested = suggestProjectName(incoming)
        // 仅当建议名不像资料文件名时才写入；否则保持未命名，避免全文错传误判
        if (suggested) {
          name = suggested
          void apiRenameCase(p.id, name).catch(() => undefined)
        }
      }
      return {
        ...p,
        name,
        files,
        auditStatus: files.length ? 'ready' : 'draft',
        folderMarks: [],
        summary: undefined,
      }
    })
    void syncFromDisk(active.id).catch((e) =>
      showError(e instanceof Error ? e.message : String(e)),
    )
  }

  function applyFindings(
    projectId: string,
    items: WorkFinding[],
    opts?: {
      note?: string
      projectName?: string
      primaryReference?: PrimaryReference | null
      primarySelection?: PrimarySelection | null
      primaryStatus?: string
      formalConclusion?: boolean
    },
  ) {
    setFindingsHint(null)
    auditLockRef.current = false
    const noPrimary = opts?.primaryStatus === 'no_primary'
    const note =
      opts?.note ||
      (noPrimary
        ? '无主文件 — 需人工指定主参考或补传后重跑；未生成正式核查结论，不能宣称核查通过。'
        : undefined)
    updateProject(projectId, (p) => {
      const { files, folderMarks, summary } = annotateFromFindings(p.files, items)
      const resolvedName = (opts?.projectName || '').trim()
      return {
        ...p,
        name: resolvedName && resolvedName !== p.name ? resolvedName : p.name,
        files,
        folderMarks,
        summary: {
          ...summary,
          note,
        },
        primaryReference:
          opts?.primaryReference !== undefined
            ? opts.primaryReference
            : p.primaryReference,
        primarySelection:
          opts?.primarySelection !== undefined
            ? opts.primarySelection
            : p.primarySelection,
        primarySelectionStatus: noPrimary
          ? 'no_primary'
          : opts?.primaryReference || opts?.primaryStatus === 'selected'
            ? 'selected'
            : p.primarySelectionStatus,
        auditStatus: 'done',
        aghMessage: undefined,
        // 无主文件时不轮询「通过」文书
        statementStatus: noPrimary
          ? 'idle'
          : p.statementStatus === 'ready'
            ? 'ready'
            : 'waiting',
      }
    })
    if (!noPrimary) startStatementPoll(projectId)
  }

  function applyFindingsPack(
    projectId: string,
    pack: Awaited<ReturnType<typeof apiGetFindings>>,
  ) {
    const items = (pack.findings?.items || []) as WorkFinding[]
    applyFindings(projectId, items, {
      projectName: pack.project_name,
      primaryReference: pack.primary_reference ?? pack.findings?.primary_reference ?? null,
      primarySelection: pack.primarySelection ?? null,
      primaryStatus: pack.primary_status || pack.findings?.primary_status,
      formalConclusion: pack.findings?.formal_conclusion,
    })
  }

  function stopStatementPoll() {
    if (statementPollRef.current) {
      window.clearInterval(statementPollRef.current)
      statementPollRef.current = null
    }
  }

  function markStatementAbsent(projectId: string) {
    stopStatementPoll()
    updateProject(projectId, (p) =>
      p.statementStatus === 'ready'
        ? p
        : {
            ...p,
            statementStatus: 'idle',
            statementFileName: undefined,
          },
    )
  }

  function startStatementPoll(projectId: string) {
    stopStatementPoll()
    let ticks = 0
    const tick = async () => {
      try {
        const st = await apiStatementStatus(projectId)
        if (st.ready) {
          updateProject(projectId, (p) => ({
            ...p,
            statementStatus: 'ready',
            statementFileName: st.fileName || undefined,
          }))
          stopStatementPoll()
          return
        }
        // Agent 已结束仍无 docx → 不再假装「正在生成」
        const auditSt = await apiAuditStatus(projectId).catch(() => null)
        if (auditSt && !auditSt.running && ticks >= 2) {
          markStatementAbsent(projectId)
          return
        }
        updateProject(projectId, (p) => ({
          ...p,
          statementStatus: 'waiting',
        }))
      } catch {
        /* ignore */
      }
    }
    void tick()
    statementPollRef.current = window.setInterval(() => {
      ticks += 1
      void tick()
      if (ticks >= 150) markStatementAbsent(projectId)
    }, 2000)
  }

  function stopPolling() {
    if (pollRef.current) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
    if (sessionPollRef.current) {
      window.clearInterval(sessionPollRef.current)
      sessionPollRef.current = null
    }
    // 不打断说明文件轮询：findings 就绪后仍需等 docx
  }

  function startSessionPoll(projectId: string) {
    if (sessionPollRef.current) {
      window.clearInterval(sessionPollRef.current)
      sessionPollRef.current = null
    }
    let ticks = 0
    sessionPollRef.current = window.setInterval(() => {
      ticks += 1
      void (async () => {
        try {
          const st = await apiAuditStatus(projectId)
          if (st.sessionId) {
            rememberSharedSession(st.sessionId, st.aghUrl)
            updateProject(projectId, (p) => ({
              ...p,
              aghSessionId: st.sessionId || undefined,
              aghUrl: st.aghUrl,
              aghPid: st.pid ?? p.aghPid,
            }))
            if (sessionPollRef.current) {
              window.clearInterval(sessionPollRef.current)
              sessionPollRef.current = null
            }
          }
        } catch {
          /* ignore */
        }
        if (ticks >= 60 && sessionPollRef.current) {
          window.clearInterval(sessionPollRef.current)
          sessionPollRef.current = null
        }
      })()
    }, 250)
  }

  function startFindingsPoll(projectId: string) {
    if (pollRef.current) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
    let ticks = 0
    pollRef.current = window.setInterval(() => {
      ticks += 1
      void (async () => {
        try {
          const pack = await apiGetFindings(projectId)
          if (pack.sessionId) {
            rememberSharedSession(pack.sessionId, pack.aghUrl)
            updateProject(projectId, (p) => ({
              ...p,
              aghSessionId: pack.sessionId || p.aghSessionId,
              aghUrl: pack.aghUrl || p.aghUrl,
            }))
          }
          if (pack.ready && pack.findings && Array.isArray(pack.findings.items)) {
            applyFindingsPack(projectId, pack)
            stopPolling()
          }
        } catch {
          /* 轮询中忽略瞬时错误 */
        }
        if (ticks >= 80) {
          if (pollRef.current) {
            window.clearInterval(pollRef.current)
            pollRef.current = null
          }
          setFindingsHint('尚未生成 findings.json，请稍候或在 AGH 网页查看进度')
        }
      })()
    }, 4000)
  }

  async function onAudit() {
    if (!active || !canStartFormalAudit(active)) {
      if (active && isUnnamedProject(active.name)) {
        showError('请先填写项目名称后再开始核查')
      } else if (active && !active.files.length) {
        showError('请先上传文件到本工程')
      } else if (active) {
        showError('请先选择工程类型后再开始核查')
      }
      return
    }
    // 幂等：已在核查中 / 请求未完成时直接忽略
    if (active.auditStatus === 'auditing' || auditLockRef.current) return
    auditLockRef.current = true
    stopPolling()
    stopStatementPoll()
    setFindingsHint(null)
    const projectId = active.id
    // 清掉旧会话（含调试「只回复OK」），只跳本轮 -p 新建的会话
    setSharedAghSessionId(null)
    setSharedAghUrl(null)
    try {
      sessionStorage.removeItem('eda-agh-session-id')
      sessionStorage.removeItem('eda-agh-session-url')
    } catch {
      /* ignore */
    }
    updateProject(projectId, (p) => ({
      ...p,
      auditStatus: 'auditing',
      aghMessage: undefined,
      aghSessionId: undefined,
      aghUrl: undefined,
      aghPid: undefined,
      folderMarks: [],
      summary: undefined,
      statementStatus: 'idle',
      statementFileName: undefined,
    }))
    try {
      await apiCreateCase(projectId, active.name, active.projectType, active.batchLabel)
      const launch = await apiStartAudit(projectId, active.name, active.projectType)
      if (launch.sessionId) rememberSharedSession(launch.sessionId, launch.aghUrl)
      updateProject(projectId, (p) => ({
        ...p,
        aghUrl: launch.sessionId ? launch.aghUrl : undefined,
        aghSessionId: launch.sessionId || undefined,
        aghPid: launch.pid,
        aghMessage: launch.status === 'error' ? launch.message : undefined,
        auditStatus: launch.status === 'error' ? 'error' : 'auditing',
        summary: undefined,
      }))
      if (launch.status === 'error') {
        auditLockRef.current = false
        showError(launch.message)
        return
      }
      startSessionPoll(projectId)
      startFindingsPoll(projectId)
    } catch (e) {
      auditLockRef.current = false
      updateProject(projectId, (p) => ({
        ...p,
        auditStatus: 'error',
        aghMessage: undefined,
      }))
      showError(e instanceof Error ? e.message : String(e))
    }
  }

  async function onCancelAudit() {
    if (!active) return
    stopPolling()
    stopStatementPoll()
    setFindingsHint(null)
    auditLockRef.current = false
    const pid = active.aghPid
    updateProject(active.id, (p) => ({
      ...p,
      auditStatus: p.files.length ? 'ready' : 'draft',
      aghMessage: undefined,
      aghPid: undefined,
      statementStatus: p.statementStatus === 'ready' ? 'ready' : 'idle',
      statementFileName: p.statementStatus === 'ready' ? p.statementFileName : undefined,
    }))
    try {
      await apiCancelAudit(active.id, pid)
    } catch {
      /* 本地状态已打断；杀进程失败可忽略 */
    }
  }

  async function onRefreshFindings() {
    if (!active) return
    try {
      const pack = await apiGetFindings(active.id)
      if (pack.sessionId) {
        updateProject(active.id, (p) => ({
          ...p,
          aghSessionId: pack.sessionId || p.aghSessionId,
          aghUrl: pack.aghUrl || p.aghUrl,
        }))
      }
      if (!pack.ready || !pack.findings) {
        setFindingsHint('尚未生成 findings.json，请稍候或在 AGH 网页查看进度')
        return
      }
      applyFindingsPack(active.id, pack)
    } catch (e) {
      setFindingsHint(e instanceof Error ? e.message : String(e))
    }
  }

  async function onSetPrimary(file: ProjectFile) {
    if (!active) return
    try {
      const res = await apiSetPrimaryReference(active.id, file.relativePath)
      updateProject(active.id, (p) => ({
        ...p,
        primaryReference: res.primary_reference,
        primarySelectionStatus: res.primary_reference ? 'selected' : undefined,
        primarySelection: null,
      }))
    } catch (e) {
      showError(e instanceof Error ? e.message : String(e))
    }
  }

  async function onClearPrimary() {
    if (!active) return
    try {
      await apiSetPrimaryReference(active.id, null)
      updateProject(active.id, (p) => ({
        ...p,
        primaryReference: null,
        primarySelectionStatus: undefined,
        primarySelection: null,
      }))
    } catch (e) {
      showError(e instanceof Error ? e.message : String(e))
    }
  }

  // 切换工程时尝试从磁盘同步一次；已完成核查则轮询说明 Word
  useEffect(() => {
    if (!active) return
    void syncFromDisk(active.id, { keepAnnotations: true }).catch(() => undefined)
    if (active.auditStatus === 'done' && active.statementStatus !== 'ready') {
      startStatementPoll(active.id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.id])

  if (!state.user) {
    return <IdentityGate onEnter={enter} />
  }

  const busy = active?.auditStatus === 'auditing'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ClipboardCheck size={22} />
          </div>
          <div>
            <h1>ArchiveCheck</h1>
            <p>工程文件核验</p>
          </div>
        </div>

        <div className="user-chip">
          <div style={{ flex: 1, minWidth: 0 }}>
            <strong>{state.user.displayName}</strong>
          </div>
          <button type="button" className="btn btn-ghost" title="退出" onClick={logout}>
            <LogOut size={16} />
          </button>
        </div>

        <div>
          <p className="section-label">我的工程批次</p>
          <div className="project-list">
            {myProjects.length === 0 && (
              <div style={{ fontSize: '0.82rem', opacity: 0.55, padding: '8px 4px' }}>
                还没有项目。新建一个批次开始上传。
              </div>
            )}
            {myProjects.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`project-item ${p.id === active?.id ? 'active' : ''}`}
                onClick={() => {
                  setRenaming(false)
                  setFindingsHint(null)
                  setState((s) => ({ ...s, activeProjectId: p.id }))
                }}
              >
                <div className="name">{p.name}</div>
                <div className="meta">
                  <span>{projectTypeLabel(p.projectType)}</span>
                  <span>{p.batchLabel}</span>
                  <span>{auditStatusLabel(p.auditStatus)}</span>
                  <span>{p.files.length} 份</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <button type="button" className="btn btn-copper" onClick={() => setShowNew(true)}>
          <Plus size={18} />
          新建核查任务
        </button>
      </aside>

      <main className="main">
        {toast && (
          <div className="toast-error" role="alert">
            {toast}
          </div>
        )}
        {!active ? (
          <div className="panel" style={{ padding: 40, textAlign: 'center' }}>
            <FolderPlus size={36} color="#c4784a" style={{ marginBottom: 12 }} />
            <h2 style={{ fontFamily: 'var(--font-display)', margin: '0 0 8px' }}>
              选择或新建工程批次
            </h2>
            <p style={{ color: 'var(--muted)', margin: '0 0 18px' }}>
              上传文件并保存至本地目录 cases/&lt;id&gt;/files/
            </p>
            <button type="button" className="btn btn-primary" onClick={() => setShowNew(true)}>
              <Plus size={18} />
              新建工程批次
            </button>
          </div>
        ) : (
          <>
            <div className="topbar">
              <div style={{ minWidth: 0, flex: 1 }}>
                {renaming ? (
                  <div className="rename-row">
                    <input
                      className="rename-input"
                      value={renameDraft}
                      placeholder="工程名称"
                      autoFocus
                      onChange={(e) => setRenameDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') void commitRenameProject()
                        if (e.key === 'Escape') {
                          cancelRenameRef.current = true
                          setRenaming(false)
                        }
                      }}
                      onBlur={() => void commitRenameProject()}
                    />
                  </div>
                ) : (
                  <div className="title-row">
                    <h2>{active.name}</h2>
                    <button
                      type="button"
                      className="icon-btn dark"
                      title="重命名工程"
                      onClick={startRenameProject}
                    >
                      <Pencil size={16} />
                    </button>
                  </div>
                )}
                <p className="sub">
                  {new Date(active.updatedAt).toLocaleString('zh-CN')}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <UploadPanel
                caseId={active.id}
                projectName={active.name}
                disabled={busy}
                onFiles={onFilesUploaded}
                onError={showError}
              />
              <div className="grid-2">
                <FileTree
                  files={active.files}
                  folderMarks={active.folderMarks}
                  extraFolders={active.extraFolders}
                  disabled={busy}
                  primaryReference={active.primaryReference}
                  onSetPrimary={(file) => void onSetPrimary(file)}
                  onClearPrimary={() => void onClearPrimary()}
                  onRenameFile={(fileId, newName) => {
                    void (async () => {
                      const file = active.files.find((f) => f.id === fileId)
                      if (!file) return
                      const folder = parentFolder(file.relativePath)
                      const to =
                        folder === ROOT_FOLDER
                          ? newName.trim()
                          : `${folder}/${newName.trim()}`
                      try {
                        await apiRenameFile(active.id, file.relativePath, normalizePath(to))
                        await syncFromDisk(active.id)
                      } catch (e) {
                        showError(e instanceof Error ? e.message : String(e))
                      }
                    })()
                  }}
                  onMoveFile={(fileId, targetFolder) => {
                    void (async () => {
                      const file = active.files.find((f) => f.id === fileId)
                      if (!file) return
                      try {
                        await apiMoveFile(active.id, file.relativePath, targetFolder)
                        await syncFromDisk(active.id)
                      } catch (e) {
                        showError(e instanceof Error ? e.message : String(e))
                      }
                    })()
                  }}
                  onDeleteFile={(fileId) => {
                    void (async () => {
                      const file = active.files.find((f) => f.id === fileId)
                      if (!file) return
                      try {
                        await apiDeleteFile(active.id, file.relativePath)
                        await syncFromDisk(active.id)
                      } catch (e) {
                        showError(e instanceof Error ? e.message : String(e))
                      }
                    })()
                  }}
                  onRenameFolder={(from, to) => {
                    void (async () => {
                      try {
                        await apiRenameFolder(active.id, from, to)
                        await syncFromDisk(active.id)
                      } catch (e) {
                        showError(e instanceof Error ? e.message : String(e))
                      }
                    })()
                  }}
                  onDeleteFolder={(folder) => {
                    void (async () => {
                      try {
                        await apiDeleteFolder(active.id, folder)
                        await syncFromDisk(active.id)
                      } catch (e) {
                        showError(e instanceof Error ? e.message : String(e))
                      }
                    })()
                  }}
                  onCreateFolder={(folder) => {
                    void (async () => {
                      try {
                        await apiCreateFolder(active.id, folder)
                        await syncFromDisk(active.id, { keepAnnotations: true })
                      } catch (e) {
                        showError(e instanceof Error ? e.message : String(e))
                      }
                    })()
                  }}
                />
                <AuditPanel
                  project={active}
                  onRun={() => void onAudit()}
                  onCancel={() => void onCancelAudit()}
                  onRefreshFindings={() => void onRefreshFindings()}
                  findingsHint={findingsHint}
                  aghWebOrigin={aghWebOrigin}
                  sharedSessionId={sharedAghSessionId}
                  sharedAghUrl={sharedAghUrl}
                />
              </div>
            </div>
          </>
        )}
      </main>

      {showNew && (
        <NewProjectModal
          onClose={() => setShowNew(false)}
          onCreate={(n, t, b) => void addProject(n, t, b)}
        />
      )}
    </div>
  )
}

export default App
