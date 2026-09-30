// Multipart client for POST /api/admin/invites/bulk, mirroring api/upload.ts:
// attach the Bearer token, and on a 401 await the shared single-flight refresh
// and retry once. gen:api can't type the multipart request, so the response
// types are aliased onto schema.d.ts below.

import { errorMessage, refreshAccessToken } from './client'
import type { components } from './schema'
import { getAccessToken } from './tokens'

// Aliased onto the generated schema (same reasoning as api/upload.ts: the
// multipart request can't be typed by gen:api, the response can).
export type BulkInviteReport = components['schemas']['BulkInviteReport']
export type BulkInviteRow = components['schemas']['BulkInviteRow']
export type BulkInviteSummary = components['schemas']['BulkInviteSummary']
export type BulkInviteStatus = BulkInviteRow['status']

export class BulkInviteError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'BulkInviteError'
    this.status = status
  }
}

const ENDPOINT = '/api/admin/invites/bulk'

function send(file: File, projectId: string, dryRun: boolean, token: string | null): Promise<Response> {
  const form = new FormData()
  form.append('file', file)
  form.append('project_id', projectId)
  form.append('dry_run', String(dryRun))
  return fetch(ENDPOINT, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  })
}

export async function bulkInvite(
  file: File,
  projectId: string,
  dryRun: boolean,
): Promise<BulkInviteReport> {
  let res = await send(file, projectId, dryRun, getAccessToken())
  if (res.status === 401) {
    const access = await refreshAccessToken()
    if (!access) throw new BulkInviteError(401, 'Your session has expired. Please sign in again.')
    res = await send(file, projectId, dryRun, access)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok || !body || typeof body !== 'object') {
    throw new BulkInviteError(res.status, errorMessage(body, 'Bulk invite failed. Please try again.'))
  }
  return body as BulkInviteReport
}
