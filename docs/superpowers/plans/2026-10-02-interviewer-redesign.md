# Interviewer redesign (direction D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the learner's four interviewer screens to Aaron's pick, mockup D:
- Welcome, Chat and Building from direction A, with a quiet speech-bubble mark for the interviewer;
- the playbook in C's order, set in A's design language;
- the Do this today block as a light red tint, not black.

**Architecture:**
- **Restyle in place.** Welcome, Needs-assessment, Chat and Building are restyled inside `pages/Interview.tsx`. Their new CSS sits in one prefixed style string (`components/interview/interviewCss.ts`, rendered once by the page), the same idiom as today's `iv-`/`pb-` local `<style>` blocks.
- **New playbook component.** The redesigned playbook is a new, learner-only component, `components/interview/LearnerPlaybook.tsx`.
- **Admin untouched.** The existing `components/interview/Playbook.tsx` stays byte-for-byte unchanged. The admin card (`pages/admin2/InterviewCard.tsx`) keeps rendering it, so the admin screens look exactly as they do today (Aaron, 2 October: "Don't touch admin screens").

**Tech Stack:**
- React 19 + TypeScript, inline style objects plus prefixed local CSS strings;
- Vitest + Testing Library;
- Playwright with the fetch stub for the browser checks.

**Spec:**
- `Learnings/2026-10 Interviewer redesign mockups/direction-d-a-with-c-playbook.html`: the visual source of truth. Its "Design notes" tab is part of the spec.
- The README next to it.
- The source CSS of the mockup: `docs/design-prototypes/ai-interviewer/redesign-2026-10/_src/a.css` + `d.css`, in the worktree `C:/Users/neuvillea/.worktrees/hub-redesign-mockups`.

## Global Constraints

- **Interviewer files only.** Never edit:
  - `components/interview/Playbook.tsx` and `Playbook.test.tsx`;
  - anything under `pages/admin2/`;
  - `components/AppNav.tsx`, `components/Spinner.tsx`, `components/ChatPanel.tsx`;
  - `lib/useChat.ts`, `index.css`, `pages/JourneyHome.tsx`.

  If a change seems to need one of them, stop and flag it to Aaron.
- **No prompt changes** (`backend/prompts/**`), no backend changes, so no eval.
- **House style for every new string, EN and NL:**
  - no em dash (U+2014), en dash (U+2013) or ellipsis character (U+2026);
  - British spelling, sentence case;
  - formal "u" in Dutch, never je/jij/jouw.

  `interviewStrings.test.ts` enforces this; keep it green.
- **Tokens and colours.**
  - Existing tokens only: `--dlw-warm-grey`, `--dlw-red-tint`, `--dlw-dot-red`, `--dlw-primary-red`, `--dlw-black`, `--dlw-text`, `--dlw-border`, `--dlw-surface`, `--dlw-faint`, `--dlw-font-body`, `--dlw-font-ui`, `--dlw-duration`, `--dlw-ease`.
  - Secondary text is the local `#6B6B6B` (5.33:1 on white, 4.56:1 on the warm grey).
  - No new global token.
- **Keep the #109 and #151 guarantees:**
  - The chat page stays pinned (`position: fixed; inset: 0`).
  - The toolbar keeps the stacked hints (`allToolbarHints`), so its height never changes with the hint.
  - Build my playbook is always rendered, greyed until `canBuild && !chat.loading`.
  - The typing dots, the single page-level live region (with `lang`), the focus moves to the Building and Playbook headings, and the Interview.tsx house-style guard all keep working.
- **No layout shift.**
  - On the chat screen, the hint height and the Build button's position must be identical in every hint state and both languages, at 1920×1080, 1280×900, 1024×640 and 640×450.
  - No sideways scrolling at 640×450 (200% zoom).
- **Contrast:** AA for all text. Non-text marks (dots, field outlines) at least 3:1, or purely decorative.
- **Workflow:**
  - work in a worktree outside OneDrive, never in the shared `ai-enablement-hub-v2` folder;
  - follow CONTRIBUTING (branch, PR, both CI checks green, squash);
  - read the Claude review; stop before merge and deploy.
- **Browser checks use invented data only** (`Learnings/interviewer-fetch-stub.js`), never the live DB.

## Review Focus

1. **A next move whose `linked_use_case` points to a rank that isn't in `use_cases`:** the move still shows, with no "For" line and no dead anchor. Test in Task 2.
2. **Today's one-paragraph summaries** (the bullets prompt is not live yet, so production playbooks have no "- " lines): the summary renders as the lead paragraph only, with no empty list. Test in Task 2.
3. **One use case, or none.** One shows the singular count text ("One use case, picked for you"). None hides the whole section, and the heading list still starts with Do this today. Test in Task 2.
4. **An empty or missing `do_this_today.action`:** the tinted block is hidden and the page opens on the use cases. The Building screen's list is static and keeps the entry; only the playbook hides the block. Test in Task 2.
5. **Long unbroken words** (Dutch compounds, system names like `Copilot-in-Excel-exportbestand`) inside cards, tags and steps at 640 px: no sideways scrolling, because `overflow-wrap: anywhere` is set on card text. Test in Task 6 (browser check with a stub override).

---

### Task 0: Worktree, plan copy and "before" screenshots

**Files:**
- Create: `docs/superpowers/plans/2026-10-02-interviewer-redesign.md` (this plan, copied in)

- [ ] **Step 1: Create the worktree from the latest main**

Run in the shared clone; this only adds a worktree and touches none of its files:
```bash
cd "/c/Users/neuvillea/OneDrive - delaware/Documents/Cowork/AI FDE/Learning Journey/ai-enablement-hub-v2"
git fetch origin
git worktree add -b feat/interviewer-redesign /c/Users/neuvillea/.worktrees/hub-interviewer-redesign origin/main
cd /c/Users/neuvillea/.worktrees/hub-interviewer-redesign
git branch --unset-upstream
cd frontend && npm ci
```
Expected: `npm ci` ends without errors.

- [ ] **Step 2: Baseline checks**

Run (in `frontend/`): `npm run typecheck && npm run lint && npm test && npm run build`
Expected:
- typecheck clean;
- lint shows 0 errors (2 old warnings in `AuthContext.tsx` and `ProposalDiff.tsx`);
- all tests pass;
- the build succeeds.

- [ ] **Step 3: Take the "before" screenshots**

1. Start Vite on a spare port: `npx vite --port 5182 --strictPort` (background).
2. With Playwright, load the stub (`page.addInitScript({ path: 'C:/Users/neuvillea/OneDrive - delaware/Documents/Cowork/AI FDE/Learning Journey/Learnings/interviewer-fetch-stub.js' })`) and set `sessionStorage['verify.mode']` / `['verify.lang']`.
3. At 1280×900, capture these into `Learnings/2026-10 Interviewer redesign - before and after/before/`:
   - welcome EN and NL;
   - chat (`resume`) EN and NL;
   - chat ready (`long`) EN;
   - building (`buildslow`, after clicking Build) EN;
   - playbook (`done`) EN and NL, viewport and full page.

   For the full-page shots, use `page.screenshot({ fullPage: true })`: outside the chat, the window itself scrolls.

- [ ] **Step 4: Copy this plan into the branch and commit**

