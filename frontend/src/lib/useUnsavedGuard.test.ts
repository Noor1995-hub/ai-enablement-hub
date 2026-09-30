import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useUnsavedGuard } from './useUnsavedGuard'

/** Dispatches a cancelable beforeunload the way the browser does and reports
 * whether anything asked it to keep the page. */
function fireBeforeUnload(): Event {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event
}

describe('useUnsavedGuard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not register a beforeunload handler while clean', () => {
    const add = vi.spyOn(window, 'addEventListener')
    renderHook(() => useUnsavedGuard(false))
    expect(add).not.toHaveBeenCalledWith('beforeunload', expect.any(Function))
    expect(fireBeforeUnload().defaultPrevented).toBe(false)
  })

  it('blocks the unload while dirty', () => {
    renderHook(() => useUnsavedGuard(true))
    expect(fireBeforeUnload().defaultPrevented).toBe(true)
  })

  it('calls preventDefault and sets returnValue to the empty string (older browsers need both)', () => {
    const add = vi.spyOn(window, 'addEventListener')
    renderHook(() => useUnsavedGuard(true))
    const call = add.mock.calls.find(([type]) => type === 'beforeunload')
    expect(call).toBeDefined()
    // A plain object rather than a jsdom Event: jsdom's Event.returnValue is
    // the legacy boolean accessor, which would coerce '' to false.
    const fake = { preventDefault: vi.fn(), returnValue: 'untouched' }
    ;(call![1] as (e: unknown) => void)(fake)
    expect(fake.preventDefault).toHaveBeenCalledTimes(1)
    expect(fake.returnValue).toBe('')
  })

  it('unregisters when dirty flips back to false', () => {
    const remove = vi.spyOn(window, 'removeEventListener')
    const { rerender } = renderHook(({ dirty }) => useUnsavedGuard(dirty), { initialProps: { dirty: true } })
    expect(fireBeforeUnload().defaultPrevented).toBe(true)

    rerender({ dirty: false })
    expect(remove).toHaveBeenCalledWith('beforeunload', expect.any(Function))
    expect(fireBeforeUnload().defaultPrevented).toBe(false)
  })

  it('unregisters on unmount', () => {
    const { unmount } = renderHook(() => useUnsavedGuard(true))
    expect(fireBeforeUnload().defaultPrevented).toBe(true)
    unmount()
    expect(fireBeforeUnload().defaultPrevented).toBe(false)
  })
})
