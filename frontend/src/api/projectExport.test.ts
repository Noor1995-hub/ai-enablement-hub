import { describe, expect, it, vi } from 'vitest'
import { fetchProjectExport, filenameFrom } from './projectExport'

// Same reasoning as pages/admin2/api.test.tsx: openapi-fetch captures fetch and
// Request when `client` is created, so install swappable ones before the import.
const net = vi.hoisted(() => {
  const holder = { handler: (async () => new Response(null, { status: 500 })) as (req: Request) => Promise<Response> }
  globalThis.fetch = ((req: Request) => holder.handler(req)) as typeof fetch
  const NativeRequest = globalThis.Request
  globalThis.Request = class extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      super(typeof input === 'string' && input.startsWith('/') ? `http://localhost${input}` : input, init)
    }
  }
  return holder
})

describe('fetchProjectExport', () => {
  it('repeats the sections parameter and returns the file with its server-given name', async () => {
    let seen: URL | null = null
    net.handler = async req => {
      seen = new URL(req.url)
      return new Response('xlsx-bytes', {
        status: 200,
        headers: {
          'content-type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'content-disposition': 'attachment; filename="acme-export-2026-10-02.xlsx"',
        },
      })
    }

    const file = await fetchProjectExport('p-1', ['people', 'interview'])

    expect(seen!.pathname).toBe('/api/admin/projects/p-1/export')
    expect(seen!.searchParams.getAll('sections')).toEqual(['people', 'interview'])
    expect(file.filename).toBe('acme-export-2026-10-02.xlsx')
    expect(await file.blob.text()).toBe('xlsx-bytes')
  })

  it('throws the server message on an error', async () => {
    net.handler = async () =>
      new Response(JSON.stringify({ error: { code: 'not_found', message: 'Project not found' } }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      })

    await expect(fetchProjectExport('p-1', ['people'])).rejects.toThrow('Project not found')
  })
})

describe('filenameFrom', () => {
  it('falls back when the header is missing or has no filename', () => {
    expect(filenameFrom(null, 'f.xlsx')).toBe('f.xlsx')
    expect(filenameFrom('attachment', 'f.xlsx')).toBe('f.xlsx')
  })
})
