import { useEffect, useMemo, useState } from 'react'
import {
  ClipboardCheck,
  FolderPlus,
  LogOut,
  Plus,
} from 'lucide-react'
import { AuditPanel } from './components/AuditPanel'
import { FileTree } from './components/FileTree'
import { IdentityGate } from './components/IdentityGate'
import { NewProjectModal } from './components/NewProjectModal'
import { UploadPanel } from './components/UploadPanel'
import { auditStatusLabel } from './components/StatusBadge'
import { runMockAudit } from './lib/auditMock'
import { mergeFiles } from './lib/files'
import {
  createProject,
  createUser,
  loadState,
  saveState,
  touchProject,
} from './store'
import type { AppState, Project, ProjectFile } from './types'

function App() {
  const [state, setState] = useState<AppState>(() => loadState())
  const [showNew, setShowNew] = useState(false)

  useEffect(() => {
    saveState(state)
  }, [state])

  const myProjects = useMemo(
    () =>
      state.projects
        .filter((p) => p.userId === state.user?.id)
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [state.projects, state.user?.id],
  )

  const active = myProjects.find((p) => p.id === state.activeProjectId) || null

  function updateProject(id: string, updater: (p: Project) => Project) {
    setState((s) => ({
      ...s,
      projects: s.projects.map((p) => (p.id === id ? touchProject(updater(p)) : p)),
    }))
  }

  function enter(name: string) {
    const trimmed = name.trim() || '核查员'
    const prev = loadState()
    const reuse =
      prev.user && prev.user.displayName === trimmed ? prev.user : createUser(trimmed)
    setState({
      user: reuse,
      projects: prev.projects,
      activeProjectId: null,
    })
  }

  function logout() {
    setState({ user: null, projects: state.projects, activeProjectId: null })
  }

  function addProject(name: string, batchLabel: string) {
    if (!state.user) return
    const p = createProject(state.user.id, name, batchLabel)
    setState((s) => ({
      ...s,
      projects: [p, ...s.projects],
      activeProjectId: p.id,
    }))
    setShowNew(false)
  }

  function onFiles(incoming: ProjectFile[]) {
    if (!active) return
    updateProject(active.id, (p) => ({
      ...p,
      files: mergeFiles(p.files, incoming),
      auditStatus: p.files.length || incoming.length ? 'ready' : 'draft',
      folderMarks: [],
      summary: undefined,
    }))
  }

  async function onAudit() {
    if (!active || !active.files.length) return
    updateProject(active.id, (p) => ({ ...p, auditStatus: 'auditing' }))
    try {
      const done = await runMockAudit(active)
      updateProject(active.id, () => done)
    } catch {
      updateProject(active.id, (p) => ({ ...p, auditStatus: 'error' }))
    }
  }

  if (!state.user) {
    return <IdentityGate onEnter={enter} />
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ClipboardCheck size={22} />
          </div>
          <div>
            <h1>ArchiveCheck</h1>
            <p>竣工资料核查台</p>
          </div>
        </div>

        <div className="user-chip">
          <div style={{ flex: 1, minWidth: 0 }}>
            <strong>{state.user.displayName}</strong>
            <span>用户 ID · {state.user.id}</span>
          </div>
          <button type="button" className="btn btn-ghost" title="退出身份" onClick={logout}>
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
                onClick={() => setState((s) => ({ ...s, activeProjectId: p.id }))}
              >
                <div className="name">{p.name}</div>
                <div className="meta">
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
          新建工程批次
        </button>
      </aside>

      <main className="main">
        {!active ? (
          <div className="panel" style={{ padding: 40, textAlign: 'center' }}>
            <FolderPlus size={36} color="#c4784a" style={{ marginBottom: 12 }} />
            <h2 style={{ fontFamily: 'var(--font-display)', margin: '0 0 8px' }}>
              选择或新建工程批次
            </h2>
            <p style={{ color: 'var(--muted)', margin: '0 0 18px' }}>
              每次上传可视为独立批次，核查结果互不覆盖。
            </p>
            <button type="button" className="btn btn-primary" onClick={() => setShowNew(true)}>
              <Plus size={18} />
              新建工程批次
            </button>
          </div>
        ) : (
          <>
            <div className="topbar">
              <div>
                <h2>{active.name}</h2>
                <p className="sub">
                  {active.batchLabel}
                  {' · '}
                  更新于 {new Date(active.updatedAt).toLocaleString('zh-CN')}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <UploadPanel
                disabled={active.auditStatus === 'auditing'}
                onFiles={onFiles}
              />
              <div className="grid-2">
                <FileTree files={active.files} folderMarks={active.folderMarks} />
                <AuditPanel project={active} onRun={() => void onAudit()} />
              </div>
            </div>
          </>
        )}
      </main>

      {showNew && (
        <NewProjectModal onClose={() => setShowNew(false)} onCreate={addProject} />
      )}
    </div>
  )
}

export default App
