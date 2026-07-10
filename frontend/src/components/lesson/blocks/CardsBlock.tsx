import type { Card, CardGroupBlock } from '../../../types/contentBlocks'

// Brand red/teal/purple + the Practitioner level rose (lib/levels.ts) so a
// four-card group gets four distinct accents.
const BORDER_COLORS = ['#C42828', '#72C4BF', '#AB9BCB', '#EE7684']

// Real content_blocks JSON contains an older card shape with what/useCase/tools
// instead of body; the renderer supports both, exactly like the old app.
type LegacyCard = Card & { what?: string; useCase?: string; tools?: string }

export default function CardsBlock({ block }: { block: CardGroupBlock }) {
  const cards: LegacyCard[] = block.cards ?? []
  if (!cards.length) return null

  return (
    <div style={{
      // One row per group: grid stretch keeps every card the same height.
      display: 'grid',
      gridTemplateColumns: `repeat(${cards.length}, minmax(0, 1fr))`,
      gap: 16,
      margin: '0 0 24px',
    }}>
      {cards.map((card, i) => (
        <div key={card.id ?? i} style={{
          background: '#fff',
          border: '1px solid #E2E2E2',
          borderLeft: `4px solid ${BORDER_COLORS[i % BORDER_COLORS.length]}`,
          borderRadius: 12,
          boxShadow: '0 1px 4px rgba(0,0,0,.05)',
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
