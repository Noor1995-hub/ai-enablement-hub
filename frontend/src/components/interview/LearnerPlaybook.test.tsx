import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import LearnerPlaybook from './LearnerPlaybook'
import type { PlaybookShared } from '../../types/domain'

function playbook(overrides: Partial<PlaybookShared> = {}): PlaybookShared {
  return {
    where_you_are_today: 'You plan production for the bakery.\n\n- Monday rebuild takes three hours.\n- Typos creep in.',
    use_cases: [
      { rank: 2, start_here: false, name: 'Spot quantity errors', pain_it_kills: 'Typos', in_practice: 'Paste the table into Copilot in Excel.', before: 'Errors on the floor.', after: 'Errors flagged early.', impact: 'Less waste.', difficulty: 'Worth a Session', systems_involved: ['SAP', 'Excel'], assumption_to_check: 'Check with IT.', cross_functional: false },
      { rank: 1, start_here: true, name: 'Draft the supplier emails', pain_it_kills: 'Five emails a week', in_practice: 'Keep one prompt in Outlook.', before: 'From scratch.', after: 'Drafts in two minutes.', impact: 'An hour back.', difficulty: 'Quick Win', systems_involved: [], assumption_to_check: null, cross_functional: true },
    ],
    next_moves: [
      { order: 2, move: 'Ask IT about the export', why_now: 'Unlocks use case 2.', linked_use_case: 2 },
      { order: 1, move: 'Try the email prompt', why_now: 'Low risk.', linked_use_case: 1 },
      { order: 3, move: 'Talk to sales', why_now: 'They need to join.', linked_use_case: 9 },
    ],
    reframes: [{ their_hesitation: 'It would not understand our recipes', the_concern: 'Domain errors', reframe: 'You stay the expert.', first_proof: 'Run it once.' }],
    do_this_today: { action: 'Paste the supplier list into Copilot.', time_required: '10 minutes', why_this_one: 'No approval needed.' },
    ...overrides,
  }
}

const headings = () => screen.getAllByRole('heading', { level: 2 }).map(h => h.textContent)

