import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import LessonView from '../components/lesson/LessonView'
import type { ContentBlock } from '../types/contentBlocks'
import { BLOCK_FACTORIES, BLOCK_LABELS, BLOCK_TYPES } from './contentBlocks'

// The renderer and editor maps are exhaustive at compile time (mapped types over
// ContentBlock['type']). What the compiler cannot see: that the runtime registries agree with
// each other, that each factory builds the type it is filed under, and that a freshly created
// block of every type actually renders.
const TYPES = Object.values(BLOCK_TYPES).sort()

// A freshly created block renders nothing when its only content is empty text; give those some.
const FILL: Partial<Record<ContentBlock['type'], Partial<ContentBlock>>> = {
  paragraph: { text: 'Some text' },
}

describe('content-block registration', () => {
  it('BLOCK_TYPES, BLOCK_LABELS and BLOCK_FACTORIES cover the same block types', () => {
    expect(Object.keys(BLOCK_LABELS).sort()).toEqual(TYPES)
    expect(Object.keys(BLOCK_FACTORIES).sort()).toEqual(TYPES)
  })

  it.each(TYPES)('the %s factory builds a %s block with its own id', type => {
    const make = BLOCK_FACTORIES[type as ContentBlock['type']]
    const a = make()
    const b = make()
    expect(a.type).toBe(type)
    expect(a.id).toBeTruthy()
    expect(a.id).not.toBe(b.id)
  })

  it.each(TYPES)('a new %s block renders in LessonView', type => {
    const key = type as ContentBlock['type']
    const block = { ...BLOCK_FACTORIES[key](), ...FILL[key] } as ContentBlock
    const { container } = render(<LessonView blocks={[block]} />)
    // LessonView wraps the blocks in one <div>; a type with no renderer yields an empty wrapper.
    expect(container.firstElementChild?.childElementCount).toBeGreaterThan(0)
    // Each block sits in its own error boundary, so a renderer that throws on its factory
    // default would still fill the wrapper, with the fallback notice. Rule that out.
    expect(screen.queryByText("This part of the lesson couldn't be displayed.")).not.toBeInTheDocument()
  })
})
