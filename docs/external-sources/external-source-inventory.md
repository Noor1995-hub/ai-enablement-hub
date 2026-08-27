# External Source Inventory
**Date:** 2026-07-09
**Purpose:** A checklist of external training content scraped for competitive/reference awareness while writing the tool tracks. Companion to `internal-source-inventory.md` (which mines internal content, lives in the separate `ai-enablement-hub` content-authoring repo at `Tool Tracks/specs/internal-source-inventory.md` — this file was relocated here to `ai-enablement-hub-rebuild/docs/external-sources/` since that's the active repo) — this one looks outward at what Anthropic and Microsoft Learn already publish on the same topics.

> ⚠️ Same rule as the internal inventory: **`tool-tracks-structure.md` leads.** Nothing here dictates lesson counts or module shape — it's raw material and a sanity check ("are we missing an angle Anthropic/Microsoft already cover well?"), not a source to transplant from. All of it is written for a technical or general-consumer audience, not the external management-first audience this project targets — expect to compress and re-pitch, same as with internal sources.
>
> For the fit-gap analysis built from this material and its current decision status, see `fit-gap-analysis.md` (this folder) and `ai-enablement-hub/Tool Tracks/specs/tool-tracks-enrichment-status.md` (single source of truth).

---

## What was scraped

### `external-sources/anthropic-skilljar-courses.md`
All 20 courses on anthropic.skilljar.com, full curriculum (description, objectives, prerequisites, module/lesson titles) — captured live off the course landing pages, no login required. Most directly relevant to the **Claude track**:
- **Claude 101** — closest analog to our "Claude chat" module (Projects, Artifacts, Skills, Connectors map almost 1:1 to our existing lesson titles)
- **Claude Code 101** / **Claude Code in Action** — feeds our dev-heavy Track 7 Claude Code content; far more granular than our internal 7-lesson version (installation across 5 platforms, CLAUDE.md, subagents, MCP, hooks as separate lessons)
- **Introduction to Claude Cowork** — direct analog to our Claude Cowork module, and notably more detailed (plugins, steering, safety-with-teams)
- **Introduction to agent skills** / **Introduction to subagents** — standalone deep-dives on two features our internal content only touches lightly
- **AI Fluency series** (Framework & Foundations, Educators, Students, Nonprofits, Small Businesses, Builders, Teaching) — a whole parallel "4D Framework" (Delegation/Description/Discernment/Diligence) pitched at non-technical audiences by persona, which is conceptually close to what our own "General track" / "AI first mindset" modules are trying to do
- Remainder (Platform 101, Claude API, MCP intro/advanced, Bedrock, Vertex AI) are developer/API-facing — not relevant to management-first tracks, only to Track 7.

### `external-sources/ms-learn-github-vscode-modules.md`
Microsoft Learn catalog filtered to `products=github,vs-code`. **Correction to an earlier assumption:** the catalog actually returns 231 modules + 49 learning paths for this filter (it's an OR across product tags, not AND) — not the ~60 first estimated from a summarized fetch. Of those:
- **51 modules** relevant to GitHub Copilot / agentic AI / MCP / spec-driven development got full detail (objectives, prerequisites, ordered unit titles) — this is the set worth mining for the **GitHub Copilot track** and Track 7. Highlights: *Foundations of Agentic AI in GitHub*, *Designing Agent Architecture and SDLC Integration*, *Governance, guardrails, and operations*, *Introduction to Copilot Spaces*, *Building applications with GitHub Copilot agent mode*, *Get started with GitHub Copilot* — Microsoft has a noticeably deeper "agentic DevOps" thread than our current 5-lesson GitHub Copilot module structure covers.
- **180 modules** (generic Azure/C#/DevOps/migration/MLOps) — catalog metadata only, out of scope for this curriculum.
- **49 learning paths** — catalog metadata only (title/summary/level), not yet drilled into.

### `external-sources/ms-learn-copilot-agent-sharepoint-module.md`
Single MS Learn module, "Build and manage an agent" (no-code Copilot Chat + SharePoint agents), full unit-by-unit text — the most directly reusable single source found in round 1. Its component breakdown (Name/Icon/Description/Instructions/Knowledge/Capabilities/Suggested prompts) and its testing checklist are good raw material for a **Copilot Studio** or **Copilot chat** lesson on building simple agents.

---

## Round 2 (2026-07-10) — closing the coverage gap

A completeness audit found round 1 only ever covered 2 of the 7 tracks in depth (Claude, GitHub Copilot). Each other track — except Obsidian, which genuinely has no official curriculum anywhere — had a real external source sitting completely untouched. Four more scrapes closed that:

### `external-sources/ms-learn-m365-copilot-modules.md`
MS Learn's actual **Microsoft 365 Copilot** catalog (`product=microsoft-365-copilot`) — 59 modules/17 paths, 24 given full detail. This is the real source for Track 2's M365 chat module (Word/Outlook/Teams/PowerPoint use cases, a strong Purview-based safety match) and upgrades Copilot Studio's source from round 1's single lucky page to MS Learn's own official 5-module "Extend Microsoft 365 Copilot in Copilot Studio" learning path. Also surfaced a cluster of 5 advanced/developer-adjacent Copilot Studio integration modules (grounding, MCP, REST APIs) — flagged as open, not yet adopted, same shape as Track 7's GitHub depth question.

### `external-sources/ms-learn-power-platform-modules.md`
MS Learn's Power Platform catalog, unioned across `power-platform,power-automate,power-apps` — 334 modules/93 paths deduped (confirmed zero duplicates even under a 3-way OR), 75 given full detail. Previously **zero** external source existed for this entire track; now every one of its 6 lessons has 2+ concrete matches, including a near-perfect capstone template ("Challenge Project - Build a booking requests app with Power Apps and Power Automate") and a tight 5-module DLP/governance cluster. Also surfaced "Use Copilot in Power Automate/Apps" (AI-assisted building) as a framing angle not currently in scope — flagged as open.

### `external-sources/atlassian-university-rovo.md`
Atlassian University's Rovo training. Confirms **Rovo** as the current, correct Confluence AI branding (resolves the structure doc's long-standing open verification note) and captures real Confluence-specific feature detail (Rovo Search/Chat/Agents/Studio, two named pre-built agents). Hit a JS-rendered SPA wall on the current learning platform — content was reconstructed from indexed search snippets, not full page fetches; disclosed in the file.

### `external-sources/lovable-academy.md`
Lovable's official Academy — a structured 11-lesson path plus a 350+ video library. The lesson list itself is sign-in gated, so the build sequence was reconstructed from the public template's feature spec, disclosed in the file. Main finding: Lovable's own path weaves auth/database wiring in early, while our 5-lesson track defers "connecting to data" to the very last lesson — flagged as an open sequencing question.

---

## Notes for content generation
- Anthropic's Skilljar courses are noticeably more granular than our internal Claude-track content on Cowork, Skills, and Subagents — worth a second look at whether our proposed lesson counts for those are too thin.
- Microsoft's "agentic DevOps" module cluster (governance, SDLC integration, agent architecture) has no real counterpart in our current GitHub Copilot track — resolved: Track 7 gained one awareness-level lesson + links out, deliberately not matching Microsoft's full depth (see `tool-tracks-enrichment-status.md`).
- Same framing rule as internal sources: strip vendor-specific/certification framing (Skilljar's "Certificate of completion," MS Learn's "Module assessment") when repurposing language — these are marketing/credentialing artifacts, not content structure to copy.
- The generic catalog-metadata-only modules across all MS Learn scrapes (github/vs-code's 180, m365-copilot's 35, power-platform's 259+93 paths) were deliberately left at title/summary depth to keep each scrape tractable — if a specific title looks relevant later, fetch its module page directly rather than re-running the full batch.
- **Round 2 finding:** the round-1 scrape only ever covered 2 of 7 tracks in depth. Before assuming any track is "fully sourced," check `tool-tracks-enrichment-status.md`'s status table rather than this file's original framing — round 2 closed Tracks 2, 3, 5, and 6's gaps (only Obsidian genuinely has no external source anywhere).
