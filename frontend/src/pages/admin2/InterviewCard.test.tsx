import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import InterviewCard from './InterviewCard'

const mutate = vi.hoisted(() => vi.fn())
vi.mock('./api', () => ({
  useInterview: () => ({
    isLoading: false,
    error: null,
    data: { status: 'in_progress', tier: null, internal: null, shared: null, transcript: [] },
  }),
  useResetInterview: () => ({ mutate, isPending: false, isError: false, error: null }),
}))

describe('InterviewCard reset confirmation', () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>
  beforeEach(() => {
    mutate.mockReset()
    confirmSpy = vi.spyOn(window, 'confirm')
  })
  afterEach(() => {
    expect(confirmSpy).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('does not reset on the first click', () => {
    render(<InterviewCard userId="u1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset interview' }))
    expect(mutate).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Yes, delete this interview' })).toBeInTheDocument()
  })

  it('resets once confirmed', () => {
    render(<InterviewCard userId="u1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset interview' }))
    fireEvent.click(screen.getByRole('button', { name: 'Yes, delete this interview' }))
    expect(mutate).toHaveBeenCalledExactlyOnceWith('u1')
  })

  it('does not reset when cancelled', () => {
    render(<InterviewCard userId="u1" />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset interview' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(mutate).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Reset interview' })).toBeInTheDocument()
  })
})
