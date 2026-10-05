import { describe, expect, it } from 'vitest'
import { INTERVIEW_STRINGS, PLAYBOOK_STRINGS, formatUseCaseCount } from './interviewStrings'

const tables = { interview: INTERVIEW_STRINGS, playbook: PLAYBOOK_STRINGS }

function values(table: Record<string, unknown>): string[] {
  return Object.values(table).flatMap(v => (typeof v === 'string' ? [v] : values(v as Record<string, unknown>)))
}

describe.each(Object.entries(tables))('%s strings', (_name, table) => {
  it('has the same keys in English and Dutch', () => {
    expect(Object.keys(table.nl).sort()).toEqual(Object.keys(table.en).sort())
  })

  it('has no empty text in either language', () => {
    for (const lang of ['en', 'nl'] as const) {
      for (const text of values(table[lang])) expect(text.trim()).not.toBe('')
    }
  })

  it('follows the house style: no em dash, en dash or ellipsis character', () => {
    for (const lang of ['en', 'nl'] as const) {
      for (const text of values(table[lang])) expect(text).not.toMatch(/[—–…]/)
    }
  })

  it('addresses the learner with the formal "u" in Dutch, never "je" or "jij"', () => {
    for (const text of values(table.nl)) expect(text).not.toMatch(/\b(je|jij|jouw)\b/i)
  })
})

describe('formatUseCaseCount', () => {
  it('uses the singular for one use case and the number for more, in both languages', () => {
    expect(formatUseCaseCount(1, PLAYBOOK_STRINGS.en)).toBe('One use case, picked for you')
    expect(formatUseCaseCount(4, PLAYBOOK_STRINGS.en)).toBe('4 use cases, ranked for you')
    expect(formatUseCaseCount(1, PLAYBOOK_STRINGS.nl)).toBe('Eén toepassing, voor u gekozen')
    expect(formatUseCaseCount(5, PLAYBOOK_STRINGS.nl)).toBe('5 toepassingen, voor u gerangschikt')
  })
})
