// Canonical maturity-level framework, in progression order — the ONE place
// level codes, display names, taglines and colors live (Assessment intro,
// admin badges and the learning path all import from here).
//
// The scoring engine (backend/src/services/scoring.py) only ever assigns the
// first three codes; 'multiplier' is aspirational — render it, never gate real
// functionality on it.

export interface LevelDef {
  code: 'explore' | 'practitioner' | 'integrator' | 'multiplier'
  name: string
  tagline: string
  sub: string
  color: string
}

export const LEVELS: readonly LevelDef[] = [
  { code: 'explore',      name: 'Explorer',     tagline: 'AI basics',           sub: 'Open the toolbox',             color: '#EF463C' },
  { code: 'practitioner', name: 'Practitioner', tagline: 'AI with context',     sub: 'Brief it. Review it. Own it.', color: '#EE7684' },
  { code: 'integrator',   name: 'Integrator',   tagline: 'AI in your workflow', sub: 'Build once, reuse daily',      color: '#AB9BCB' },
  { code: 'multiplier',   name: 'Multiplier',   tagline: 'Close the loop',      sub: 'Share, measure, multiply',     color: '#72C4BF' },
]

/** Levels the scoring engine can actually produce (subset of LEVELS codes). */
export type AssignableLevel = 'explore' | 'practitioner' | 'integrator'

export function levelByCode(code: string | null | undefined): LevelDef | undefined {
  return LEVELS.find(l => l.code === code)
}

/** The four level colors as one left-to-right gradient, a stop at each segment centre. */
export const LEVEL_GRADIENT =
  `linear-gradient(to right, ${LEVELS.map((l, i) => `${l.color} ${12.5 + i * 25}%`).join(', ')})`
