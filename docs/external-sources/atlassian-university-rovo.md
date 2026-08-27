# Atlassian University — Rovo Course Catalog
**Source:** https://university.atlassian.com/student/catalog/list?category_ids=39227-rovo
**Scraped:** 2026-07-09

## Branding verification (resolves open note on the Confluence track spec)

**Confirmed: Rovo is the current, live branding for Atlassian's AI product experience** (as of 2026-07-09). This is not a rename in progress or a rumor — it's shipped and documented across Atlassian's own site.

The relationship between the two names people see referenced ("Atlassian Intelligence" and "Rovo") is **not** old-name/new-name. They are two different layers:

- **Atlassian Intelligence** = the underlying AI *engine/infrastructure* embedded in Jira, Confluence, JSM, etc. (launched May 2024, built in collaboration with OpenAI, uses the Teamwork Graph). It is not something you buy or open separately — it's the plumbing.
- **Rovo** = the branded, user-facing AI *product* built on top of that engine: Search, Chat, Agents, and Studio. Rovo requires Atlassian Intelligence to be enabled to unlock its full feature set (Chat, Agents).
- Rovo was made generally available and free for all Atlassian users starting at Atlassian Team '25 (Anaheim), rolling out to Jira/Confluence/JSM sites April–July 2025 and to Standard-tier customers August–October 2025. By the current date, rollout should be complete for essentially all cloud customers.
- Atlassian's own Confluence AI marketing page is literally titled **"Rovo in Confluence: AI features"** (`atlassian.com/software/confluence/ai`) — confirming Rovo, not "Atlassian Intelligence" or any older name (e.g., there is no more "Confluence AI" or "Smart Editor AI" branding), is the term Atlassian uses when talking about AI *in Confluence specifically*.
- Legacy/parallel course slugs still resolve on Atlassian's learning site (e.g. `get-the-most-out-of-atlassian-intelligence`, `best-practices-for-using-atlassian-intelligence`), which appear to be earlier-named versions of the same courses now live under `...-rovo` slugs — evidence of an internal rename/reorg of the training catalog itself, consistent with the engine-vs-product framing above.

**Action for the Confluence track spec:** replace "AI-features-only" language that hedges on branding with "Rovo" as the primary term, optionally glossing "powered by Atlassian Intelligence" as the underlying tech for accuracy.

## Platform / access note

Atlassian's course platform migrated: the old `university.atlassian.com` URLs now issue a **302 redirect** to `community.atlassian.com/learning` — Atlassian University content has been folded into Atlassian Community's "Learning" hub. Old university.atlassian.com deep links (course/path IDs) still resolve via redirect but land on the new community.atlassian.com equivalent, not always on the exact matching page.

