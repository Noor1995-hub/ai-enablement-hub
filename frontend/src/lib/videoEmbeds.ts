// Normalizes a pasted video URL (or a full `<iframe …>` embed snippet) into a
// canonical embed URL whose origin is on the CSP frame-src allowlist, or null
// when the provider isn't allowed. The allowlist here MIRRORS the backend CSP
// frame-src exactly (backend/src/main.py::_build_csp):
//   youtube-nocookie.com · player.vimeo.com · *.sharepoint.com
// A url this function rejects would be blocked by the browser at render time
// anyway, so rejecting here just lets the editor show a friendly hint first.

const YOUTUBE_HOSTS = new Set([
  'youtube.com',
  'www.youtube.com',
  'm.youtube.com',
  'youtube-nocookie.com',
  'www.youtube-nocookie.com',
  'youtu.be',
])

const VIMEO_HOSTS = new Set(['vimeo.com', 'www.vimeo.com', 'player.vimeo.com'])

// YouTube video ids are 11 chars from a URL-safe alphabet; Vimeo ids are numeric.
const YOUTUBE_ID = /^[A-Za-z0-9_-]{11}$/
const VIMEO_ID = /^\d+$/

// Pull the src out of a pasted `<iframe … src="…" …>` snippet (single or double
// quoted). Returns null when there is no iframe/src to extract.
function extractIframeSrc(snippet: string): string | null {
  const match = snippet.match(/<iframe[^>]*\bsrc\s*=\s*["']([^"']+)["']/i)
  return match ? match[1] : null
}

// Parse into a URL, tolerating a scheme-less paste (e.g. "youtu.be/…") by
// assuming https — the only scheme any allowlisted embed would use.
function toUrl(raw: string): URL | null {
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`
  try {
    return new URL(withScheme)
  } catch {
    return null
  }
}

function segments(url: URL): string[] {
  return url.pathname.split('/').filter(Boolean)
}

export function normalizeEmbedUrl(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) return null

  const raw = trimmed.startsWith('<') ? extractIframeSrc(trimmed) : trimmed
  if (!raw) return null

  const url = toUrl(raw)
  if (!url) return null

  const host = url.hostname.toLowerCase()

  // ── YouTube: watch?v= / youtu.be / shorts / embed (incl. nocookie) ──────────
  if (YOUTUBE_HOSTS.has(host)) {
    const parts = segments(url)
    let id: string | null = null
    if (host === 'youtu.be') {
      id = parts[0] ?? null
    } else if (url.pathname === '/watch') {
      id = url.searchParams.get('v')
    } else if (parts[0] === 'shorts' || parts[0] === 'embed' || parts[0] === 'v') {
      id = parts[1] ?? null
    }
    return id && YOUTUBE_ID.test(id) ? `https://www.youtube-nocookie.com/embed/${id}` : null
  }

  // ── Vimeo: vimeo.com/{id} or player.vimeo.com/video/{id} ────────────────────
  if (VIMEO_HOSTS.has(host)) {
    const parts = segments(url)
    const id = host === 'player.vimeo.com'
      ? (parts[0] === 'video' ? parts[1] ?? null : null)
      : parts[0] ?? null
    return id && VIMEO_ID.test(id) ? `https://player.vimeo.com/video/${id}` : null
  }

  // ── MS Stream / SharePoint: any https *.sharepoint.com …embed.aspx, as-is ───
  if (host === 'sharepoint.com' || host.endsWith('.sharepoint.com')) {
    if (url.protocol === 'https:' && url.pathname.toLowerCase().includes('embed.aspx')) {
      return url.toString()
    }
    return null
  }

  return null
}
