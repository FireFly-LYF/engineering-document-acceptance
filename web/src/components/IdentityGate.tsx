import { useState } from 'react'
import { ClipboardCheck } from 'lucide-react'

export function IdentityGate({ onEnter }: { onEnter: (name: string) => void }) {
  const [name, setName] = useState('')

  return (
    <div className="gate">
      <div className="gate-card">
        <div className="mark">
          <ClipboardCheck size={28} strokeWidth={2} />
        </div>
        <h1>工程文件核验</h1>
        <p>
          按用户与工程批次管理上传材料。支持 ZIP、PDF 与本地文件夹，可分目录整理，核查后对照归档清单为文件与目录打标。
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            onEnter(name)
          }}
        >
          <div className="field">
            <label htmlFor="displayName">您的称呼</label>
            <input
              id="displayName"
              placeholder="例如：张工 / 资料员小陈"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <button className="btn btn-primary" type="submit" style={{ width: '100%' }}>
            进入工作台
          </button>
        </form>
      </div>
    </div>
  )
}
