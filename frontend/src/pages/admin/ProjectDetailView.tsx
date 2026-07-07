import React, { useState } from 'react'
import { client, errorMessage } from '../../api/client'
import type { ComponentKey } from '../../lib/constants'
import type { AdminUser, ComponentState, EmailStatus } from '../../types/domain'
import type { ResetLinkEntry } from '../Admin'
import { s, COMPONENT_KEYS, COMPONENT_LABELS } from './adminStyles'
import { LevelBadge, Field, formatDate } from './adminHelpers'

/*
 * Props are grouped into logical objects to keep the signature manageable.
 * The old `authH` prop is gone (the api client owns auth — A2), and the old
 * `learning` group is gone too: it was destructured here but never rendered.
 */

export interface SelectedProject {
  id: string
  name: string
  company_name: string
}

interface ParticipantsProps {
  users: AdminUser[]
  loading: boolean
  error: string | null
  surveyLevels: Record<string, string>
  togglingRole: string | null
  generatingReset: string | null
  resetLinks: Record<string, ResetLinkEntry>
  confirmDelete: string | null
  deleting: string | null
}

interface ComponentAccessProps {
  data: Record<string, ComponentState>
  loading: boolean
  error: string | null
  toggling: string | null
}

interface Handlers {
  onBack: () => void
  onToggleComponent: (comp: ComponentKey, current: ComponentState, field: 'hidden' | 'locked') => void
  onRoleToggle: (userId: string, currentRole: string) => void
  onDelete: (userId: string) => void
  onSetConfirmDelete: (userId: string) => void
  onGenerateResetLink: (userId: string) => void
  onCopyResetLink: (userId: string) => void
  onDismissResetLink: (userId: string) => void
  onOpenUserPanel: (user: AdminUser) => void
  onProjectRefresh?: () => void
}

interface ProjectDetailViewProps {
  project: SelectedProject
  participants: ParticipantsProps
  componentAccess: ComponentAccessProps
  handlers: Handlers
}

interface FormMsg {
  ok: boolean
  text: string
}

type InviteField = 'first_name' | 'last_name' | 'email'

