import { useMemo, useState } from 'react'
import { caseFileRawUrl } from '../lib/api'
import { normalizeCaseFilePath, pathsEqual } from '../lib/auditPaths'
import type {
  AuditDetail,
  FieldConsensusEntry,
  ProjectFile,
  RuleFindingItem,
} from '../types'

type TabId = 'compare' | 'rules' | 'file'

function fieldEmptyLabel(entry: {
  applicable?: boolean
  value?: string | null
  fieldStatus?: string
}): { label: string; tone: string } {
  if (entry.applicable === false) return { label: '不适用', tone: 'neutral' }
  if (entry.fieldStatus === 'needs_human_review') {
    return { label: '字段冲突', tone: 'warn' }
  }
  if (entry.value == null || entry.value === '') {
    return { label: '未提取到', tone: 'neutral' }
  }
  return { label: '已提取', tone: 'ok' }
}

function statusBadge(status?: string) {
  if (status === 'needs_human_review') return <span className="badge warn">需复核</span>
  if (status === 'provided') return <span className="badge ok">一致</span>
  if (status === 'missing') return <span className="badge neutral">缺失</span>
  if (status === 'suspect_duplicate_or_misfiled') {
    return <span className="badge warn">错传/重复</span>
  }
  if (status === 'unmatched') return <span className="badge neutral">未匹配</span>
  return status ? <span className="badge neutral">{status}</span> : null
}

function consistencyLabel(consistency?: string) {
  if (consistency === 'global') return '全局一致'
  if (consistency === 'scoped') return '分类内一致'
  return consistency || null
}

/** 将内部术语转成面向用户的说明（兼容已生成的旧结果） */
function userFacingText(text?: string | null) {
  if (!text) return text
  return text
    .replace(/以主参考\s*manifest\s*为准核对使用文件类别/g, '请以主文件参考值为准，核对相关材料中的该字段')
    .replace(/在使用文件类别间核对并人工确认/g, '请在相关材料之间核对取值并人工确认')
    .replace(/；?\s*全局字段/g, '（全部材料应一致）')
    .replace(/；?\s*文件类别内字段/g, '（仅在指定材料类别内比较）')
    .replace(/适用文件中存在与\s*manifest\s*不一致/g, '适用材料中的取值与参考值不一致')
    .replace(/适用且有值文件均与\s*manifest/g, '适用材料均与参考值')
    .replace(/\bmanifest\b/gi, '参考值')
    .replace(/使用文件类别/g, '相关材料')
}

function PageJump({
  page,
  onJump,
}: {
  page?: number | null
  onJump?: (page: number) => void
}) {
  if (page == null || page <= 0) return <span className="muted">—</span>
  if (!onJump) return <span>p.{page}</span>
  return (
    <button type="button" className="page-jump" onClick={() => onJump(page)}>
      第 {page} 页
    </button>
  )
}

