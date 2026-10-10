import type {
  AuditSummary,
  FileAnnotation,
  FindingStatus,
  FolderMark,
  Project,
  ProjectFile,
} from '../types'
import { groupByFolder } from './files'

/** 与 _work/findings.json 条目形状对齐的轻量结构 */
export interface WorkFinding {
  code?: string
  name?: string
  status: FindingStatus | string
  severity?: string
  matched_file?: string
  similar_files?: string[]
  reason?: string
  suggestion?: string
  evidence?: string[]
}

function basename(p: string) {
  return p.replace(/\\/g, '/').split('/').pop() || p
}

function statusOf(raw: string): FindingStatus {
  if (
    raw === 'provided' ||
    raw === 'missing' ||
    raw === 'suspect_duplicate_or_misfiled' ||
    raw === 'needs_human_review'
  ) {
    return raw
  }
  return 'needs_human_review'
}

/**
 * 根据 findings（_work 形态）给已上传文件打标记。
 * 框架阶段：前端本地匹配；后续可改为读取服务端写入的 _work。
 */
export function annotateFromFindings(
  files: ProjectFile[],
  findings: WorkFinding[],
): { files: ProjectFile[]; folderMarks: FolderMark[]; summary: AuditSummary } {
  const byBase = new Map<string, WorkFinding>()
  const byPath = new Map<string, WorkFinding>()

  for (const f of findings) {
    if (f.matched_file) {
      const norm = f.matched_file.replace(/\\/g, '/')
      byPath.set(norm.toLowerCase(), f)
      byPath.set(basename(norm).toLowerCase(), f)
      byBase.set(basename(norm).toLowerCase(), f)
    }
    for (const s of f.similar_files || []) {
      byBase.set(basename(s).toLowerCase(), f)
    }
  }

  const annotated = files.map((file) => {
    const hit =
      byPath.get(file.relativePath.toLowerCase()) ||
      byPath.get(`files/${file.relativePath}`.toLowerCase()) ||
      byBase.get(file.name.toLowerCase())

    if (!hit) {
      const annotation: FileAnnotation = {
        status: 'unscanned',
        reason: '未命中清单条目（待接入完整核查脚本）',
      }
      return { ...file, annotation }
    }

    const annotation: FileAnnotation = {
      status: statusOf(String(hit.status)),
      code: hit.code,
      checklistName: hit.name,
      reason: hit.reason || (hit.evidence && hit.evidence[0]) || undefined,
      suggestion: hit.suggestion,
      severity: (hit.severity as FileAnnotation['severity']) || 'info',
    }
    return { ...file, annotation }
  })

  // 缺失项：无 matched_file，在摘要中体现
  const missing = findings.filter((f) => statusOf(String(f.status)) === 'missing')

  const folderMarks = buildFolderMarks(annotated)
  const summary = buildSummary(annotated, missing.length)

  return { files: annotated, folderMarks, summary }
}

function buildFolderMarks(files: ProjectFile[]): FolderMark[] {
  const groups = groupByFolder(files)
  const marks: FolderMark[] = []

  for (const [path, list] of groups) {
    const counts: Partial<Record<FindingStatus, number>> = {}
    for (const f of list) {
      const st = f.annotation?.status || 'unscanned'
      counts[st] = (counts[st] || 0) + 1
    }
    const mis = counts.suspect_duplicate_or_misfiled || 0
    const rev = counts.needs_human_review || 0
    const miss = counts.missing || 0
    const ok = counts.provided || 0
    let tone: FolderMark['tone'] = 'neutral'
    let label = '待核查'
    let summary = `${list.length} 份文件`

    if (mis + miss > 0) {
      tone = 'bad'
      label = '存在问题'
      summary = `错传/重复 ${mis} · 关联缺失需关注`
    } else if (rev > 0) {
      tone = 'warn'
      label = '需复核'
      summary = `${rev} 份需人工确认`
    } else if (ok > 0 && ok + (counts.unscanned || 0) === list.length) {
      tone = 'ok'
      label = '基本齐套'
      summary = `已对齐清单 ${ok} 份`
    }

    marks.push({ path, label, summary, tone, counts })
  }

  return marks.sort((a, b) => a.path.localeCompare(b.path, 'zh-CN'))
}

