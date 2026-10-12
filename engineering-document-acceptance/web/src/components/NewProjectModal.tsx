import { useState } from 'react'
import { PROJECT_TYPE_OPTIONS } from '../store'
import type { ProjectType } from '../types'

export function NewProjectModal({
  onClose,
  onCreate,
}: {
  onClose: () => void
  onCreate: (name: string, projectType: ProjectType, batchLabel: string) => void
}) {
  const [name, setName] = useState('')
  const [projectType, setProjectType] = useState<ProjectType | ''>('')
  const [batch, setBatch] = useState('')

  const trimmedName = name.trim()
  const canCreate = Boolean(trimmedName && projectType)

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>新建核查任务</h3>
        <p>请选择工程类型并填写项目名称；二者均为必填，创建后写入任务身份。</p>
        <div className="field">
          <label>工程类型（必选）</label>
          <select
            value={projectType}
            onChange={(e) => setProjectType(e.target.value as ProjectType | '')}
            autoFocus
          >
            <option value="" disabled>
              请选择工程类型
            </option>
            {PROJECT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>项目名称（必填）</label>
          <input
            placeholder="例如：云港新区市民活动中心图书馆工程"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="field">
          <label>批次备注（可选）</label>
          <input
            placeholder="例如：第二次补件 / 竣工图卷"
            value={batch}
            onChange={(e) => setBatch(e.target.value)}
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost dark" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            className="btn btn-copper"
            disabled={!canCreate}
            onClick={() => {
              if (!projectType || !trimmedName) return
              onCreate(trimmedName, projectType, batch)
            }}
          >
            创建
          </button>
        </div>
      </div>
    </div>
  )
}
