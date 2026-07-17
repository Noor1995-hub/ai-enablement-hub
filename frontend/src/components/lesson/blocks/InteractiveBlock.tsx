import { useState, type CSSProperties } from 'react'
import type { InteractiveBlock as InteractiveBlockType } from '../../../types/contentBlocks'
import { renderInline } from './renderInline'

interface InteractiveBlockProps {
  block: InteractiveBlockType
}

const card: CSSProperties = {
  background: '#fff',
  border: '1px solid #E2E2E2',
  borderRadius: 12,
  boxShadow: '0 1px 4px rgba(0,0,0,.05)',
  padding: '24px 28px',
  margin: '0 0 24px',
}

const headerStyle: CSSProperties = {
  fontFamily: 'var(--dlw-font-body)',
  fontWeight: 700,
  fontSize: 18,
  color: '#101820',
  margin: '0 0 20px',
}

const MODE_LABELS = {
  sort: 'Sort',
  predict: 'Predict',
  spot_the_flaw: 'Spot the flaw',
} satisfies Record<InteractiveBlockType['mode'], string>

function Header({ mode }: { mode: InteractiveBlockType['mode'] }) {
  return <h2 style={headerStyle}>{MODE_LABELS[mode]}</h2>
}

const promptStyle: CSSProperties = {
  fontFamily: 'var(--dlw-font-body)',
  fontWeight: 600,
  fontSize: 15,
  color: '#101820',
  margin: '0 0 16px',
}

const retryButtonStyle: CSSProperties = {
  padding: '10px 22px',
  borderRadius: 999,
  border: '1.5px solid #E2E2E2',
  background: '#fff',
  color: '#3C3C3C',
  fontFamily: 'var(--dlw-font-body)',
  fontWeight: 600,
  fontSize: 14,
  cursor: 'pointer',
}

const checkButtonStyle: CSSProperties = {
  padding: '11px 18px',
  borderRadius: 8,
  background: '#C42828',
  border: 'none',
  color: '#fff',
  fontFamily: 'var(--dlw-font-body)',
  fontWeight: 800,
  fontSize: 14,
  cursor: 'pointer',
}

function ReasonNote({ good, text }: { good: boolean; text: string }) {
  if (!text) return null
  return (
    <p style={{
      fontFamily: 'var(--dlw-font-body)',
      fontWeight: 300,
      fontSize: 13,
      color: good ? '#1D7A52' : '#991B1B',
      margin: '4px 0 0',
    }}>
      {renderInline(text)}
    </p>
  )
}

