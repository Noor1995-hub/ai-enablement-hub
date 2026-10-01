import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import LanguagePicker from './LanguagePicker'

describe('LanguagePicker', () => {
  it('offers English and Nederlands, each labelled in its own language', () => {
    render(<LanguagePicker value="en" onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'English' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Nederlands' })).toBeTruthy()
  })

  it('marks the current choice as pressed', () => {
    render(<LanguagePicker value="nl" onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Nederlands' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'English' }).getAttribute('aria-pressed')).toBe('false')
  })

  it('reports the new choice', () => {
    const onChange = vi.fn()
    render(<LanguagePicker value="en" onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nederlands' }))
    expect(onChange).toHaveBeenCalledWith('nl')
  })
})
