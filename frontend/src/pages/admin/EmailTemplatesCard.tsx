import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { client, errorMessage } from '../../api/client'
import type { EmailTemplate, EmailTemplatePreview, EmailTemplatePurpose } from '../../types/domain'
import { s } from './adminStyles'

/*
 * Per-project invite/reset email editor. Owns its own data (GET/PUT/DELETE/
 * preview) so ProjectDetailView stays a thin container. The message is Markdown
 * with {{tokens}}; the action link goes wherever the admin drops its token, and
 * rendering (Markdown → HTML) happens server-side so the preview is faithful.
 */

const PURPOSES: { key: EmailTemplatePurpose; label: string }[] = [
  { key: 'invite', label: 'Invitation' },
  { key: 'reset', label: 'Password reset' },
]

// Mirrors the backend's ALLOWED_TOKENS; the link token is required in the body
// (enforced on save + flagged inline, so it needs no special chip styling).
const TOKENS: Record<EmailTemplatePurpose, { name: string; hint: string }[]> = {
  invite: [
    { name: 'invite_link', hint: 'set-password link (required)' },
    { name: 'first_name', hint: 'recipient first name' },
    { name: 'last_name', hint: 'recipient last name' },
    { name: 'project_name', hint: 'this project' },
    { name: 'ttl_days', hint: 'link validity, e.g. “7 days”' },
    { name: 'login_url', hint: 'Microsoft sign-in (Entra only)' },
  ],
  reset: [
    { name: 'reset_link', hint: 'password-reset link (required)' },
    { name: 'first_name', hint: 'recipient first name' },
    { name: 'last_name', hint: 'recipient last name' },
    { name: 'project_name', hint: 'this project' },
    { name: 'ttl_days', hint: 'link validity, e.g. “7 days”' },
  ],
}

const linkToken = (purpose: EmailTemplatePurpose): string =>
  purpose === 'invite' ? 'invite_link' : 'reset_link'

interface Draft {
  subject: string
  body_markdown: string
}

