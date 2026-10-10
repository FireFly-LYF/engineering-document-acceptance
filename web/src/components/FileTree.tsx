import { FileText, Folder } from 'lucide-react'
import { formatBytes, groupByFolder } from '../lib/files'
import type { FolderMark, ProjectFile } from '../types'
import { StatusBadge } from './StatusBadge'

export function FileTree({
  files,
  folderMarks,
}: {
  files: ProjectFile[]
  folderMarks: FolderMark[]
}) {
  const groups = groupByFolder(files)
  const markMap = new Map(folderMarks.map((m) => [m.path, m]))

  if (!files.length) {
    return (
      <div className="panel">
        <div className="panel-hd">
          <h3>材料目录</h3>
        </div>
        <div className="panel-bd">
          <div className="empty">尚未上传文件。请先添加 ZIP / PDF / 本地文件夹。</div>
        </div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-hd">
        <h3>材料目录与标记</h3>
        <span className="badge neutral">{files.length} 份</span>
      </div>
      <div className="panel-bd">
        <div className="folder-list">
          {Array.from(groups.entries()).map(([folder, list]) => {
            const mark = markMap.get(folder)
            return (
              <div key={folder} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div className="folder-row">
                  <Folder size={18} color="#c4784a" />
                  <div style={{ minWidth: 0 }}>
                    <div className="title">{folder}</div>
                    <div className="desc">
                      {mark?.summary || `${list.length} 份文件`}
                    </div>
                  </div>
                  {mark ? (
                    <span className={`badge ${mark.tone}`}>{mark.label}</span>
                  ) : (
                    <span className="badge neutral">待标记</span>
                  )}
                </div>
                <div className="file-list" style={{ paddingLeft: 12 }}>
                  {list.map((f) => (
                    <div className="file-row" key={f.id} title={f.annotation?.reason}>
                      <FileText size={16} color="#5c6d78" />
                      <div style={{ minWidth: 0 }}>
                        <div className="title">
                          {f.annotation?.code ? `[${f.annotation.code}] ` : ''}
                          {f.name}
                        </div>
                        <div className="desc">
                          {f.annotation?.checklistName || f.annotation?.reason || f.relativePath}
                          {' · '}
                          {formatBytes(f.size)}
                        </div>
                      </div>
                      <StatusBadge status={f.annotation?.status} />
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
