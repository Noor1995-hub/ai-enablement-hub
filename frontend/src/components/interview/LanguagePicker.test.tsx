import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import LanguagePicker from './LanguagePicker'
import type { InterviewLanguage } from '../../lib/interviewStrings'

/** The picker in a page that keeps its choice, as the welcome screen does. */
function Controlled({ initial = 'en' as InterviewLanguage }) {
  const [value, setValue] = useState<InterviewLanguage>(initial)
  return <LanguagePicker value={value} onChange={setValue} />
}

describe('LanguagePicker', () => {
  it('is a labelled radio group offering English and Nederlands, each named in its own language', () => {
    render(<LanguagePicker value="en" onChange={() => {}} label="Interview language" />)
    expect(screen.getByRole('radiogroup', { name: 'Interview language' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'English' }).getAttribute('lang')).toBe('en')
    expect(screen.getByRole('radio', { name: 'Nederlands' }).getAttribute('lang')).toBe('nl')
  })

  it('marks the current choice as checked', () => {
    render(<LanguagePicker value="nl" onChange={() => {}} />)
    expect(screen.getByRole('radio', { name: 'Nederlands' }).getAttribute('aria-checked')).toBe('true')
    expect(screen.getByRole('radio', { name: 'English' }).getAttribute('aria-checked')).toBe('false')
  })

  it('reports the new choice on click', () => {
    const onChange = vi.fn()
    render(<LanguagePicker value="en" onChange={onChange} />)
    fireEvent.click(screen.getByRole('radio', { name: 'Nederlands' }))
    expect(onChange).toHaveBeenCalledWith('nl')
  })

  it('has one tab stop: the chosen option', () => {
    render(<LanguagePicker value="nl" onChange={() => {}} />)
    expect(screen.getByRole('radio', { name: 'Nederlands' }).tabIndex).toBe(0)
    expect(screen.getByRole('radio', { name: 'English' }).tabIndex).toBe(-1)
  })

  it('moves and chooses with the arrow keys, wrapping at the ends', () => {
    render(<Controlled />)
    const english = screen.getByRole('radio', { name: 'English' })
    const dutch = screen.getByRole('radio', { name: 'Nederlands' })

    english.focus()
    fireEvent.keyDown(english, { key: 'ArrowRight' })
    expect(document.activeElement).toBe(dutch)
    expect(dutch.getAttribute('aria-checked')).toBe('true')
    expect(dutch.tabIndex).toBe(0)
    expect(english.tabIndex).toBe(-1)

    fireEvent.keyDown(dutch, { key: 'ArrowDown' })
    expect(document.activeElement).toBe(english)
    expect(english.getAttribute('aria-checked')).toBe('true')

    fireEvent.keyDown(english, { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(dutch)
    fireEvent.keyDown(dutch, { key: 'ArrowUp' })
    expect(document.activeElement).toBe(english)
  })

  it('ignores other keys', () => {
    const onChange = vi.fn()
    render(<LanguagePicker value="en" onChange={onChange} />)
    fireEvent.keyDown(screen.getByRole('radio', { name: 'English' }), { key: 'a' })
    expect(onChange).not.toHaveBeenCalled()
  })
})
