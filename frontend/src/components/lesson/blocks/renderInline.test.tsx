import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderInline } from './renderInline'

function html(text: string) {
  return render(<p>{renderInline(text)}</p>).container
}

describe('renderInline links', () => {
  it('renders a safe link as an anchor that opens in a new tab', () => {
    const a = html('[delaware](https://delaware.pro)').querySelector('a')
    expect(a?.getAttribute('href')).toBe('https://delaware.pro')
    expect(a?.getAttribute('target')).toBe('_blank')
    expect(a?.getAttribute('rel')).toBe('noopener noreferrer')
    expect(a?.textContent).toBe('delaware')
  })

  it('keeps mailto and relative links', () => {
    const c = html('[mail](mailto:hi@delaware.pro) and [learning](/learning)')
    expect([...c.querySelectorAll('a')].map(a => a.getAttribute('href'))).toEqual([
      'mailto:hi@delaware.pro',
      '/learning',
    ])
  })

  it.each([
    'javascript:alert',
    'JaVaScRiPt:alert',
    ' javascript:alert',
    'java\tscript:alert',
    'data:text/html,hi',
  ])('renders %j as plain label text with no anchor', (target) => {
    const c = html(`before [do not click](${target}) after`)
    expect(c.querySelector('a')).toBeNull()
    expect(c.textContent).toBe('before do not click after')
  })

  it('still renders bold and italic around a blocked link', () => {
    const c = html('**b** *i* [x](javascript:alert)')
    expect(c.querySelector('strong')?.textContent).toBe('b')
    expect(c.querySelector('em')?.textContent).toBe('i')
    expect(c.querySelector('a')).toBeNull()
  })
})
