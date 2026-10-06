import type { components } from '../api/schema'

export type OrgImpact = components['schemas']['OrgImpactResponse']

const n = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`

/** The delete warning (B6): exactly what goes, and who is kept. */
export function impactSentence(kind: 'project' | 'company', name: string, impact: OrgImpact): string {
  const parts: string[] = []
  if (kind === 'company') parts.push(`its ${n(impact.projects, 'project')}`)
  if (impact.users_deleted > 0) {
    const staff = impact.other_project_admins_deleted > 0
      ? `, including ${n(impact.other_project_admins_deleted, 'admin')} of another project`
      : ''
    parts.push(`its ${n(impact.users_deleted, 'user')} (${impact.users_with_progress} with progress) with their assessments and interviews${staff}`)
  }
  if (kind === 'project') parts.push('its settings and email templates')
  if (impact.project_admin_grants > 0) parts.push(n(impact.project_admin_grants, 'project-admin grant'))
  const list = parts.length <= 1 ? parts.join('') : `${parts.slice(0, -1).join(', ')}, and ${parts[parts.length - 1]}`
  let sentence = `Deletes ${name}${list ? (parts.length === 1 ? ` and ${list}` : `, ${list}`) : ''}.`
  if (impact.users_deleted === 0) sentence += ' No users are affected.'
  if (impact.power_admins_kept > 0) {
    sentence += ` ${n(impact.power_admins_kept, 'power admin')} in it ${impact.power_admins_kept === 1 ? 'keeps their account' : 'keep their accounts'}.`
  }
  return sentence
}
