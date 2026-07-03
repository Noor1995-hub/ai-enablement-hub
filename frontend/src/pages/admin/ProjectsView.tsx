import type { CompanyWithProjects, ProjectOut } from '../../types/domain'
import { s } from './adminStyles'

interface ProjectsViewProps {
  companiesData: CompanyWithProjects[]
  loadingCompanies: boolean
  companiesError: string | null
  onOpenProject: (project: ProjectOut, companyName: string) => void
}

export default function ProjectsView({ companiesData, loadingCompanies, companiesError, onOpenProject }: ProjectsViewProps) {
  if (loadingCompanies) return <p style={{ fontSize: 14, color: '#B6B6B6', fontWeight: 300 }}>Loading…</p>
  if (companiesError)   return <p style={{ fontSize: 14, color: '#C42828' }}>{companiesError}</p>
  if (companiesData.length === 0) return <p style={{ fontSize: 14, color: '#B6B6B6', fontWeight: 300 }}>No companies yet. Go to Setup to create one.</p>

  return (
    <div>
      <h1 style={s.pageTitle}>Projects</h1>
      <p style={s.pageSubtitle}>Select a project to manage its participants and access settings.</p>
      {companiesData.map(company => (
        <div key={company.id} style={s.companyBlock}>
          <p style={s.companyLabel}>{company.name}</p>
          {company.projects.length === 0 ? (
            <p style={{ fontSize: 13, color: '#B6B6B6', fontWeight: 300 }}>No projects yet.</p>
          ) : (
            <div style={s.projectGrid}>
              {company.projects.map(project => (
                <div
                  key={project.id}
                  className="project-card"
                  style={s.projectCard}
                  onClick={() => onOpenProject(project, company.name)}
                >
                  <p style={s.projectCardName}>{project.name}</p>
                  <p style={s.projectCardMeta}>{company.name}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
