# MS Learn Module — Build and Manage an Agent (SharePoint / Copilot Chat)
**Source:** https://learn.microsoft.com/en-us/training/modules/build-manage-no-code-copilot-agent-sharepoint/
**Scraped:** 2026-07-09
**Level:** Beginner · **Audience:** Administrator, Business User, Developer, Student · **Units:** 12
**Products:** Microsoft 365, Office 365, Microsoft 365 Copilot, Microsoft 365 Copilot Chat

## Description
This module guides you through the foundational concepts and practical steps required to create, test, and manage agents in Microsoft 365 Copilot Chat and SharePoint.

## Learning objectives
- Identify the differences in the tools used by everyday business users to create agents in SharePoint and Microsoft 365 Copilot Chat.
- Identify the components that make up agents in SharePoint and Microsoft 365 Copilot Chat.
- Create agents in Copilot Chat and SharePoint.
- Create clear, concise, and effective Instructions and Starter Prompts when creating agents.
- Test and edit agents in Copilot Chat and SharePoint.
- Manage agents in Copilot Chat and SharePoint.

## Prerequisites
None.

---

## Unit 1 — Introduction (1 min)
Automation via no-code agents (SharePoint, Copilot Chat) lets non-programmers streamline document approvals, notifications, data entry. Module covers: agent components (Instructions, Knowledge sources, Starter Prompts), creating/managing agents in SharePoint and Copilot Chat, and testing/editing them.

## Unit 2 — Examine the tools used to create agents (3 min)
Two distinct tools:
- **Copilot Chat** → Agent Builder (inside Copilot Studio) — no-code, guided form-based interface. Developers can go further in full Copilot Studio (Actions, data connections, auth flows) — out of scope for this training.
- **SharePoint** → the embedded Copilot agent tool — grounded directly in SharePoint site/library content, inherits SharePoint's own permission model.

Key differences table:
| Feature | SharePoint Copilot agent tool | Agent Builder (Copilot Chat) |
|---|---|---|
| Scope/integration | Tied to the SharePoint site/content it was created from | Broader Microsoft 365 Copilot scenarios, wider knowledge sources |
| Capabilities/customization | Simpler, focused on SharePoint content | More settings: instructions, knowledge, prompts, templates, docs/charts/code, images |
| Management/sharing | Managed in SharePoint, tied to site/library/folder/file | Managed in Agent Builder; use Copilot Studio for advanced publishing |

## Unit 3 — Explore the components of an agent (10 min)
Every agent has: **Name** (≤30 chars, auto-suggested from description if blank), **Icon** (.png, ≤192×192, ≤1MB, transparent bg recommended), **Description** (≤1,000 chars — drives auto-generated Instructions if left blank), **Instructions** (≤8,000 chars, natural language → tool auto-generates the underlying logic), **Knowledge** (sources the agent grounds on), **Capabilities** (Copilot Chat agents only), **Suggested prompts**.

**Knowledge sources**: Web content (toggle depends on org policy — "Allow web search in Copilot"), SharePoint content (file types/limits: .docx/.pdf/.pptx up to 512MB, .doc/.txt/.ppt up to 150MB, .html 150MB; hub sites auto-include associated sites; blocked if Restricted SharePoint Search is enabled), URL entry (max 2 levels deep, modern pages only, no classic .aspx), SharePoint file picker, Microsoft Graph connectors (admin-enabled, e.g. ServiceNow/Salesforce/Confluence/Azure).

**Capabilities** (Copilot Chat only, off by default): **Code Interpreter** (Python-based — charts, docs, code from natural language, no coding needed by the user) and **Image Generator** (built on Microsoft Designer).

**Suggested prompts**: auto-generated from description/instructions/template; fully editable.

## Unit 4 — Create an agent in Copilot Chat, Part 1 (7 min)
Agent Builder = lightweight in-context authoring inside Copilot Chat; can later be upgraded into full Copilot Studio. Start via **New agent** → describe in natural language, **Skip to configure** (manual), or pick a **template**. The **Describe** tab (region/language-dependent) has a conversational flow: Agent Builder proposes name, expanded description, instructions, conversation starters, and capability defaults, then asks clarifying questions (purpose, audience, context, tone, query handling, integrations, fallback behavior). After refining, you can test the draft in the **Agent preview** pane, keep chatting to iterate, or jump to **Configure** to finalize/publish.

