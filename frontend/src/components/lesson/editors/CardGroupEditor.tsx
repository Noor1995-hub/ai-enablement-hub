import type { Card, CardGroupBlock } from '../../../types/contentBlocks'

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)',
  fontWeight: 600,
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#8A8A8A',
  marginBottom: 4,
  display: 'block',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  border: '1px solid #E2E2E2',
  borderRadius: 6,
  fontFamily: 'var(--dlw-font-body)',
  fontSize: 13,
  color: '#101820',
  outline: 'none',
  boxSizing: 'border-box',
}

// Real JSONB carries an older "structured" card shape (what/useCase/tools
// instead of body) — the editor round-trips both, like CardsBlock renders both.
type LegacyCard = Card & { what?: string; useCase?: string; tools?: string }

function isStructured(card: LegacyCard): boolean {
  return 'what' in card
}

interface CardGroupEditorProps {
  block: CardGroupBlock
  onChange: (b: CardGroupBlock) => void
}

export default function CardGroupEditor({ block, onChange }: CardGroupEditorProps) {
  const cards = (block.cards ?? []) as LegacyCard[]

  function updateCard(i: number, updated: LegacyCard) {
    const next = cards.map((c, idx) => idx === i ? updated : c)
    onChange({ ...block, cards: next })
  }

  function removeCard(i: number) {
    onChange({ ...block, cards: cards.filter((_, idx) => idx !== i) })
  }

  function addCard() {
    onChange({ ...block, cards: [...cards, { id: crypto.randomUUID(), title: '', body: '' }] })
  }

  function toggleMode(i: number) {
    const card = cards[i]
    // The old editor dropped the id when switching modes; keep it so React keys
    // stay stable (Card.id is required by the type anyway).
    const next: LegacyCard = isStructured(card)
      ? { id: card.id, title: card.title, body: card.what ?? '' }
      : { id: card.id, title: card.title, body: '', what: card.body ?? '', useCase: '', tools: '' }
    updateCard(i, next)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {cards.map((card, i) => (
        <div key={card.id ?? i} style={{ border: '1px solid #E2E2E2', borderRadius: 10, padding: '14px 16px', background: '#FAFAFA' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 12, color: '#8A8A8A' }}>
              Card {i + 1}
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => toggleMode(i)} style={{
                padding: '3px 10px', borderRadius: 5, border: '1px solid #E2E2E2',
                background: '#fff', fontFamily: 'var(--dlw-font-ui)', fontSize: 11, color: '#8A8A8A', cursor: 'pointer',
              }}>
                {isStructured(card) ? 'Simple' : 'Structured'}
              </button>
              {cards.length > 1 && (
                <button type="button" onClick={() => removeCard(i)} style={{
                  padding: '3px 8px', borderRadius: 5, border: '1px solid #FCA5A5',
                  background: '#FEF2F2', fontFamily: 'var(--dlw-font-ui)', fontSize: 11, color: '#C42828', cursor: 'pointer',
                }}>
                  Remove
                </button>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div>
              <label style={labelStyle}>Title</label>
              <input style={inputStyle} value={card.title} onChange={e => updateCard(i, { ...card, title: e.target.value })} placeholder="Card title…" />
            </div>

            {isStructured(card) ? (
              <>
                <div>
                  <label style={labelStyle}>What</label>
                  <input style={inputStyle} value={card.what ?? ''} onChange={e => updateCard(i, { ...card, what: e.target.value })} placeholder="What it is…" />
                </div>
                <div>
                  <label style={labelStyle}>Use case</label>
                  <input style={inputStyle} value={card.useCase ?? ''} onChange={e => updateCard(i, { ...card, useCase: e.target.value })} placeholder="When to use it…" />
                </div>
                <div>
                  <label style={labelStyle}>Tools</label>
                  <input style={inputStyle} value={card.tools ?? ''} onChange={e => updateCard(i, { ...card, tools: e.target.value })} placeholder="Relevant tools…" />
                </div>
              </>
            ) : (
              <div>
                <label style={labelStyle}>Body</label>
                <textarea style={{ ...inputStyle, resize: 'vertical' }} rows={2} value={card.body ?? ''} onChange={e => updateCard(i, { ...card, body: e.target.value })} placeholder="Card description…" />
              </div>
            )}
          </div>
        </div>
      ))}

      <button type="button" onClick={addCard} style={{
        padding: '8px 0', border: '1.5px dashed #E2E2E2', borderRadius: 8,
        background: 'none', color: '#8A8A8A',
        fontFamily: 'var(--dlw-font-body)', fontSize: 13, cursor: 'pointer',
      }}>
        + Add card
      </button>
    </div>
  )
}
