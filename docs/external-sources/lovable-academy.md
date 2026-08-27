# Lovable Academy & Official Video Library
**Source:** https://academy.lovable.app/academy, https://lovable.dev/videos, https://lovable.dev/videos/tutorial
**Scraped:** 2026-07-09

**Access note:** The Academy's structured 11-lesson path (`/academy/learning-path/lessons`) is a client-rendered app gated behind Google/email sign-in ("Checking your account..." / "Continue with Google") — individual lesson titles and in-lesson instructional text are not exposed to an unauthenticated fetch. Everything below the app's own shell (nav, hero copy, and the live embedded preview of the app being built) is genuinely all that is visible without logging in and clicking through lesson-by-lesson. Where lesson content couldn't be retrieved directly, this doc states that explicitly and instead documents the target app's full feature set (pulled from the matching public "Upvote" template listing), which is the closest available proxy for what the 11 lessons must cover, in build order.

---

## Academy Hub
**URL:** https://academy.lovable.app/academy
**Description:** Lovable's official learning hub — "Learn to build with AI." Landing page organized into three nav groups: **Learn** (Get started, Learning paths, Learn to prompt, Video catalog), **Build** (Templates, Build inspiration), **Reference** (Go deeper, Docs, Community).
**Structure on the hub page:**
- Hero → "Explore the learning paths" (links to Learning Paths)
- "Learn the basics" → Learning Paths
- "Browse videos" → Video catalog
- "Browse templates" → Templates
- "Read the guide" → Learn to Prompt
- Persona strip (Founders, Marketers, Engineers, Designers, Educators, Students shown; "See all 14 personas" → Build Inspiration)
- Templates preview: Inspo Canvas, DeskFlow, Obsidian, SmartRoute, Maison, Dealflow
- "Explore advanced topics" → Go Deeper

---

## Learning Paths — hub
**URL:** https://academy.lovable.app/academy/learning-path
**Description:** Presents the two ways to go from a blank prompt to a live, working product.
1. **Structured Path** (fixed curriculum) — "Build this board, step by step."
2. **Blueprint** (dynamic, idea-based) — turns the user's own idea into a custom chain of prompts.

Both require sign-in to save progress; no prerequisites or objectives are stated on this overview page.

---

