# Participant inline detail (replace slide-out panel) — design

**Date:** 2026-07-23
**Status:** approved, implementing

## Problem

On the admin project page (`/admin` → a project → Participants table), clicking
a participant's name opens their details (assessment results, maturity level,
track assignment) in a fixed-position slide-out panel anchored to the right
edge of the screen, overlaying the table. This is disorienting: the panel
covers other rows, and its content sits in the same table's context but reads
as a disconnected overlay.

Desired behaviour instead: clicking a name expands their details **inline,
directly under that participant's row**, pushing the rows below it down —
an accordion, not an overlay. This is the same mechanic already used elsewhere
on this exact table for the "reset link" row that appears under a participant
after clicking "reset link".

## Behaviour

- Clicking a participant's name toggles an inline expansion directly beneath
  their row, spanning the full width of the table (not the narrow ~560px width
  the old panel used).
- **Accordion, not independent toggles:** only one participant's details can be
  expanded at a time. Clicking a different participant's name collapses
  whichever row was open and expands the new one (fetching that participant's
  survey data as today). Clicking the currently-expanded participant's name
  again collapses it.
- A chevron next to the name (▼ expanded / ▶ collapsed) shows expansion state.
  There is no separate close/× button — clicking the name (or its chevron)
  again is the only way to collapse, mirroring the existing track/module
  expanders already inside this same content (see below).
- The content itself is unchanged: Assessment results, the Maturity level box
  (pin dropdown), and Track assignment (with its own existing nested
  track → module → lesson expanders and bulk-assign buttons). None of that
  internal behaviour changes — only where and how the whole block is shown.

## Implementation

### `Admin.tsx` (state owner — unchanged responsibilities, per its documented
"god component" role for this page)

- `openUserPanel(user)` becomes a toggle: if `panelUserId === user.id`, collapse
  (`setPanelUserId(null)`); otherwise proceed with the existing fetch flow
  (`setPanelUserId(user.id)` + `GET /api/admin/surveys/{user_id}`), which
  naturally replaces whichever user was previously expanded (accordion).
- Stop rendering `<UserPanel>` as a fixed overlay sibling of `<main>`. Instead
  pass the same state (`panelUserId`, `panelUserData`, `panelSurvey`,
  `loadingPanel`, `learningUser`, `tracks`, `learningData`, `togglingItem`,
  `savingMaturity`) and handlers (`onToggleLearning`, `onBulkAssign`,
  `onSetMaturity`) down into `ProjectDetailView` as a new grouped prop (e.g.
  `panel: {...}`), alongside the existing `participants` / `componentAccess`
  prop groups.
- No other Admin.tsx behaviour changes.

### `ProjectDetailView.tsx`

- Name cell: add a chevron (▼/▶) next to the name button reflecting whether
  this row is the expanded one.
- Rename the click handler prop from `onOpenUserPanel` to `onToggleUserPanel`
  (same signature, now toggle semantics live in `Admin.tsx`).
- Reuse the existing inline-expansion mechanic already used for the reset-link
  row (`React.Fragment` wrapping the `<tr>` + a conditional second
  `<tr><td colSpan={7}>`): add a second conditional row, shown when
  `panel.expandedUserId === u.id`, rendering the detail content (see below).
  This sits alongside the existing reset-link conditional row in the same
  fragment — both can be open at once if triggered independently, matching
  today's independent reset-link behavior.
- No fixed-width wrapper: the `<td colSpan={7}>` content uses the table's full
  width, per the "full width, not narrow" direction.

### `UserPanel.tsx` → renamed `ParticipantDetail.tsx`

- Drop the overlay/backdrop wrapper (`panelOverlay`, `panel`) and the header
  (name/email/close button) — the name and email are already visible in the
  table row above, so repeating them would be redundant, and there's no close
  button per the "chevron/name-click only" decision.
- Keep the three content sections exactly as they are today (Assessment
  results, Maturity level box, Track assignment with its nested
  `expandedTracks`/`expandedModules` accordions and bulk-assign buttons) —
  same props, same internal logic, just rendered directly instead of inside
  panel chrome.

### `adminStyles.ts`

- Retire the panel-chrome-only styles (`panelOverlay`, `panel`, `panelHeader`,
  `panelClose`, `panelName`, `panelMeta`) since nothing references them after
  the rename above.
- Keep `panelBody`, `panelSection`, `panelSectionTitle`, `noSurvey`, `select`,
  `toggleAssigned`, `toggleUnassigned`, `toggleBusy`, `moduleList`,
  `moduleItem`, `moduleTitle`, `surveyQLabel` — all still used by
  `ParticipantDetail.tsx`.
- Add a style for the new inline container `<td>` (padding + a bottom border,
  following the same visual treatment as the existing reset-link row's cell).

## Out of scope / non-goals

- No change to the Assessment results / Maturity level / Track assignment
  internal layout or logic — only their container changes (inline vs.
  overlay).
- No backend/API changes — this is presentation-only.
- No change to the independent reset-link row behavior.
