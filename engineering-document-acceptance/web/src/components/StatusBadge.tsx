import {
  AlertTriangle,
  CheckCircle2,
  CircleOff,
  HelpCircle,
  Layers,
  XCircle,
} from 'lucide-react'
import type { FindingStatus } from '../types'

const META: Record<
  FindingStatus,
  { label: string; tone: 'ok' | 'warn' | 'bad' | 'neutral' | 'copper'; icon: typeof CheckCircle2 }
> = {
  provided: { label: '已提供', tone: 'ok', icon: CheckCircle2 },
  missing: { label: '缺失', tone: 'bad', icon: XCircle },
  suspect_duplicate_or_misfiled: { label: '错传/重复', tone: 'warn', icon: AlertTriangle },
  needs_human_review: { label: '需复核', tone: 'copper', icon: HelpCircle },
  unmatched: { label: '未匹配', tone: 'neutral', icon: CircleOff },
  unscanned: { label: '未扫描', tone: 'neutral', icon: Layers },
}

export function StatusBadge({ status }: { status?: FindingStatus }) {
  const meta = META[status || 'unscanned']
  const Icon = meta.icon
  return (
    <span className={`badge ${meta.tone}`}>
      <Icon size={12} strokeWidth={2.4} />
      {meta.label}
    </span>
  )
}

export function auditStatusLabel(s: string) {
  return (
    {
      draft: '草稿',
      ready: '待核查',
      auditing: '核查中',
      done: '已完成',
      error: '失败',
    }[s] || s
  )
}
