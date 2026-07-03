import type { ReactNode } from 'react'

// Converts **bold**, *italic*, [text](url) markdown inline syntax into React elements.
export function renderInline(text: string): ReactNode {
  if (!text) return null
  const parts = text.split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^)\n]+\))/g)
  return parts.map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (/^\*[^*]+\*$/.test(part))     return <em key={i}>{part.slice(1, -1)}</em>
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) return <a key={i} href={link[2]} target="_blank" rel="noopener noreferrer" style={{ color: '#C42828' }}>{link[1]}</a>
    return part || null
  })
}
