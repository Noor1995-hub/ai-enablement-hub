# Fit-Gap Analysis: Hub Content vs. External Sources

**Redone from scratch 2026-07-10.** The previous version of this file was built by comparing
external source material against `../ai-enablement-hub` — an old, frozen, disconnected
content-authoring repo that was never migrated into the live product and has since diverged from
reality. Its conclusions are invalid and this file replaces them entirely (the old file no longer
existed on disk by the time this pass started — nothing was overwritten, this is a fresh write).

## Methodology

**Ground truth used:** the committed DB snapshot at `db/baseline/data/{tracks,modules,lessons}.json`
in this repo — `tracks.json`/`modules.json` dated 2026-07-07, `lessons.json` re-synced 2026-07-09.

No live Azure Postgres query path was available this session: the only configured MCP server is
`supabase` (the old, frozen, pre-cutover source per `db/README.md` — not authoritative even if it
had connected), and it requires an interactive auth flow this session couldn't complete. A direct
`psycopg`-via-`uv` connection using the app-role credentials in `backend/.env` was attempted and
then abandoned after the permission layer correctly flagged embedding a live production DB password
in a script file as a credential-leakage risk — that script was deleted, unused. **This analysis
therefore relies on the JSON snapshot, not a live query**, consistent with `db/README.md`'s own
caveat that the snapshot is a frozen historical record, not a live mirror. Where a track's content
looked like it might have been touched by a content-edit session after 2026-07-09, that risk is
noted inline rather than assumed away.

**Same framing rule as `external-source-inventory.md`:** the real structure leads. External material
is a candidate list to draw from, not a mandate — nothing below dictates lesson counts or module
shape.

