import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { PlaybookShared } from '../../types/domain'
import Playbook from './Playbook'

const PLAYBOOK: PlaybookShared = {
  where_you_are_today: 'U werkt elke maand aan het rapport.',
  use_cases: [
    {
      rank: 1,
      start_here: true,
      name: 'Het commentaar laten voorbereiden',
      pain_it_kills: 'Twee dagen kopiëren en plakken.',
      in_practice: 'U plakt de tabel in Copilot.',
      before: 'Twee dagen',
      after: 'Een halve dag',
      impact: 'Anderhalve dag per maand.',
      difficulty: 'Quick Win',
      systems_involved: ['Excel', 'Copilot'],
      assumption_to_check: null,
      cross_functional: false,
    },
  ],
  next_moves: [{ order: 1, move: 'Probeer het op vorige maand', why_now: 'De cijfers zijn vers.', linked_use_case: 1 }],
  reframes: [],
  do_this_today: { action: 'Open het rapport van vorige maand', time_required: '15 minuten', why_this_one: 'Weinig werk.' },
}

describe('Playbook headings (#83)', () => {
  it('are English by default', () => {
    render(<Playbook shared={PLAYBOOK} />)
    expect(screen.getByRole('heading', { name: 'Where you are today' })).toBeTruthy()
    expect(screen.getByText('Quick win')).toBeTruthy()
  })

  it('follow the interview language', () => {
    render(<Playbook shared={PLAYBOOK} language="nl" />)
    expect(screen.getByRole('heading', { name: 'Waar u vandaag staat' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Doe dit vandaag' })).toBeTruthy()
    expect(screen.getByText('Snelle winst')).toBeTruthy()
  })
})
