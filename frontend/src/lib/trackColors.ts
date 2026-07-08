// Track chrome color = a LIGHTENED tint of the track's maturity level color
// (2026-07-08). Every track that requires the same level shares one soft tint
// derived from lib/levels.ts, so the learning path reads as "this lane belongs
// to <level>" at a glance. The tint is pale enough to stay below the vivid
// four-color level scale (badges, rings) — it colors the lane, it doesn't shout.
//
// WHY a frontend resolver (kept from the old id-hash version): TrackNode /
// TrackOut both carry `required_level`, so color is derived, never stored. If we
// later want a per-track override, change ONLY this function to prefer
// track.color — the call sites never change.

import type { TrackNode } from '../types/domain'
import { levelByCode } from './levels'

/** How far each level color is mixed toward white (0 = raw level color, 1 = white). */
const TINT = 0

/** Neutral fallback when a track has no resolvable level (should not happen). */
export const FALLBACK_TRACK_COLOR = '#D8D8D8'

/** Mix a #rrggbb color toward white by `amount` (0..1). Returns #rrggbb. */
function lighten(hex: string, amount: number): string {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim())
  if (!m) return hex
  const mix = (c: number) => Math.round(c + (255 - c) * amount)
  const [r, g, b] = [
    mix(parseInt(m[1]!, 16)),
    mix(parseInt(m[2]!, 16)),
    mix(parseInt(m[3]!, 16)),
  ]
  return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('')
}

/**
 * The lightened level color for a track, keyed on its `required_level`. Tracks
 * at the same level get the same tint by design. Falls back to a neutral grey
 * if the level can't be resolved.
 */
export function resolveTrackColor(track: Pick<TrackNode, 'required_level'>): string {
  const level = levelByCode(track.required_level)
  return level ? lighten(level.color, TINT) : FALLBACK_TRACK_COLOR
}
