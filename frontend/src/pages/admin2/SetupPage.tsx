import { useState, type FormEvent } from 'react'
import { useCompanies, useCreateCompany, useCreateProject } from './api'
import { Card, ErrorState, Spinner } from './kit'

interface FormMsg {
  ok: boolean
  text: string
}

/** Setup screen (spec §3.6, `/admin/setup`) — ports the old panel's
 * SetupView (frontend/src/pages/admin/SetupView.tsx) two forms onto kit
 * components + the `useCreateCompany`/`useCreateProject` mutations (both
 * invalidate `['admin','companies']`, so the existing-companies list below
 * and the New-project company dropdown pick up a fresh company/project
 * together). The existing-companies list nested under the New-company form
 * is SetupView's actual behavior (name + project count); the prototype
 * mock's separate combined company+project "Existing" card is not ported —
 * it has no counterpart in the real component this task lifts from. */
export default function SetupPage() {
  const companiesQuery = useCompanies()
  const createCompany = useCreateCompany()
  const createProject = useCreateProject()

  const [companyName, setCompanyName] = useState('')
  const [companyMsg, setCompanyMsg] = useState<FormMsg | null>(null)

  const [projectName, setProjectName] = useState('')
  const [projectCompanyId, setProjectCompanyId] = useState('')
  const [projectMsg, setProjectMsg] = useState<FormMsg | null>(null)

  async function handleCreateCompany() {
    const name = companyName.trim()
    if (!name || createCompany.isPending) return
    setCompanyMsg(null)
    try {
      const company = await createCompany.mutateAsync(name)
      setCompanyMsg({ ok: true, text: `Company "${company.name}" created.` })
      setCompanyName('')
    } catch (e) {
      setCompanyMsg({ ok: false, text: e instanceof Error ? e.message : 'Something went wrong.' })
    }
  }

  async function handleCreateProject() {
    const name = projectName.trim()
    if (!name || !projectCompanyId || createProject.isPending) return
    setProjectMsg(null)
    try {
      const project = await createProject.mutateAsync({ name, companyId: projectCompanyId })
      setProjectMsg({ ok: true, text: `Project "${project.name}" created.` })
      setProjectName('')
      setProjectCompanyId('')
    } catch (e) {
      setProjectMsg({ ok: false, text: e instanceof Error ? e.message : 'Something went wrong.' })
    }
  }

  if (companiesQuery.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (companiesQuery.isError || !companiesQuery.data) {
    return (
      <ErrorState
        message={companiesQuery.error?.message ?? 'Failed to load companies.'}
        onRetry={() => void companiesQuery.refetch()}
      />
    )
  }

  const companies = companiesQuery.data

  return (
    <div>
      <h1 className="adm-page-title">Setup</h1>
      <p className="adm-page-sub">Create companies and projects.</p>

      <div className="adm-grid-2">
        <Card title="New company">
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              void handleCreateCompany()
            }}
            noValidate
          >
            <div className="adm-field">
              <label className="adm-field-label" htmlFor="setup-company-name">
                Company name
              </label>
              <input
                id="setup-company-name"
                className="adm-field-input"
                placeholder="Acme NV"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="adm-btn adm-btn-red"
              disabled={!companyName.trim() || createCompany.isPending}
            >
              {createCompany.isPending && <Spinner size="sm" />}
              Create company
            </button>
            {companyMsg && (
              <p className={`adm-form-msg ${companyMsg.ok ? 'adm-form-msg-ok' : 'adm-form-msg-err'}`}>
                {companyMsg.ok ? '✓ ' : ''}
                {companyMsg.text}
              </p>
            )}
          </form>

          {companies.length > 0 && (
            <div className="adm-modal-section">
              <p className="adm-field-label">Existing companies</p>
              {companies.map(company => (
                <div key={company.id} className="adm-setup-list-row">
                  <span>{company.name}</span>
                  <span className="adm-subtext">
                    {company.projects.length} {company.projects.length === 1 ? 'project' : 'projects'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="New project">
          <form
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              void handleCreateProject()
            }}
            noValidate
          >
            <div className="adm-field">
              <label className="adm-field-label" htmlFor="setup-project-company">
                Company
              </label>
              <select
                id="setup-project-company"
                className="adm-field-input"
                value={projectCompanyId}
                onChange={e => setProjectCompanyId(e.target.value)}
              >
                <option value="">Select a company…</option>
                {companies.map(company => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="adm-field">
              <label className="adm-field-label" htmlFor="setup-project-name">
                Project name
              </label>
              <input
                id="setup-project-name"
                className="adm-field-input"
                placeholder="Pilot Q3 2026"
                value={projectName}
                onChange={e => setProjectName(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="adm-btn adm-btn-red"
              disabled={!projectName.trim() || !projectCompanyId || createProject.isPending}
            >
              {createProject.isPending && <Spinner size="sm" />}
              Create project
            </button>
            {projectMsg && (
              <p className={`adm-form-msg ${projectMsg.ok ? 'adm-form-msg-ok' : 'adm-form-msg-err'}`}>
                {projectMsg.ok ? '✓ ' : ''}
                {projectMsg.text}
              </p>
            )}
          </form>
        </Card>
      </div>
    </div>
  )
}
