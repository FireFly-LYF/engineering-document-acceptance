import { useRef, useState, type DragEvent, type InputHTMLAttributes } from 'react'
import { FileArchive, FileText, FolderOpen, LoaderCircle } from 'lucide-react'
import { apiUploadFiles, apiUploadZip } from '../lib/api'
import type { ProjectFile } from '../types'

type DirInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string
  directory?: string
}

export function UploadPanel({
  caseId,
  projectName,
  disabled,
  onFiles,
  onError,
}: {
  caseId: string
  projectName?: string
  disabled?: boolean
  onFiles: (files: ProjectFile[]) => void
  onError?: (message: string) => void
}) {
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const zipRef = useRef<HTMLInputElement>(null)
  const pdfRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)

  async function run(task: () => Promise<ProjectFile[]>) {
    if (busy || disabled) return
    setBusy(true)
    try {
      const files = await task()
      if (files.length) onFiles(files)
    } catch (e) {
      onError?.(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function handleZip(list: FileList | null) {
    if (!list?.[0]) return
    await run(() => apiUploadZip(caseId, list[0], projectName))
    if (zipRef.current) zipRef.current.value = ''
  }

  async function handlePdfs(list: FileList | null) {
    if (!list?.length) return
    const items = Array.from(list)
      .filter((f) => f.name.toLowerCase().endsWith('.pdf') || f.type === 'application/pdf')
      .map((f) => ({ file: f, relativePath: f.name }))
    await run(() => apiUploadFiles(caseId, items, 'pdf', projectName))
    if (pdfRef.current) pdfRef.current.value = ''
  }

  async function handleFolder(list: FileList | null) {
    if (!list?.length) return
    const items: Array<{ file: File; relativePath: string }> = []
    for (const f of Array.from(list)) {
      const rel =
        (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name
      if (!rel || rel.endsWith('/')) continue
      if (rel.split('/').some((seg) => seg.startsWith('.') || seg === '__MACOSX')) continue
      items.push({ file: f, relativePath: rel.replace(/\\/g, '/') })
    }
    await run(() => apiUploadFiles(caseId, items, 'folder', projectName))
    if (folderRef.current) folderRef.current.value = ''
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault()
    setDrag(false)
    if (disabled || busy) return
    const items = Array.from(e.dataTransfer.files)
    const zip = items.find((f) => f.name.toLowerCase().endsWith('.zip'))
    if (zip) {
      await run(() => apiUploadZip(caseId, zip, projectName))
      return
    }
    const pdfs = items.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length) {
      await run(() =>
        apiUploadFiles(
          caseId,
          pdfs.map((f) => ({ file: f, relativePath: f.name })),
          'pdf',
          projectName,
        ),
      )
    }
  }

  const locked = disabled || busy

  return (
    <div
      className="panel"
      onDragOver={(e) => {
        e.preventDefault()
        setDrag(true)
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => void onDrop(e)}
    >
      <div className="panel-hd">
        <h3>上传本批次材料</h3>
        {busy && (
          <span className="badge copper" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <LoaderCircle className="spin" size={14} />
            正在写入 cases/{caseId}/files/
          </span>
        )}
      </div>
      <div className="panel-bd">
        <p style={{ margin: '0 0 12px', color: 'var(--muted)', fontSize: '0.82rem' }}>
          文件将保存到磁盘目录 <code>cases/{caseId}/files/</code>
        </p>
        <div className="upload-grid">
          <label className={`upload-card ${drag ? 'drag' : ''}`}>
            <input
              ref={zipRef}
              type="file"
              accept=".zip,application/zip"
              disabled={locked}
              onChange={(e) => void handleZip(e.target.files)}
            />
            <div className="ico">
              <FileArchive size={20} />
            </div>
            <strong>上传 ZIP</strong>
            <span>服务端解压落盘</span>
          </label>

          <label className="upload-card">
            <input
              ref={pdfRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              disabled={locked}
              onChange={(e) => void handlePdfs(e.target.files)}
            />
            <div className="ico">
              <FileText size={20} />
            </div>
            <strong>选择 PDF</strong>
            <span>可多选单份资料</span>
          </label>

          <label className="upload-card">
            <input
              ref={folderRef}
              type="file"
              {...({ webkitdirectory: '', directory: '' } as DirInputProps)}
              multiple
              disabled={locked}
              onChange={(e) => void handleFolder(e.target.files)}
            />
            <div className="ico">
              <FolderOpen size={20} />
            </div>
            <strong>读取文件夹</strong>
            <span>保留本地目录结构</span>
          </label>
        </div>
      </div>
    </div>
  )
}