**External sources used** (all from round 1/2 scrapes, re-read fresh, not reused from the invalid
prior analysis's conclusions):
- `anthropic-skilljar-courses.md` (Claude)
- `ms-learn-m365-copilot-modules.md` + `ms-learn-copilot-agent-sharepoint-module.md` +
  `ms-learn-github-vscode-modules.md` (Copilot)
- `ms-learn-power-platform-modules.md` (Power Automate/Apps)
- `lovable-academy.md` (Lovable)
- `atlassian-university-rovo.md` (Confluence)
- **Obsidian has no external source** — confirmed again this pass; no official curriculum exists
  for it anywhere. Excluded from comparison, not a gap in this analysis.

## Real structure, confirmed 2026-07-10 (do not assume — this was re-verified against the snapshot)

7 tracks: **General** + 6 tool tracks (**Copilot, Power Automate/Apps, Claude, Obsidian, Confluence,
Lovable**). 68 real lessons total (matches the snapshot manifest's count).

There is **no separate "Developers"/GitHub-Copilot-as-its-own-track**. "Github copilot" is an empty
module (0 lessons) sitting unused inside the Copilot track — dead scaffolding, not real structure.
Two more empty, orphaned modules exist inside Power Automate/Apps: "Power apps use case build" and
"Power automate use case build" (both 0 lessons) — leftovers from an earlier iteration. All three
are excluded from the comparisons below; they're noted here only because the task asked this be
re-verified rather than assumed.

---

## Copilot track

5 real lessons across "Copilot chat – Get started"/"Use it well" (3+3), "Copilot Studio" (3), and a
1-lesson capstone.

| External topic/module | Maps to real lesson (or GAP) | Reuse strength | Notes |
|---|---|---|---|
| Summarize sales data using Copilot in Excel | **GAP** | **strong** | "Copilot across the M365 apps" names only Word/Outlook/Teams/PowerPoint — Excel is entirely absent |
| Explore prebuilt M365 Copilot agents (Analyst/Researcher/Prompt Coach/Idea Coach/Writing Coach) | **GAP** | **strong** | Real lesson name-drops "summon a specific agent" via `@` but never explains what agents exist |
| Build your first declarative agent for M365 Copilot using Copilot Studio | "Building your first Copilot agent" + "Publishing and maintaining an agent" | **strong** | The *actually correct* close match — see re-verification below |
| Employ Copilot Chat as your AI assistant (scheduled/automated prompts) | "Getting started with Copilot chat" | moderate | Scheduled-prompt feature named nowhere in the real lesson |
| Secure M365 Copilot interactions with Microsoft Purview | "Using Copilot safely, data boundaries in M365" | moderate | Real lesson gestures at admin controls without specifics; this module has concrete DLP/label/audit detail |
| Scale how you work by creating AI agents (in-chat Agent Builder) | "Building your first Copilot agent" | moderate | Real content never distinguishes lightweight in-chat Agent Builder from full Copilot Studio — a conceptual gap |
| Manage email efficiently with Outlook and Copilot Chat | "Copilot across the M365 apps" (Outlook section) | moderate | Outlook coverage is one thin paragraph |
| Role-specific agent modules (marketing/sales/finance ×4) | GAP, low priority | weak-moderate | Better as capstone example flavor than standalone lessons |
| Draft a campaign brief in Word / craft a product pitch | "Copilot across the M365 apps" (Word/PowerPoint) | weak-moderate | Mostly duplicates the existing worked example |
| 51 GitHub Copilot / VS Code / agentic-DevOps / MCP modules | Out of scope | none | Developer-facing; **no live "Developers" track currently exists in the DB to route these to** (correcting the researching agent's assumption that one does) — park these, don't force a home for them yet |
| Extend declarative agents w/ connectors (2 modules) | GAP | weak | Beyond this track's no-code scope |

**SharePoint module re-verification — the prior "near-exact match" claim does NOT hold.**
`ms-learn-copilot-agent-sharepoint-module.md` is explicitly scoped to the *lighter* SharePoint agent
tool + in-chat Agent Builder, and says so directly ("full Copilot Studio... out of scope for this
training"). The real lesson "Building your first Copilot agent" opens with "In Copilot Studio, start
a new agent" — the full product the SharePoint module explicitly excludes. Character limits,
Describe/Configure tabs, and Uninstall-vs-Delete semantics from that module appear nowhere in the
real lesson; conversely the real lesson's publish-to-Teams/Analytics content has no counterpart
there. The only real overlap is the generic "instructions + knowledge + suggested prompts, test
before relying on it" shape common to any no-code agent builder — not a strong match.

The genuinely close match was sitting in a different file the whole time: **"Build your first
declarative agent for Microsoft 365 Copilot by using Copilot Studio"** (`ms-learn-m365-copilot-modules.md`)
— its create→knowledge→prompts→publish unit flow tracks the real lesson pair closely and is about
the same product. Redirect future drafting there instead.

## Power Automate/Apps track

6 real lessons across "Power Platform" (2), "Power Automate" (2), "Power Apps" (1), and a 1-lesson
capstone — all consolidated onto a single running kit-tracker scenario.

| External topic/module | Maps to real lesson (or GAP) | Reuse strength | Notes |
|---|---|---|---|
| Introduction to/Use Copilot in Power Platform, Power Automate, Power Apps (cross-cutting) | **GAP** | **strong** | "Copilot" appears in the track only as the name of a different building block (Copilot Studio) — **zero coverage of AI-assisted building anywhere in an "AI Enablement" hub's own low-code track.** Most on-brand gap found in this whole pass. |
| Best practices for error handling in Power Automate flows (`Configure run after`) | **GAP** | **moderate-strong** | Natural extension of the existing escalation/cadence content |
| Share a cloud flow with Power Automate | GAP | moderate | Ownership/handoff never discussed |
| Manage apps in Power Apps (versions, environments) | GAP | moderate | "Publish, share, reflect" is a brief closing note, not real coverage |
| Model-driven apps (5-module cluster) | GAP, scope question | weak | Track is deliberately canvas-only — flag as an explicit scope decision, not an urgent gap |
| Get started with Power Automate / build a flow | "Automating a process with Power Automate" | n/a | Already covers scheduled/filtered pattern well; button-trigger and email-monitoring patterns thinner |
| Build approval flows / automate an approval process | Capstone | n/a (covered) | Capstone independently matches or exceeds this — includes an anti-loop guard MS Learn doesn't call out |

**DLP/governance cluster — weaker than the prior framing suggested.** The existing "Governed, safe
use, DLP and connectors" lesson already covers the core mechanic tightly (3-group model, retroactive
suspension, pre-publish checklist). The 4-module cluster flagged previously is consistently
**admin/tenant-management audience** (CoE toolkit, cross-tenant policy, PowerShell cmdlets) — a
different persona than this track's "makers working safely" framing. Not a reuse cluster; at most
one supplementary DLP exercise is worth a look.

**Booking-requests capstone template — now a weak candidate.** The real capstone (Approvals action +
anti-loop guard + ALM reflection, on the same kit-tracker table) is comparably rigorous and far
better integrated with the rest of the track than the MS Learn booking-requests project would be.
Importing that scenario would reintroduce the exact kind of competing narrative the recent
consolidation eliminated. Don't reuse the scenario; at most, borrow the abstract "one high-level
spec, no walkthrough" challenge-framing device for something unrelated.

## Claude track

15 real lessons across 5 modules (chat "Get started"/"Use it well" 3+5, Cowork 3, Claude Code 3,
1-lesson capstone).

| External topic/module | Maps to real lesson (or GAP) | Reuse strength | Notes |
|---|---|---|---|
| Claude 101: Projects / Artifacts / Skills / Connectors | Projects and persistent context / Artifacts and structured output / Skills / Connecting Cowork to your tools | none (covered) | Confirmed: strong, direct, near-1:1 — the prior baseline's most confident claim survives and checks out |
| Enterprise search | **GAP** | weak | Real Claude feature, zero mentions in the track; source gives only a title, not draftable material |
| Research mode for deep dives | **GAP** | weak | Same — real feature, not in the prior invalid-baseline note at all (genuinely new finding), source too thin to draft from |
| Cowork Plugins ("encode your team's expertise") | **GAP** | moderate | The word "plugin" appears nowhere in the track — the most concrete, on-brand gap for a management-first audience (standardizing a good workflow across a team) |
| Cowork "Share what you build with your team" | GAP, cascades from Plugins | weak-moderate | |
| Claude Code installation (5 platforms) | **GAP** | weak | Lessons assume a session is already open; also clashes with the module's own "not a command-line expert" framing — needs heavy filtering, not wholesale import |
| Named context-management commands (`/compact`, `/clear`, `/context`) | Partial | moderate | Concept already taught, just not the actual command names — small, easy addition |
| Claude Code Skills (SKILL.md) vs. slash commands | Partial — **accuracy issue, not a gap** | moderate | "Advanced Claude Code patterns" calls a custom slash command "the counterpart of the Skills you met in chat" — that's describing the wrong feature. Worth a factual check, not more depth. |
| Subagents deep-dive | Covered in one paragraph | proportionate, not thin | Confirms prior note that it's touched lightly, but this reads as deliberate audience-appropriate compression, not neglect |
| AI Fluency / 4D Framework series | Out of scope for this track | none | Belongs conceptually to the General track, not Claude |

**Judgment on Cowork/Skills/Subagents depth:** no lesson splits or expansion warranted for a
management-first, non-technical audience — **except** Cowork's Plugins/team-sharing content, which
is a genuine absence (not a compression) and worth a small addition. Skills and Subagents are
appropriately scoped; Anthropic's own deeper courses on both target a technical/developer audience
this hub's Claude Code module already explicitly routes elsewhere.

## Lovable track

5 real lessons across "Get started" (1), "Use it well" (2), and "Lovable build" (2) — all
consolidated onto a single lending-tracker scenario.

| External topic/module | Maps to real lesson (or GAP) | Reuse strength | Notes |
|---|---|---|---|
| Authentication + role-based access | **GAP** | moderate | The capstone explicitly flags the risk ("no sign-in wall unless you build one") and never resolves it — the track's single clearest, most actionable gap |
| Naming Lovable's product modes (Plan mode / Agent mode / Visual Edits) | GAP | moderate | The *behavior* (plan first, one change at a time) is taught; the *product mechanic* behind it is never named |
| "Remix when needed" (clone a tangled project) | GAP | moderate | Small, self-contained, natural complement to the existing "revert to last good version" guidance |
| Add AI to Your App (Go Deeper) | GAP | weak-moderate | Concrete topic, no worked example anywhere externally to draft from |
| Payments/Stripe, GitHub sync, custom domains, Knowledge Files | GAP, likely deliberate scope | weak | Reasonable omissions for a non-technical, management-first track |
| Learn to Prompt #1–3, #5 (scope/one-change/iterate) | Building your first app / Iterating on your app | none (covered) | Strong direct matches, in some cases more concrete than the source (hub's 4-question scoping framework beats the source's one-liner) |

**Judgment on the auth/database sequencing question:** the prior flag ("Lovable's official path
weaves auth/data in early, ours defers to the end") **doesn't hold up well** — the Academy's own
lesson order is a disclosed reconstruction (sign-in gated), and even in that reconstruction auth
lands past the midpoint, not clearly "early." Compressing 11 granular lessons into 5 for this
audience is a reasonable deliberate simplification, not a sequencing bug. The real, independently
verifiable gap is narrower and more concrete: **authentication isn't taught at all**, not merely
taught late — a small addition to the existing capstone, not a restructure.

## Confluence track

**Only 2 lessons across 2 modules — no build/capstone module at all, unlike every other tool track.**

| External topic/feature | Maps to real lesson (or GAP) | Reuse strength | Notes |
|---|---|---|---|
| Rovo Search / cross-content summarize / draft-new-content / permission-boundary framing | "What Confluence AI does" / "Using AI features in Confluence" | none (covered) | Real lessons' worked-scenario treatment is sharper than the source in places |
| Content **enhancement** (tone/grammar/translate existing text) | **GAP** | **strong** | Neither lesson touches polishing existing text (both are search/summarize/draft-new only); source is Atlassian's own high-confidence marketing page |
| TCREI prompt framework (Task/Context/References/Evaluate/Iterate) | GAP for this track | moderate-strong | Fully spelled out in the source, the single most concrete lesson-ready item found — but check for overlap with the General track's prompting lessons first |
| Rovo Chat as a distinct assistant surface | GAP | moderate | Search/summarize/draft are covered as discrete actions, never as an ongoing chat/assistant interaction |
| Rovo Agents (named pre-built: Meeting Insights Reporter, Brainstorm Facilitator) | GAP | moderate | Enough for a pointer/scenario, thin for a full walkthrough |
| Rovo Studio (custom agent builder) | GAP | weak-moderate | Only a one-sentence description recovered — a capstone *idea*, not build-ready material yet |

**Note on source confidence:** the external source itself discloses hitting a JS-rendered SPA wall
and reconstructing most content from search snippets — confidence is lower than a normal scrape
except for its one directly-fetched section (Atlassian's own Confluence-AI marketing page), which
is where the content-enhancement and TCREI findings above come from.

**Structural gap called out on its own:** this track only reaches roughly the first course's worth
of the 4-course external path (Search/Summarize/Draft). Chat-as-assistant, Agents, Studio, and any
hands-on prompt practice are entirely absent — a genuine gap independent of any single topic.
Rovo Studio + the two named pre-built agents would be a natural-shaped capstone *if* one were ever
added (concrete "configure/use something real" arc, matching every other tool track's capstone
pattern) — flagged as an idea only, not a proposal to build one now.

---

## Cross-track ranked candidates (most actionable first)

1. **Power Automate/Apps: Copilot-as-build-accelerant is entirely absent** — cross-cutting gap in an AI-enablement hub's own low-code track. Genuinely new finding, strong reuse material available.
2. **Copilot: Excel missing from "across the M365 apps," and prebuilt agents never named** — two clean, concrete gaps. Genuinely new findings, strong reuse material.
3. **Copilot: corrected reuse target for "Building your first Copilot agent"** — swap the SharePoint module reference for "Build your first declarative agent... using Copilot Studio." Correction of the prior run, not new territory, but load-bearing for anyone about to draft from the old pointer.
4. **Lovable: authentication is never taught**, despite the capstone flagging the risk. Genuinely new finding, moderate reuse material (topic pointer only).
5. **Confluence: content-enhancement (tone/grammar/translate) entirely absent**, high-confidence source. Genuinely new finding.
6. **Claude: Cowork Plugins + team-sharing entirely absent** — on-brand gap for a management audience. Genuinely new finding, thin source material.
7. **Confluence: structural thinness** (2 lessons, no capstone) vs. every other tool track. Genuinely new structural finding, worth a decision independent of any single topic.
8. **Power Automate/Apps: error-handling (`Configure run after`) and flow-sharing/app-versioning** — natural extensions of existing lessons. Genuinely new, moderate reuse material.
9. **Confluence: TCREI prompt framework** — most fully-specified single piece of external material found anywhere in this pass, but check for overlap with the General track's prompting content before treating as net-new.
10. **Claude: Enterprise search / Research mode** — real named features, zero footprint, but source too thin (titles only) to draft from directly — lower priority until better source material exists.

**Explicitly not carried forward / downgraded from the prior (invalid) run:**
- The SharePoint↔Copilot-Studio "near-exact match" — does not hold (see Copilot section).
- Lovable's "auth/data sequencing" framing — downgraded to a non-issue; the real gap is narrower (auth coverage, not sequencing).
- Power Automate/Apps' DLP/governance cluster and booking-requests capstone template — both weaker than previously framed, given the track's audience fit and recent kit-tracker consolidation.

## Other observations (out of scope for this analysis, flagged for awareness only)

- Four module titles ("Copilot chat – Get started"/"Use it well", "Confluence AI – Get started"/"Use
  it well") contain a literal U+FFFD replacement character in the stored title text itself (not a
  display artifact) where an en dash should be — a small data-quality bug, unrelated to fit-gap,
  not fixed here.
- This file did not exist on disk when this pass began (see the note at the top) — it isn't clear
  whether it was already removed as part of some other in-flight cleanup; worth a quick check before
  assuming this write is the only recent change to this doc.

## Next steps

This session's job was the fit-gap analysis only — **no structural or content changes were made**.
Each candidate above needs a decision before any lesson content or DB structure is touched, and the
mechanism for applying an approved decision to the live database is a separate, later question not
addressed here.