describe('LearnerPlaybook', () => {
  it('opens on Do this today and ends with where you are today (C’s order)', () => {
    render(<LearnerPlaybook shared={playbook()} />)
    expect(headings()).toEqual(['Do this today', 'Your AI use cases', 'Your next moves', 'What might be holding you back', 'Where you are today'])
    expect(screen.getByText('Paste the supplier list into Copilot.')).toBeTruthy()
    expect(screen.getByText('10 minutes')).toBeTruthy()
  })

  it('shows the summary as a lead plus bullets, and an old one-paragraph summary as the lead only', () => {
    const { unmount } = render(<LearnerPlaybook shared={playbook()} />)
    const summary = screen.getByRole('region', { name: 'Where you are today' })
    expect(within(summary).getByText('You plan production for the bakery.')).toBeTruthy()
    expect(within(summary).getAllByRole('listitem').map(li => li.textContent)).toEqual(['Monday rebuild takes three hours.', 'Typos creep in.'])
    unmount()
    render(<LearnerPlaybook shared={playbook({ where_you_are_today: 'One paragraph, written before bullets.' })} />)
    const old = screen.getByRole('region', { name: 'Where you are today' })
    expect(within(old).getByText('One paragraph, written before bullets.')).toBeTruthy()
    expect(within(old).queryByRole('list')).toBeNull()
  })

  it('lists use cases by rank, marks start here, and shows the count', () => {
    render(<LearnerPlaybook shared={playbook()} />)
    const names = screen.getAllByRole('heading', { level: 3 }).map(h => h.textContent)
    expect(names).toEqual(['Draft the supplier emails', 'Spot quantity errors'])
    expect(screen.getByText('Start here')).toBeTruthy()
    expect(screen.getByText('2 use cases, ranked for you')).toBeTruthy()
  })

  it('uses the singular count for one use case and hides the section when there are none', () => {
    const one = playbook()
    const { unmount } = render(<LearnerPlaybook shared={{ ...one, use_cases: [one.use_cases[1]] }} />)
    expect(screen.getByText('One use case, picked for you')).toBeTruthy()
    unmount()
    render(<LearnerPlaybook shared={playbook({ use_cases: [] })} />)
    expect(headings()).not.toContain('Your AI use cases')
  })

  it('shows systems and "Involves colleagues" as tags', () => {
    render(<LearnerPlaybook shared={playbook()} />)
    const lists = screen.getAllByRole('list', { name: 'Systems' })
    expect(lists).toHaveLength(2)
    expect(within(lists[0]).getAllByRole('listitem').map(li => li.textContent)).toEqual(['Involves colleagues'])
    expect(within(lists[1]).getAllByRole('listitem').map(li => li.textContent)).toEqual(['SAP', 'Excel'])
  })

  it('shows no tag list for a use case with no systems and no colleagues', () => {
    const lone = { ...playbook().use_cases[0], systems_involved: [], cross_functional: false }
    render(<LearnerPlaybook shared={playbook({ use_cases: [lone] })} />)
    expect(screen.queryByRole('list', { name: 'Systems' })).toBeNull()
  })

  it('keeps details collapsed until asked, then shows them and relabels the button', () => {
    render(<LearnerPlaybook shared={playbook()} />)
    const button = screen.getAllByRole('button', { name: 'Show details' })[0]
    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('Keep one prompt in Outlook.')).toBeNull()
    fireEvent.click(button)
    expect(button.getAttribute('aria-expanded')).toBe('true')
    expect(button.textContent).toBe('Hide details')
    expect(screen.getByText('Keep one prompt in Outlook.')).toBeTruthy()
    expect(screen.getByText('In practice')).toBeTruthy()
  })

  it('orders next moves, links each to its use case, and drops the link for an unknown rank', () => {
    render(<LearnerPlaybook shared={playbook()} />)
    const moves = screen.getByRole('region', { name: 'Your next moves' })
    const items = within(moves).getAllByRole('listitem')
    expect(items.map(li => within(li).getByText(/Try|Ask|Talk/).textContent)).toEqual(['Try the email prompt', 'Ask IT about the export', 'Talk to sales'])
    const link = within(items[0]).getByRole('link', { name: 'Draft the supplier emails' })
    expect(document.getElementById(link.getAttribute('href')!.slice(1))).toBeTruthy()
    expect(within(items[2]).queryByText(/^For:/)).toBeNull()
    expect(within(items[2]).queryByRole('link')).toBeNull()
  })

  it('hides Do this today when there is no action', () => {
    render(<LearnerPlaybook shared={playbook({ do_this_today: { action: '', time_required: '', why_this_one: '' } })} />)
    expect(headings()[0]).toBe('Your AI use cases')
  })

  it('speaks Dutch in a Dutch interview', () => {
    render(<LearnerPlaybook shared={playbook()} language="nl" />)
    expect(headings()).toEqual(['Doe dit vandaag', 'Uw AI-toepassingen', 'Uw volgende stappen', 'Wat u misschien tegenhoudt', 'Waar u vandaag staat'])
    expect(screen.getAllByRole('button', { name: 'Details tonen' })).toHaveLength(2)
  })

  it('lays next moves out in as many columns as there are moves (the prompt allows up to four)', () => {
    const four = playbook({ next_moves: [1, 2, 3, 4].map(order => ({ order, move: `Move ${order}`, why_now: 'Why.', linked_use_case: 1 })) })
    render(<LearnerPlaybook shared={four} />)
    const steps = within(screen.getByRole('region', { name: 'Your next moves' })).getByRole('list')
    expect(steps.style.getPropertyValue('--lpb-steps')).toBe('4')
  })

  it('wraps long unbroken words anywhere in the playbook, so a URL never scrolls the page sideways', () => {
    const { container } = render(<LearnerPlaybook shared={playbook()} />)
    const css = container.querySelector('style')!.textContent!
    expect(css).toMatch(/\.lpb \{[^}]*overflow-wrap: anywhere/)
  })
})
