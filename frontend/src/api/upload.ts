// Media upload helper for the lesson editors. XHR-based rather than fetch: only
// XMLHttpRequest reports upload progress (matters for 300 MB videos). Mirrors
// the auth flow of api/client.ts — attach the Bearer access token, and on a 401
// await the shared single-flight refresh and retry the upload exactly once.

import { errorMessage, refreshAccessToken } from './client'
import { getAccessToken } from './tokens'

// Hand-typed to match backend MediaUploadOut (schemas/admin_media.py); gen:api
// is skipped here because it needs a locally running backend + the shared DB.
export interface UploadedMedia {
  blob_path: string
  url: string           // freshly-stamped SAS for instant preview (not persisted)
  content_type: string
  size_bytes: number
}

// Carries the HTTP status so the editors can show a friendly, media-kind-aware
// message for the two expected rejections: 413 (too large) and 415 (unsupported
// type). `message` is the backend's detail as a fallback.
export class UploadError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'UploadError'
    this.status = status
  }
}

const ENDPOINT = '/api/admin/media'

function defaultMessage(status: number): string {
  if (status === 413) return 'That file is too large.'
  if (status === 415) return "That file type isn't supported."
  if (status === 401) return 'Your session has expired. Please sign in again.'
  return 'Upload failed. Please try again.'
}

function send(
  file: File,
  onProgress: ((pct: number) => void) | undefined,
  token: string | null,
): Promise<{ ok: true; media: UploadedMedia } | { ok: false; status: number; body: unknown }> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', ENDPOINT)
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      })
    }

    xhr.addEventListener('load', () => {
      let body: unknown = null
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        body = null
      }
      if (xhr.status === 201 && body && typeof body === 'object') {
        resolve({ ok: true, media: body as UploadedMedia })
      } else {
        resolve({ ok: false, status: xhr.status, body })
      }
    })
    xhr.addEventListener('error', () => reject(new UploadError(0, 'Network error during upload.')))
    xhr.addEventListener('abort', () => reject(new UploadError(0, 'Upload cancelled.')))

    xhr.send(form)
  })
}

export async function uploadMedia(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadedMedia> {
  let result = await send(file, onProgress, getAccessToken())

  // 401 → refresh once via the shared single-flight, then retry with the new token.
  if (!result.ok && result.status === 401) {
    const access = await refreshAccessToken()
    if (!access) throw new UploadError(401, defaultMessage(401))
    result = await send(file, onProgress, access)
  }

  if (result.ok) return result.media
  throw new UploadError(result.status, errorMessage(result.body, defaultMessage(result.status)))
}
