import { useState } from 'react'
import { client, errorMessage } from '../../api/client'
import type { CompanyWithProjects } from '../../types/domain'
import { s } from './adminStyles'
import { Field } from './adminHelpers'

// Contract deviation from the old app: project creation is its own endpoint
// (POST /api/admin/projects), not a `type: 'project'` variant of the companies
// POST — and both return the created row directly, not wrapped in
// {company}/{project}.

interface SetupViewProps {
  companiesData: CompanyWithProjects[]
  onCompaniesChanged: () => void
}

interface FormMsg {
  ok: boolean
  text: string
}

export default function SetupView({ companiesData, onCompaniesChanged }: SetupViewProps) {
  const [companyForm, setCompanyForm] = useState({ name: '' })
  const [companyFocused, setCompanyFocused] = useState<{ name?: boolean }>({})
  const [companySubmitting, setCompanySubmitting] = useState(false)
  const [companyMsg, setCompanyMsg] = useState<FormMsg | null>(null)

  const [projectForm, setProjectForm] = useState({ name: '', company_id: '' })
  const [projectFocused, setProjectFocused] = useState<{ name?: boolean }>({})
  const [projectSubmitting, setProjectSubmitting] = useState(false)
  const [projectMsg, setProjectMsg] = useState<FormMsg | null>(null)

  async function handleCreateCompany(e: React.FormEvent) {
    e.preventDefault()
    if (!companyForm.name.trim() || companySubmitting) return
    setCompanySubmitting(true)
    setCompanyMsg(null)
    try {
      const { data, error } = await client.POST('/api/admin/companies', {
        body: { name: companyForm.name },
      })
      if (data) {
        setCompanyMsg({ ok: true, text: `Company "${data.name}" created.` })
        setCompanyForm({ name: '' })
        onCompaniesChanged()
      } else {
        setCompanyMsg({ ok: false, text: errorMessage(error, 'Something went wrong.') })
      }
    } catch {
      setCompanyMsg({ ok: false, text: 'Network error.' })
    }
    setCompanySubmitting(false)
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault()
    if (!projectForm.name.trim() || !projectForm.company_id || projectSubmitting) return
    setProjectSubmitting(true)
    setProjectMsg(null)
    try {
      const { data, error } = await client.POST('/api/admin/projects', {
        body: { name: projectForm.name, company_id: projectForm.company_id },
      })
      if (data) {
        setProjectMsg({ ok: true, text: `Project "${data.name}" created.` })
        setProjectForm({ name: '', company_id: '' })
        onCompaniesChanged()
      } else {
        setProjectMsg({ ok: false, text: errorMessage(error, 'Something went wrong.') })
      }
    } catch {
      setProjectMsg({ ok: false, text: 'Network error.' })
    }
    setProjectSubmitting(false)
  }

  return (
    <div>
      <h1 style={s.pageTitle}>Setup</h1>
      <p style={s.pageSubtitle}>Create companies and projects.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'start' }}>

        {/* create company */}
        <div style={s.card}>
          <p style={s.cardTitle}>New company</p>
          <form onSubmit={handleCreateCompany} noValidate>
            <div style={s.formRow}>
              <Field
                id="company-name" label="Company name" placeholder="Acme NV"
                value={companyForm.name} onChange={v => setCompanyForm({ name: v })}
                focused={companyFocused.name}
                onFocus={() => setCompanyFocused({ name: true })}
                onBlur={() => setCompanyFocused({})}
              />
            </div>
            <div style={s.formActions}>
              <button
                type="submit" className="btn-red-dark"
                disabled={!companyForm.name.trim() || companySubmitting}
                style={{ ...s.submitBtn, ...(!companyForm.name.trim() || companySubmitting ? s.submitBtnDisabled : {}) }}
              >
                {companySubmitting ? 'creating…' : 'Create company'}
              </button>
              {companyMsg && (
                <span style={{ ...s.formMsg, ...(companyMsg.ok ? s.formMsgOk : s.formMsgErr) }}>
                  {companyMsg.ok ? '✓ ' : ''}{companyMsg.text}
                </span>
              )}
            </div>
          </form>

          {companiesData.length > 0 && (
            <div style={{ marginTop: 20, borderTop: '1px solid #F0EFED', paddingTop: 16 }}>
              <p style={{ ...s.companyLabel, marginBottom: 8 }}>Existing companies</p>
              {companiesData.map(c => (
                <div key={c.id} style={{ fontSize: 13, color: '#3C3C3C', padding: '4px 0', display: 'flex', justifyContent: 'space-between' }}>
                  <span>{c.name}</span>
                  <span style={{ color: '#B6B6B6', fontSize: 12 }}>{c.projects.length} {c.projects.length === 1 ? 'project' : 'projects'}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* create project */}
        <div style={s.card}>
          <p style={s.cardTitle}>New project</p>
          <form onSubmit={handleCreateProject} noValidate>
            <div style={{ ...s.fieldWrap, marginBottom: 14 }}>
              <label style={s.label}>Company</label>
              <select
                style={s.select}
                value={projectForm.company_id}
                onChange={e => setProjectForm(f => ({ ...f, company_id: e.target.value }))}
              >
                <option value="">Select a company…</option>
                {companiesData.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div style={s.formRow}>
              <Field
                id="project-name" label="Project name" placeholder="Pilot Q3 2026"
                value={projectForm.name} onChange={v => setProjectForm(f => ({ ...f, name: v }))}
                focused={projectFocused.name}
                onFocus={() => setProjectFocused({ name: true })}
                onBlur={() => setProjectFocused({})}
              />
            </div>
            <div style={s.formActions}>
              <button
                type="submit" className="btn-red-dark"
                disabled={!projectForm.name.trim() || !projectForm.company_id || projectSubmitting}
                style={{ ...s.submitBtn, ...(!projectForm.name.trim() || !projectForm.company_id || projectSubmitting ? s.submitBtnDisabled : {}) }}
              >
                {projectSubmitting ? 'creating…' : 'Create project'}
              </button>
              {projectMsg && (
                <span style={{ ...s.formMsg, ...(projectMsg.ok ? s.formMsgOk : s.formMsgErr) }}>
                  {projectMsg.ok ? '✓ ' : ''}{projectMsg.text}
                </span>
              )}
            </div>
          </form>
        </div>

      </div>
    </div>
  )
}