```bash
cp "/c/Users/neuvillea/OneDrive - delaware/Documents/Cowork/AI FDE/Learning Journey/Learnings/2026-10-02 Interviewer redesign - build plan.md" docs/superpowers/plans/2026-10-02-interviewer-redesign.md
git add docs/superpowers/plans/2026-10-02-interviewer-redesign.md
git commit -m "docs(plan): interviewer redesign, direction D"
```

---

### Task 1: Summary parser and the new strings

The summary parser is copied **byte-for-byte** from `origin/feat/interviewer-summary-bullets` (commit `7b2be37`). Whichever branch lands first, the other then adds an identical file, which git resolves without a conflict.

**Files:**
- Create: `frontend/src/lib/playbookSummary.ts`
- Create: `frontend/src/lib/playbookSummary.test.ts`
- Modify: `frontend/src/lib/interviewStrings.ts` (INTERVIEW_EN, INTERVIEW_NL, PLAYBOOK_EN, PLAYBOOK_NL)

**Interfaces:**
- Produces:
  - `parseSummary(text: string): { intro: string[]; bullets: string[] }`
  - new INTERVIEW keys `interviewerName`, `playbookWillContain`
  - new PLAYBOOK keys `showDetails`, `hideDetails`, `systems`, `withColleagues`, `forUseCase`, `timeNeeded`, `useCaseCountOne`, `useCaseCountMany` (contains the literal `{n}`)
  - `useCaseCount(n: number, t: PlaybookStrings): string`, exported from `interviewStrings.ts`

- [ ] **Step 1: Copy the parser and its test from the bullets branch**

```bash
git show 7b2be37:frontend/src/lib/playbookSummary.ts > frontend/src/lib/playbookSummary.ts
git show 7b2be37:frontend/src/lib/playbookSummary.test.ts > frontend/src/lib/playbookSummary.test.ts
git diff --no-index --stat <(git show 7b2be37:frontend/src/lib/playbookSummary.ts) frontend/src/lib/playbookSummary.ts
```
Expected: the last command prints nothing (identical).

For reference, the parser is:
```ts
/** The playbook's "Where you are today" text, split for display: a short intro, then bullet
 *  points (lines starting with "- "; a model sometimes writes "•" or "*" instead). The field
 *  stays one string in the API, so a summary written before bullets (one paragraph) simply
 *  comes back as intro only and renders as before. */
export function parseSummary(text: string): { intro: string[]; bullets: string[] } {
  const intro: string[] = []
  const bullets: string[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const bullet = line.match(/^[-•*]\s+(.*)$/)
    if (bullet) bullets.push(bullet[1].trim())
    else intro.push(line)
  }
  return { intro, bullets }
}
```

- [ ] **Step 2: Write the failing test for `useCaseCount`**

Append to `frontend/src/lib/interviewStrings.test.ts`:
```ts
import { useCaseCount } from './interviewStrings'

describe('useCaseCount', () => {
  it('uses the singular for one use case and the number for more, in both languages', () => {
    expect(useCaseCount(1, PLAYBOOK_STRINGS.en)).toBe('One use case, picked for you')
    expect(useCaseCount(4, PLAYBOOK_STRINGS.en)).toBe('4 use cases, ranked for you')
    expect(useCaseCount(1, PLAYBOOK_STRINGS.nl)).toBe('Eén toepassing, voor u gekozen')
    expect(useCaseCount(5, PLAYBOOK_STRINGS.nl)).toBe('5 toepassingen, voor u gerangschikt')
  })
})
```
(Merge the import into the existing import line at the top: `import { INTERVIEW_STRINGS, PLAYBOOK_STRINGS, useCaseCount } from './interviewStrings'`.)

- [ ] **Step 3: Run it to see it fail**

Run (in `frontend/`): `npx vitest run src/lib/interviewStrings.test.ts`
Expected: FAIL, `useCaseCount` is not exported.

- [ ] **Step 4: Add the strings and the helper**

In `INTERVIEW_EN`, after `conversationLabel`:
```ts
  interviewerName: 'Your interviewer',
```
After `buildingAnnouncement`:
```ts
  playbookWillContain: 'Your playbook will contain',
```
In `INTERVIEW_NL`, at the same places:
```ts
  interviewerName: 'Uw interviewer',
```
```ts
  playbookWillContain: 'Uw playbook bevat',
```
In `PLAYBOOK_EN`, at the end:
```ts
  showDetails: 'Show details',
  hideDetails: 'Hide details',
  systems: 'Systems',
  withColleagues: 'Involves colleagues',
  forUseCase: 'For: ',
  timeNeeded: 'Time needed: ',
  useCaseCountOne: 'One use case, picked for you',
  useCaseCountMany: '{n} use cases, ranked for you',
```
In `PLAYBOOK_NL`, at the end:
```ts
  showDetails: 'Details tonen',
  hideDetails: 'Details verbergen',
  systems: 'Systemen',
  withColleagues: 'Samen met collega’s',
  forUseCase: 'Voor: ',
  timeNeeded: 'Benodigde tijd: ',
  useCaseCountOne: 'Eén toepassing, voor u gekozen',
  useCaseCountMany: '{n} toepassingen, voor u gerangschikt',
```
After `PLAYBOOK_STRINGS`:
```ts
/** The use-case count under the playbook's use-case heading, singular for one. */
export function useCaseCount(n: number, t: PlaybookStrings): string {
  return n === 1 ? t.useCaseCountOne : t.useCaseCountMany.replace('{n}', String(n))
}
```

- [ ] **Step 5: Run the tests**

Run: `npx vitest run src/lib/interviewStrings.test.ts src/lib/playbookSummary.test.ts`
Expected: PASS. The existing same-keys, no-empty, house-style and formal-"u" tests also cover the new keys.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/playbookSummary.ts frontend/src/lib/playbookSummary.test.ts frontend/src/lib/interviewStrings.ts frontend/src/lib/interviewStrings.test.ts
git commit -m "feat(interview): summary parser and strings for the redesigned screens"
```

---

### Task 2: `LearnerPlaybook`, C's structure in A's design language

**Files:**
- Create: `frontend/src/components/interview/LearnerPlaybook.tsx`
- Create: `frontend/src/components/interview/LearnerPlaybook.test.tsx`

**Interfaces:**
- Consumes: `parseSummary` (Task 1), `useCaseCount`, `PLAYBOOK_STRINGS`, `DEFAULT_INTERVIEW_LANGUAGE`, `InterviewLanguage` (Task 1), the types `PlaybookShared`, `UseCase`, `Difficulty` from `types/domain`.
- Produces: `export default function LearnerPlaybook({ shared, language }: { shared: PlaybookShared; language?: InterviewLanguage })`. It renders sections only; the page supplies the `<h1>`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/interview/LearnerPlaybook.test.tsx`:
```tsx
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
})
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/components/interview/LearnerPlaybook.test.tsx`
Expected: FAIL, cannot resolve `./LearnerPlaybook`.

- [ ] **Step 3: Write the component**

