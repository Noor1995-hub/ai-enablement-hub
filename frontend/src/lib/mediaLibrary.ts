import type { components } from '../api/schema'

export type MediaFile = components['schemas']['MediaFileOut']
export interface MediaFilter { usage: 'all' | 'unused'; kind: 'all' | 'image' | 'video' }

export const isUnused = (file: MediaFile) => file.used_in.length === 0 && file.proposals === 0

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${Math.round(bytes / 1024)} KB`
  const mb = bytes / 1_048_576
  return `${Number.isInteger(mb) ? mb : mb.toFixed(1)} MB`
}

export function mediaSummary(files: MediaFile[]): string {
  const unused = files.filter(isUnused)
  const total = files.reduce((s, f) => s + f.size_bytes, 0)
  const unusedTotal = unused.reduce((s, f) => s + f.size_bytes, 0)
  return `${files.length} file${files.length === 1 ? '' : 's'} · ${formatBytes(total)} · ${unused.length} unused (${formatBytes(unusedTotal)})`
}

export function filterMedia(files: MediaFile[], filter: MediaFilter): MediaFile[] {
  return files.filter(f => (filter.usage === 'all' || isUnused(f)) && (filter.kind === 'all' || f.kind === filter.kind))
}