function buildSummary(files: ProjectFile[], missingExtra: number): AuditSummary {
  let provided = 0
  let missing = missingExtra
  let misfiled = 0
  let review = 0
  for (const f of files) {
    const st = f.annotation?.status
    if (st === 'provided') provided += 1
    if (st === 'suspect_duplicate_or_misfiled') misfiled += 1
    if (st === 'needs_human_review') review += 1
  }
  return {
    provided,
    missing,
    misfiled,
    review,
    totalFiles: files.length,
    generatedAt: new Date().toISOString(),
    note: '框架演示：标记逻辑对齐 _work/findings；完整核查将调用 audit_prepare.py',
  }
}

/** 演示用轻量 findings：按文件名关键词猜测清单命中 */
export function heuristicFindings(files: ProjectFile[]): WorkFinding[] {
  const rules: { code: string; name: string; keys: string[]; status?: FindingStatus }[] = [
    { code: 'A-01', name: '建设工程规划许可证', keys: ['规划许可'] },
    { code: 'A-02', name: '施工许可证', keys: ['施工许可'] },
    { code: 'A-03', name: '施工合同', keys: ['施工合同'] },
    { code: 'A-04', name: '监理合同', keys: ['监理合同'] },
    { code: 'E-01', name: '工程竣工验收报告', keys: ['竣工验收报告'] },
    { code: 'E-02', name: '工程竣工预验收报告', keys: ['预验收'] },
    { code: 'G-01', name: '消防验收意见或备案凭证', keys: ['消防验收', '消防备案'] },
    { code: 'D-01', name: '主要材料检测报告', keys: ['检测报告', '材料检测'] },
  ]

  const findings: WorkFinding[] = []
  const used = new Set<string>()

  for (const rule of rules) {
    const hit = files.find((f) => rule.keys.some((k) => f.name.includes(k)))
    if (hit) {
      used.add(hit.id)
      const isPre = hit.name.includes('预验收') && rule.code === 'E-01'
      findings.push({
        code: rule.code,
        name: rule.name,
        status: isPre ? 'missing' : 'provided',
        matched_file: hit.relativePath,
        similar_files: isPre ? [hit.relativePath] : undefined,
        reason: isPre ? '预验收不能替代正式竣工验收报告' : '文件名与清单别名匹配（演示）',
        suggestion: isPre ? '补充正式《工程竣工验收报告》' : undefined,
        severity: isPre ? 'error' : 'info',
      })
    } else if (['E-01', 'G-01', 'D-01'].includes(rule.code)) {
      findings.push({
        code: rule.code,
        name: rule.name,
        status: 'missing',
        reason: '上传包中未找到可接受文件（演示启发式）',
        suggestion: `请补充《${rule.name}》`,
        severity: 'error',
      })
    }
  }

  for (const f of files) {
    if (used.has(f.id)) continue
    if (/其他工程|他项|错传|副本/.test(f.name)) {
      findings.push({
        code: 'MISFILE',
        name: '疑似错传或重复',
        status: 'suspect_duplicate_or_misfiled',
        matched_file: f.relativePath,
        reason: '文件名含他项/错传示意关键词（演示）',
        severity: 'warning',
      })
    }
  }

  return findings
}

export async function runMockAudit(project: Project): Promise<Project> {
  await new Promise((r) => setTimeout(r, 900))
  const findings = heuristicFindings(project.files)
  const { files, folderMarks, summary } = annotateFromFindings(project.files, findings)
  return {
    ...project,
    files,
    folderMarks,
    summary,
    auditStatus: 'done',
    updatedAt: new Date().toISOString(),
  }
}