`frontend/src/components/interview/LearnerPlaybook.tsx`:
```tsx
import { useId, useState, type CSSProperties } from 'react'
import type { Difficulty, PlaybookShared, UseCase } from '../../types/domain'
import { parseSummary } from '../../lib/playbookSummary'
import { DEFAULT_INTERVIEW_LANGUAGE, PLAYBOOK_STRINGS, useCaseCount, type InterviewLanguage, type PlaybookStrings } from '../../lib/interviewStrings'

/* The learner's playbook (redesign D, 2 October): C's order (Do this today first, the use
   cases as cards, next moves across, hesitations as cards, the summary last) in A's design
   language. Learner-only: the admin card keeps components/interview/Playbook.tsx, unchanged. */

/* The semantic difficulty palette, the same values as Playbook.tsx (kept separate so the
   admin component is not touched). */
const DIFFICULTY_CHIP: Record<Difficulty, { bg: string; color: string }> = {
  'Quick Win': { bg: '#EDFAF4', color: '#1D7A52' },
  'Worth a Session': { bg: '#FEFCE8', color: '#A16207' },
  'Bigger Build': { bg: '#FFF1E8', color: '#B24A0F' },
}
const CHIP_FALLBACK = { bg: 'var(--dlw-surface)', color: '#6B6B6B' }

function difficultyLabel(d: Difficulty, t: PlaybookStrings): string {
  const labels: Record<Difficulty, string> = {
    'Quick Win': t.difficultyQuickWin, 'Worth a Session': t.difficultyWorthASession, 'Bigger Build': t.difficultyBiggerBuild,
  }
  return labels[d] ?? d
}

/** The playbook strings end inline labels with ": " ("In practice: "); as a block label the
 *  colon goes. */
const blockLabel = (label: string) => label.replace(/:\s*$/, '')

/* What inline styles can't express: the red-dot markers, hover and focus, and the narrow-window
   and 200% zoom layouts. Local, with an `lpb-` prefix (the iv-/pb-/lp- idiom). */
const CSS = `
.lpb { display: flex; flex-direction: column; }
.lpb-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: var(--dlw-dot-red); flex: none; }
.lpb-h2 { font-family: var(--dlw-font-body); font-weight: 800; font-size: 25px; line-height: 1.2; letter-spacing: -0.012em; color: var(--dlw-black); margin: 0; }
.lpb-sec { margin-bottom: 48px; }
.lpb-sec-head { display: flex; align-items: baseline; justify-content: space-between; gap: 6px 16px; flex-wrap: wrap; margin-bottom: 18px; }
.lpb-count { margin: 0; font-size: 14px; color: #6B6B6B; font-weight: 400; }
.lpb-today { border-radius: 18px; background: var(--dlw-red-tint); border: 1.5px solid rgba(196, 40, 40, .28); padding: 30px 36px 28px; margin-bottom: 48px; }
.lpb-today h2 { display: flex; align-items: center; gap: 10px; margin: 0 0 12px; font-family: var(--dlw-font-ui); font-size: 14px; font-weight: 600; color: var(--dlw-primary-red); }
.lpb-act { margin: 0 0 22px; font-size: 30px; line-height: 1.25; font-weight: 800; letter-spacing: -0.015em; max-width: 32ch; color: var(--dlw-black); overflow-wrap: anywhere; }
.lpb-meta { display: flex; align-items: center; gap: 12px 22px; flex-wrap: wrap; padding-top: 18px; border-top: 1px solid rgba(196, 40, 40, .18); }
.lpb-time { display: inline-flex; background: #fff; color: var(--dlw-black); border: 1px solid rgba(196, 40, 40, .28); border-radius: 999px; padding: 4px 13px; font-family: var(--dlw-font-ui); font-weight: 700; font-size: 13.5px; }
.lpb-why { margin: 0; font-size: 15.5px; font-weight: 400; color: var(--dlw-text); }
.lpb-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }
.lpb-card { border: 1px solid var(--dlw-border); border-radius: 14px; padding: 18px 20px 14px; background: #fff; display: flex; flex-direction: column; gap: 8px; scroll-margin-top: 16px; overflow-wrap: anywhere; }
.lpb-card.is-start { border: 2px solid var(--dlw-black); }
.lpb-card-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.lpb-rank { font-weight: 800; font-size: 15px; color: var(--dlw-black); width: 28px; height: 28px; border-radius: 50%; border: 1.5px solid var(--dlw-black); display: inline-flex; align-items: center; justify-content: center; }
.lpb-start { display: inline-flex; align-items: center; gap: 7px; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 12.5px; color: var(--dlw-primary-red); }
.lpb-start .lpb-dot { width: 8px; height: 8px; }
.lpb-chip { display: inline-flex; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 11.5px; padding: 3px 10px; border-radius: 999px; white-space: nowrap; }
.lpb-card h3 { margin: 0; font-weight: 800; font-size: 18px; line-height: 1.3; color: var(--dlw-black); }
.lpb-pain { margin: 0; font-size: 14.5px; line-height: 1.5; color: #6B6B6B; font-weight: 400; }
.lpb-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 2px 0 0; padding: 0; list-style: none; }
.lpb-tags li { font-family: var(--dlw-font-ui); font-size: 12px; font-weight: 500; color: var(--dlw-text); border: 1px solid var(--dlw-border); border-radius: 6px; padding: 2px 8px; }
.lpb-tags li.is-colleagues { border-color: transparent; background: var(--dlw-surface); }
.lpb-toggle { align-self: flex-start; border: none; background: none; padding: 6px 0; cursor: pointer; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 13px; color: var(--dlw-black); text-decoration: underline; text-underline-offset: 3px; text-decoration-color: var(--dlw-faint); }
.lpb-toggle:hover { text-decoration-color: currentColor; }
.lpb-toggle:focus-visible, .lpb a:focus-visible { outline: 2px solid var(--dlw-primary-red); outline-offset: 2px; }
.lpb-detail { display: flex; flex-direction: column; gap: 12px; padding-top: 12px; border-top: 1px solid var(--dlw-border); font-size: 14.5px; line-height: 1.55; font-weight: 400; }
.lpb-detail p { margin: 0; }
.lpb-label { display: block; font-family: var(--dlw-font-ui); font-weight: 600; font-size: 12.5px; color: #6B6B6B; margin-bottom: 2px; }
.lpb-ba { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.lpb-ba div { background: var(--dlw-surface); border-radius: 10px; padding: 10px 12px; font-size: 13.5px; }
.lpb-assume { background: #FFFBEB; border: 1px dashed #E8C46A; border-radius: 10px; padding: 9px 12px; font-size: 14px; color: #6B5414; }
.lpb-assume .lpb-label { color: #6B5414; }
.lpb-steps { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.lpb-steps li { position: relative; padding-right: 24px; overflow-wrap: anywhere; }
.lpb-steps li:not(:last-child)::before { content: ""; position: absolute; left: 42px; right: 10px; top: 15px; height: 2px; background: var(--dlw-border); }
.lpb-num { width: 32px; height: 32px; border-radius: 50%; background: var(--dlw-black); color: #fff; font-weight: 800; font-size: 14px; display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
.lpb-move { margin: 0 0 2px; font-weight: 800; font-size: 17px; line-height: 1.4; color: var(--dlw-black); }
.lpb-why-now { margin: 0 0 4px; font-size: 15px; line-height: 1.5; color: var(--dlw-text); font-weight: 400; }
.lpb-for { margin: 0; font-size: 13.5px; color: #6B6B6B; font-weight: 400; }
.lpb-for a { color: var(--dlw-black); text-underline-offset: 3px; text-decoration-color: var(--dlw-faint); }
.lpb-rfs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.lpb-rf { background: var(--dlw-warm-grey); border-radius: 14px; padding: 22px 24px; overflow-wrap: anywhere; }
.lpb-rf p { margin: 0 0 8px; font-size: 15px; line-height: 1.6; font-weight: 400; color: var(--dlw-text); }
.lpb-rf p:last-child { margin: 0; }
.lpb-q { font-size: 19px !important; line-height: 1.4 !important; font-weight: 700 !important; font-style: italic; color: var(--dlw-black) !important; margin-bottom: 12px !important; }
.lpb-concern { font-size: 13.5px !important; color: #6B6B6B !important; }
.lpb-summary { padding-top: 40px; border-top: 1px solid var(--dlw-border); margin-bottom: 0; }
.lpb-lead { font-size: 19px; line-height: 1.55; font-weight: 400; color: var(--dlw-black); margin: 18px 0 22px; max-width: 60ch; }
.lpb-bullets { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 40px; }
.lpb-bullets li { position: relative; padding-left: 26px; font-size: 16.5px; line-height: 1.55; color: var(--dlw-text); font-weight: 400; }
.lpb-bullets li::before { content: ""; position: absolute; left: 2px; top: .52em; width: 9px; height: 9px; border-radius: 50%; background: var(--dlw-dot-red); }
@media (max-width: 1100px) { .lpb-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 900px) {
  .lpb-cards, .lpb-steps, .lpb-rfs, .lpb-bullets { grid-template-columns: 1fr; }
  .lpb-today { padding: 24px; }
  .lpb-act { font-size: 24px; }
  .lpb-steps li { padding: 0 0 20px 48px; }
  .lpb-steps li:not(:last-child)::before { left: 15px; right: auto; top: 36px; bottom: 0; width: 2px; height: auto; }
  .lpb-num { position: absolute; left: 0; top: 0; }
}
`

const s = { srOnly: { position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 } } satisfies Record<string, CSSProperties>

function UseCaseCard({ uc, idBase, open, onToggle, t }: { uc: UseCase; idBase: string; open: boolean; onToggle: () => void; t: PlaybookStrings }) {
  const chip = DIFFICULTY_CHIP[uc.difficulty] ?? CHIP_FALLBACK
  const detailId = `${idBase}-detail`
  const hasTags = uc.systems_involved.length > 0 || uc.cross_functional
  return (
    <article className={`lpb-card${uc.start_here ? ' is-start' : ''}`} id={idBase} aria-labelledby={`${idBase}-name`}>
      <div className="lpb-card-top">
        <span className="lpb-rank">{uc.rank}</span>
        {uc.start_here && <span className="lpb-start"><span className="lpb-dot" aria-hidden="true" />{t.startHere}</span>}
        <span className="lpb-chip" style={{ background: chip.bg, color: chip.color }}>{difficultyLabel(uc.difficulty, t)}</span>
      </div>
      <h3 id={`${idBase}-name`}>{uc.name}</h3>
      {uc.pain_it_kills && <p className="lpb-pain">{uc.pain_it_kills}</p>}
      {hasTags && (
        <ul className="lpb-tags" aria-label={t.systems}>
          {uc.systems_involved.map(sys => <li key={sys}>{sys}</li>)}
          {uc.cross_functional && <li className="is-colleagues">{t.withColleagues}</li>}
        </ul>
      )}
      <button type="button" className="lpb-toggle" aria-expanded={open} aria-controls={detailId} onClick={onToggle}>
        {open ? t.hideDetails : t.showDetails}
      </button>
      {open && (
        <div className="lpb-detail" id={detailId}>
          {uc.in_practice && <p><span className="lpb-label">{blockLabel(t.inPractice)}</span>{uc.in_practice}</p>}
          {(uc.before || uc.after) && (
            <div className="lpb-ba">
              <div><span className="lpb-label">{t.before}</span>{uc.before}</div>
              <div><span className="lpb-label">{t.after}</span>{uc.after}</div>
            </div>
          )}
          {uc.impact && <p><span className="lpb-label">{blockLabel(t.impact)}</span>{uc.impact}</p>}
          {uc.assumption_to_check != null && (
            <p className="lpb-assume"><span className="lpb-label">{blockLabel(t.assumptionToCheck)}</span>{uc.assumption_to_check}</p>
          )}
        </div>
      )}
    </article>
  )
}

/** The redesigned playbook for the learner. Pure presentational; the page supplies the h1. */
export default function LearnerPlaybook({ shared, language = DEFAULT_INTERVIEW_LANGUAGE }: { shared: PlaybookShared; language?: InterviewLanguage }) {
  const t = PLAYBOOK_STRINGS[language]
  const id = useId()
  const [openRanks, setOpenRanks] = useState<Set<number>>(() => new Set())
  const toggle = (rank: number) => setOpenRanks(prev => {
    const next = new Set(prev)
    if (next.has(rank)) next.delete(rank)
    else next.add(rank)
    return next
  })

  const useCases = [...shared.use_cases].sort((a, b) => a.rank - b.rank)
  const cardId = (rank: number) => `${id}-uc-${rank}`
  const moves = [...shared.next_moves].sort((a, b) => a.order - b.order)
  const summary = parseSummary(shared.where_you_are_today ?? '')
  const today = shared.do_this_today
  const hasToday = Boolean(today?.action)

  return (
    <div className="lpb">
      <style>{CSS}</style>

      {hasToday && (
        <section className="lpb-today" aria-labelledby={`${id}-today`}>
          <h2 id={`${id}-today`}><span className="lpb-dot" aria-hidden="true" />{t.doThisToday}</h2>
          <p className="lpb-act">{today.action}</p>
          {(today.time_required || today.why_this_one) && (
            <div className="lpb-meta">
              {today.time_required && <span className="lpb-time"><span style={s.srOnly}>{t.timeNeeded}</span>{today.time_required}</span>}
              {today.why_this_one && <p className="lpb-why">{today.why_this_one}</p>}
            </div>
          )}
        </section>
      )}

      {useCases.length > 0 && (
        <section className="lpb-sec" aria-labelledby={`${id}-ucs`}>
          <div className="lpb-sec-head">
            <h2 className="lpb-h2" id={`${id}-ucs`}>{t.useCases}</h2>
            <p className="lpb-count">{useCaseCount(useCases.length, t)}</p>
          </div>
          <div className="lpb-cards">
            {useCases.map(uc => (
              <UseCaseCard key={uc.rank} uc={uc} idBase={cardId(uc.rank)} open={openRanks.has(uc.rank)} onToggle={() => toggle(uc.rank)} t={t} />
            ))}
          </div>
        </section>
      )}

      {moves.length > 0 && (
        <section className="lpb-sec" aria-labelledby={`${id}-moves`}>
          <div className="lpb-sec-head"><h2 className="lpb-h2" id={`${id}-moves`}>{t.nextMoves}</h2></div>
          <ol className="lpb-steps">
            {moves.map((m, i) => {
              const linked = useCases.find(uc => uc.rank === m.linked_use_case)
              return (
                <li key={m.order}>
                  <span className="lpb-num" aria-hidden="true">{i + 1}</span>
                  <p className="lpb-move">{m.move}</p>
                  {m.why_now && <p className="lpb-why-now">{m.why_now}</p>}
                  {linked && <p className="lpb-for">{t.forUseCase}<a href={`#${cardId(linked.rank)}`}>{linked.name}</a></p>}
                </li>
              )
            })}
          </ol>
        </section>
      )}

      {shared.reframes.length > 0 && (
        <section className="lpb-sec" aria-labelledby={`${id}-rfs`}>
          <div className="lpb-sec-head"><h2 className="lpb-h2" id={`${id}-rfs`}>{t.holdingYouBack}</h2></div>
          <div className="lpb-rfs">
            {shared.reframes.map((rf, i) => (
              <div className="lpb-rf" key={i}>
                <p className="lpb-q">&ldquo;{rf.their_hesitation}&rdquo;</p>
                <p>{rf.reframe}</p>
                <p><strong style={{ fontWeight: 800, color: 'var(--dlw-black)' }}>{t.firstProof}: </strong>{rf.first_proof}</p>
                <p className="lpb-concern">{t.realConcern}: {rf.the_concern}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {(summary.intro.length > 0 || summary.bullets.length > 0) && (
        <section className="lpb-sec lpb-summary" aria-labelledby={`${id}-sum`}>
          <h2 className="lpb-h2" id={`${id}-sum`}>{t.whereYouAreToday}</h2>
          {summary.intro.map((line, i) => <p className="lpb-lead" key={i}>{line}</p>)}
          {summary.bullets.length > 0 && <ul className="lpb-bullets">{summary.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>}
        </section>
      )}
    </div>
  )
}
```
Note: `<section aria-labelledby>` gives each section the ARIA role "region" with the heading as its name, which the tests rely on.

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/components/interview/LearnerPlaybook.test.tsx`
Expected: PASS.

- [ ] **Step 5: Typecheck and lint**

Run: `npm run typecheck && npm run lint`
Expected: clean (0 errors).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/interview/LearnerPlaybook.tsx frontend/src/components/interview/LearnerPlaybook.test.tsx
git commit -m "feat(interview): learner playbook in the redesign's order and style (admin keeps Playbook)"
```

---

### Task 3: The page canvas, Welcome, Needs-assessment and Building (direction A)

**Files:**
- Create: `frontend/src/components/interview/interviewCss.ts`
- Modify: `frontend/src/pages/Interview.tsx`:
  - the `s` styles `page`, `main`, `languageRow`, plus removal of `eyebrow`, `stepsGrid`, `stepCard`, `stepLabel`, `stepText`, `notice`, `noticeText`, `buildingWrap`, `buildingTitle`, `buildingSub` once unused;
  - `WelcomeScreen`, `NeedsAssessmentScreen` and `BuildingScreen`;
  - the page JSX, including the error and unavailable messages.
- Test: `frontend/src/pages/Interview.test.tsx`

**Interfaces:**
- Consumes: `INTERVIEW_STRINGS[...].playbookWillContain` (Task 1), `PLAYBOOK_STRINGS` section names.
- Produces: `export const INTERVIEW_CSS: string` with these classes: `iv-sheet`, `iv-sheet-wide`, `iv-dot`, `iv-h1`, `iv-lead`, `iv-top`, `iv-steps`, `iv-start`, `iv-privacy`, `iv-track`, `iv-run`, `iv-small`, `iv-parts`, `iv-pb-head`, and the chat classes used in Task 4 (`iv-chat`, `iv-chat-head`, `iv-mark`, `iv-who`, `iv-msg-ai`, `iv-msg-me`).

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/pages/Interview.test.tsx` (inside `describe('Interview: the language choice', ...)`):
```tsx
  it('shows the three steps as an ordered list and no label above the heading', async () => {
    renderPage()
    await screen.findByRole('heading', { name: EN.welcomeHeading })
    const steps = screen.getAllByRole('list').find(list => list.tagName === 'OL')!
    expect(steps).toBeTruthy()
    expect(within(steps).getAllByRole('listitem').map(li => li.textContent)).toEqual([
      EN.stepTalkLabel + EN.stepTalkText, EN.stepBuildLabel + EN.stepBuildText, EN.stepStartLabel + EN.stepStartText,
    ])
    expect(screen.queryByText(EN.eyebrow)).toBeNull()
  })
```
Add `within` to the Testing Library import at the top of the file.

Add a new describe block for Building:
```tsx
describe('Interview: building', () => {
  it('lists what the playbook will contain, in the playbook’s order, in the interview language', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    api.buildPlaybook.mockReturnValue(new Promise(() => {}))
    chat.messages = longConversation()
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: NL.buildButton }))
    expect(await screen.findByRole('heading', { name: NL.buildingHeading })).toBeTruthy()
    expect(screen.getByText(NL.playbookWillContain)).toBeTruthy()
    const parts = screen.getByText(NL.playbookWillContain).nextElementSibling as HTMLElement
    expect(within(parts).getAllByRole('listitem').map(li => li.textContent)).toEqual([
      'Doe dit vandaag', 'Uw AI-toepassingen', 'Uw volgende stappen', 'Wat u misschien tegenhoudt', 'Waar u vandaag staat',
    ])
  })
})
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/pages/Interview.test.tsx`
Expected: the two new tests FAIL (there is no `<ol>` and the building list is missing); the rest PASS.

- [ ] **Step 3: Create `interviewCss.ts`**

`frontend/src/components/interview/interviewCss.ts`:
```ts
/** The interview page's look (redesign D, from direction A): a warm-grey page with a white
 *  sheet, large Mulish type, and the red dot from the delaware logo as the step and bullet
 *  marker. What inline styles can't express lives here: pseudo-elements, keyframes, media
 *  queries. Rendered once by pages/Interview.tsx. Prefix `iv-`, the page's existing idiom. */
export const INTERVIEW_CSS = `
.iv-sheet { width: min(860px, 100%); box-sizing: border-box; margin: 28px auto 48px; background: #fff; border-radius: 20px; padding: 40px 64px 48px; box-shadow: 0 1px 0 rgba(16, 24, 32, .04), 0 28px 56px -36px rgba(16, 24, 32, .30); }
.iv-sheet-wide { width: min(1000px, 100%); padding-top: 48px; }
.iv-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: var(--dlw-dot-red); flex: none; }
.iv-h1 { font-family: var(--dlw-font-body); font-weight: 800; font-size: 44px; line-height: 1.08; letter-spacing: -0.022em; color: var(--dlw-black); margin: 0 0 22px; max-width: 24ch; }
.iv-lead { font-size: 19px; line-height: 1.55; font-weight: 400; color: var(--dlw-black); margin: 0 0 30px; max-width: 60ch; }
.iv-lead strong { font-weight: 800; }
.iv-top { display: flex; justify-content: flex-end; margin: -8px 0 6px; }
.iv-steps { list-style: none; margin: 0 0 28px; padding: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; position: relative; }
.iv-steps::before { content: ""; position: absolute; left: 6px; right: calc(33.333% - 22px); top: 5px; height: 2px; background: var(--dlw-border); }
.iv-steps li { position: relative; display: flex; flex-direction: column; gap: 6px; padding-top: 26px; }
.iv-steps .iv-dot { position: absolute; top: 0; left: 0; }
.iv-steps strong { font-weight: 800; font-size: 17px; color: var(--dlw-black); }
.iv-steps span:last-child { font-size: 15px; line-height: 1.5; color: var(--dlw-text); font-weight: 400; max-width: 28ch; }
.iv-start { display: flex; align-items: center; gap: 22px; flex-wrap: wrap; padding-top: 24px; border-top: 1px solid var(--dlw-border); }
.iv-privacy { margin: 0; font-size: 13px; line-height: 1.5; color: #6B6B6B; max-width: 46ch; font-weight: 400; }
.iv-track { position: relative; height: 12px; margin: 4px 0 34px; }
.iv-track::before { content: ""; position: absolute; left: 0; right: 0; top: 5px; height: 2px; background: var(--dlw-border); }
@keyframes iv-run { 0% { left: 0 } 50% { left: calc(100% - 12px) } 100% { left: 0 } }
.iv-run { position: absolute; top: 0; left: 0; animation: iv-run 2.4s var(--dlw-ease) infinite; }
@media (prefers-reduced-motion: reduce) { .iv-run { animation: none; } }
.iv-small { font-family: var(--dlw-font-ui); font-weight: 600; font-size: 13px; color: #6B6B6B; margin: 0 0 10px; }
.iv-parts { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.iv-parts li { display: flex; align-items: center; gap: 12px; font-size: 15.5px; font-weight: 400; color: var(--dlw-black); }
.iv-parts .iv-dot { width: 8px; height: 8px; background: var(--dlw-border); }
.iv-pb-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px 24px; flex-wrap: wrap; margin-bottom: 26px; }
.iv-pb-head .iv-h1 { font-size: 36px; margin: 0; max-width: none; }
.iv-pb-head p { margin: 0; font-size: 14.5px; color: #6B6B6B; font-weight: 400; }

/* Chat (Task 4) */
.iv-chat { background: #fff; border-radius: 20px; box-shadow: 0 1px 0 rgba(16, 24, 32, .04), 0 28px 56px -36px rgba(16, 24, 32, .30); }
.iv-chat-head { display: flex; gap: 12px; align-items: flex-start; padding: 18px 28px 16px; border-bottom: 1px solid var(--dlw-border); }
.iv-mark { width: 22px; height: 22px; flex: none; margin-top: 1px; color: #6B6B6B; }
.iv-who { margin: 0 0 2px; font-weight: 800; font-size: 15px; color: var(--dlw-black); line-height: 1.3; }
.iv-msg-ai { align-self: flex-start; max-width: 64ch !important; background: none !important; color: var(--dlw-black) !important; font-size: 16px !important; font-weight: 400; padding: 0 0 0 18px !important; border-radius: 0 !important; }
.iv-msg-ai::before { content: ""; position: absolute; left: 0; top: .62em; width: 7px; height: 7px; border-radius: 50%; background: var(--dlw-dot-red); }
.iv-msg-me { background: var(--dlw-warm-grey) !important; color: var(--dlw-black) !important; font-size: 16px !important; font-weight: 400; padding: 11px 16px !important; border-radius: 16px 16px 4px 16px !important; max-width: 72% !important; }

@media (max-width: 900px) {
  .iv-sheet { padding: 32px 24px 36px; margin: 16px auto 28px; }
  .iv-h1 { font-size: 32px; }
  .iv-lead { font-size: 17px; }
  .iv-steps { grid-template-columns: 1fr; gap: 18px; }
  .iv-steps::before { left: 5px; right: auto; top: 6px; bottom: 6px; width: 2px; height: auto; }
  .iv-steps li { padding: 0 0 0 28px; }
  .iv-chat-head { padding-left: 18px; padding-right: 18px; }
}
`
```
(The `!important` on the chat message classes overrides the existing inline bubble styles from `s.bubble*`, which are kept for layout. Task 4 removes the colour and radius from the inline styles, so these can drop `!important` there if the implementer prefers. Either way is fine, as long as the result matches the mockup.)

- [ ] **Step 4: Restyle the page shell, Welcome, Needs-assessment and Building in `Interview.tsx`**

Imports, add:
```ts
import { INTERVIEW_CSS } from '../components/interview/interviewCss'
import { DEFAULT_INTERVIEW_LANGUAGE, INTERVIEW_STRINGS, PLAYBOOK_STRINGS, interviewError, type InterviewLanguage, type InterviewStrings } from '../lib/interviewStrings'
```
(Replace the existing `interviewStrings` import line with the second one.)

In `s`, replace `page`, `languageRow` and `main` with:
```ts
  page: { minHeight: '100vh', background: 'var(--dlw-warm-grey)', display: 'flex', flexDirection: 'column' },
  main: { flex: 1, width: '100%', margin: '0 auto', padding: '0 24px', boxSizing: 'border-box' },
```
Change `mainChat` to:
```ts
  mainChat: { display: 'flex', flexDirection: 'column', width: 'min(908px, 100%)', padding: '24px 24px 20px' },
```
(908 = the 860 px sheet plus 2 × 24 px padding, so the chat lines up with the other screens.)

Replace `WelcomeScreen`'s return with:
```tsx
  const steps: [string, string][] = [
    [t.stepTalkLabel, t.stepTalkText], [t.stepBuildLabel, t.stepBuildText], [t.stepStartLabel, t.stepStartText],
  ]
  return (
    <div className="iv-sheet">
      {/* The learner's language choice (#83), first thing on the page: the screen switches
          as soon as one is picked, and the interview runs in it. */}
      <div className="iv-top">
        <LanguagePicker value={language} onChange={onLanguageChange} label={t.languagePickerLabel} />
      </div>
      {/* No eyebrow above the heading here: the heading says it on its own. */}
      <h1 className="iv-h1">{t.welcomeHeading}</h1>
      <p className="iv-lead">
        {t.welcomeBodyBefore}<strong>{t.welcomeBodyStrong}</strong>{t.welcomeBodyAfter}
      </p>
      {/* The three steps really are a sequence: a line with the logo's red dots. */}
      <ol className="iv-steps">
        {steps.map(([label, text]) => (
          <li key={label}><span className="iv-dot" aria-hidden="true" /><strong>{label}</strong><span>{text}</span></li>
        ))}
      </ol>
      <div className="iv-start">
        <button type="button" className="btn-red-dark" style={{ ...s.btnPrimary, padding: '14px 32px', fontSize: 16 }} onClick={onStart}>
          {t.startButton}
        </button>
        <p className="iv-privacy">{t.privacyNotice}</p>
      </div>
    </div>
  )
```
Replace `NeedsAssessmentScreen`'s return with:
```tsx
  return (
    <div className="iv-sheet">
      <h1 className="iv-h1">{t.needsAssessmentHeading}</h1>
      <p className="iv-lead">{t.needsAssessmentText}</p>
      <button type="button" className="btn-red-dark" style={s.btnPrimary} onClick={onGoToAssessment}>
        {t.needsAssessmentButton}
      </button>
    </div>
  )
```
Replace `BuildingScreen` with:
```tsx
function BuildingScreen({ language }: { language: InterviewLanguage }) {
  const t = INTERVIEW_STRINGS[language]
  const p = PLAYBOOK_STRINGS[language]
  // The playbook's own section order (LearnerPlaybook), so the list matches what appears.
  const parts = [p.doThisToday, p.useCases, p.nextMoves, p.holdingYouBack, p.whereYouAreToday]
  return (
    <div className="iv-sheet">
      {/* Indeterminate on purpose: the build reports no progress, so nothing pretends to. */}
      <div className="iv-track" aria-hidden="true"><span className="iv-dot iv-run" /></div>
      <h1 id={BUILDING_HEADING_ID} tabIndex={-1} className="iv-h1" style={s.focusTarget}>{t.buildingHeading}</h1>
      <p className="iv-lead" style={{ fontSize: 18, color: 'var(--dlw-text)' }}>{t.buildingText}</p>
      <p className="iv-small">{t.playbookWillContain}</p>
      <ul className="iv-parts">
        {parts.map(part => <li key={part}><span className="iv-dot" aria-hidden="true" />{part}</li>)}
      </ul>
    </div>
  )
}
```
In the page JSX:
- add `<style>{INTERVIEW_CSS}</style>` as the first child of the outer `<div>`;
- `<BuildingScreen t={t} />` becomes `<BuildingScreen language={language} />`;
- the load error becomes `<div className="iv-sheet"><p style={s.errorMsg}>{shownLoadError}</p></div>`;
- the unavailable message becomes `<div className="iv-sheet"><p style={s.errorMsg}>{t.playbookUnavailable}</p></div>`.

Change `errorMsg` to `margin: 0`.

Delete the now-unused style keys: `languageRow`, `eyebrow`, `heading` (only if Task 5 no longer uses it; keep it until then), `body`, `stepsGrid`, `stepCard`, `stepLabel`, `stepText`, `notice`, `noticeText`, `buildingWrap`, `buildingTitle`, `buildingSub`. Typecheck reports none of these, so search with `grep -n "s\.<key>" frontend/src/pages/Interview.tsx` before deleting each.

- [ ] **Step 5: Run the tests**

Run: `npx vitest run src/pages/Interview.test.tsx`
Expected: PASS, including the house-style guard. All new visible text comes from the dictionary; the CSS lives in `interviewCss.ts`, which the guard doesn't scan, and it holds no prose.

- [ ] **Step 6: Typecheck, lint, commit**

Run: `npm run typecheck && npm run lint`
Expected: clean.
```bash
git add frontend/src/components/interview/interviewCss.ts frontend/src/pages/Interview.tsx frontend/src/pages/Interview.test.tsx
git commit -m "feat(interview): warm-grey page and white sheet; welcome, needs-assessment and building in the redesign"
```

---

### Task 4: The chat, direction A with the quiet mark

**Files:**
- Modify: `frontend/src/pages/Interview.tsx`: the `s` styles `chatShell`, `chatToolbar`, `messages`, `bubble`, `bubbleUser`, `bubbleAssistant`, `privacyNotice`, `chatForm`; the `ChatScreen` JSX
- Test: `frontend/src/pages/Interview.test.tsx`

**Interfaces:**
- Consumes: `INTERVIEW_CSS` chat classes (Task 3), `t.interviewerName` (Task 1).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Write the failing test**

Add to `describe('Interview: the language choice', ...)`:
```tsx
  it('names the interviewer above the hint in the chat header', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'in_progress', language: 'nl', conversation_id: 'c1' })
    chat.messages = [{ role: 'assistant', content: 'Waar werkt u het meest in?' }]
    renderPage()
    const hint = await screen.findByText(NL.hintFirstAnswer)
    const header = hint.closest('.iv-chat-head') as HTMLElement
    expect(header).toBeTruthy()
    expect(within(header).getByText(NL.interviewerName)).toBeTruthy()
  })
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/pages/Interview.test.tsx -t "names the interviewer"`
Expected: FAIL, no `.iv-chat-head`.

- [ ] **Step 3: Restyle the chat**

Add the mark above `ChatScreen`:
```tsx
/** A quiet speech-bubble outline next to "Your interviewer" (redesign D): the black disc with
 *  the logo dot was too prominent. Decorative; the name next to it says who it is. */
function InterviewerMark() {
  return (
    <svg className="iv-mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {/* Path written with commas, not spaces: the house-style guard reads a capitalised
          literal with spaces as prose. */}
      <path d="M4,5.5A2.5,2.5,0,0,1,6.5,3h11A2.5,2.5,0,0,1,20,5.5v8a2.5,2.5,0,0,1-2.5,2.5H10l-4.2,3.6c-.5.4-1.3.1-1.3-.6V16A2.5,2.5,0,0,1,4,13.5z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}
```
In `s`:
- `chatShell`: remove `border`, `borderRadius`, `background` and `boxShadow`; keep `display`, `flexDirection`, `flex`, `maxHeight` and `overflow`. Add `borderRadius: 20` back (inline, because `overflow: 'clip'` needs it).
- Delete `chatToolbar`. The header is the `iv-chat-head` class.
- `messages`: padding `'26px 28px'`, gap `18`.
- `bubble`: keep `position: 'relative'`, `maxWidth: '78%'`, `padding: '10px 14px'`, `borderRadius: 14`, `fontSize: 14.5`, `lineHeight: 1.55`, `whiteSpace: 'pre-wrap'`. The classes in `interviewCss.ts` restyle these with `!important`; or move the values here and drop the `!important`s.
- `bubbleUser`: `{ alignSelf: 'flex-end' }`.
- `bubbleAssistant`: `{ alignSelf: 'flex-start' }`.
- `privacyNotice`: `{ fontSize: 12, fontWeight: 400, color: MUTED_TEXT, padding: '4px 28px 14px', margin: 0 }`.
- `chatForm`: padding `'14px 20px 6px 28px'`.

In `ChatScreen`, the shell and toolbar become:
```tsx
      <div className="iv-chat" style={s.chatShell}>
        <div className="iv-chat-head">
          <InterviewerMark />
          <div style={{ flex: 1, minWidth: 0 }}>
            <p className="iv-who">{t.interviewerName}</p>
            <div style={s.chatToolbarHints}>
              <p id={BUILD_HINT_ID} style={s.chatToolbarHint}>{toolbarHint}</p>
              {/* Hidden (to screen readers too): they only hold the toolbar's height. */}
              {allToolbarHints(language).filter(hint => hint !== toolbarHint).map(hint => (
                <p key={hint} style={{ ...s.chatToolbarHint, ...s.chatToolbarHintSpacer }}>{hint}</p>
              ))}
            </div>
          </div>
        </div>
```
Change `chatToolbarHint` to `fontSize: 13.5, fontWeight: 400, lineHeight: 1.45`.

On every message `<div>` (the opening typing bubble and the mapped ones), add `className={m.role === 'user' ? 'iv-msg-me' : 'iv-msg-ai'}`. The opening typing bubble always gets `className="iv-msg-ai"`.

Keep the speaker labels, the typing views, `bubbleView`, the error alerts, the composer, the Build bar and all effects exactly as they are.

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/pages/Interview.test.tsx src/lib`
Expected: PASS (all existing chat, error and guard tests included).

- [ ] **Step 5: Quick browser check of the no-shift guarantee before committing**

With Vite on 5182 and the stub:
- measure `#interview-build-hint`'s parent height and the Build button's `getBoundingClientRect().top`;
- for `fresh` (Start, then after the greeting, then after one answer) and `long`;
- in `en` and `nl`;
- at 1280×900 and 640×450.

Expected: the height and top are identical across states within each size and language. If not, fix before committing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Interview.tsx frontend/src/pages/Interview.test.tsx
git commit -m "feat(interview): chat in the redesign, with a quiet interviewer mark"
```

---

### Task 5: The playbook page uses `LearnerPlaybook`

**Files:**
- Modify: `frontend/src/pages/Interview.tsx`: imports and the `state?.playbook` branch
- Test: `frontend/src/pages/Interview.test.tsx`

**Interfaces:**
- Consumes: `LearnerPlaybook` (Task 2), `iv-sheet-wide` and `iv-pb-head` (Task 3).

- [ ] **Step 1: Write the failing test**

Add:
```tsx
describe('Interview: the playbook', () => {
  const shared = {
    where_you_are_today: 'Intro.\n\n- One.\n- Two.',
    use_cases: [{ rank: 1, start_here: true, name: 'Draft the supplier emails', pain_it_kills: 'Five emails', in_practice: 'Prompt.', before: 'B.', after: 'A.', impact: 'I.', difficulty: 'Quick Win' as const, systems_involved: ['Outlook'], assumption_to_check: null, cross_functional: false }],
    next_moves: [{ order: 1, move: 'Try it Monday', why_now: 'Low risk.', linked_use_case: 1 }],
    reframes: [],
    do_this_today: { action: 'Paste the list into Copilot.', time_required: '10 minutes', why_this_one: 'No approval.' },
  }

  it('opens on the page heading, then Do this today, in the interview language', async () => {
    api.getInterviewState.mockResolvedValue({ status: 'complete', playbook: shared, language: 'nl' })
    renderPage()
    expect(await screen.findByRole('heading', { level: 1, name: NL.playbookHeading })).toBeTruthy()
    expect(screen.getAllByRole('heading', { level: 2 })[0].textContent).toBe('Doe dit vandaag')
    expect(screen.getByText('Paste the list into Copilot.')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/pages/Interview.test.tsx -t "the playbook"`
Expected: FAIL. The current page renders `Playbook`, whose first h2 is "Waar u vandaag staat".

- [ ] **Step 3: Swap the component on the page**

Replace `import Playbook from '../components/interview/Playbook'` with `import LearnerPlaybook from '../components/interview/LearnerPlaybook'`. The branch becomes:
```tsx
        ) : state?.playbook ? (
          // The heading lives here, not in the playbook component. The admin card keeps its own
          // Playbook (components/interview/Playbook.tsx); this page renders the learner's.
          <div className="iv-sheet iv-sheet-wide">
            <header className="iv-pb-head">
              <h1 id={PLAYBOOK_HEADING_ID} tabIndex={-1} className="iv-h1" style={s.focusTarget}>{t.playbookHeading}</h1>
              <p>{t.playbookIntro}</p>
            </header>
            <LearnerPlaybook shared={state.playbook} language={language} />
          </div>
        ) : (
```
Then delete `s.heading` and `s.body` if they are unused now (grep first).

- [ ] **Step 4: Run all frontend tests and checks**

Run: `npm run typecheck && npm run lint && npm test && npm run build`
Expected: all green.

- [ ] **Step 5: Confirm the admin screens are untouched**

Run:
```bash
git diff --name-only origin/main -- frontend/src/components/interview/Playbook.tsx frontend/src/components/interview/Playbook.test.tsx frontend/src/pages/admin2 frontend/src/components/AppNav.tsx frontend/src/components/Spinner.tsx frontend/src/lib/useChat.ts frontend/src/index.css
```
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Interview.tsx frontend/src/pages/Interview.test.tsx
git commit -m "feat(interview): the playbook page renders the redesigned learner playbook"
```

---

### Task 6: Browser verification, "after" screenshots, PR

**Files:**
- No code changes, unless a check fails: then fix in the file the check points to, re-run Task 5 Step 4, and commit as `fix(interview): ...`.

- [ ] **Step 1: Run the stubbed browser pass**

Vite on 5182, the stub loaded. Check at 1920×1080, 1280×900, 1024×640 and 640×450, both languages:
- **welcome:** the picker's arrow keys work; Start is visible at 1280×900 without scrolling;
- **chat:** for `fresh`, `resume`, `long`, `chatfail` and `openfail`, the hint height and Build top are constant across states; the Dutch errors are localised; the live region has `lang`;
- **building:** for `buildslow`, the heading takes focus; the dot moves, and stands still under `prefers-reduced-motion: reduce` (`page.emulateMedia({ reducedMotion: 'reduce' })`);
- **playbook:** for `done`, Do this today comes first; "Show details" toggles; the "For" links jump to their card; three cards across at 1280, two at 1024, one at 640;
- **all screens:** no sideways scrolling.

Review Focus 5: override the stub's playbook for one run with a 40-character unbroken system name and a long Dutch compound in a use-case name (`page.addInitScript` after the stub, patching `window.fetch` for `/api/interview/me`). Expected: no sideways scrolling at 640×450.

- [ ] **Step 2: Take the "after" screenshots**

Capture the same set as Task 0 Step 3 into `Learnings/2026-10 Interviewer redesign - before and after/after/`.

- [ ] **Step 3: Stop Vite**

Stop the background task, then check port 5182 with `Get-NetTCPConnection -LocalPort 5182 -State Listen`. If it's still listening, confirm the PID's command line is this worktree's vite, then `Stop-Process`.

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin HEAD
gh pr create --base main --title "feat(interview): redesign the learner screens (direction D)" --body-file <body>
```
The body covers:
- what changed per screen;
- that the admin card is untouched (list the Task 5 Step 5 command and its empty output);
- the new strings in EN and NL;
- the parser copied byte-for-byte from the bullets branch;
- the verification results with the numbers;
- the before/after folder;
- the risk: learner-facing UI only, no backend, no prompt;
- the Claude Code attribution line.

- [ ] **Step 5: Wait for CI, read the Claude review, then stop**

Both required checks must be green. Fix real findings; don't merge. Report to Aaron with the PR link, the review result and the before/after folder. **Stop before merge and deploy.**

---

## Notes for Aaron (not tasks)

- **The bullets branch doesn't block this anymore.** The admin card keeps `Playbook.tsx`, and this PR never edits it, so the only file the two branches share is `lib/playbookSummary.ts`, added byte-for-byte identical. The bullets branch's own edit to `Playbook.tsx` then changes only the admin card. That is that stream's call, not part of this one.
- **Live playbooks show their summary as one paragraph until the bullets prompt ships.** The bullets prompt is not live, so today's playbooks have no "- " lines. The redesign handles that: the summary shows as the lead paragraph only.
- **The needs-assessment screen loses its label too**, for consistency with your call on the welcome screen.
- **The arrow is gone from the Start and assessment buttons**, as in the mockup.
