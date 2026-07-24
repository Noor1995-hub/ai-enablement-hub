import { useState } from 'react'
import type { EmailStatus } from '../../types/domain'
import { useDefaults, useInvite, useTracks } from './api'
import { Modal, Spinner } from './kit'

interface InviteModalProps {
  projectId: string
  projectName: string
  onClose: () => void
}

interface FormMsg {
  ok: boolean
  text: string
}

interface InviteForm {
  firstName: string
  lastName: string
  email: string
}

const EMPTY_FORM: InviteForm = { firstName: '', lastName: '', email: '' }

/** Single-participant invite (spec §3.2). The two submit paths and the
 * email_status copy/link-box conventions are lifted from
 * frontend/src/pages/admin/ProjectDetailView.tsx's handleInvite; the
 * project-defaults banner is new to this redesign (spec §4.1 — defaults are
 * materialized server-side on invite, this banner just previews them via
 * useDefaults + useTracks). */
export default function InviteModal({ projectId, projectName, onClose }: InviteModalProps) {
  const [form, setForm] = useState<InviteForm>(EMPTY_FORM)
  const [formMsg, setFormMsg] = useState<FormMsg | null>(null)
  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const [emailStatus, setEmailStatus] = useState<EmailStatus>('disabled')
  const [copied, setCopied] = useState(false)

  const invite = useInvite()
  const tracksQuery = useTracks()
  const defaultsQuery = useDefaults(projectId)

  const valid = form.email.includes('@') && form.firstName.trim() !== '' && form.lastName.trim() !== ''
  const busy = invite.isPending

  const defaultTrackIds = defaultsQuery.data?.track_ids ?? []
  const defaultsBanner = defaultsQuery.isLoading
    ? null
    : defaultTrackIds.length === 0
      ? 'No project defaults configured.'
      : `Will automatically receive: ${defaultTrackIds
          .map(id => tracksQuery.data?.find(t => t.id === id)?.name ?? id)
          .join(', ')}`

  async function submit(sendEmail: boolean) {
    if (!valid || busy) return
    setFormMsg(null)
    setInviteLink(null)
    setCopied(false)
    try {
      const data = await invite.mutateAsync({
        email: form.email,
        firstName: form.firstName,
        lastName: form.lastName,
        projectId,
        sendEmail,
      })
      setEmailStatus(data.email_status)
      setFormMsg(
        data.email_status === 'sent'
          ? { ok: true, text: `${form.firstName} added — invitation emailed.` }
          : data.email_status === 'failed'
            ? { ok: false, text: `${form.firstName} added, but the email could not be sent — share the link below manually.` }
            : { ok: true, text: `${form.firstName} added. Share the link below:` },
      )
      setInviteLink(data.link)
      setForm(EMPTY_FORM)
    } catch (e) {
      setFormMsg({ ok: false, text: e instanceof Error ? e.message : 'Something went wrong.' })
    }
  }

  function copyLink() {
    if (!inviteLink) return
    void navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Modal
      title="Invite participant"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="adm-btn adm-btn-red" disabled={!valid || busy} onClick={() => void submit(true)}>
            {busy ? <Spinner size="sm" /> : <MailIcon />}
            Send email invite
          </button>
          <button type="button" className="adm-btn adm-btn-ghost" disabled={!valid || busy} onClick={() => void submit(false)}>
            Create invite link only
          </button>
          <button type="button" className="adm-btn adm-btn-subtle adm-push-right" disabled={busy} onClick={onClose}>
            Cancel
          </button>
        </>
      }
    >
      <p className="adm-hint">{projectName}</p>

      <div className="adm-field">
        <label className="adm-field-label" htmlFor="invite-first-name">First name</label>
        <input
          id="invite-first-name"
          className="adm-field-input"
          placeholder="Sarah"
          value={form.firstName}
          onChange={e => setForm(f => ({ ...f, firstName: e.target.value }))}
        />
      </div>
      <div className="adm-field">
        <label className="adm-field-label" htmlFor="invite-last-name">Last name</label>
        <input
          id="invite-last-name"
          className="adm-field-input"
          placeholder="Mertens"
          value={form.lastName}
          onChange={e => setForm(f => ({ ...f, lastName: e.target.value }))}
        />
      </div>
      <div className="adm-field">
        <label className="adm-field-label" htmlFor="invite-email">Work email</label>
        <input
          id="invite-email"
          type="email"
          className="adm-field-input"
          placeholder="sarah@company.com"
          value={form.email}
          onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
        />
      </div>

      {defaultsBanner && <div className="adm-note-banner">{defaultsBanner}</div>}

      {formMsg && (
        <p className={`adm-form-msg ${formMsg.ok ? 'adm-form-msg-ok' : 'adm-form-msg-err'}`}>
          {formMsg.ok ? '✓ ' : ''}{formMsg.text}
        </p>
      )}

      {inviteLink && (
        <div className="adm-link-box">
          <p className="adm-link-box-label">
            {emailStatus === 'sent'
              ? 'Invite link — emailed to the participant (fallback below)'
              : emailStatus === 'failed'
                ? 'Email failed — send this link to the participant'
                : 'Invite link — send this to the participant'}
          </p>
          <div className="adm-link-row">
            <input className="adm-link-input" readOnly value={inviteLink} onFocus={e => e.target.select()} />
            <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" onClick={copyLink}>
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function MailIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={2} y={4} width={20} height={16} rx={2} />
      <path d="m22 7-10 6L2 7" />
    </svg>
  )
}
