import { useState } from 'react'
import { fetchProjectExport, saveFile, type ExportSection } from '../../api/projectExport'
import { Modal, Spinner } from './kit'

interface ExportModalProps {
  projectId: string
  projectName: string
  onClose: () => void
}

interface SectionOption {
  value: ExportSection
  label: string
  hint: string
}

// Order = the sheet order the backend writes. Interview starts unticked: it holds
// the learner's own words and the delaware-internal playbook (#92).
const SECTIONS: SectionOption[] = [
  { value: 'people', label: 'People', hint: 'Name, email, status, maturity, last active' },
  { value: 'assessment', label: 'Assessment', hint: 'Every answer as text and code, scores; drafts marked' },
  { value: 'progress', label: 'Progress', hint: 'Each assigned or completed lesson, with the date' },
  { value: 'interview', label: 'Interview (sensitive)', hint: 'Shared and internal playbook, full transcript' },
]

const DEFAULT_SECTIONS: ExportSection[] = ['people', 'assessment', 'progress']

/** "Export data" on the People page (#92): tick sections, download one .xlsx. */
export default function ExportModal({ projectId, projectName, onClose }: ExportModalProps) {
  const [picked, setPicked] = useState<Set<ExportSection>>(new Set(DEFAULT_SECTIONS))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggle(section: ExportSection) {
    setPicked(prev => {
      const next = new Set(prev)
      if (next.has(section)) next.delete(section)
      else next.add(section)
      return next
    })
  }

  async function download() {
    if (picked.size === 0 || busy) return
    setBusy(true)
    setError(null)
    try {
      const sections = SECTIONS.map(s => s.value).filter(value => picked.has(value))
      saveFile(await fetchProjectExport(projectId, sections))
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The export failed. Please try again.')
      setBusy(false)
    }
  }

  return (
    <Modal
      title="Export data"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="adm-btn adm-btn-red" disabled={picked.size === 0 || busy} onClick={() => void download()}>
            {busy && <Spinner size="sm" />}
            Download .xlsx
          </button>
          <button type="button" className="adm-btn adm-btn-subtle adm-push-right" disabled={busy} onClick={onClose}>
            Cancel
          </button>
        </>
      }
    >
      <p className="adm-hint">{projectName} · learners only, one sheet per section</p>

      <div className="adm-check-list adm-modal-section">
        {SECTIONS.map(section => (
          <label key={section.value} className="adm-check-row">
            <input type="checkbox" checked={picked.has(section.value)} onChange={() => toggle(section.value)} />
            <span>
              {section.label}
              <span className="adm-subtext"> · {section.hint}</span>
            </span>
          </label>
        ))}
      </div>

      <div className="adm-note-banner" role="note">
        This file contains personal data about the project's learners. Store it only where the
        client engagement allows, share it with no one who doesn't need it, and delete it when
        you're done.
      </div>

      {error && (
        <p className="adm-form-msg adm-form-msg-err" role="alert">
          {error}
        </p>
      )}
    </Modal>
  )
}