## Unit 5 — Create an agent in Copilot Chat, Part 2 (9 min)
The **Configure** tab (synced live with Describe) covers: **Template** (optional, prepopulates fields, resets config if switched later), **Icon**, **Name/Description/Instructions** (validate the AI's interpretation), **Knowledge sources** (web toggle, ≤4 public URLs, embedded files, ≤5 Teams chat URLs, SharePoint files/folders/sites, M365 Copilot connectors), **Capabilities** (Code Interpreter, Image Generator — org policy/licensing dependent), **Suggested prompts**. Finish by testing in the preview pane, then **Create** to publish — triggers a share/open dialog.

## Unit 6 — Exercise: Create a Copilot Chat agent (20 min)
Hands-on lab: define purpose, configure instructions/knowledge sources, test with real prompts. **Requires your own licensed Microsoft 365 Copilot subscription** (not provided by the course). Lab launches externally at microsoftlearning.github.io (MS-4019 course repo, Lab M03).

## Unit 7 — Create an agent in SharePoint (6 min)
Requires **Edit** permission or higher on the site/library. Four entry points: site homepage (**+New → Agent**), document library command bar (**Create an agent**), file context menu (select files → **Create an agent**), or the agent chat pane. Configuration form has three tabs:
- **Overview** — name, description, icon.
- **Sources** — default is "Source from entire site"; can switch to specific document libraries/folders/files via a picker.
- **Behavior** — Welcome message (SharePoint-only feature), up to 3 starter prompts, and natural-language Instructions (unlike Agent Builder, SharePoint's tool does **not** conversationally refine instructions — you edit manually).

Draft vs. live: changes stay in draft until **Save and close**. SharePoint agents lack: templates, Code Interpreter, and Image Generator (by design — focused on content discovery/document workflows, not general-purpose tasks).

## Unit 8 — Exercise: Create a SharePoint agent (20 min)
Hands-on lab: choose a site, configure sources/behavior, test against site content. Same **bring-your-own-subscription** requirement as Unit 6. External lab link (MS-4019, Lab M03).

## Unit 9 — Test and edit your agents (4 min)
Why test: catch issues early, refine instructions, validate UX, optimize performance, gather feedback, ensure compliance. Test both pre- and post-deployment.

Test dimensions: **Instructions** (tone/style, clarity/accuracy, consistency across phrasings, response to new instructions, adaptability, edge cases, user feedback); **Knowledge sources** (integration accuracy, update-then-retest, cross-referencing multiple/hub sites); **Capabilities** (Code Interpreter and Image Generator — simple queries, complex queries, edge cases, user feedback); **Suggested prompts** (default prompt quality, customization, real user interaction).

Editing: same authoring tool used to create (Agent Builder for Copilot Chat, SharePoint's Copilot tool for SharePoint agents). Shared users only see changes after **re-share**. Copilot Chat agents live under **.agent** files in SharePoint (Site Contents → Site Assets → Copilots, or wherever created).

## Unit 10 — Manage your agents (5 min)
Why manage: consistency/reliability, scalability, compliance/security, continuous optimization, resource allocation. Best practices: plan automation deliberately, keep flows simple, document them, review/update regularly.

**Default agent**: every SharePoint site auto-assigns its ready-made agent as default; owners/admins can override via ellipsis → **Set as site default** (always resettable).

**Uninstall vs. Delete** (Copilot Chat): *Uninstall* removes from view but preserves config (useful for temporary removal, troubleshooting, resource decluttering, access control); *Delete* is permanent, for you and anyone you shared it with.

**SharePoint agents**: no separate uninstall concept — delete like any other file via ellipsis → Delete → confirm.

## Unit 11 — Module assessment (6 min)
1. Which combination is required to create a SharePoint agent? → **Edit or higher permissions on the site/library + the Copilot agent tool in SharePoint.**
2. Purpose of the Code Interpreter in a Copilot Chat agent? → **Solves complex tasks using Python code generated from natural language prompts** (user never writes the code).
3. To include external data (e.g., a Fabrikam account) in a no-code agent? → **Microsoft Graph connectors.**

## Unit 12 — Summary (1 min)
Recaps: agent components (Instructions, Knowledge sources, Starter Prompts) → creating/managing agents in SharePoint and Copilot Chat → testing/editing for accuracy and consistency. Positions this as empowering non-technical users to build automation integrated with Microsoft 365 services.
