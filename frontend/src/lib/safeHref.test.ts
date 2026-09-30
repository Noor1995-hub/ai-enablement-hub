import { describe, expect, it } from 'vitest'
import { safeHref } from './safeHref'

describe('safeHref', () => {
  it('allows http and https', () => {
    expect(safeHref('http://example.com')).toBe('http://example.com')
    expect(safeHref('https://delaware.pro')).toBe('https://delaware.pro')
  })

  it('allows mailto', () => {
    expect(safeHref('mailto:hello@delaware.pro')).toBe('mailto:hello@delaware.pro')
  })

  it('allows a site-relative path untouched', () => {
    expect(safeHref('/learning')).toBe('/learning')
  })

  it('allows an in-page anchor untouched', () => {
    expect(safeHref('#anchor')).toBe('#anchor')
  })

  it('allows a protocol-relative host (inherits the page scheme)', () => {
    expect(safeHref('//host/path')).toBe('//host/path')
  })

  it('allows a bare host with no scheme (resolves relative, same as a bare href always did)', () => {
    expect(safeHref('example.com')).toBe('example.com')
  })

  it('blocks javascript:', () => {
    expect(safeHref('javascript:alert(1)')).toBeNull()
  })

  it('blocks javascript: regardless of case', () => {
    expect(safeHref('JaVaScRiPt:alert(1)')).toBeNull()
  })

  it('blocks a tab-obfuscated javascript: scheme', () => {
    expect(safeHref('java\tscript:alert(1)')).toBeNull()
  })

  it('blocks a leading-C0-control-obfuscated javascript: scheme', () => {
    expect(safeHref('\x01javascript:alert(1)')).toBeNull()
  })

  it('blocks vbscript:', () => {
    expect(safeHref('vbscript:msgbox(1)')).toBeNull()
  })

  it('blocks data:', () => {
    expect(safeHref('data:text/html,<script>alert(1)</script>')).toBeNull()
  })

  it('rejects empty and whitespace-only input', () => {
    expect(safeHref('')).toBeNull()
    expect(safeHref('   ')).toBeNull()
  })
})