## Structured Path: "Build Your First App" (11 lessons — Upvote board)
**URL:** https://academy.lovable.app/academy/learning-path/lessons
**Description:** "The structured path is 11 short lessons that take you from a blank prompt to a deployed feature request board — everything you need to learn Lovable by doing." Estimated duration: ~1 hour.
**Learning objectives (as stated/implied):** Take a user from a blank prompt to a live, deployed app; explicitly said to cover **authentication, databases, and AI** as core concepts along the way.
**Prerequisites:** None stated. Free sign-in (Google or email) required to start/save progress; no coding background implied or required.
**What the finished app is:** "Upvote" — a feature request / voting board, live at `upvote.lovable.app`, embedded in the lesson page as a running preview the learner builds toward. Visible finished-state UI: a submit-idea flow, a "Most Voted" sorted list, vote counts (e.g., 128 / 94 / 61 / 47), status labels (Planned / In Progress / New), and category tags (UI/UX, Integrations, Data).
**Lesson-by-lesson titles:** Not retrievable without an authenticated session — the lesson list itself only renders after sign-in. **Inferred build scope**, cross-referenced against the public Upvote template spec (which documents the full feature set this path builds toward) and the "authentication, databases, and AI" framing, in the order the finished feature set implies:
- Starting from a blank prompt / first generation (the app shell)
- Building the idea-submission form (title, description, category)
- Wiring up a database/backend to persist requests (Lovable Cloud)
- Building the upvote/downvote mechanism and vote-based sorting ("Most Voted")
- Adding status (New → Under Review → Planned → In Progress → Shipped) and category tagging/filtering
- Adding authentication (Google OAuth + email/password, per the template spec) and role-based access (admin / moderator / user)
- Adding comments/discussion on requests
- Search, sort, and filter UI
- Responsive design / branding pass
- Deploying the finished board to a live URL
- (11th lesson likely a wrap-up/what's-next, consistent with other Lovable/Anthropic course conclusions)

This is a best-effort reconstruction from the visible target-state artifact, not a scrape of the actual lesson text — flagged here so it isn't mistaken for confirmed titles.

---

## Blueprint (dynamic path)
**URL:** https://academy.lovable.app/academy/learning-path/blueprint
**Description:** The alternative to the fixed structured path. User provides their own idea, goal, or PRD; the system asks clarifying questions, then generates "an ordered chain of paste-ready Lovable prompts, with plain-language lessons dropped in at the moments they actually matter" plus a checkpoint at each step to verify completion before moving on.
**Key framing:** "It's not a fixed course. Every prompt, lesson, and checkpoint is generated from your idea — so you learn exactly what you need to ship it." Progress saves to the user's account across devices.
**Prerequisites:** A starting idea/goal/PRD; sign-in to save progress.

---

## Learn to Prompt (guide)
**URL:** https://academy.lovable.app/academy/prompting
**Description:** "Five principles that separate great results from frustrating ones. The single most valuable thing you can learn before your first build."
**Curriculum (5 principles):**
1. **Know what you're building before you build it** — plan before prompting; Lovable's speed can tempt you to skip the thinking step.
2. **Build one piece at a time** — treat it like Lego: a working foundation, then one brick at a time, rather than describing the whole app at once.
3. **Say exactly what you want, and what you don't** — tell Lovable what to build, where, and what to leave alone, to avoid unintended edits elsewhere.
4. **Use the right tool for the job** — Plan mode (strategic thinking), Agent mode (development work), Visual Edits (refinements); picking the right one avoids wasted credits.
5. **Think in iterations, not in one shot** — "you are not trying to write the perfect prompt, you are managing a build"; each change is a foundation for the next.

---

## Video Catalog (in-Academy)
**URL:** https://academy.lovable.app/academy/video-catalog
**Description:** Short in-Academy videos organized into two tiers by length/depth.
**Structure:**
- **Feature Spotlights** (2–4 min each): Intro to Lovable (platform orientation), Lovable Cloud (backend/database/auth), Lovable AI (AI feature integration), Design, Debugging, SEO optimization, Plan mode, Reverts, Publishing, Custom knowledge, Prompt queueing, Security infrastructure, Skills, Exec Tools.
- **Deep Dives** (24–45 min each): "Master Lovable in 24 minutes" (full platform walkthrough), "How vibecoding actually works" (technical foundations), "Build an AI Discord mod in 45 minutes" (practical project build), agent-update/advanced-feature walkthroughs.

---

## Templates
**URL:** https://academy.lovable.app/academy/templates
**Description:** "Start from a working app and make it yours. Every template is remixable."
**Featured templates:** Inspo Canvas, DeskFlow, Obsidian, SmartRoute, Maison, Dealflow (full catalog is larger; "View all" browses the complete set). The Upvote template used as the structured-path target app is a separate, related template: see https://lovable.dev/templates/apps/product-management/upvote-feature-request-voting-board-template — full feature spec: submit idea (title/description/category), upvote/downvote with real-time counts driving default sort, five-stage status (new → under review → planned → in progress → shipped) settable by admins, comments (authors can delete their own), search by title, sort by votes/newest, filter by category with one-click reset, three roles (admin/moderator/user), Google OAuth + email/password auth with verification, user profiles, responsive design, customizable branding via CSS variables/Tailwind tokens, real-time updates, deploy-ready hosting.

---

## Build Inspiration (14 personas)
**URL:** https://academy.lovable.app/academy/what-to-build
**Description:** Role-specific "what should I build" guidance, one framing line + example apps per persona.
**Personas:**
1. Founders — "I'm launching something new" (CRM trackers, proposal generators, expense tracking)
2. Marketers — "I'm growing an audience" (campaign briefs, content calendars, social schedulers)
3. Engineers — "I'm shipping software" (incident trackers, API doc viewers, dependency monitors)
4. Designers — "I'm crafting experiences" (color palette explorers, design review systems, accessibility checkers)
5. Salespeople — "I'm closing deals" (pipeline trackers, proposal generators, lead scoring)
6. Product Managers — "I'm shaping the roadmap" (roadmap viewers, prioritization matrices, feature request boards)
7. Operators — "I'm running the business" (inventory management, approval workflows)
8. Educators — "I'm teaching others" (course builders, quiz tools, lesson planners)
9. Students — "I'm learning and growing" (flashcard apps, note-taking tools, exam prep builders)
10. Project Managers — "I'm keeping things on track" (Kanban boards, Gantt charts, time tracking)
11. HR Teams — "I'm building the team" (onboarding portals, performance trackers, applicant tracking)
12. Community Builders — "I'm bringing people together" (member directories, event calendars, discussion forums)
13. Nonprofits — "I'm making an impact" (donation trackers, volunteer management, grant applications)
14. Media & Publishers — "I'm telling stories" (news aggregators, editorial CMS, newsletter builders)

---

## Go Deeper (Advanced Topics)
**URL:** https://academy.lovable.app/academy/go-deeper
**Description:** "Auth, payments, custom domains, and everything else you need to ship a real product." Each topic links out to the corresponding docs.lovable.dev page.
**Topics:**
1. **Use Lovable Cloud** — backend services, database, storage, edge functions for server-side logic.
2. **Add Authentication** — signup/login, OAuth (Google, GitHub), protected routes, pre-wired.
3. **Integrate Stripe** — payments, subscriptions, customer portals.
4. **Add AI to Your App** — chat interfaces, content generation, LLM-powered features.
5. **Design Your App** — design tool, responsive layouts, component library.
6. **Use Knowledge Files** — custom project context (brand guidelines, API specs, domain knowledge).
7. **Deploy with a Custom Domain** — DNS, go-live in minutes.
8. **Sync with GitHub** — version control, push/pull, team collaboration.

---

## Supplementary: "From Idea to Working App" (official docs guide)
**URL:** https://docs.lovable.dev/tips-tricks/from-idea-to-app
**Description:** Not part of the Academy proper, but the closest official "how to actually get started" narrative guide — addresses builders stuck between inspiration and execution.
**Curriculum (best-practices list):**
1. Start outside Lovable — shape the idea externally first (voice notes, AI brainstorming).
2. Write it out first — spend 15 minutes documenting what the product does, its users, minimum viable features.
3. Choose a build style — frontend-first (beginners) vs. back-to-front (advanced).
4. Use Plan Mode — project-aware assistant for debugging, brainstorming, planning before generating.
5. Break into bricks — divide the project into individual features, build/test sequentially.
6. Prompt with purpose — maintain clear intent across the conversation.
7. Avoid error loops — use dev tools and Plan mode instead of repeated blind fix attempts.
8. Remix when needed — clone the project when complexity becomes unmanageable.
9. Validate quickly — test prototypes with real users early.
10. Build bad ideas — throwaway projects specifically to build a skill.
Ends with a "Builder's Checklist" and encouragement that no coding knowledge is required given proper planning.

---

## Lovable Official Video Library
**URLs:** https://lovable.dev/videos, https://lovable.dev/videos/tutorial
**Description:** Lovable's public video catalog (350+ videos per the site) — largely third-party/YouTube creator content curated by Lovable, plus some in-house founder/product content, rather than a structured course. No numbered lesson sequence; organized by filterable tags, not modules.
**Filter tags available (identical set on both URLs):** All, 21st dev, Anton Osika, Community, Highlights, Livestreams, Reviews, Tutorials, ai app builder, ai image generator, ai website builder, anthropic, bolt ai, bolt new, builder.io, clerk, community, cursor ai, d3, deploy, elevenlabs, figma, figma ai, github, lemon squeezy, make, mapbox, n8n, notion, openai, p5, postgres, product hunt, replicate, replit, resend, squarespace, stability, stripe, supabase, tailwind, threejs, tutorial, twilio, vercel, vibe coding, webflow, website builder, wix, zapier.

**Representative titles by topic cluster (topic = inferred from tags, not an official category label):**
- **Website building/redesign:** "Can AI Fix the Worst Website in 8 Minutes?"; "Found the WORST Site & Rebuilt It in 15 Minutes with AI"; "Found the UGLIEST Site & Rebuilt It in 10 Minutes with AI!"
- **App-building fundamentals / first app:** "Anyone Can Create An App! UX/UI/Dev With AI"; "Build Web Apps with AI—No Coding Required! Full Lovable Tutorial"; "How I Built an App with Lovable in Under 1 Hour (2025 Tutorial)"; "Build an AI App with an AI Agent | Complete Beginner"; "Build an AI-Powered Web App in 20 Minutes—No Code Required"
- **AI-powered SaaS builds:** "Building a No Code STARTUP with AI in 1 Hour! (DeepSearch + Lovable)"; "How to Build an AI-Powered SaaS With Lovable (Step-by-Step)"; "How to Build a $1m AI Web app (Lovable + Stripe)"
- **Supabase / backend & database:** "How to Connect Your Lovable App to Supabase – Quick & Easy!"; "How to Store & Manage Data in Supabase – Full Guide!"; "From Zero to Backend – Supabase Introduction & Setup Guide"
- **Authentication:** "How to Add Authentication in Supabase – Step-by-Step Guide!"; "Master Clerk Authentication: Custom Domains, Waitlists & Secure User..."
- **Payments (Stripe):** "How to QUICKLY Add Stripe Payments to Your Apps (Lovable AI)"; "Tutorial: Add payment checkout to Lovable apps"
- **Automation/agentic workflows (n8n):** "Build a Complete AI SaaS with zero code (Lovable + N8N)"; "I Built a FULL Web App with n8n, Lovable & Supabase (NO CODE!)"; "Tutorial: Build agentic apps with Lovable + n8n"
- **Design-to-code (Figma):** "Brand NEW Lovable x Figma Integration (Build Amazing UI)"; "From Figma to Full-Stack App – Lovable x Builder.io!"; "Turn Figma designs into full stack apps with AI"
- **Specialized project builds:** "Build a STUNNING Portfolio Website From Scratch with AI"; "Build a Nomad List Clone with Google Sheets – No Code Needed!"; "Build Your First AI Game With ZERO Coding"; "I Built A Duolingo Clone In Just 33 Minutes with LOVABLE AI"
- **Voice/AI agents:** "Can you really create AI voice agents just by talking?"; "How I Built JARVIS with No Code (Lovable, ElevenLabs, n8n)"; "I Built An App Using JUST MY VOICE (Lovable AI + Aqua Voice)"
- **Comparative/tool-evaluation:** "I Chose the BEST! Bolt x V0 x Lovable x Tempolabs Comparison 2025"; "I Tested Bolt and Lovable Here's What's Best for Your Project"; "Lovable: The AI Coding Revolution - Is It the Best Cursor Alternative?"
- **Multi-part educational series (closest thing to a course in this library):** "FULL FREE Lovable Dev Course 1: Why Lovable?" (implies a numbered multi-video series, not confirmed how many parts); "Vibe Coding FULL COURSE For Beginners [In 1 Hour]"; "Vibe Coding on Lovable AI for Absolute Beginners"
- **Non-English:** French ("Comment créer un SaaS de A à Z sans coder"), Portuguese ("Como criar aplicativos completos com Lovable"), Spanish ("Crea productos digitales en minutos con Lovable.dev")
- **Company/founder content:** "Anton Osika, Co-Founder and CEO @ Lovable" (retention metrics); "Building Lovable: $10M ARR in 60 days with 15 people"; "Anton Osika, Co-Founder CEO @ Lovable: Hitting 85% Day 30 Retention"

**Note:** These are overwhelmingly third-party creator videos aggregated by Lovable (YouTube-style tutorial/review content, tagged by tool/integration), not an authored, sequenced Lovable curriculum. The only true first-party sequenced curriculum is the Academy's 11-lesson structured path above.

---

## Comparison to the curriculum's existing 5-lesson Lovable track

The curriculum's Lovable track (Bands 1–3, 5 lessons: "What Lovable is and when to use it" → "Building your first app" → "Iterating on your app" → "Vibecoding" → "Deploying/sharing/connecting to data") **broadly matches the shape** of Lovable's own official on-ramp, but compresses it:

- Lovable's own primary on-ramp is the **11-lesson structured path** (Upvote board), not a 5-lesson one — it's roughly 2x the granularity, breaking "build → iterate → deploy" into many smaller single-concept steps (per-feature lessons: submission form, DB wiring, voting, status/tags, auth, comments, search/filter, deploy), consistent with Lovable's own "Build one piece at a time" prompting principle.
- The curriculum's **"What Lovable is and when to use it"** has no direct 1:1 lesson in the structured path (which jumps straight into building), but is closest in spirit to the Academy hub's framing + the "Learn to Prompt" guide's principle 1 ("know what you're building before you build it").
- The curriculum's **"Building your first app"** and **"Iterating on your app"** map well onto the bulk of the 11 lessons (incremental, piece-by-piece build) and onto the "From Idea to Working App" docs guide's "Break into bricks" / "Prompt with purpose" steps.
- The curriculum's **"Vibecoding"** as a distinct lesson has no exact Academy analog by that name inside the structured path, but the term is used extensively in Lovable's own video library (e.g., "How vibecoding actually works," "Vibe Coding FULL COURSE For Beginners") — so the term and framing are authentically Lovable's own, just surfaced in the video library rather than the Academy path.
- The curriculum's **"Deploying/sharing/connecting to data" capstone** matches the structured path's final stretch closely: the Upvote path explicitly ends in a deployed app and (per the target template) covers backend/database connection, auth, and going live — i.e., Lovable's own sequence also treats "connect data + deploy" as the natural endpoint of the guided build, supporting the curriculum's choice to make that the Band 3 capstone.
- Biggest structural difference: Lovable's official path treats **auth and database wiring as core, first-party steps inside the one guided build** (not a separate "advanced topics" concern), while the curriculum's 5-lesson track only reaches "connecting to data" at the very end. This is worth flagging as a possible reason to review whether the curriculum's auth/database coverage is late relative to Lovable's own sequencing.
- The individual lesson titles/order inside the 11-lesson path could not be confirmed (sign-in gated); the comparison above is based on the confirmed lesson count, stated topic coverage ("authentication, databases, and AI"), and the finished app's full feature spec, not verbatim lesson text.
