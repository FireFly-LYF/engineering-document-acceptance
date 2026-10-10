import { useRef, useState, type DragEvent, type InputHTMLAttributes } from 'react'
import { FileArchive, FileText, FolderOpen } from 'lucide-react'
import { ingestFolder, ingestPdfs, ingestZip } from '../lib/files'
import type { ProjectFile } from '../types'

type DirInputProps = InputHTMLAttributes<HTMLInputElement> & {
  webkitdirectory?: string
  directory?: string
}

export function UploadPanel({
  disabled,
  onFiles,
}: {
  disabled?: boolean
  onFiles: (files: ProjectFile[]) => void
}) {
  const [drag, setDrag] = useState(false)
  const zipRef = useRef<HTMLInputElement>(null)
  const pdfRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)

  async function handleZip(list: FileList | null) {
    if (!list?.[0]) return
    const files = await ingestZip(list[0])
    onFiles(files)
    if (zipRef.current) zipRef.current.value = ''
  }

  async function handlePdfs(list: FileList | null) {
    if (!list?.length) return
    onFiles(await ingestPdfs(list))
    if (pdfRef.current) pdfRef.current.value = ''
  }

  async function handleFolder(list: FileList | null) {
    if (!list?.length) return
    onFiles(await ingestFolder(list))
    if (folderRef.current) folderRef.current.value = ''
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault()
    setDrag(false)
    if (disabled) return
    const items = Array.from(e.dataTransfer.files)
    const zip = items.find((f) => f.name.toLowerCase().endsWith('.zip'))
    if (zip) {
      onFiles(await ingestZip(zip))
      return
    }
    const pdfs = items.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length) onFiles(await ingestPdfs(pdfs))
  }

  return (
    <div
      className="panel"
      onDragOver={(e) => {
        e.preventDefault()
        setDrag(true)
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
    >
      <div className="panel-hd">
        <h3>上传本批次材料</h3>
      </div>
      <div className="panel-bd">
        <div className="upload-grid">
          <label className={`upload-card ${drag ? 'drag' : ''}`}>
            <input
              ref={zipRef}
              type="file"
              accept=".zip,application/zip"
              disabled={disabled}
              onChange={(e) => void handleZip(e.target.files)}
            />
            <div className="ico">
              <FileArchive size={20} />
            </div>
            <strong>上传 ZIP</strong>
            <span>整包解压为相对路径</span>
          </label>

          <label className="upload-card">
            <input
              ref={pdfRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              disabled={disabled}
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
              disabled={disabled}
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
