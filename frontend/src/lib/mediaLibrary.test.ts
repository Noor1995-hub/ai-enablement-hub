import { describe, expect, it } from 'vitest'
import { filterMedia, formatBytes, mediaSummary, type MediaFile } from './mediaLibrary'

const f = (path: string, kind: 'image' | 'video', size: number, used: boolean): MediaFile => ({
  path, kind, size_bytes: size, uploaded_at: '2026-10-06T10:00:00Z', preview_url: null,
  used_in: used ? [{ lesson_id: 'l', lesson_title: 'L', module_title: 'M' }] : [], proposals: 0,
})
const FILES = [f('images/a.png', 'image', 1_048_576, true), f('videos/b.mp4', 'video', 3 * 1_048_576, false)]

describe('mediaLibrary', () => {
  it('summarises totals and the unused share', () => {
    expect(mediaSummary(FILES)).toBe('2 files · 4 MB · 1 unused (3 MB)')
  })
  it('filters by usage and kind', () => {
    expect(filterMedia(FILES, { usage: 'unused', kind: 'all' }).map(x => x.path)).toEqual(['videos/b.mp4'])
    expect(filterMedia(FILES, { usage: 'all', kind: 'image' }).map(x => x.path)).toEqual(['images/a.png'])
  })
  it('formats bytes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2 KB')
    expect(formatBytes(1_572_864)).toBe('1.5 MB')
  })
})
