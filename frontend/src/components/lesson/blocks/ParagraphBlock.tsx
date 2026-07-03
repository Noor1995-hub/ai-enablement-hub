import type { CSSProperties } from 'react'
import type { ParagraphBlock as ParagraphBlockType } from '../../../types/contentBlocks'
import { renderInline } from './renderInline'

const bodyStyle: CSSProperties = {
  fontFamily: 'var(--dlw-font-body)',
  fontWeight: 300,
  fontSize: 16,
  lineHeight: 1.7,
  color: '#3C3C3C',
}

function renderTable(lines: string[], key: number) {
  const dataRows = lines.filter(l => !/^\|[\s|:-]+\|$/.test(l))
  if (dataRows.length === 0) return null

  const parseRow = (l: string) => l.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
  const [header, ...body] = dataRows

  return (
    <table key={key} style={{ width: '100%', borderCollapse: 'collapse', margin: '0 0 20px', ...bodyStyle }}>
      <thead>
        <tr>
          {parseRow(header).map((cell, i) => (
            <th key={i} style={{ textAlign: 'left', padding: '10px 14px', borderBottom: '2px solid #E2E2E2', fontWeight: 700, color: '#101820', fontSize: 14 }}>
              {renderInline(cell)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {body.map((row, i) => (
          <tr key={i} style={{ borderBottom: '1px solid #F0EFED' }}>
            {parseRow(row).map((cell, j) => (
              <td key={j} style={{ padding: '10px 14px', color: '#3C3C3C', fontWeight: 300, fontSize: 15 }}>
                {renderInline(cell)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

type SegmentType = 'table' | 'olist' | 'ulist' | 'text'

interface Segment {
  type: SegmentType
  lines: string[]
}

// Split text into typed segments so one block can contain mixed content
// (e.g. a sentence followed by a list, or a table).
function parseSegments(text: string): Segment[] {
  const segments: Segment[] = []
  let current: Segment | null = null

  for (const raw of text.split('\n')) {
    const line = raw.trimEnd()
    const t    = line.trim()

    if (!t) {
      if (current) { segments.push(current); current = null }
      continue
    }

    const type: SegmentType = t.startsWith('|')     ? 'table'
               : /^\d+\.\s/.test(t)   ? 'olist'
               : /^[-*]\s/.test(t)    ? 'ulist'
               :                        'text'

    // `current && …` rather than `current?.…`: tsc 5.6 resolves the loop-carried
    // flow type of `current` to never under the optional-chain form.
    if (current && current.type === type) {
      current.lines.push(t)
    } else {
      if (current) segments.push(current)
      current = { type, lines: [t] }
    }
  }
  if (current) segments.push(current)
  return segments
}

export default function ParagraphBlock({ block }: { block: ParagraphBlockType }) {
  const segments = parseSegments(block.text)

  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === 'table') return renderTable(seg.lines, i)

        if (seg.type === 'olist') return (
          <ol key={i} style={{ ...bodyStyle, margin: '0 0 16px', paddingLeft: 28 }}>
            {seg.lines.map((line, j) => (
              <li key={j} style={{ marginBottom: 6 }}>
                {renderInline(line.replace(/^\d+\.\s*/, ''))}
              </li>
            ))}
          </ol>
        )

        if (seg.type === 'ulist') return (
          <ul key={i} style={{ ...bodyStyle, margin: '0 0 16px', paddingLeft: 28 }}>
            {seg.lines.map((line, j) => (
              <li key={j} style={{ marginBottom: 6 }}>
                {renderInline(line.replace(/^[-*]\s*/, ''))}
              </li>
            ))}
          </ul>
        )

        return (
          <p key={i} style={{ ...bodyStyle, margin: '0 0 16px' }}>
            {renderInline(seg.lines.join('\n'))}
          </p>
        )
      })}
    </>
  )
}
