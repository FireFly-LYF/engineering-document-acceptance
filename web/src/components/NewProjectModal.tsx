import { useState } from 'react'

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
        <p>不同上传批次请分项目保存，避免混检。</p>
        <div className="field">
          <label>工程名称</label>
          <input
            placeholder="例如：云港新区市民活动中心图书馆工程"
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
            onClick={() => onCreate(name || '未命名工程', batch)}
          >
            创建
          </button>
        </div>
      </div>
    </div>
  )
}
