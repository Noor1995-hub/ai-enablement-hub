import { useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { bulkInvite, BulkInviteError, type BulkInviteReport, type BulkInviteRow } from '../../api/bulkInvite'
import { s } from './kit/legacyStyles'

interface Props {
  projectId: string
  projectName: string
  onClose: () => void
  onCommitted: () => void
}

type Phase = 'idle' | 'previewing' | 'preview' | 'committing' | 'done'

const STATUS_LABEL: Record<BulkInviteRow['status'], string> = {
  valid: 'will invite',
  duplicate: 'skip — exists',
  invalid: 'skip — invalid',
  created: 'invited',
  email_failed: 'created, email failed',
}

function badgeFor(status: BulkInviteRow['status']): CSSProperties {
  if (status === 'valid' || status === 'created') return s.badgeActive
  if (status === 'invalid' || status === 'email_failed') return { background: '#FFF0EF', color: '#C42828' }
  return s.badgeInvited // duplicate
}

function downloadTemplate() {
  const blob = new Blob(['first_name,last_name,email\n'], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'invite-template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function BulkInviteModal({ projectId, projectName, onClose, onCommitted }: Props) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [report, setReport] = useState<BulkInviteReport | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const fileRef = useRef<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function onPick(file: File) {
    fileRef.current = file
    setFileError(null)
    setPhase('previewing')
    try {
      const r = await bulkInvite(file, projectId, true)
      setReport(r)
      setPhase('preview')
    } catch (e) {
      setFileError(e instanceof BulkInviteError ? e.message : 'Could not read that file.')
      setPhase('idle')
    }
  }

  async function onConfirm() {
    if (!fileRef.current) return
    setPhase('committing')
    try {
      const r = await bulkInvite(fileRef.current, projectId, false)
      setReport(r)
      setPhase('done')
      onCommitted()
    } catch (e) {
      setFileError(e instanceof BulkInviteError ? e.message : 'Something went wrong sending invites.')
      setPhase('preview')
    }
  }

  const sum = report?.summary
  return (
    <div style={overlay} onClick={() => { if (phase !== 'previewing' && phase !== 'committing') onClose() }}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <div style={s.tableHeader}>
          <p style={s.tableTitle}>Bulk invite to {projectName}</p>
          <button type="button" style={s.panelClose} onClick={onClose}>×</button>
        </div>

        <div style={{ padding: '20px 24px' }}>
          {(phase === 'idle' || phase === 'previewing') && (
            <>
              <p style={hint}>
                Download the template, fill it in (you can edit it in Excel — just use
                <b> File → Save As → CSV</b> when done), then upload it here. Columns:
                <b> first_name</b>, <b>last_name</b>, <b>email</b>. People already in the system
                are skipped automatically.
              </p>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14 }}>
                <button
                  type="button"
                  style={{ ...s.submitBtn, fontSize: 13, ...(phase === 'previewing' ? s.submitBtnDisabled : {}) }}
                  disabled={phase === 'previewing'}
                  onClick={() => inputRef.current?.click()}
                >
                  {phase === 'previewing' ? 'reading…' : 'choose CSV file'}
                </button>
                <button type="button" style={ghost} onClick={downloadTemplate}>↓ download template</button>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,text/csv"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) onPick(f)
                  e.target.value = ''
                }}
              />
              {fileError && <p style={errText}>{fileError}</p>}
            </>
          )}

          {(phase === 'preview' || phase === 'committing') && sum && report && (
            <>
              <p style={hint}>
                <b>{sum.valid}</b> will be invited · <b>{sum.duplicates}</b> already registered ·{' '}
                <b>{sum.invalid}</b> invalid — of {sum.total_rows} rows
              </p>
              {fileError && <p style={errText}>{fileError}</p>}
              <PreviewTable rows={report.rows} />
              <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                <button type="button" style={ghost} disabled={phase === 'committing'} onClick={() => setPhase('idle')}>
                  ← choose another file
                </button>
                <button
                  type="button"
                  style={{ ...s.submitBtn, ...(sum.valid === 0 || phase === 'committing' ? s.submitBtnDisabled : {}) }}
                  disabled={sum.valid === 0 || phase === 'committing'}
                  onClick={onConfirm}
                >
                  {phase === 'committing' ? 'sending…' : `confirm & send ${sum.valid} invite${sum.valid === 1 ? '' : 's'}`}
                </button>
              </div>
            </>
          )}

          {phase === 'done' && sum && report && (
            <>
              <p style={{ ...hint, color: '#1D7A52' }}>
                ✓ {sum.created} invited{sum.email_failed ? `, ${sum.email_failed} created but email failed` : ''} ·{' '}
                {sum.duplicates} skipped · {sum.invalid} invalid
              </p>
              {sum.email_failed > 0 && (
                <p style={hint}>
                  For the rows whose email failed, use the “reset link” button on that person in the
                  participants table to share a link manually.
                </p>
              )}
              <PreviewTable rows={report.rows} />
              <div style={{ marginTop: 16 }}>
                <button type="button" style={s.submitBtn} onClick={onClose}>done</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function PreviewTable({ rows }: { rows: BulkInviteRow[] }) {
  return (
    <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid #F0EFED', borderRadius: 8 }}>
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>Row</th>
            <th style={s.th}>Name</th>
            <th style={s.th}>Email</th>
            <th style={s.th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.row_number}>
              <td style={s.td}>{r.row_number}</td>
              <td style={s.td}>{r.first_name} {r.last_name}</td>
              <td style={s.td}>{r.email}</td>
              <td style={s.td}>
                <span style={{ ...s.badge, ...badgeFor(r.status) }}>{STATUS_LABEL[r.status]}</span>
                {r.detail ? <span style={{ fontSize: 11, color: '#8A8A8A', marginLeft: 6 }}>{r.detail}</span> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const overlay: CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,.18)', zIndex: 60,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const modal: CSSProperties = {
  width: 'min(720px, 94vw)', maxHeight: '88vh', overflowY: 'auto',
  background: '#fff', border: '1px solid #E2E2E2', borderRadius: 12,
}
const hint: CSSProperties = { fontSize: 13, color: '#3C3C3C', fontWeight: 300, lineHeight: 1.6, marginBottom: 14 }
const ghost: CSSProperties = {
  padding: '9px 16px', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
  color: '#8A8A8A', background: 'none', border: '1px solid #E2E2E2', borderRadius: 999, cursor: 'pointer',
}
const errText: CSSProperties = { fontSize: 13, color: '#C42828', marginTop: 6 }
