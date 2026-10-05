// The editor's save dialog (B5): findings / removal warning / conflict prompt.
// Inline styles to match LessonEditor (the admin kit's CSS isn't loaded on
// the /learning routes).
import type { Gate } from './useGuardedSave'

interface Props {
  gate: Gate
  onSaveAnyway: () => void
  onKeepEditing: () => void
  onReload: () => void
  onOverwrite: () => void
}

const panel: React.CSSProperties = { margin: '12px 20px', padding: 16, border: '1px solid #E2E2E2', borderRadius: 12, background: '#FFFBEB', fontFamily: 'var(--dlw-font-body)', fontSize: 14 }
const btn: React.CSSProperties = { padding: '7px 16px', borderRadius: 999, border: '1px solid #E2E2E2', background: '#fff', fontWeight: 600, cursor: 'pointer', marginRight: 8 }
const primary: React.CSSProperties = { ...btn, background: '#3BC9BC', border: 'none', color: '#fff' }

function at(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function SaveGate({ gate, onSaveAnyway, onKeepEditing, onReload, onOverwrite }: Props) {
  if (gate.kind === 'idle' || gate.kind === 'busy') return null
  if (gate.kind === 'error') {
    return <div role="alert" style={{ ...panel, background: '#FEF2F2', color: '#C42828' }}>{gate.message}</div>
  }
  if (gate.kind === 'conflict') {
    return (
      <div role="alertdialog" aria-label="This lesson changed" style={panel}>
        <p style={{ marginTop: 0 }}>
          <strong>{gate.updatedByName ?? 'Someone'} changed this lesson</strong> at {at(gate.updatedAt)} while you were editing.
        </p>
        <p>Reload their version (your unsaved edits are discarded), or overwrite it with yours.</p>
        <button type="button" style={btn} onClick={onReload}>Reload their version</button>
        <button type="button" style={primary} onClick={onOverwrite}>Overwrite with mine</button>
      </div>
    )
  }
  const warnings = gate.findings.filter(f => f.severity === 'warning')
  const infos = gate.findings.filter(f => f.severity === 'info')
  return (
    <div role="dialog" aria-label="Check results" style={panel}>
      {gate.checkError && (
        <p role="alert" style={{ marginTop: 0 }}>
          Couldn't run the checks ({gate.checkError}). You can still save.
        </p>
      )}
      {gate.removal && <p role="alert" style={{ marginTop: 0, color: '#C42828', fontWeight: 600 }}>{gate.removal}</p>}
      {warnings.length === 0 && !gate.removal && !gate.checkError && <p style={{ marginTop: 0 }}>No house-style findings.</p>}
      {warnings.length > 0 && (
        <ul style={{ margin: '0 0 12px', paddingLeft: 18 }}>
          {warnings.map((f, i) => <li key={i}><span style={{ color: '#8A8A8A' }}>{f.where}:</span> {f.message}</li>)}
        </ul>
      )}
      {infos.length > 0 && (
        <p style={{ color: '#8A8A8A', fontSize: 13 }}>{infos.length} note{infos.length === 1 ? '' : 's'} (e.g. image placeholders awaiting upload) — fine to save.</p>
      )}
      {gate.checkOnly ? (
        <button type="button" style={btn} onClick={onKeepEditing}>Close</button>
      ) : (
        <>
          <button type="button" style={btn} onClick={onKeepEditing}>Keep editing</button>
          <button type="button" style={primary} onClick={onSaveAnyway}>Save anyway</button>
        </>
      )}
    </div>
  )
}
