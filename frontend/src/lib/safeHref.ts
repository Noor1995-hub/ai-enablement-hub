// Only these schemes may become a real <a href>. `javascript:` and `data:` are
// the ones that matter: React 18 warns on a javascript: href but still renders
// it, and lesson content is no longer purely admin-authored — the
// content-improvement agent drafts blocks from learner-submitted feedback, so
// an admin approving a proposal is the last gate before a link goes live for
// everyone. Anything not on this list renders as plain text instead.
// Matches the backend allowlist in
// `backend/src/services/content_blocks_validation.py::check_link_schemes`;
// this is defence-in-depth for rows stored before that check existed.
const SAFE_PROTOCOLS = ['http:', 'https:', 'mailto:']

/** Returns the href to use, or null when the target isn't a safe link. */
export function safeHref(raw: string): string | null {
  const url = raw.trim()
  if (!url) return null
  // Site-relative and in-page targets carry no scheme at all, so they can never
  // be javascript:/data: — pass them through untouched.
  if (url.startsWith('/') || url.startsWith('#')) return url
  let parsed: URL
  try {
    // The base makes scheme-less input ("example.com/x") resolve as relative,
    // which is what it already did as a bare href.
    parsed = new URL(url, window.location.origin)
  } catch {
    return null
  }
  return SAFE_PROTOCOLS.includes(parsed.protocol) ? url : null
}
