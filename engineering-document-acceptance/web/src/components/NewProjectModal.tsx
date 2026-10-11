import { useState } from 'react'
import { UNNAMED_PROJECT } from '../store'

export function NewProjectModal({
  onClose,
  onCreate,
}: {
  onClose: () => void
  onCreate: (name: string, batchLabel: string) => void
}) {
  const [name, setName] = useState('')
  const [batch, setBatch] = useState('')

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>新建工程批次</h3>
        <p>可不填名称：首次上传后将自动使用第一个文件名，之后仍可重命名。</p>
        <div className="field">
          <label>工程名称（可选）</label>
          <input
            placeholder="留空则暂为未命名，上传后自动命名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
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
            onClick={() => onCreate(name.trim() || UNNAMED_PROJECT, batch)}
          >
            创建
          </button>
        </div>
      </div>
    </div>
  )
}