function SortMode({ block }: { block: Extract<InteractiveBlockType, { mode: 'sort' }> }) {
  const [assignments, setAssignments] = useState<Record<string, string>>({})
  const [checked, setChecked] = useState(false)

  const allAssigned = block.items.length > 0 && block.items.every(item => assignments[item.id])
  const score = block.items.filter(item => assignments[item.id] === item.bucketId).length

  // Side-by-side pills only read well for 2 buckets. At 3+, stack them in a
  // column beside the item text instead, all sized off this block's own
  // longest label so short-label blocks stay compact and long-sentence
  // blocks (e.g. "Governance for agentic engineering") get the room they need.
  const manyBuckets = block.buckets.length > 2
  const bucketColWidth = Math.max(...block.buckets.map(b => b.label.length)) + 4

  function assign(itemId: string, bucketId: string) {
    if (checked) return
    setAssignments(a => ({ ...a, [itemId]: bucketId }))
  }

  function reset() {
    setAssignments({})
    setChecked(false)
  }

  return (
    <div style={card}>
      <Header mode={block.mode} />
      <p style={promptStyle}>{renderInline(block.prompt)}</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
        {block.items.map(item => {
          const picked = assignments[item.id]
          const correct = checked && picked === item.bucketId
          const wrong = checked && picked && picked !== item.bucketId

          return (
            <div key={item.id} style={{
              padding: '12px 16px', borderRadius: 8,
              border: '1px solid #E2E2E2',
              background: correct ? '#EDFAF4' : wrong ? '#FEF2F2' : '#FAFAFA',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'nowrap' }}>
                <p style={{ fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#101820', margin: 0, fontWeight: 500, flex: '1 1 auto', minWidth: 0 }}>
                  {renderInline(item.text)}
                </p>
                <div role="group" aria-label={`Assign: ${item.text}`} style={{
                  display: 'flex',
                  flexDirection: manyBuckets ? 'column' : 'row',
                  gap: 8, flexShrink: 0,
                  flexWrap: manyBuckets ? 'nowrap' : 'wrap',
                  justifyContent: manyBuckets ? 'flex-start' : 'flex-end',
                  alignItems: manyBuckets ? 'stretch' : undefined,
                }}>
                  {block.buckets.map(bucket => {
                    const selected = picked === bucket.id
                    return (
                      <button
                        key={bucket.id}
                        type="button"
                        aria-pressed={selected}
                        disabled={checked}
                        onClick={() => assign(item.id, bucket.id)}
                        style={{
                          padding: '6px 14px', borderRadius: 999,
                          border: selected ? '1.5px solid #101820' : '1px solid #E2E2E2',
                          background: selected ? '#101820' : '#fff',
                          color: selected ? '#fff' : '#3C3C3C',
                          fontFamily: 'var(--dlw-font-body)', fontSize: 13, fontWeight: 600,
                          cursor: checked ? 'default' : 'pointer',
                          whiteSpace: 'nowrap',
                          width: manyBuckets ? `${bucketColWidth}ch` : undefined,
                          textAlign: manyBuckets ? 'center' : undefined,
                        }}
                      >
                        {bucket.label}
                      </button>
                    )
                  })}
                </div>
              </div>
              {checked && <ReasonNote good={!!correct} text={item.reason} />}
            </div>
          )
        })}
      </div>

      {checked && (
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#101820', margin: '0 0 16px' }}>
          {score} / {block.items.length} correct
        </p>
      )}

      {checked ? (
        <button type="button" onClick={reset} className="btn-ghost" style={retryButtonStyle}>Try again</button>
      ) : (
        <button type="button" onClick={() => setChecked(true)} disabled={!allAssigned} className="lesson-cta" style={{ ...checkButtonStyle, opacity: allAssigned ? 1 : 0.5, cursor: allAssigned ? 'pointer' : 'default' }}>
          Check
        </button>
      )}
    </div>
  )
}

function PredictMode({ block }: { block: Extract<InteractiveBlockType, { mode: 'predict' }> }) {
  const [picked, setPicked] = useState<string | null>(null)

  function reset() {
    setPicked(null)
  }

  return (
    <div style={card}>
      <Header mode={block.mode} />
      <p style={promptStyle}>{renderInline(block.prompt)}</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
        {block.options.map(opt => {
          const isCorrectOpt = opt.id === block.correctOptionId
          const isPicked = picked === opt.id
          let bg = '#fff', border = '1px solid #E2E2E2', color = '#3C3C3C'

          if (picked) {
            if (isCorrectOpt)     { bg = '#EDFAF4'; border = '1.5px solid #1D7A52'; color = '#1D7A52' }
            else if (isPicked)    { bg = '#FEF2F2'; border = '1.5px solid #C42828'; color = '#991B1B' }
            else                  { border = '1px solid #F0EFED'; color = '#B0B0B0' }
          }

          return (
            <div key={opt.id}>
              <button
                type="button"
                disabled={!!picked}
                onClick={() => setPicked(opt.id)}
                style={{
                  width: '100%', textAlign: 'left', padding: '12px 16px',
                  borderRadius: 8, border, background: bg, color,
                  fontFamily: 'var(--dlw-font-body)', fontSize: 14,
                  cursor: picked ? 'default' : 'pointer',
                }}
              >
                {renderInline(opt.label)}
              </button>
              {picked && (isCorrectOpt || isPicked) && (
                <div style={{ padding: '4px 16px 0' }}>
                  <ReasonNote good={isCorrectOpt} text={opt.reason} />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {picked && <button type="button" onClick={reset} className="btn-ghost" style={retryButtonStyle}>Predict again</button>}
    </div>
  )
}

function SpotTheFlawMode({ block }: { block: Extract<InteractiveBlockType, { mode: 'spot_the_flaw' }> }) {
  const [picked, setPicked] = useState<string | null>(null)

  function reset() {
    setPicked(null)
  }

  return (
    <div style={card}>
      <Header mode={block.mode} />
      <p style={promptStyle}>{renderInline(block.prompt)}</p>

      <div style={{
        padding: '14px 18px', borderRadius: 8, marginBottom: 16,
        background: '#FAFAFA', border: '1px solid #E2E2E2',
        fontFamily: 'var(--dlw-font-body)', fontSize: 14, color: '#3C3C3C', lineHeight: 1.6,
        whiteSpace: 'pre-wrap',
      }}>
        {renderInline(block.example)}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
        {block.candidates.map(candidate => {
          const isPicked = picked === candidate.id
          let bg = '#fff', border = '1px solid #E2E2E2', color = '#3C3C3C'

          if (picked) {
            if (candidate.isFlaw)      { bg = '#EDFAF4'; border = '1.5px solid #1D7A52'; color = '#1D7A52' }
            else if (isPicked)         { bg = '#FEF2F2'; border = '1.5px solid #C42828'; color = '#991B1B' }
            else                       { border = '1px solid #F0EFED'; color = '#B0B0B0' }
          }

          return (
            <div key={candidate.id}>
              <button
                type="button"
                disabled={!!picked}
                onClick={() => setPicked(candidate.id)}
                style={{
                  width: '100%', textAlign: 'left', padding: '12px 16px',
                  borderRadius: 8, border, background: bg, color,
                  fontFamily: 'var(--dlw-font-body)', fontSize: 14,
                  cursor: picked ? 'default' : 'pointer',
                }}
              >
                {renderInline(candidate.text)}
              </button>
              {picked && (candidate.isFlaw || isPicked) && (
                <div style={{ padding: '4px 16px 0' }}>
                  <ReasonNote good={candidate.isFlaw} text={candidate.reason} />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {picked && <button type="button" onClick={reset} className="btn-ghost" style={retryButtonStyle}>Try again</button>}
    </div>
  )
}

export default function InteractiveBlock({ block }: InteractiveBlockProps) {
  if (block.mode === 'sort') return <SortMode block={block} />
  if (block.mode === 'predict') return <PredictMode block={block} />
  if (block.mode === 'spot_the_flaw') return <SpotTheFlawMode block={block} />
  return null
}
