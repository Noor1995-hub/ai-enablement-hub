// Hand-typed multipart client for POST /api/admin/invites/bulk, mirroring
// api/upload.ts: attach the Bearer token, and on a 401 await the shared
// single-flight refresh and retry once. gen:api is skipped for multipart (same
// reasoning as upload.ts), so the response types are hand-kept in sync with the
// backend BulkInviteReport (schemas/admin_users.py).

import { errorMessage, refreshAccessToken } from './client'
import { getAccessToken } from './tokens'

export type BulkInviteStatus = 'valid' | 'duplicate' | 'invalid' | 'created' | 'email_failed'

export interface BulkInviteRow {
  row_number: number
  first_name: string
  last_name: string
  email: string
  status: BulkInviteStatus
  detail: string | null
}

export interface BulkInviteSummary {
  total_rows: number
  valid: number
  duplicates: number
  invalid: number
  created: number
  email_failed: number
}

export interface BulkInviteReport {
  dry_run: boolean
  project_id: string
  summary: BulkInviteSummary
  rows: BulkInviteRow[]
}

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
