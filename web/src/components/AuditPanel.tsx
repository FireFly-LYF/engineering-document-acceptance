import { LoaderCircle, Play, Sparkles } from 'lucide-react'
import type { Project } from '../types'
import { auditStatusLabel } from './StatusBadge'

export function AuditPanel({
  project,
  onRun,
}: {
  project: Project
  onRun: () => void
}) {
  const s = project.summary
  const busy = project.auditStatus === 'auditing'

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
          {s?.note ||
            '上传完成后可启动核查。框架阶段使用本地启发式打标，后续将对接 audit_prepare 写入的 _work/findings。'}
        </p>

        <button
          type="button"
          className="btn btn-primary"
          style={{ width: '100%' }}
          disabled={!project.files.length || busy}
          onClick={onRun}
        >
          {busy ? (
            <>
              <LoaderCircle className="spin" size={18} />
              正在对照归档清单…
            </>
          ) : (
            <>
              {project.auditStatus === 'done' ? <Sparkles size={18} /> : <Play size={18} />}
              {project.auditStatus === 'done' ? '重新核查本批次' : '开始核查'}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
