import { useMemo, useState } from 'react'
import {
  FileText,
  Folder,
  FolderPlus,
  MoreHorizontal,
  Pencil,
  Star,
  Trash2,
  FolderInput,
} from 'lucide-react'
import {
  ROOT_FOLDER,
  formatBytes,
  groupByFolder,
  listFolders,
  normalizePath,
} from '../lib/files'
import type { FolderMark, PrimaryReference, ProjectFile } from '../types'
import { StatusBadge } from './StatusBadge'

/** 将主参考 file_id（含 files/ 前缀）与 ProjectFile.relativePath 对齐 */
export function primaryFileRelPath(primary?: PrimaryReference | null): string | null {
  if (!primary?.file_id) return null
  let rel = primary.file_id.replace(/\\/g, '/')
  if (rel.startsWith('files/')) rel = rel.slice('files/'.length)
  return rel
}

type DialogState =
  | { kind: 'create-folder' }
  | { kind: 'rename-file'; file: ProjectFile }
  | { kind: 'move-file'; file: ProjectFile }
  | { kind: 'rename-folder'; folder: string }
  | null

export function FileTree({
  files,
  folderMarks,
  extraFolders = [],
  disabled,
  primaryReference,
  onRenameFile,
  onMoveFile,
  onDeleteFile,
  onRenameFolder,
  onDeleteFolder,
  onCreateFolder,
  onSetPrimary,
  onClearPrimary,
}: {
  files: ProjectFile[]
  folderMarks: FolderMark[]
  extraFolders?: string[]
  disabled?: boolean
  primaryReference?: PrimaryReference | null
  onRenameFile: (fileId: string, newName: string) => void
  onMoveFile: (fileId: string, targetFolder: string) => void
  onDeleteFile: (fileId: string) => void
  onRenameFolder: (from: string, to: string) => void
  onDeleteFolder: (folder: string) => void
  onCreateFolder: (folder: string) => void
  onSetPrimary?: (file: ProjectFile) => void
  onClearPrimary?: () => void
}) {
  const primaryRel = primaryFileRelPath(primaryReference)
  const [dialog, setDialog] = useState<DialogState>(null)
  const [menuId, setMenuId] = useState<string | null>(null)

  const groups = groupByFolder(files)
  const allFolders = useMemo(
    () => listFolders(files, extraFolders),
    [files, extraFolders],
  )
  const markMap = new Map(folderMarks.map((m) => [m.path, m]))

  const folderKeys = useMemo(() => {
    const keys = new Set<string>([ROOT_FOLDER, ...allFolders])
    for (const key of groups.keys()) keys.add(key)
    return Array.from(keys).sort((a, b) => {
      if (a === ROOT_FOLDER) return -1
      if (b === ROOT_FOLDER) return 1
      return a.localeCompare(b, 'zh-CN')
    })
  }, [allFolders, groups])

  function confirmDeleteFile(file: ProjectFile) {
    if (disabled) return
    if (window.confirm(`确定删除文件「${file.name}」？`)) {
      onDeleteFile(file.id)
    }
    setMenuId(null)
  }

  function confirmDeleteFolder(folder: string) {
    if (disabled || folder === ROOT_FOLDER) return
    const count = files.filter(
      (f) => f.relativePath === folder || f.relativePath.startsWith(`${folder}/`),
    ).length
    const msg =
      count > 0
        ? `确定删除目录「${folder}」及其下 ${count} 个文件？`
        : `确定删除空目录「${folder}」？`
    if (window.confirm(msg)) {
      onDeleteFolder(folder)
    }
    setMenuId(null)
  }

  return (
    <div className="panel">
      <div className="panel-hd">
        <h3>材料目录与标记</h3>
        <div className="panel-hd-actions">
          <span className="badge neutral">{files.length} 份</span>
          <button
            type="button"
            className="btn btn-ghost dark btn-sm"
            disabled={disabled}
            onClick={() => setDialog({ kind: 'create-folder' })}
            title="新建目录"
          >
            <FolderPlus size={15} />
            新建目录
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {!files.length && allFolders.length === 0 ? (
          <div className="empty">尚未上传文件。请先添加 ZIP / PDF / 本地文件夹。</div>
        ) : (
          <div className="folder-list">
            {folderKeys.map((folder) => {
              const list = groups.get(folder) || []
              const isExtra = allFolders.includes(folder)
              if (folder === ROOT_FOLDER && list.length === 0 && allFolders.length > 0) {
                return null
              }
              if (folder !== ROOT_FOLDER && list.length === 0 && !isExtra) {
                return null
              }
              const mark = markMap.get(folder)
              const menuKey = `folder:${folder}`
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
                    <div className="row-end">
                      {mark ? (
                        <span className={`badge ${mark.tone}`}>{mark.label}</span>
                      ) : (
                        <span className="badge neutral">待标记</span>
                      )}
                      {folder !== ROOT_FOLDER && (
                        <div className="row-menu">
                          <button
                            type="button"
                            className="icon-btn"
                            disabled={disabled}
                            title="目录操作"
                            onClick={() =>
                              setMenuId(menuId === menuKey ? null : menuKey)
                            }
                          >
                            <MoreHorizontal size={16} />
                          </button>
                          {menuId === menuKey && (
                            <div className="menu-pop">
                              <button
                                type="button"
                                onClick={() => {
                                  setMenuId(null)
                                  setDialog({ kind: 'rename-folder', folder })
                                }}
                              >
                                <Pencil size={14} /> 重命名目录
                              </button>
                              <button
                                type="button"
                                className="danger"
                                onClick={() => confirmDeleteFolder(folder)}
                              >
                                <Trash2 size={14} /> 删除目录
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="file-list" style={{ paddingLeft: 12 }}>
                    {list.map((f) => {
                      const fileMenu = `file:${f.id}`
                      const isPrimary =
                        primaryRel != null && f.relativePath.replace(/\\/g, '/') === primaryRel
                      return (
                        <div className="file-row" key={f.id} title={f.annotation?.reason}>
                          <FileText size={16} color={isPrimary ? '#c4784a' : '#5c6d78'} />
                          <div style={{ minWidth: 0 }}>
                            <div className="title">
                              {f.annotation?.code ? `[${f.annotation.code}] ` : ''}
                              {f.name}
                            </div>
                            <div className="desc">
                              {f.annotation?.checklistName ||
                                f.annotation?.reason ||
                                f.relativePath}
                              {' · '}
                              {formatBytes(f.size)}
                            </div>
                          </div>
                          <div className="row-end">
                            {isPrimary && (
                              <span className="badge copper" title="主参考文件">
                                主参考
                              </span>
                            )}
                            <StatusBadge status={f.annotation?.status} />
                            <div className="row-menu">
                              <button
                                type="button"
                                className="icon-btn"
                                disabled={disabled}
                                title="文件操作"
                                onClick={() =>
                                  setMenuId(menuId === fileMenu ? null : fileMenu)
                                }
                              >
                                <MoreHorizontal size={16} />
                              </button>
                              {menuId === fileMenu && (
                                <div className="menu-pop">
                                  {onSetPrimary && !isPrimary && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setMenuId(null)
                                        if (
                                          window.confirm(
                                            `将「${f.name}」设为主参考文件？\n请确保该文件内容正确，核查将以它为数据锚点。`,
                                          )
                                        ) {
                                          onSetPrimary(f)
                                        }
                                      }}
                                    >
                                      <Star size={14} /> 设为主参考
                                    </button>
                                  )}
                                  {onClearPrimary && isPrimary && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setMenuId(null)
                                        onClearPrimary()
                                      }}
                                    >
                                      <Star size={14} /> 取消主参考
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setMenuId(null)
                                      setDialog({ kind: 'rename-file', file: f })
                                    }}
                                  >
                                    <Pencil size={14} /> 重命名
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setMenuId(null)
                                      setDialog({ kind: 'move-file', file: f })
                                    }}
                                  >
                                    <FolderInput size={14} /> 移动到…
                                  </button>
                                  <button
                                    type="button"
                                    className="danger"
                                    onClick={() => confirmDeleteFile(f)}
                                  >
                                    <Trash2 size={14} /> 删除
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                    {list.length === 0 && (
                      <div className="empty-folder-hint">空目录 — 可将文件移动到此处</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {dialog?.kind === 'create-folder' && (
        <PathDialog
          title="新建目录"
          hint="支持多级路径，例如：01-准备/结构"
          initial=""
          folders={allFolders}
          onClose={() => setDialog(null)}
          onSubmit={(value) => {
            const path = normalizePath(value)
            if (!path) return
            onCreateFolder(path)
            setDialog(null)
          }}
        />
      )}

      {dialog?.kind === 'rename-file' && (
        <PathDialog
          title="重命名文件"
          hint="仅修改文件名，不改变所在目录"
          initial={dialog.file.name}
          onClose={() => setDialog(null)}
          onSubmit={(value) => {
            const name = value.trim().replace(/[\\/]/g, '')
            if (!name || name === dialog.file.name) {
              setDialog(null)
              return
            }
            onRenameFile(dialog.file.id, name)
            setDialog(null)
          }}
        />
      )}

      {dialog?.kind === 'rename-folder' && (
        <PathDialog
          title="重命名目录"
          hint="可改为多级路径"
          initial={dialog.folder}
          folders={allFolders.filter((f) => f !== dialog.folder)}
          onClose={() => setDialog(null)}
          onSubmit={(value) => {
            const path = normalizePath(value)
            if (!path || path === dialog.folder) {
              setDialog(null)
              return
            }
            onRenameFolder(dialog.folder, path)
            setDialog(null)
          }}
        />
      )}

      {dialog?.kind === 'move-file' && (
        <MoveDialog
          file={dialog.file}
          folders={[ROOT_FOLDER, ...allFolders]}
          onClose={() => setDialog(null)}
          onSubmit={(target) => {
            onMoveFile(dialog.file.id, target)
            setDialog(null)
          }}
        />
      )}
    </div>
  )
}

function PathDialog({
  title,
  hint,
  initial,
  folders,
  onClose,
  onSubmit,
}: {
  title: string
  hint: string
  initial: string
  folders?: string[]
  onClose: () => void
  onSubmit: (value: string) => void
}) {
  const [value, setValue] = useState(initial)
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <p>{hint}</p>
        <div className="field">
          <label>名称 / 路径</label>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSubmit(value)
            }}
          />
        </div>
        {folders && folders.length > 0 && (
          <div className="field">
            <label>已有目录（点选填入）</label>
            <div className="chip-list">
              {folders.map((f) => (
                <button
                  key={f}
                  type="button"
                  className="path-chip"
                  onClick={() => setValue(f)}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost dark" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            className="btn btn-copper"
            onClick={() => onSubmit(value)}
          >
            确定
          </button>
        </div>
      </div>
    </div>
  )
}

function MoveDialog({
  file,
  folders,
  onClose,
  onSubmit,
}: {
  file: ProjectFile
  folders: string[]
  onClose: () => void
  onSubmit: (target: string) => void
}) {
  const current = file.relativePath.includes('/')
    ? file.relativePath.split('/').slice(0, -1).join('/')
    : ROOT_FOLDER
  const [target, setTarget] = useState(current)
  const [custom, setCustom] = useState('')

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>移动文件</h3>
        <p>
          将「{file.name}」移动到目标目录。
        </p>
        <div className="field">
          <label>选择目录</label>
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            {folders.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>或输入新目录路径</label>
          <input
            placeholder="例如：02-施工/隐蔽验收"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost dark" onClick={onClose}>
            取消
          </button>
          <button
            type="button"
            className="btn btn-copper"
            onClick={() => {
              const dest = custom.trim() ? normalizePath(custom) : target
              onSubmit(dest || ROOT_FOLDER)
            }}
          >
            移动
          </button>
        </div>
      </div>
    </div>
  )
}