export default function ProjectDetailView({
  project,
  participants,
  componentAccess,
  handlers,
}: ProjectDetailViewProps) {
  const {
    users: projectUsers, loading: loadingProjectUsers, error: projectUsersError,
    surveyLevels, togglingRole, generatingReset, resetLinks, confirmDelete, deleting,
  } = participants

  const {
    data: projectComponents, loading: loadingComponents, error: componentError,
    toggling: togglingComponent,
  } = componentAccess

  const {
    onBack, onToggleComponent, onRoleToggle, onDelete, onSetConfirmDelete,
    onGenerateResetLink, onCopyResetLink, onDismissResetLink, onOpenUserPanel,
    onProjectRefresh,
  } = handlers

  const [inviteForm, setInviteForm] = useState<Record<InviteField, string>>({ first_name: '', last_name: '', email: '' })
  const [focused, setFocused] = useState<Partial<Record<InviteField, boolean>>>({})
  const [submittingAction, setSubmittingAction] = useState<'link' | 'email' | null>(null)
  const [formMsg, setFormMsg] = useState<FormMsg | null>(null)
  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const [inviteEmailStatus, setInviteEmailStatus] = useState<EmailStatus>('disabled')
  const [copied, setCopied] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)

  const valid = inviteForm.email.includes('@') && inviteForm.first_name.trim() && inviteForm.last_name.trim()

  async function handleInvite(sendEmail: boolean) {
    if (!valid || submittingAction) return
    setSubmittingAction(sendEmail ? 'email' : 'link')
    setFormMsg(null)
    setInviteLink(null)
    setCopied(false)
    try {
      const { data, error } = await client.POST('/api/admin/invites', {
        body: { ...inviteForm, project_id: project.id, send_email: sendEmail },
      })
      if (data) {
        setInviteEmailStatus(data.email_status)
        setFormMsg(
          data.email_status === 'sent'
            ? { ok: true, text: `${inviteForm.first_name} added — invitation emailed.` }
            : data.email_status === 'failed'
              ? { ok: false, text: `${inviteForm.first_name} added, but the email could not be sent — share the link below manually.` }
              : { ok: true, text: `${inviteForm.first_name} added. Share the link below:` },
        )
        setInviteLink(data.link)
        setInviteForm({ first_name: '', last_name: '', email: '' })
        onProjectRefresh?.()
      } else {
        setFormMsg({ ok: false, text: errorMessage(error, 'Something went wrong.') })
      }
    } catch {
      setFormMsg({ ok: false, text: 'Network error, please try again.' })
    }
    setSubmittingAction(null)
  }

  function copyInviteLink() {
    if (!inviteLink) return
    navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div>
      {/* header */}
      <div style={s.projectViewHeader}>
        <button type="button" style={s.backLink} onClick={onBack}>← All projects</button>
        <div style={s.navDivider} />
        <h1 style={s.projectViewTitle}>
          {project.name}
          <span style={s.projectViewCo}>— {project.company_name}</span>
        </h1>
      </div>

      {/* invite toggle */}
      <div style={{ marginBottom: 20, display: 'flex', gap: 10, alignItems: 'center' }}>
        <button
          type="button"
          style={{ ...s.submitBtn, fontSize: 13, padding: '9px 20px' }}
          onClick={() => { setInviteOpen(o => !o); setFormMsg(null); setInviteLink(null) }}
        >
          {inviteOpen ? '× Cancel' : '+ Add participant'}
        </button>
      </div>

      {/* invite form */}
      {inviteOpen && (
        <div style={{ ...s.card, marginBottom: 24 }}>
          <p style={s.cardTitle}>Add a participant to {project.name}</p>
          <form onSubmit={e => { e.preventDefault(); handleInvite(false) }} noValidate>
            <div style={s.formRow}>
              <Field id="invite-first" label="First name" placeholder="Sarah" value={inviteForm.first_name}
                onChange={v => setInviteForm(f => ({ ...f, first_name: v }))}
                focused={focused.first_name}
                onFocus={() => setFocused(f => ({ ...f, first_name: true }))}
                onBlur={() => setFocused(f => ({ ...f, first_name: false }))} />
              <Field id="invite-last" label="Last name" placeholder="Mertens" value={inviteForm.last_name}
                onChange={v => setInviteForm(f => ({ ...f, last_name: v }))}
                focused={focused.last_name}
                onFocus={() => setFocused(f => ({ ...f, last_name: true }))}
                onBlur={() => setFocused(f => ({ ...f, last_name: false }))} />
              <Field id="invite-email" label="Work email" type="email" placeholder="sarah@company.com" value={inviteForm.email}
                onChange={v => setInviteForm(f => ({ ...f, email: v }))}
                focused={focused.email}
                onFocus={() => setFocused(f => ({ ...f, email: true }))}
                onBlur={() => setFocused(f => ({ ...f, email: false }))} />
            </div>
            <div style={s.formActions}>
              <button
                type="submit" className="btn-ghost"
                disabled={!valid || !!submittingAction}
                style={{ ...s.submitBtn, ...(!valid || !!submittingAction ? s.submitBtnDisabled : {}) }}
              >
                {submittingAction === 'link' ? 'creating…' : 'create invite link →'}
              </button>
              <button
                type="button" className="btn-red-dark"
                disabled={!valid || !!submittingAction}
                onClick={() => handleInvite(true)}
                style={{ ...s.submitBtn, ...(!valid || !!submittingAction ? s.submitBtnDisabled : {}) }}
              >
                {submittingAction === 'email' ? 'sending…' : 'send email with invite →'}
              </button>
              {formMsg && (
                <span style={{ ...s.formMsg, ...(formMsg.ok ? s.formMsgOk : s.formMsgErr) }}>
                  {formMsg.ok ? '✓ ' : ''}{formMsg.text}
                </span>
              )}
            </div>
          </form>
          {inviteLink && (
            <div style={s.linkBox}>
              <p style={s.linkBoxLabel}>
                {inviteEmailStatus === 'sent'
                  ? 'Invite link — emailed to the participant (fallback below)'
                  : inviteEmailStatus === 'failed'
                    ? 'Email failed — send this link to the participant'
                    : 'Invite link — send this to the participant'}
              </p>
              <div style={s.linkRow}>
                <input style={s.linkInput} readOnly value={inviteLink} onFocus={e => e.target.select()} />
                <button style={s.copyBtn} onClick={copyInviteLink}>{copied ? '✓ copied' : 'copy'}</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* participants table */}
      <div style={{ ...s.tableCard, marginBottom: 28 }}>
        <div style={s.tableHeader}>
          <p style={s.tableTitle}>Participants</p>
          <span style={s.userCount}>{projectUsers.length} {projectUsers.length === 1 ? 'person' : 'people'}</span>
        </div>
        <table style={s.table}>
          <thead>
            <tr>
              <th style={s.th}>Name</th>
              <th style={s.th}>Email</th>
              <th style={s.th}>Added</th>
              <th style={s.th}>Status</th>
              <th style={s.th}>Maturity</th>
              <th style={s.th}>Role</th>
              <th style={s.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loadingProjectUsers ? (
              <tr><td colSpan={7} style={s.emptyRow}>loading…</td></tr>
            ) : projectUsersError ? (
              <tr><td colSpan={7} style={{ ...s.emptyRow, color: '#C42828' }}>{projectUsersError}</td></tr>
            ) : projectUsers.length === 0 ? (
              <tr><td colSpan={7} style={s.emptyRow}>no participants yet.</td></tr>
            ) : projectUsers.map(u => {
              return (
                <React.Fragment key={u.id}>
                  <tr>
                    <td style={{ ...s.td, ...s.tdName }}>
                      <button
                        type="button"
                        style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', fontWeight: 700, fontSize: 14, color: '#101820', textDecoration: 'underline', textDecorationColor: '#E2E2E2', fontFamily: 'inherit' }}
                        onClick={() => onOpenUserPanel(u)}
                      >
                        {u.first_name} {u.last_name}
                      </button>
                    </td>
                    <td style={s.td}>{u.email}</td>
                    <td style={s.td}>{formatDate(u.created_at)}</td>
                    <td style={s.td}>
                      <span style={{ ...s.badge, ...(u.is_active ? s.badgeActive : s.badgeInvited) }}>
                        {u.is_active ? 'active' : 'invited'}
                      </span>
                    </td>
                    <td style={s.td}>
                      {surveyLevels[u.id]
                        ? <LevelBadge level={surveyLevels[u.id]} />
                        : <span style={{ fontSize: 12, color: '#C4C4C4' }}>—</span>}
                    </td>
                    <td style={s.td}>
                      <button
                        style={{
                          ...s.badge, cursor: 'pointer', border: 'none',
                          ...(u.role === 'admin' ? { background: '#101820', color: '#fff' } : { background: '#F5F5F5', color: '#8A8A8A' }),
                          ...(togglingRole === u.id ? { opacity: 0.5, cursor: 'not-allowed' } : {}),
                        }}
                        disabled={togglingRole === u.id}
                        onClick={() => onRoleToggle(u.id, u.role)}
                        title={u.role === 'admin' ? 'Click to remove admin' : 'Click to make admin'}
                      >
                        {togglingRole === u.id ? '…' : u.role || 'user'}
                      </button>
                    </td>
                    <td style={s.td}>
                      <div style={s.actionCell}>
                        <button className="btn-ghost" style={s.resendBtn}
                          disabled={generatingReset === u.id}
                          onClick={() => onGenerateResetLink(u.id)}
                        >
                          {generatingReset === u.id ? '…' : resetLinks[u.id] ? 'regenerate' : 'reset link'}
                        </button>
                        {confirmDelete === u.id ? (
                          <button style={s.deleteBtnConfirm} onClick={() => onDelete(u.id)} disabled={deleting === u.id}>
                            {deleting === u.id ? 'deleting…' : 'confirm'}
                          </button>
                        ) : (
                          <button className="btn-ghost-danger" style={s.deleteBtn}
                            onClick={() => onSetConfirmDelete(u.id)} disabled={deleting === u.id}>
                            delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {resetLinks[u.id] && (
                    <tr>
                      <td colSpan={7} style={{ padding: '0 24px 14px', borderBottom: '1px solid #F5F5F5' }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '10px 14px', background: '#FEF3F2', border: '1px solid #FBCFCC', borderRadius: 6 }}>
                          <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, color: '#C42828', whiteSpace: 'nowrap', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                            {resetLinks[u.id].emailStatus === 'sent'
                              ? 'Password reset link · emailed'
                              : resetLinks[u.id].emailStatus === 'failed'
                                ? 'Password reset link · email failed — share manually'
                                : 'Password reset link'}
                          </span>
                          <input style={{ ...s.linkInput, borderColor: '#FBCFCC', flex: 1 }} readOnly value={resetLinks[u.id].link} onFocus={e => e.target.select()} />
                          <button style={{ ...s.copyBtn, color: '#C42828', borderColor: '#FBCFCC' }} onClick={() => onCopyResetLink(u.id)}>
                            {resetLinks[u.id].copied ? '✓ copied' : 'copy'}
                          </button>
                          <button style={{ ...s.copyBtn, color: '#B6B6B6', borderColor: '#E2E2E2' }} onClick={() => onDismissResetLink(u.id)}>
                            dismiss
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* component access */}
      <div style={{ ...s.tableCard, marginBottom: 28 }}>
        <div style={s.tableHeader}>
          <p style={s.tableTitle}>Component access</p>
        </div>
        {componentError && (
          <div style={{ margin: '0 24px 16px', padding: '10px 14px', background: '#FFF0EF', border: '1px solid #FBCFCC', borderRadius: 6, fontSize: 13, color: '#C42828' }}>
            {componentError}
          </div>
        )}
        {loadingComponents ? (
          <p style={{ padding: '32px 24px', fontSize: 14, color: '#B6B6B6', fontWeight: 300 }}>loading…</p>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Component</th>
                <th style={s.th}>Lock state</th>
                <th style={s.th}>Visibility</th>
              </tr>
            </thead>
            <tbody>
              {COMPONENT_KEYS.map(comp => {
                const current = projectComponents[comp] ?? { locked: false, hidden: false }
                const busyLocked = togglingComponent === `${comp}-locked`
                const busyHidden = togglingComponent === `${comp}-hidden`
                return (
                  <tr key={comp}>
                    <td style={{ ...s.td, ...s.tdName }}>{COMPONENT_LABELS[comp]}</td>
                    <td style={s.td}>
                      <button
                        style={{ ...(current.locked ? s.toggleLocked : s.toggleOpen), ...(busyLocked ? s.toggleBusy : {}) }}
                        onClick={() => onToggleComponent(comp, current, 'locked')}
                        disabled={busyLocked || busyHidden}
                      >
                        {busyLocked ? '…' : current.locked ? 'locked' : 'open'}
                      </button>
                    </td>
                    <td style={s.td}>
                      <button
                        style={{ ...(current.hidden ? s.toggleHidden : s.toggleVisible), ...(busyHidden ? s.toggleBusy : {}) }}
                        onClick={() => onToggleComponent(comp, current, 'hidden')}
                        disabled={busyLocked || busyHidden}
                      >
                        {busyHidden ? '…' : current.hidden ? 'hidden' : 'visible'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
