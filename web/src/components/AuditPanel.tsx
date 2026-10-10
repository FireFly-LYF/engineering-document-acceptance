import { Circle, ExternalLink, LoaderCircle, Play, RefreshCw, Sparkles } from 'lucide-react'
import type { Project } from '../types'
import { auditStatusLabel } from './StatusBadge'

const DEFAULT_AGH_ORIGIN = 'http://127.0.0.1:4177'

export function AuditPanel({
  project,
  onRun,
  onCancel,
  onRefreshFindings,
  findingsHint,
  aghWebOrigin,
  sharedSessionId,
  sharedAghUrl,
}: {
  project: Project
  onRun: () => void
  onCancel?: () => void
  onRefreshFindings?: () => void
  findingsHint?: string | null
  aghWebOrigin?: string
  /** 进页预取的本机 AGH 会话，保证一点核查就能深链跳转 */
  sharedSessionId?: string | null
  sharedAghUrl?: string | null
}) {
  const s = project.summary
  const busy = project.auditStatus === 'auditing'
  const home = (aghWebOrigin || DEFAULT_AGH_ORIGIN).replace(/\/$/, '')
  const sessionId = project.aghSessionId || sharedSessionId || null
  const jumpUrl = sessionId
    ? project.aghUrl ||
      sharedAghUrl ||
      `${home}/?session=${encodeURIComponent(sessionId)}`
    : null
  // 核查中/已完成：即使尚无 session，也给出入口（不再卡在「生成中」无按钮）
  const openUrl = jumpUrl || (busy || project.auditStatus === 'done' ? home : null)

  return (
    <div className="panel" style={{ animationDelay: '0.05s' }}>
      <div className="panel-hd">
        <h3>核查结果</h3>
        <span className="badge copper">{auditStatusLabel(project.auditStatus)}</span>
      </div>
      <div className="panel-bd">
        <div className="stats">
          <div className="stat">
            <b>{s?.provided ?? '—'}</b>
            <span>已提供</span>
          </div>
          <div className="stat">
            <b>{s?.missing ?? '—'}</b>
            <span>缺失</span>
          </div>
          <div className="stat">
            <b>{s?.misfiled ?? '—'}</b>
            <span>错传/重复</span>
          </div>
          <div className="stat">
            <b>{s?.review ?? '—'}</b>
            <span>需复核</span>
          </div>
        </div>

        <p style={{ margin: '0 0 14px', color: 'var(--muted)', fontSize: '0.86rem', lineHeight: 1.55 }}>
          {project.auditStatus === 'done' && s?.note
            ? s.note
            : '点击开始核查后，将整段交给本机 AGH Agent。可随时打开 AGH 网页查看运行过程。'}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {busy ? (
            <button type="button" className="btn btn-primary" style={{ width: '100%' }} disabled>
              <LoaderCircle className="spin" size={18} />
              核查进行中…
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              style={{ width: '100%' }}
              disabled={!project.files.length}
              onClick={onRun}
            >
              {project.auditStatus === 'done' ? <Sparkles size={18} /> : <Play size={18} />}
              {project.auditStatus === 'done' ? '重新核查本批次' : '开始核查（AGH）'}
            </button>
          )}

          {busy && onCancel && (
            <button
              type="button"
              className="btn btn-ghost dark"
              style={{ width: '100%', color: '#9a3d30' }}
              onClick={onCancel}
            >
              <Circle size={14} fill="currentColor" strokeWidth={0} />
              终止核查
            </button>
          )}

          {openUrl && (
            <a
              className="btn btn-copper"
              style={{ width: '100%', textDecoration: 'none' }}
              href={openUrl}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={18} />
              {jumpUrl ? '在 AGH 网页查看运行过程' : '打开 AGH 网页'}
            </a>
          )}

          {onRefreshFindings && (busy || project.auditStatus === 'done') && (
            <button
              type="button"
              className="btn btn-ghost dark"
              style={{ width: '100%' }}
              onClick={onRefreshFindings}
            >
              <RefreshCw size={16} />
              刷新核查结果
            </button>
          )}
        </div>

        {findingsHint && (
          <p
            style={{
              margin: '12px 0 0',
              fontSize: '0.84rem',
              color: 'var(--muted)',
              lineHeight: 1.5,
            }}
          >
            {findingsHint}
          </p>
        )}
      </div>
    </div>
  )
}
