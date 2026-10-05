// Project data export (#92): GET /api/admin/projects/{project_id}/export returns
// one .xlsx. Goes through the typed client (so the Bearer token and the shared
// 401 refresh apply) with parseAs: 'blob', then hands the file to the browser.

import { client, errorMessage } from './client'
import type { paths } from './schema'

export type ExportSection = NonNullable<
  paths['/api/admin/projects/{project_id}/export']['get']['parameters']['query']
>['sections'][number]

export interface ProjectExportFile {
  blob: Blob
  filename: string
}

/** `attachment; filename="x.xlsx"` → `x.xlsx`; a fallback when the header is absent. */
export function filenameFrom(disposition: string | null, fallback: string): string {
  const match = disposition?.match(/filename="([^"]+)"/)
  return match ? match[1] : fallback
}

export async function fetchProjectExport(projectId: string, sections: ExportSection[]): Promise<ProjectExportFile> {
  const { data, error, response } = await client.GET('/api/admin/projects/{project_id}/export', {
    params: { path: { project_id: projectId }, query: { sections } },
    parseAs: 'blob',
  })
  if (error !== undefined || !data) {
    throw new Error(errorMessage(error, 'The export failed. Please try again.'))
  }
  return { blob: data, filename: filenameFrom(response.headers.get('content-disposition'), 'project-export.xlsx') }
}

/** Save a blob through a temporary object URL and a synthetic link click. */
export function saveFile({ blob, filename }: ProjectExportFile): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Revoke on the next tick: some browsers start the download asynchronously.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