The new `community.atlassian.com/learning/...` course, path, and lesson pages are a **JavaScript-rendered single-page app**. Direct fetching only returns the static shell (top nav, footer, category links) — no course title, description, objectives, or lesson body text renders without executing client-side JS (this held true for every course/path/lesson URL tried, including ones that don't require login). This is a technical rendering barrier, not a login wall — no login prompt was encountered blocking specific content; the pages are simply empty shells to a non-JS fetch.

**Everything below was reconstructed from search-engine-indexed snippets of these pages** (titles, meta descriptions, and cached excerpts), cross-checked across multiple queries per page, rather than from a direct render of the page body. Confidence is noted per item. Nothing below was guessed without a snippet backing it — where detail wasn't recoverable this way, it's marked "not retrieved."

---

## Learning Path: Get the most out of Rovo
**URL:** https://community.atlassian.com/learning/path/get-the-most-out-of-rovo
(Legacy URL, redirects: https://university.atlassian.com/student/path/2207536-get-the-most-out-of-rovo)

**Description:** A set of short, self-paced, free courses that teach how to use Rovo — Atlassian's AI-powered product — to find, learn, and act on information faster across Atlassian and connected third-party apps.

**Learning objectives (reconstructed from course-level snippets, not a single itemized list):**
- Use Rovo Chat to find information and generate content
- Work with Rovo Agents (and create custom ones)
- Use Rovo Search to find information across Atlassian and connected third-party products
- Write effective AI prompts (TCREI framework)
- Generate and enhance content with Rovo across Jira, JSM, and Confluence

**Prerequisites:** None stated. Free; on-demand.

**Curriculum (courses within the path, in the order they were referenced across sources):**
- Get started quickly with Rovo
- Create and enhance content with Rovo
- Get help from Rovo Search, Chat, and Agents (also referenced under the shorter title "Get help from Rovo Chat and Agents" — see note below)
- Best practices for using Rovo

**Tied certification:** Completing the path prepares learners for the free **Rovo Fundamentals** certificate (see below).

**Note on naming inconsistency found in source data:** search results surfaced two different slugs/titles for what appears to be the same course — `get-help-from-rovo-chat-and-agents` ("Get help from Rovo Chat and Agents") and `get-help-from-rovo-search-and-chat` / "Get help from Rovo Search, Chat, and Agents." Likely explanation: the course was renamed/restructured after Search was folded in as covered content, and both old and new indexed snapshots are still surfacing in search. Treating them as the same course below.

---

## Course: Get started quickly with Rovo
**URL:** https://community.atlassian.com/learning/course/get-started-quickly-with-rovo
(Legacy URL, redirects: https://university.atlassian.com/student/path/2207544-get-started-quickly-with-rovo — note: legacy platform modeled this as its own "path," not a course, another artifact of the reorg)

**Description:** A quick-start course to locate and use Rovo Search, Chat, Agents, Studio, and AI features across Atlassian apps and connected third-party platforms. A free 60-minute live/on-demand class version also exists ("Get Started with Rovo AI").

**Learning objectives:**
- Explain how Rovo helps find, learn, and act on information; list Rovo's key features
- Quickly find relevant pages, issues, spaces, and people across Atlassian and connected third-party products using natural-language search
- Explore Rovo's knowledge cards — compact, interactive panels with quick insights and related connections
- Explore Rovo's contextual definitions for unfamiliar terms/acronyms

**Prerequisites:** None stated. Free, no Atlassian account required to start (per catalog listing).

**Curriculum (lessons, in course order per indexed lesson URLs):**
- What is Rovo
- Start navigating Rovo: Search, Chat, and Agents (Rovo powers the Jira/Confluence quick-search bar; Rovo Chat opens via the "Ask Rovo" icon, `/rovo` in the editor, or the app switcher; covers the Rovo browser extension too)
- Learn from Rovo knowledge cards and definitions

(A differently-slugged lesson, "Find information across products with Rovo Search," also surfaced under this course's URL path in search results — likely an earlier or parallel title for the Search-focused lesson content above; not confirmed as a fourth, distinct lesson.)

---

## Course: Create and enhance content with Rovo
**URL:** https://community.atlassian.com/learning/path/get-the-most-out-of-rovo/course/create-and-enhance-content-with-rovo

**Description:** Covers pre-defined Rovo prompts for creating well-structured stories in Jira, keeping Jira Service Management tickets up to date, simplifying task management, formatting work item descriptions, and enhancing/summarizing content. Confluence use is covered specifically for drafting content/blog posts.

**Learning objectives:**
- Generate new content with Rovo (Jira: user stories, summaries, comments; JSM: ticket updates; **Confluence: quickly draft content or blog posts**)
- Enhance existing content (change tone more friendly/formal, improve writing, fix spelling/grammar, translate to another language)
- Restructure work item descriptions for clarity via "Improve description"
- Summarize content

**Prerequisites:** None stated.

**Curriculum (lessons):**
- Generate new content using Rovo
- Enhance your content using Rovo

---

## Course: Get help from Rovo Search, Chat, and Agents
**URL:** https://community.atlassian.com/learning/path/get-the-most-out-of-rovo/course/get-help-from-rovo-chat-and-agents

**Description:** Covers the key elements of successful AI prompts, how to use Rovo Chat to find information and generate content without disrupting workflow, how to work faster with Rovo Agents, and how to create a custom Rovo Agent. Feature availability depends on product subscription.

**Learning objectives:**
- Identify the elements of a successful AI prompt (TCREI framework — see Best Practices course below)
- Use Rovo Chat to find information and generate content
- Work with Rovo Agents via three surfaces: Chat (browsing/starring Agents), Editor (drafting content with Agents integrated into the Confluence/Jira editor), and Automations
- Create a custom Rovo Agent: identify tasks Agents are best suited for, duplicate/modify an existing Agent, or build one from scratch with instructions, conversation starters, and knowledge sources

**Prerequisites:** None stated.

**Curriculum (lessons):**
- Best practices for writing AI prompts
- Get help from Rovo Chat ("Chat with Rovo to get answers quickly")
- Work with Rovo Agents
- Create custom Rovo Agents

---

## Course: Best practices for using Rovo (in Atlassian apps)
**URL:** https://community.atlassian.com/learning/path/get-the-most-out-of-rovo/course/best-practices-for-using-rovo

**Description:** Best practices for prompting Rovo effectively — a shorter, standalone framing of the prompt-writing lesson that also appears inside the "Get help from Rovo Search, Chat, and Agents" course (see naming-inconsistency note above; may be the same underlying lesson surfaced under two course groupings).

**Learning objectives / content confirmed:**
- The **TCREI framework** for prompt writing: **T**ask (define the outcome expected from Rovo, including persona/format), **C**ontext (background info so Rovo understands the scenario), **R**eferences (attachments, links, examples/benchmarks to guide style), **E**valuate (review Rovo's output against your needs), **I**terate (refine with follow-up prompts rather than starting over). Note: TCREI is not Atlassian-original — it's a widely used AI-prompting framework (also taught by Google) that Atlassian has adopted for Rovo training.
- Be specific; break complex requests into smaller tasks; use action verbs ("Create," "Summarize," "Find," "List")
- Don't front-load excessive detail — start basic, add detail iteratively, treat it like a conversation
- Always manually validate AI-generated output; never share personal/confidential/sensitive data in prompts

**Prerequisites:** None stated.

**Curriculum (lessons):**
- Best practices for writing AI prompts

---

## Course: Rovo for software developers
**URL:** https://community.atlassian.com/learning/course/rovo-for-software-developers

**Description:** A quick-start course exploring how software development teams use Rovo Agents and **Rovo Dev** to review code, reduce manual effort during the release process, and accelerate delivery. Not confirmed whether this course sits inside the "Get the most out of Rovo" path or is a standalone/developer-track course — search snippets place it under general Atlassian University Rovo offerings without a clear parent-path link.

**Learning objectives:** Not itemized in retrievable snippets beyond the description above (code review via Rovo Agents; release-process automation; Rovo Dev).

**Prerequisites:** Not stated in retrievable content; likely implies a software/dev-team audience.

**Curriculum:** Lesson-level breakdown not retrieved — no lesson URLs for this course surfaced in search results.

---

## Certification: Rovo Fundamentals
**URL:** https://community.atlassian.com/learning/certifications/rovo-fundamentals

**Description:** Free credential proving the ability to find, learn, and act on information using Rovo's Search, Chat, and Agents across Atlassian and connected third-party apps.

**Requirements:**
- Prep: the "Get the most out of Rovo" learning path (all four courses above)
- Exam: 20 multiple-choice questions, single correct answer each, 45-minute time limit, open-book, free
- Related/adjacent certifications: Jira Essentials, Confluence Essentials, Loom Fundamentals

**Prerequisites:** None explicitly required — positioned for both current and prospective Rovo users.

---

## What Rovo does inside Confluence specifically
**Primary source:** https://www.atlassian.com/software/confluence/ai (page titled "Rovo in Confluence: AI features")
**Secondary source:** https://www.atlassian.com/software/rovo/features (product-wide feature page, cross-checked for Confluence relevance)

This is the most directly reusable material for the 2-lesson, AI-features-only Confluence track. Named features/agents, as stated on Atlassian's own Confluence AI page:

- **Rovo Search** — "Get spot-on results faster with Rovo Search": retrieves answers across the entire connected toolstack from inside Confluence — company policies, project ownership, etc. — not just Confluence content.
- **Rovo Chat** — "Get answers, iterate on work, or catch up on what you missed with Rovo Chat." An AI assistant built into the Confluence UI that uses work context to answer complex questions, summarize pages, help draft content, and find specific information, while respecting existing permissions. Opened via the "Ask Rovo" icon in the nav bar, `/rovo` in the editor, or the app switcher; can run in a side panel or full-screen.
- **Rovo Agents** — pre-built, task-specific AI teammates usable directly in Confluence:
  - **Meeting Insights Reporter** — AI-generated meeting notes; lets users catch up on missed discussion or action items.
  - **Brainstorm Facilitator** — assists/elevates brainstorming sessions.
  - Agents generally: "create, review, and refine content," complete workflow steps, do cleanup tasks, and answer/critique — configurable by end users, not just admins.
- **Studio** — the no-code/low-code builder for creating **custom** agents and automations tailored to a team's specific knowledge or actions (distinct from the pre-built agents above).
- **Content generation** — "Create with AI to turn ideas into share-worthy content, fast" (drafting pages/blog posts from a prompt).
- **Writing enhancement** — polish writing, fix errors, change tone (friendlier/more formal), translate.
- **Inline/contextual definitions** — knowledge cards that surface definitions for team-specific jargon/acronyms encountered while reading.
- **Knowledge cards** (product-wide feature, applies in Confluence search results) — compact interactive panels showing quick insights and related connections for a search query or highlighted term.
- **Content transformation** — converting between formats/artifacts, e.g. "Whiteboards to Live Docs to Jira work items" (cross-product workflow, Confluence is one endpoint).
- **Privacy framing** — Atlassian states Rovo is built with "privacy by design" and respects existing permission boundaries when surfacing search/chat results.

**Positioning statement (from the marketing page):** Rovo's differentiator from generic AI is that it's powered by Atlassian's **Teamwork Graph** — the contextual map of connections across Confluence, Jira, Slack, and other connected enterprise apps — rather than operating on Confluence content in isolation.

**Confluence vs. Jira/other-product distinction:** Atlassian's own feature pages don't sharply partition capability-by-product — Search, Chat, Agents, and Studio are described as the same underlying product surfaced consistently across apps. The Confluence-specific page's distinguishing content is the **use-case framing** (page/blog drafting, meeting notes, brainstorming, knowledge-card definitions for docs) rather than functionally different underlying AI capability. This matters for the curriculum: it's accurate to teach "Rovo Search/Chat/Agents/Studio, applied to Confluence's content workflows" rather than "Confluence has its own separate AI feature set."

---

## Not retrieved / could not confirm

- Full lesson-by-lesson body text for any course — the community.atlassian.com/learning platform is a JS-rendered SPA; direct fetch only returned the site's static navigation shell for every course/path/lesson URL attempted (course landing pages, path landing pages, and individual lesson pages alike). No login wall was hit; this is a rendering limitation, not an access-control one.
- Exact lesson count and titles for "Create and enhance content with Rovo" beyond the two confirmed (there may be more granular lessons, e.g. separate "Improve descriptions" or "Summarize content" lessons, that weren't individually indexed/surfaced by search).
- Full lesson list for "Rovo for software developers."
- Whether "Rovo for software developers" belongs to the "Get the most out of Rovo" path or is fully standalone.
- Exact total duration (minutes) for the learning path or any individual course (only the standalone 60-minute live class, "Get Started with Rovo AI," had a stated duration: https://university.atlassian.com/student/page/2922771-get-started-with-rovo-ai-free-public-class).
- The `enable.atlassian.com` domain (e.g. `https://enable.atlassian.com/student/path/2207536-get-the-most-out-of-rovo`) surfaced in search as another mirror/alias of the same path; not separately fetched since it appears to be the same content under yet another Atlassian sub-domain (partner/enablement-branded instance of the same course platform).

