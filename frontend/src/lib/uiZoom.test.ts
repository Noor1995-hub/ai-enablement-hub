import { afterEach, describe, expect, it, vi } from 'vitest'
import { getRectZoomFactor } from './uiZoom'

function measureProbeAs(width: number) {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width,
  } as DOMRect)
}

describe('getRectZoomFactor', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('is 1 when rects are not scaled', () => {
    measureProbeAs(1000)
    expect(getRectZoomFactor()).toBe(1)
  })

  it('is the measured ratio when CSS zoom scales rects (Chrome/Edge/Firefox at zoom 1.25)', () => {
    measureProbeAs(1250)
    expect(getRectZoomFactor()).toBe(1.25)
  })

  it('is 1 when the probe measures 0 (no layout, e.g. jsdom)', () => {
    measureProbeAs(0)
    expect(getRectZoomFactor()).toBe(1)
  })

  it('removes its probe element again', () => {
    measureProbeAs(1250)
    const before = document.body.childElementCount
    getRectZoomFactor()
    expect(document.body.childElementCount).toBe(before)
  })
})
