import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ContentImprovementPage from './ContentImprovementPage'

const PROPOSAL_ID = '33333333-3333-3333-3333-333333333333'
const LESSON_ID = '11111111-1111-1111-1111-111111111111'

// Production-shaped rows (ProposalSummaryOut / ProposalDetailOut) held in a
// mutable store: an approve flips both to `approved`, as the invalidated
// queries would after a real Accept, and the test re-renders to pick it up.
const store = vi.hoisted(() => ({
  status: 'pending' as 'pending' | 'approved',
  reviewMutate: vi.fn(),
}))

function summary() {
  return {
    id: PROPOSAL_ID,
    lesson_id: LESSON_ID,
    lesson_title: 'Prompting basics',
    module_title: 'Getting started',
    track_id: '44444444-4444-4444-4444-444444444444',
    track_name: 'General I',
    track_level: 'explore',
    summary: 'Clarified the second paragraph.',
    status: store.status,
    source_feedback_count: 1,
    created_at: '2026-09-01T10:00:00Z',
    reviewed_at: null,
  }
}

function detail() {
  return {
    id: PROPOSAL_ID,
    lesson_id: LESSON_ID,
    lesson_title: 'Prompting basics',
    summary: 'Clarified the second paragraph.',
    status: store.status,
    base_blocks: [{ id: 'p1', type: 'paragraph', text: 'Old text' }],
    proposed_blocks: [{ id: 'p1', type: 'paragraph', text: 'Drafted text' }],
    source_feedback: [{ id: 'f1', message: 'Unclear.' }],
    created_at: '2026-09-01T10:00:00Z',
    reviewed_at: null,
    edited_blocks: null,
    critiqued_at: null,
  }
}

const idleMutation = { mutate: vi.fn(), isPending: false, isSuccess: false, isError: false, error: null, variables: undefined, data: undefined }

vi.mock('./api', () => ({
  PROPOSAL_PAGE_SIZE: 20,
  useProposals: () => ({ data: { items: [summary()], total: 1 }, isLoading: false, error: null, refetch: vi.fn() }),
  useProposal: (id: string | null) =>
    id === null
      ? { data: undefined, isLoading: false, error: null, refetch: vi.fn() }
      : { data: detail(), isLoading: false, error: null, refetch: vi.fn() },
  useReviewProposal: () => ({ ...idleMutation, mutate: store.reviewMutate }),
  useGenerateLearnCard: () => idleMutation,
  useRunImprovement: () => idleMutation,
  useCalibrationNotes: () => ({ data: { items: [], total: 0 } }),
}))

/** True when a beforeunload listener asks the browser to keep the page. */
function unloadBlocked(): boolean {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}

function openAndEditDraft() {
  fireEvent.click(screen.getByText('Review changes'))
  fireEvent.click(screen.getByText('Edit the draft'))
  fireEvent.change(screen.getByDisplayValue('Drafted text'), { target: { value: 'My better text' } })
}

describe('ProposalRow unsaved-changes guard', () => {
  beforeEach(() => {
    store.status = 'pending'
    store.reviewMutate.mockReset()
  })

  it('does not guard an expanded draft the admin has not changed', () => {
    render(<ContentImprovementPage />)
    fireEvent.click(screen.getByText('Review changes'))
    fireEvent.click(screen.getByText('Edit the draft'))
    expect(unloadBlocked()).toBe(false)
  })

  it('keeps guarding after "Back to comparison": the edited draft is still what Accept submits', () => {
    render(<ContentImprovementPage />)
    openAndEditDraft()
    expect(unloadBlocked()).toBe(true)

    fireEvent.click(screen.getByText('Back to comparison'))
    expect(screen.getByText('Edit the draft')).toBeInTheDocument()
    expect(unloadBlocked()).toBe(true)
  })

  it('releases the guard once Accept has saved the edited draft', () => {
    store.reviewMutate.mockImplementation(() => { store.status = 'approved' })
    const { rerender } = render(<ContentImprovementPage />)
    openAndEditDraft()
    expect(unloadBlocked()).toBe(true)

    fireEvent.click(screen.getByText('Accept'))
    fireEvent.click(screen.getByText('Yes, accept'))
    expect(store.reviewMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        decision: 'approve',
        editedBlocks: [{ id: 'p1', type: 'paragraph', text: 'My better text' }],
      }),
      expect.anything(),
    )
    // The invalidated queries now report the proposal approved; the row is
    // still on screen (e.g. under the "All" filter), still in edit mode.
    rerender(<ContentImprovementPage />)
    expect(screen.queryByText('Accept')).not.toBeInTheDocument()
    expect(unloadBlocked()).toBe(false)
  })

  it('releases the guard when the row is collapsed (the working copy is dropped)', () => {
    render(<ContentImprovementPage />)
    openAndEditDraft()
    fireEvent.click(screen.getByText('Hide changes'))
    expect(unloadBlocked()).toBe(false)
  })
})
