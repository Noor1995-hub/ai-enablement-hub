import type { ReactNode } from 'react'
import { safeHref } from '../../../lib/safeHref'

// Converts **bold**, *italic*, [text](url) markdown inline syntax into React elements.
export function renderInline(text: string): ReactNode {
  if (!text) return null
  const parts = text.split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^)\n]+\))/g)
  return parts.map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i} style={{ fontWeight: 700 }}>{part.slice(2, -2)}</strong>
    if (/^\*[^*]+\*$/.test(part))     return <em key={i}>{part.slice(1, -1)}</em>
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) {
      const href = safeHref(link[2])
      // Blocked scheme: show the label as plain text rather than dropping it, so
      // the sentence still reads correctly and nothing silently disappears.
      if (!href) return <span key={i}>{link[1]}</span>
      return <a key={i} href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#C42828' }}>{link[1]}</a>
    }
    return part || null
  })
}
