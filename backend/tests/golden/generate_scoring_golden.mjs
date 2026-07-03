// One-off golden-corpus generator for the scoring port (design-backend.md §5).
//
// Runs the REAL legacy scorer (app/api/_lib/scoring.js) over a deterministic
// corpus and dumps every input/output (or thrown 422) to scoring_golden.json.
// tests/unit/test_scoring.py replays that file against the Python port.
//
// Usage (from backend/):
//   node tests/golden/generate_scoring_golden.mjs [path-to-scoring.js]
//
// The output file is committed; re-run only if the legacy scorer ever changes.

import { pathToFileURL } from 'node:url'
import { writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const scoringPath = resolve(here, process.argv[2] ?? '../../../../app/api/_lib/scoring.js')
const { scoreResponse } = await import(pathToFileURL(scoringPath))

const C_CODES = ['MISSING', 'PARTIAL', 'HAVE', 'ADV_D', 'ADV_E']
const C5_CODES = ['PUBLIC_PASTE', 'APPROVED_PASTE', 'KEPT_OUT', 'UNSURE', 'NO_USE']
const FREQS = ['NEVER', 'MONTHLY', 'WEEKLY', 'DAILY', 'INTENSIVE']
const BREADTHS = ['NONE', 'FEW', 'SEVERAL', 'MOST', 'ALL']

// Sentinel: "leave this key out of the input object entirely" (JSON has no undefined).
const ABSENT = Symbol('absent')

const baseline = {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'HAVE', c4_code: 'HAVE',
  c5_codes: ['KEPT_OUT'], c6_code: 'HAVE', b_freq: 'WEEKLY', b_breadth: 'SEVERAL',
}

function makeInput(overrides) {
  const input = { ...baseline, ...overrides }
  for (const key of Object.keys(input)) if (input[key] === ABSENT) delete input[key]
  return input
}

const cases = []
function addCase(name, overrides) {
  const input = makeInput(overrides)
  try {
    cases.push({ name, input, expected: scoreResponse(input) })
  } catch (err) {
    cases.push({ name, input, error: { status: err.status ?? 500, message: err.message } })
  }
}

// (a) All 31 non-empty subsets of the five C5 codes over a competent baseline.
for (let mask = 1; mask < 32; mask++) {
  const subset = C5_CODES.filter((_, i) => mask & (1 << i))
  addCase(`c5-subset:${subset.join('+')}`, { c5_codes: subset })
}

// (b) Full freq × breadth matrix, plus unknown/null/absent pairs.
for (const freq of FREQS) for (const breadth of BREADTHS)
  addCase(`band:${freq}x${breadth}`, { b_freq: freq, b_breadth: breadth })
for (const [freq, breadth] of [
  ['SOMETIMES', 'FEW'], ['WEEKLY', 'LOTS'], ['SOMETIMES', 'LOTS'],
  [null, 'FEW'], ['WEEKLY', null], [null, null], [ABSENT, 'FEW'], ['WEEKLY', ABSENT],
  [ABSENT, ABSENT],
]) addCase(`band-edge:${String(freq)}x${String(breadth)}`, { b_freq: freq, b_breadth: breadth })

// (c) 500 seeded pseudo-random full-answer combos, including invalid codes and
// missing fields, to lock error behavior and error precedence (c1..c4, c6, c5).
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const rand = mulberry32(20260703)
const pick = arr => arr[Math.floor(rand() * arr.length)]

function randomValidC5() {
  // Any subset drawn from the cascade inputs, including combinations that 422
  // (e.g. NO_USE together with another code) — the cascade itself decides.
  const size = 1 + Math.floor(rand() * 3)
  const subset = []
  for (let i = 0; i < size; i++) {
    const code = pick(C5_CODES)
    if (!subset.includes(code)) subset.push(code)
  }
  return subset
}
const BAD_C = [null, ABSENT, 'BOGUS', 'have', '', 'ADV', 'HAVE ', 'MISSNG']
const BAD_C5 = [null, ABSENT, [], 'KEPT_OUT' /* not an array */, ['BOGUS'], ['NO_USE', 'BOGUS']]
function corruptOneField(input) {
  const field = pick(['c1_code', 'c2_code', 'c3_code', 'c4_code', 'c6_code', 'c5_codes'])
  input[field] = field === 'c5_codes' ? pick(BAD_C5) : pick(BAD_C)
  return field
}
for (let i = 0; i < 500; i++) {
  const overrides = {
    c1_code: pick(C_CODES), c2_code: pick(C_CODES), c3_code: pick(C_CODES),
    c4_code: pick(C_CODES), c6_code: pick(C_CODES), c5_codes: randomValidC5(),
    // Bands never throw, so invalid/missing values here still yield scored cases.
    b_freq: rand() < 0.85 ? pick(FREQS) : pick([null, ABSENT, 'BOGUS']),
    b_breadth: rand() < 0.85 ? pick(BREADTHS) : pick([null, ABSENT, 'BOGUS']),
  }
  // 30%: corrupt exactly one field, locking per-field error text and the
  // evaluation order (c1..c4, then c6, then c5) without drowning scored cases.
  // 5%: corrupt two fields to lock error precedence between them.
  const r = rand()
  let label = 'valid'
  if (r < 0.30) {
    label = `bad-${corruptOneField(overrides)}`
  } else if (r < 0.35) {
    label = `bad-${corruptOneField(overrides)}-${corruptOneField(overrides)}`
  }
  addCase(`random:${i}:${label}`, overrides)
}

// (d) Hand-picked boundary cases.
addCase('exactly-integrator', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'ADV_D', c4_code: 'ADV_E',
  c5_codes: ['KEPT_OUT'], c6_code: 'HAVE',
})
addCase('integrator-minus-have_count', {
  c1_code: 'PARTIAL', c2_code: 'ADV_D', c3_code: 'ADV_D', c4_code: 'ADV_E',
  c5_codes: ['KEPT_OUT'], c6_code: 'HAVE',
})
addCase('integrator-minus-adv_count', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'HAVE', c4_code: 'ADV_D',
  c5_codes: ['KEPT_OUT'], c6_code: 'HAVE',
})
addCase('integrator-minus-c5-gate', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'ADV_D', c4_code: 'ADV_E',
  c5_codes: ['UNSURE'], c6_code: 'HAVE',
})
addCase('integrator-minus-c6-gate', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'ADV_D', c4_code: 'ADV_E',
  c5_codes: ['KEPT_OUT'], c6_code: 'PARTIAL',
})
// THE JS/Python trap: c5_rung null (NO_USE alone) — `null >= 2` is false in JS,
// so an otherwise-integrator answer set lands on practitioner (and no safe-use).
addCase('no_use-null-c5-otherwise-integrator', {
  c1_code: 'ADV_D', c2_code: 'ADV_E', c3_code: 'HAVE', c4_code: 'HAVE',
  c5_codes: ['NO_USE'], c6_code: 'ADV_D',
})
addCase('have_count-2-is-explore', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'PARTIAL', c4_code: 'MISSING',
})
addCase('have_count-3-is-practitioner', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'HAVE', c4_code: 'PARTIAL',
})
addCase('public-paste-alone', { c5_codes: ['PUBLIC_PASTE'] })
addCase('public-paste-mitigated-approved', { c5_codes: ['PUBLIC_PASTE', 'APPROVED_PASTE'] })
addCase('public-paste-mitigated-kept-out', { c5_codes: ['PUBLIC_PASTE', 'KEPT_OUT'] })
addCase('mandatory-both-ordered', {
  c1_code: 'HAVE', c2_code: 'HAVE', c3_code: 'HAVE', c4_code: 'PARTIAL',
  c5_codes: ['UNSURE'], c6_code: 'PARTIAL',
})
addCase('no_use-plus-other-is-422', { c5_codes: ['NO_USE', 'UNSURE'] })
addCase('unknown-band-is-null', { b_freq: 'BOGUS', b_breadth: 'ALL' })
addCase('empty-answers', {
  c1_code: ABSENT, c2_code: ABSENT, c3_code: ABSENT, c4_code: ABSENT,
  c5_codes: ABSENT, c6_code: ABSENT, b_freq: ABSENT, b_breadth: ABSENT,
})
addCase('error-precedence-c6-before-c5', { c6_code: 'BOGUS', c5_codes: [] })
addCase('error-precedence-c1-first', { c1_code: null, c2_code: 'BOGUS', c5_codes: [] })

const out = resolve(here, 'scoring_golden.json')
writeFileSync(out, JSON.stringify(cases, null, 1) + '\n')
const errors = cases.filter(c => c.error).length
console.log(`${cases.length} cases (${cases.length - errors} scored, ${errors} errors) -> ${out}`)
