import { useState } from 'react'
import { ClipboardCheck } from 'lucide-react'

export function IdentityGate({ onEnter }: { onEnter: (name: string) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  return (
    <div className="gate">
      <div className="gate-card">
        <div className="mark">
          <ClipboardCheck size={28} strokeWidth={2} />
        </div>
        <h1>工程文件核验</h1>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            onEnter(username)
          }}
        >
          <div className="field">
            <label htmlFor="username">用户名</label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              placeholder="用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
