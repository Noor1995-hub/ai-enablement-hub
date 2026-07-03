import type { Card, CardGroupBlock } from '../../../types/contentBlocks'

const BORDER_COLORS = ['#C42828', '#3BC9BC', '#7B5EA7']

// Real content_blocks JSON contains an older card shape with what/useCase/tools
// instead of body; the renderer supports both, exactly like the old app.
type LegacyCard = Card & { what?: string; useCase?: string; tools?: string }

export default function CardsBlock({ block }: { block: CardGroupBlock }) {
  const cards: LegacyCard[] = block.cards ?? []
  if (!cards.length) return null

  const cols = cards.length === 2 ? 2 : Math.min(cards.length, 3)

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(${cols}, 1fr)`,
      gap: 16,
      margin: '0 0 24px',
    }}>
      {cards.map((card, i) => (
        <div key={card.id ?? i} style={{
          background: '#fff',
          border: '1px solid #E2E2E2',
          borderLeft: `4px solid ${BORDER_COLORS[i % 3]}`,
          borderRadius: '0 10px 10px 0',
          padding: '18px 20px',
        }}>
          <h3 style={{
            fontFamily: 'var(--dlw-font-body)',
            fontWeight: 700,
            fontSize: 13,
            color: '#101820',
            margin: '0 0 8px',
          }}>
            {card.title}
          </h3>

          {card.what ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {([['What', card.what], ['Use case', card.useCase], ['Tools', card.tools]] as const).map(([label, val]) => val ? (
                <p key={label} style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 13, color: '#3C3C3C', margin: 0, lineHeight: 1.5 }}>
                  <span style={{ fontWeight: 600, color: '#101820' }}>{label}:</span> {val}
                </p>
              ) : null)}
            </div>
          ) : (
            <p style={{
              fontFamily: 'var(--dlw-font-body)',
              fontWeight: 300,
              fontSize: 13,
              color: '#3C3C3C',
              margin: 0,
              lineHeight: 1.6,
            }}>
              {card.body}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}