export default function EmailTemplatesCard({ projectId }: { projectId: string }) {
  const [loaded, setLoaded] = useState<Record<EmailTemplatePurpose, EmailTemplate> | null>(null)
  const [draft, setDraft] = useState<Record<EmailTemplatePurpose, Draft> | null>(null)
  const [purpose, setPurpose] = useState<EmailTemplatePurpose>('invite')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const [preview, setPreview] = useState<EmailTemplatePreview | null>(null)
  const [previewing, setPreviewing] = useState(false)

  const bodyRef = useRef<HTMLTextAreaElement | null>(null)

  async function load() {
    setLoadError(null)
    const { data, error } = await client.GET('/api/admin/projects/{project_id}/email-templates', {
      params: { path: { project_id: projectId } },
    })
    if (data) {
      const byPurpose = Object.fromEntries(data.templates.map(t => [t.purpose, t])) as Record<
        EmailTemplatePurpose,
        EmailTemplate
      >
      setLoaded(byPurpose)
      setDraft(
        Object.fromEntries(
          data.templates.map(t => [t.purpose, { subject: t.subject, body_markdown: t.body_markdown }]),
        ) as Record<EmailTemplatePurpose, Draft>,
      )
    } else {
      setLoadError(errorMessage(error, 'Could not load email templates.'))
    }
  }

  useEffect(() => {
    let cancelled = false
    void (async () => {
      await load()
      if (cancelled) return
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  // Switching purpose or projects clears the transient preview/message.
  useEffect(() => {
    setPreview(null)
    setMsg(null)
    setConfirmReset(false)
  }, [purpose])

  if (loadError) {
    return (
      <div style={{ ...s.tableCard, marginBottom: 28 }}>
        <div style={s.tableHeader}>
          <p style={s.tableTitle}>Email templates</p>
        </div>
        <p style={{ padding: '24px', fontSize: 13, color: '#C42828' }}>{loadError}</p>
      </div>
    )
  }
  if (!loaded || !draft) {
    return (
      <div style={{ ...s.tableCard, marginBottom: 28 }}>
        <div style={s.tableHeader}>
          <p style={s.tableTitle}>Email templates</p>
        </div>
        <p style={{ padding: '24px', fontSize: 14, color: '#B6B6B6', fontWeight: 300 }}>loading…</p>
      </div>
    )
  }

  const current = draft[purpose]
  const server = loaded[purpose]
  const dirty =
    current.subject !== server.subject || current.body_markdown !== server.body_markdown
  const required = linkToken(purpose)
  const hasLink = current.body_markdown.includes(`{{${required}}}`)
  const canSave = dirty && current.subject.trim() !== '' && current.body_markdown.trim() !== '' && hasLink

  function setField(field: keyof Draft, value: string) {
    setDraft(d => (d ? { ...d, [purpose]: { ...d[purpose], [field]: value } } : d))
    setMsg(null)
  }

  function insertToken(token: string) {
    const ta = bodyRef.current
    const value = current.body_markdown
    if (!ta) {
      setField('body_markdown', `${value}{{${token}}}`)
      return
    }
    const start = ta.selectionStart ?? value.length
    const end = ta.selectionEnd ?? value.length
    const snippet = `{{${token}}}`
    setField('body_markdown', value.slice(0, start) + snippet + value.slice(end))
    requestAnimationFrame(() => {
      ta.focus()
      const caret = start + snippet.length
      ta.setSelectionRange(caret, caret)
    })
  }

  async function handleSave() {
    if (!canSave || saving) return
    setSaving(true)
    setMsg(null)
    const { error } = await client.PUT(
      '/api/admin/projects/{project_id}/email-templates/{purpose}',
      {
        params: { path: { project_id: projectId, purpose } },
        body: { subject: current.subject, body_markdown: current.body_markdown },
      },
    )
    if (!error) {
      setLoaded(l =>
        l ? { ...l, [purpose]: { ...l[purpose], ...current, is_custom: true } } : l,
      )
      setMsg({ ok: true, text: 'Saved.' })
    } else {
      setMsg({ ok: false, text: errorMessage(error, 'Could not save the template.') })
    }
    setSaving(false)
  }

  async function handleResetToDefault() {
    if (resetting) return
    setResetting(true)
    setMsg(null)
    const { error } = await client.DELETE(
      '/api/admin/projects/{project_id}/email-templates/{purpose}',
      { params: { path: { project_id: projectId, purpose } } },
    )
    if (!error) {
      await load()
      setMsg({ ok: true, text: 'Reverted to the default template.' })
    } else {
      setMsg({ ok: false, text: errorMessage(error, 'Could not reset the template.') })
    }
    setConfirmReset(false)
    setResetting(false)
  }

  async function handlePreview() {
    if (previewing) return
    setPreviewing(true)
    setMsg(null)
    const { data, error } = await client.POST(
      '/api/admin/projects/{project_id}/email-templates/{purpose}/preview',
      {
        params: { path: { project_id: projectId, purpose } },
        body: { subject: current.subject, body_markdown: current.body_markdown },
      },
    )
    if (data) setPreview(data)
    else setMsg({ ok: false, text: errorMessage(error, 'Could not render the preview.') })
    setPreviewing(false)
  }

  return (
    <div style={{ ...s.tableCard, marginBottom: 28 }}>
      <div style={s.tableHeader}>
        <p style={s.tableTitle}>Email templates</p>
        <span style={{ ...s.badge, ...(server.is_custom ? s.badgeActive : es.defaultBadge) }}>
          {server.is_custom ? 'customized' : 'default'}
        </span>
      </div>

      <div style={es.body}>
        {/* purpose switcher */}
        <div style={es.tabs}>
          {PURPOSES.map(p => (
            <button
              key={p.key}
              type="button"
              onClick={() => setPurpose(p.key)}
              style={{ ...es.tab, ...(purpose === p.key ? es.tabActive : es.tabInactive) }}
            >
              {p.label}
            </button>
          ))}
        </div>

        <p style={es.hint}>
          Write the message in Markdown (**bold**, lists, [links](url)). Insert a{' '}
          <code>{`{{token}}`}</code> where you want a value filled in — the message must include{' '}
          <code>{`{{${required}}}`}</code>, which becomes the clickable link wherever you place it.
        </p>

        {/* subject */}
        <label style={s.label} htmlFor="tpl-subject">
          Subject
        </label>
        <input
          id="tpl-subject"
          style={{ ...s.input, marginBottom: 16 }}
          value={current.subject}
          onChange={e => setField('subject', e.target.value)}
        />

        {/* body */}
        <label style={s.label} htmlFor="tpl-body">
          Message body
        </label>
        <div style={es.tokenRow}>
          {TOKENS[purpose].map(t => (
            <button
              key={t.name}
              type="button"
              title={t.hint}
              onClick={() => insertToken(t.name)}
              style={es.tokenChip}
            >
              {`{{${t.name}}}`}
            </button>
          ))}
        </div>
        <textarea
          id="tpl-body"
          ref={bodyRef}
          style={es.textarea}
          value={current.body_markdown}
          onChange={e => setField('body_markdown', e.target.value)}
          spellCheck
        />
        {!hasLink && (
          <p style={{ ...s.formMsg, ...s.formMsgErr, marginTop: 8 }}>
            The message must include the {`{{${required}}}`} token so the email has its link.
          </p>
        )}

        {/* actions */}
        <div style={{ ...s.formActions, flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave || saving}
            style={{ ...s.submitBtn, ...(!canSave || saving ? s.submitBtnDisabled : {}) }}
          >
            {saving ? 'saving…' : 'Save template'}
          </button>
          <button
            type="button"
            onClick={handlePreview}
            disabled={previewing}
            style={{ ...es.secondaryBtn, ...(previewing ? { opacity: 0.6, cursor: 'wait' } : {}) }}
          >
            {previewing ? 'rendering…' : 'Preview'}
          </button>
          {server.is_custom &&
            (confirmReset ? (
              <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 13, color: '#C42828' }}>Revert to default?</span>
                <button
                  type="button"
                  onClick={handleResetToDefault}
                  disabled={resetting}
                  style={s.deleteBtnConfirm}
                >
                  {resetting ? 'reverting…' : 'yes, revert'}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmReset(false)}
                  style={s.deleteBtn}
                >
                  cancel
                </button>
              </span>
            ) : (
              <button type="button" onClick={() => setConfirmReset(true)} style={s.deleteBtn}>
                Reset to default
              </button>
            ))}
          {msg && (
            <span style={{ ...s.formMsg, ...(msg.ok ? s.formMsgOk : s.formMsgErr) }}>
              {msg.ok ? '✓ ' : ''}
              {msg.text}
            </span>
          )}
        </div>

        {/* preview */}
        {preview && (
          <div style={es.preview}>
            <div style={es.previewMeta}>
              <span style={es.previewLabel}>Preview (sample values)</span>
              <span style={es.previewSubject}>Subject: {preview.subject}</span>
            </div>
            <iframe
              title="Email preview"
              sandbox=""
              srcDoc={preview.html}
              style={es.previewFrame}
            />
          </div>
        )}
      </div>
    </div>
  )
}

const es = {
  body: { padding: '20px 24px 24px' },
  defaultBadge: { background: '#F5F5F5', color: '#8A8A8A' },
  tabs: { display: 'flex', gap: 4, marginBottom: 18 },
  tab: {
    padding: '6px 16px', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
    border: 'none', borderRadius: 6, cursor: 'pointer', transition: 'background 150ms, color 150ms',
  },
  tabActive: { background: '#101820', color: '#fff' },
  tabInactive: { background: '#F5F5F5', color: '#8A8A8A' },
  hint: { fontSize: 13, fontWeight: 300, color: '#8A8A8A', lineHeight: 1.6, margin: '0 0 18px' },
  tokenRow: { display: 'flex', flexWrap: 'wrap', gap: 6, margin: '0 0 8px' },
  tokenChip: {
    fontFamily: 'ui-monospace, Menlo, Consolas, monospace', fontSize: 11, fontWeight: 600,
    padding: '4px 9px', borderRadius: 6, cursor: 'pointer',
    border: '1px solid #E2E2E2', background: '#FAFAF9', color: '#3C3C3C',
  },
  textarea: {
    width: '100%', minHeight: 220, padding: '12px 14px', boxSizing: 'border-box',
    fontFamily: 'ui-monospace, Menlo, Consolas, monospace', fontSize: 13, lineHeight: 1.6,
    color: '#101820', border: '1px solid #E2E2E2', borderRadius: 4, outline: 'none',
    resize: 'vertical',
  },
  secondaryBtn: {
    padding: '11px 20px', fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 14,
    color: '#101820', background: '#fff', border: '1px solid #E2E2E2', borderRadius: 999,
    cursor: 'pointer', whiteSpace: 'nowrap',
  },
  preview: { marginTop: 20 },
  previewMeta: { display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'baseline', marginBottom: 8 },
  previewLabel: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.1em',
    textTransform: 'uppercase', color: '#8A8A8A',
  },
  previewSubject: { fontSize: 13, fontWeight: 600, color: '#101820' },
  previewFrame: {
    width: '100%', height: 340, border: '1px solid #E2E2E2', borderRadius: 8, background: '#fff',
  },
} satisfies Record<string, CSSProperties>