export function AuditResults({
  caseId,
  detail,
  selectedFile,
  files,
  findingItems,
  onSelectFilePath,
}: {
  caseId: string
  detail?: AuditDetail | null
  selectedFile?: ProjectFile | null
  files?: ProjectFile[]
  findingItems?: RuleFindingItem[]
  onSelectFilePath?: (relativePath: string) => void
}) {
  const [tab, setTab] = useState<TabId>('compare')
  const [previewPath, setPreviewPath] = useState<string | null>(null)
  const [previewPage, setPreviewPage] = useState<number | null>(null)

  const consensusFields = detail?.field_consensus?.fields || []
  const ruleFromConsensus = detail?.field_consensus?.rule_findings || []
  const ruleFromFindings = (findingItems || []).filter(
    (i) => i.code === 'RULE' || (i.rule_ids && i.rule_ids.length > 0),
  )
  const rules = ruleFromConsensus.length ? ruleFromConsensus : ruleFromFindings
  const unmatchedRules: RuleFindingItem[] = useMemo(
    () =>
      (files || [])
        .filter((f) => f.annotation?.status === 'unmatched')
        .map((f) => ({
          code: 'UNMATCHED',
          name: f.name,
          field_name: f.name,
          status: 'unmatched',
          severity: f.annotation?.severity || 'info',
          reason: f.annotation?.reason || '已扫描，但未匹配到清单条目',
          suggestion: f.annotation?.suggestion,
          matched_file: f.relativePath,
        })),
    [files],
  )
  const rulesWithUnmatched = useMemo(
    () => [...rules, ...unmatchedRules],
    [rules, unmatchedRules],
  )

  const selectedRel = selectedFile
    ? normalizeCaseFilePath(selectedFile.relativePath)
    : ''

  const fileFieldsEntry = useMemo(() => {
    if (!selectedRel || !detail?.fields?.files) return null
    const files = detail.fields.files
    for (const [key, val] of Object.entries(files)) {
      if (pathsEqual(key, selectedRel)) return val
    }
    // 有时 key 带 files/ 前缀
    for (const [key, val] of Object.entries(files)) {
      if (pathsEqual(key, `files/${selectedRel}`)) return val
    }
    return null
  }, [detail, selectedRel])

  const fileConsensusRows = useMemo(() => {
    if (!selectedRel) return []
    const rows: Array<{
      field: FieldConsensusEntry
      row: FieldConsensusEntry['values_by_file'][number] | null
    }> = []
    for (const field of consensusFields) {
      const row =
        field.values_by_file?.find((v) => pathsEqual(v.file_id, selectedRel)) || null
      rows.push({ field, row })
    }
    return rows
  }, [consensusFields, selectedRel])

  function jumpTo(fileId: string, page?: number | null) {
    const rel = normalizeCaseFilePath(fileId)
    setPreviewPath(rel)
    setPreviewPage(page && page > 0 ? page : 1)
    onSelectFilePath?.(rel)
  }

  // 仅在显式跳页/打开时显示预览；关闭后不因「已选文件」自动再开
  const activePreviewPath = previewPath
  const previewUrl =
    activePreviewPath && caseId
      ? caseFileRawUrl(caseId, activePreviewPath, previewPage)
      : null

  if (
    !detail?.ready &&
    !consensusFields.length &&
    !rulesWithUnmatched.length
  ) {
    return (
      <div className="audit-results empty-inline">
        核查完成后将在此展示字段比较、规则结果与文件字段；请先完成核查或点击「刷新核查结果」。
      </div>
    )
  }

  const showPreview = Boolean(previewUrl && activePreviewPath)

  return (
    <div className="audit-results">
      <div className="result-tabs" role="tablist">
        {(
          [
            ['compare', '字段比较'],
            ['rules', '规则结果'],
            ['file', '文件字段'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            className={tab === id ? 'active' : ''}
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className={`audit-results-split${showPreview ? ' with-preview' : ''}`}>
      <div className="audit-results-main">
      {tab === 'compare' && (
        <div className="result-pane">
          {!consensusFields.length ? (
            <div className="empty-inline">暂无 field_consensus 数据。</div>
          ) : (
            consensusFields.map((field) => (
              <div className="result-card" key={field.field_key}>
                <div className="result-card-hd">
                  <div>
                    <strong>{field.field_name}</strong>
                  </div>
                  <div className="row-end">
                    {consistencyLabel(field.consistency) ? (
                      <span className="badge neutral">
                        {consistencyLabel(field.consistency)}
                      </span>
                    ) : null}
                    {statusBadge(field.status)}
                  </div>
                </div>
                <div className="result-card-bd">
                  <div className="kv">
                    <span>参考值</span>
                    <b>{field.manifest_value ?? '（空）'}</b>
                  </div>
                  <table className="result-table result-table--compare">
                    <thead>
                      <tr>
                        <th>文件</th>
                        <th>取值</th>
                        <th>页</th>
                        <th>状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(field.values_by_file || []).map((v) => {
                        const empty = fieldEmptyLabel({
                          applicable: v.applicable,
                          value: v.value,
                          fieldStatus: field.status,
                        })
                        const display =
                          v.applicable === false
                            ? v.out_of_scope_value
                              ? `（范围外）${v.out_of_scope_value}`
                              : '—'
                            : (v.value ?? '—')
                        return (
                          <tr key={`${field.field_key}:${v.file_id}`}>
                            <td title={v.file_id}>
                              <button
                                type="button"
                                className="linkish"
                                onClick={() => {
                                  setTab('file')
                                  jumpTo(v.file_id, v.page)
                                }}
                              >
                                {v.file_name || normalizeCaseFilePath(v.file_id).split('/').pop()}
                              </button>
                            </td>
                            <td>{display}</td>
                            <td>
                              <PageJump
                                page={v.applicable ? v.page : null}
                                onJump={(p) => jumpTo(v.file_id, p)}
                              />
                            </td>
                            <td>
                              <span className={`badge ${empty.tone}`}>{empty.label}</span>
                              {!v.applicable && v.reason ? (
                                <div className="muted tiny">{v.reason}</div>
                              ) : null}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'rules' && (
        <div className="result-pane">
          {!rulesWithUnmatched.length ? (
            <div className="empty-inline">
              暂无规则级结果（字段冲突会出现 RULE；未匹配清单的文件也会列在此处）。
            </div>
          ) : (
            <div className="result-card">
              <div className="result-card-bd">
                <table className="result-table result-table--rules">
                  <thead>
                    <tr>
                      <th>字段 / 文件</th>
                      <th>状态</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rulesWithUnmatched.map((r, idx) => (
                      <tr key={`${r.code}-${r.field || r.matched_file}-${idx}`}>
                        <td>
                          <div className="rule-field">
                            <strong>
                              {r.status === 'unmatched'
                                ? r.field_name || r.name || '未匹配文件'
                                : r.field_name || r.name || '规则'}
                            </strong>
                            {consistencyLabel(r.consistency) ? (
                              <span className="badge neutral">
                                {consistencyLabel(r.consistency)}
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td>{statusBadge(r.status)}</td>
                        <td className="rule-desc">
                          {r.reason ? <div>{userFacingText(r.reason)}</div> : null}
                          {r.suggestion ? (
                            <div className="muted tiny">
                              {userFacingText(r.suggestion)}
                            </div>
                          ) : null}
                          {r.matched_file ? (
                            <button
                              type="button"
                              className="linkish"
                              onClick={() => jumpTo(r.matched_file!)}
                            >
                              {normalizeCaseFilePath(r.matched_file).split('/').pop()}
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'file' && (
        <div className="result-pane">
          {!selectedFile ? (
            <div className="empty-inline">请在左侧材料目录点击一份文件查看其提取字段。</div>
          ) : (
            <>
              <div className="result-card">
                <div className="result-card-hd">
                  <strong>{selectedFile.name}</strong>
                  {fileFieldsEntry?.unreadable ? (
                    <span className="badge warn">不可读</span>
                  ) : fileFieldsEntry?.unsupported_format ? (
                    <span className="badge warn">不支持格式</span>
                  ) : (
                    <span className="badge neutral">
                      {fileFieldsEntry?.page_count ?? '—'} 页
                    </span>
                  )}
                </div>
                <div className="result-card-bd">
                  {!fileConsensusRows.length && !fileFieldsEntry?.candidates?.length ? (
                    <div className="empty-inline">该文件无字段抽取结果。</div>
                  ) : (
                    <table className="result-table result-table--file">
                      <thead>
                        <tr>
                          <th>字段</th>
                          <th>值</th>
                          <th>页</th>
                          <th>状态</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fileConsensusRows.map(({ field, row }) => {
                          const empty = fieldEmptyLabel({
                            applicable: row?.applicable,
                            value: row?.value,
                            fieldStatus: field.status,
                          })
                          return (
                            <tr key={field.field_key}>
                              <td>{field.field_name}</td>
                              <td>
                                {row?.applicable === false
                                  ? row.out_of_scope_value
                                    ? `（范围外）${row.out_of_scope_value}`
                                    : '—'
                                  : (row?.value ?? '—')}
                              </td>
                              <td>
                                <PageJump
                                  page={row?.applicable ? row.page : null}
                                  onJump={(p) => jumpTo(selectedRel, p)}
                                />
                              </td>
                              <td>
                                <span className={`badge ${empty.tone}`}>{empty.label}</span>
                                {row?.applicable === false && row.reason ? (
                                  <div className="muted tiny">{row.reason}</div>
                                ) : null}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  )}
                  {fileFieldsEntry?.candidates && fileFieldsEntry.candidates.length > 0 ? (
                    <details style={{ marginTop: 12 }}>
                      <summary className="muted">
                        全部候选（{fileFieldsEntry.candidates.length}）
                      </summary>
                      <ul className="candidate-list">
                        {fileFieldsEntry.candidates.map((c, i) => (
                          <li key={`${c.field_key}-${c.page}-${i}`}>
                            <b>{c.name || c.field_key}</b>：{c.value ?? '—'}{' '}
                            <PageJump
                              page={c.page}
                              onJump={(p) => jumpTo(selectedRel, p)}
                            />
                            {c.evidence ? (
                              <div className="muted tiny">{c.evidence}</div>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </div>
              </div>
            </>
          )}
        </div>
      )}
      </div>

      {showPreview ? (
        <div className="pdf-preview">
          <div className="pdf-preview-hd">
            <span>
              预览
              {previewPage ? ` · 第 ${previewPage} 页` : ''}
              {` · ${activePreviewPath!.split('/').pop()}`}
            </span>
            <div className="pdf-preview-actions">
              <a className="linkish" href={previewUrl!} target="_blank" rel="noreferrer">
                新窗口打开
              </a>
              <button
                type="button"
                className="btn btn-ghost dark btn-sm"
                onClick={() => {
                  setPreviewPath(null)
                  setPreviewPage(null)
                }}
              >
                关闭预览
              </button>
            </div>
          </div>
          <iframe title="pdf-preview" src={previewUrl!} />
        </div>
      ) : null}
      </div>
    </div>
  )
}
