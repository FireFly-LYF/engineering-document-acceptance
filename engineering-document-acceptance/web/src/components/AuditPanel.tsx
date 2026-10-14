import {
  Circle,
  Download,
  ExternalLink,
  LoaderCircle,
  Play,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { statementDownloadUrl } from '../lib/api'
import { canStartFormalAudit, isUnnamedProject } from '../store'
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
  sharedSessionId?: string | null
  sharedAghUrl?: string | null
}) {
  const s = project.summary
  const busy = project.auditStatus === 'auditing'
  const home = (aghWebOrigin || DEFAULT_AGH_ORIGIN).replace(/\/$/, '')
  // 核查中只认本轮 session，禁止回落到共享/旧「只回复OK」会话
  const sessionId = project.aghSessionId || (busy ? null : sharedSessionId) || null
  const jumpUrl = sessionId
    ? project.aghUrl ||
      (!busy ? sharedAghUrl : null) ||
      `${home}/?session=${encodeURIComponent(sessionId)}`
    : null
  // 无本轮 session 时不给裸首页链接（首页会打开上次调试会话）
  const openUrl = jumpUrl

  const statementReady = project.statementStatus === 'ready'
  const showStatement =
    statementReady ||
    project.statementStatus === 'waiting' ||
    project.auditStatus === 'done'

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
          <div className="stat">
            <b>{s?.unmatched ?? '—'}</b>
            <span>未匹配</span>
          </div>
        </div>

        <div
          style={{
            margin: '0 0 12px',
            padding: '10px 12px',
            borderRadius: 8,
            background: 'var(--surface-2, rgba(0,0,0,0.04))',
            fontSize: '0.84rem',
            lineHeight: 1.5,
            color: 'var(--muted)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
              marginBottom: 4,
            }}
          >
            <div style={{ color: 'var(--text, inherit)', fontWeight: 600 }}>
              主参考文件
            </div>
            {project.primarySelectionStatus === 'no_primary' ? (
              <span className="badge warn">无主文件</span>
            ) : project.primaryReference?.source === 'user' ? (
              <span className="badge copper">用户选择</span>
            ) : project.primaryReference?.source === 'auto' ? (
              <span className="badge copper">自动选择</span>
            ) : null}
          </div>
          {project.primarySelectionStatus === 'no_primary' ? (
            <span style={{ color: '#9a3d30' }}>
              需人工指定或补传后重跑；未生成正式核查结论。
              {project.primarySelection?.reason
                ? `（${project.primarySelection.reason}）`
                : ''}
            </span>
          ) : project.primaryReference?.file_name ? (
            <span>
              {project.primaryReference.file_name}
              {project.primaryReference.document_code
                ? ` · ${project.primaryReference.document_code}`
                : ''}
            </span>
          ) : (
            <span>未指定。可在材料目录设为主参考，或由核查脚本自动选择。</span>
          )}
        </div>

        <p style={{ margin: '0 0 14px', color: 'var(--muted)', fontSize: '0.86rem', lineHeight: 1.55 }}>
          {project.auditStatus === 'done' && s?.note
            ? s.note
            : isUnnamedProject(project.name)
              ? '未命名任务不能进入正式核查，请先填写项目名称。'
              : !project.files.length
                ? '请先上传工程资料后再开始核查。'
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
              disabled={!canStartFormalAudit(project)}
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
              在 AGH 网页查看本轮核查
            </a>
          )}

          {busy && !openUrl && (
            <button type="button" className="btn btn-copper" style={{ width: '100%' }} disabled>
              <LoaderCircle className="spin" size={18} />
              会话创建中，请稍候再打开 AGH…
            </button>
          )}

          {showStatement && statementReady && (
            <a
              className="btn btn-copper"
              style={{ width: '100%', textDecoration: 'none' }}
              href={statementDownloadUrl(project.id)}
              download={project.statementFileName || true}
              title={project.statementFileName || '下载说明文件'}
            >
              <Download size={18} />
              下载说明文件
            </a>
          )}

          {showStatement && !statementReady && project.statementStatus === 'waiting' && (
            <button type="button" className="btn btn-copper" style={{ width: '100%' }} disabled>
              <LoaderCircle className="spin" size={18} />
              正在生成说明文件
            </button>
          )}

          {showStatement &&
            !statementReady &&
            project.statementStatus !== 'waiting' && (
              <button type="button" className="btn btn-ghost dark" style={{ width: '100%' }} disabled>
                尚未生成说明文件
              </button>
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
