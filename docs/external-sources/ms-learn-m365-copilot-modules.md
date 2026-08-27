# MS Learn — Modules tagged microsoft-365-copilot

**Source:** https://learn.microsoft.com/en-us/training/browse/?products=microsoft-365-copilot (catalog API: `product=microsoft-365-copilot&type=modules,learningPaths`)

**Scraped:** 2026-07-09

**Total modules found:** 59 | **Learning paths found:** 17

> **Note on scope and methodology:** This curriculum has exactly two tracks this catalog can feed: a "Copilot" track (M365 Copilot chat usage in Word/Outlook/Teams/Excel/PowerPoint, grounding on org data, data-boundary safety) and its "Copilot Studio" sub-module (building declarative/no-code agents). Of the 59 modules, **24** were judged directly relevant — end-user Copilot Chat/agent usage, Copilot Studio agent-building, Copilot-specific governance/security (Purview), or a concrete Copilot-in-app use case — and got full page-level detail (objectives, prerequisites, ordered unit titles) via live fetches. **23** of those 24 were freshly fetched; the 24th, *Build and manage an agent* (SharePoint/Copilot Chat no-code agents), is cross-referenced rather than re-fetched because it's already fully documented in `ms-learn-copilot-agent-sharepoint-module.md` in this same folder. The remaining **35** modules are catalog metadata only — explicitly out of scope per the triage rubric: generic non-AI Outlook UI training (compose mail, manage calendar, organize inbox, customize new Outlook), a parallel "AI business solution architecture" module series aimed at solution architects (ALM, extensibility, requirements analysis, cost/benefit, overall strategy, responsible-AI governance — these share a common product tag set of `microsoft-365-copilot,m365,microsoft-365-copilot-chat,power-platform,microsoft-copilot-studio` and roles like `solution-architect`/`database-administrator`, and read as enterprise architecture content, not end-user or maker tool training), education-vertical modules (special education, multilingual family communication, Agent 365 in education), nonprofit/Surface-for-business modules, and Copilot-Studio "Challenge project" hands-on exercises (listed but lower priority than the core lessons per instructions). The 17 learning paths are listed by title/summary/module-count only — out of scope for page-level expansion.
>
> **Borderline calls, explicitly noted:**
> - *Included as full detail despite a developer/maker/admin framing* — "Introduction to Microsoft AI agent solutions," "Introduction to developing AI agents," and "Choose the best Microsoft 365 Copilot extensibility path for your scenario" are all decision-framework/orientation modules for the "Build a foundation to build AI agents and extend Microsoft 365 Copilot" learning path. They're the closest thing MS Learn has to a Copilot Studio on-ramp ("when do I use Copilot Chat vs. Copilot Studio vs. a fully custom agent?"), so they were kept in scope even though their roles skew developer/maker rather than pure business-user.
> - *Included* — "Explore Microsoft 365 Copilot and agents" and "Craft a compelling product pitch using AI" are borderline: the former is admin/functional-consultant-flavored (licensing, deployment, governance) rather than purely end-user, and the latter spans multiple M365 apps rather than one concrete task. Both were included because they still map cleanly onto "using Copilot as an end user" and "Copilot-in-app use case," respectively.
> - *Excluded despite touching agents/Copilot* — "Integrate your agent with Microsoft 365" (Foundry custom-engine agents published to Teams/Copilot — a different product/track from Copilot Studio's declarative agents), "Orchestrate configuration of prebuilt agents and apps" (Dynamics 365/finance/supply-chain config, part of the excluded solution-architect series despite superficially mentioning "agents"), "Plan your organization's AI skilling journey with Microsoft 365 Copilot" (org change-management/skilling strategy, not hands-on tool usage), "Protect and govern Microsoft 365 data" (generic M365 data governance — Copilot is one of several tagged products but the content isn't Copilot-specific the way the Purview module is), "Drive business value with Microsoft Copilot solutions" (business-value narrative for leaders, not a hands-on skill), and "Unlock productivity with generative AI" (generic gen-AI overview that name-drops Copilot Studio and Azure AI in passing, not a skill-building module) were all kept catalog-only.

---

## Directly relevant modules (full detail fetched)

*24 modules — Microsoft 365 Copilot Chat/agent end-user usage, Copilot Studio declarative-agent building, Copilot-specific governance (Purview), and concrete Copilot-in-app use cases. 23 fetched live; 1 cross-referenced to an existing file in this folder.*

## Secure Microsoft 365 Copilot interactions with Microsoft Purview
**URL:** https://learn.microsoft.com/en-us/training/modules/purview-ai-secure-copilot/
**Level:** Intermediate | **Units:** 11
**Summary:** AI tools like Microsoft 365 Copilot create new ways to interact with sensitive data, but they also introduce new risks. Learn how Microsoft Purview helps you apply security and compliance controls that protect data, manage AI activity, and support responsible use at scale.
**Objectives:**
- Control Copilot's access to sensitive content with sensitivity labels
- Prevent data exposure in Copilot interactions using data loss prevention policies
- Retain and audit Copilot prompts and responses with retention and audit
- Investigate Copilot activity using eDiscovery
- Detect risky or inappropriate Copilot usage with Communication Compliance
- Assess AI compliance using Compliance Manager
**Prerequisites:** Familiarity with Microsoft 365 Copilot; basic knowledge of Microsoft Purview; understanding of compliance and data protection concepts; experience with Microsoft 365 roles and permissions
**Unit titles:** 1. Introduction 2. Understand how Microsoft 365 Copilot changes data protection needs 3. Assess Copilot regulatory compliance with Compliance Manager 4. Audit Copilot interactions with Microsoft Purview 5. Analyze Copilot interactions with Communication Compliance 6. Classify and protect Copilot content with sensitivity labels 7. Apply DLP policies to Microsoft 365 Copilot 8. Apply retention policies to Copilot prompts and responses 9. Investigate and delete Copilot activity with eDiscovery 10. Module assessment 11. Summary

---

## Summarize sales data using Copilot in Excel
**URL:** https://learn.microsoft.com/en-us/training/modules/summarize-sales-data/
**Level:** Beginner | **Units:** 5
**Summary:** Explore ways to use Copilot in Excel to quickly summarize, analyze, and visualize sales performance data.
**Objectives:**
- Describe how Copilot in Excel interprets and summarizes structured data.
- Use prompts to generate summaries, comparisons, and visualizations from a dataset.
- Apply Copilot suggestions to extend analysis with features like PivotTables, charts, or calculated columns.
**Prerequisites:** None
**Unit titles:** 1. Introduction 2. Understand how Copilot interprets data in Excel 3. Exercise - Summarize and visualize sales data with Copilot 4. Knowledge check 5. Summary

---

## Manage email efficiently with Microsoft Outlook and Copilot Chat
**URL:** https://learn.microsoft.com/en-us/training/modules/manage-email-efficiently/
**Level:** Beginner | **Units:** 9
**Summary:** Discover how business professionals can streamline communication and save time using Microsoft Outlook and Copilot Chat.
**Objectives:**
- Organize your inbox to focus on high-priority messages.
- Summarize email threads efficiently using Copilot Chat.
- Draft professional email replies with the help of Copilot Chat.
**Prerequisites:** None
**Unit titles:** 1. Introduction 2. Summarize email threads with Copilot Chat in Outlook 3. Exercise - summarize an email thread 4. Draft reply emails using Copilot Chat 5. Exercise - draft a reply email 6. Create inbox rules using Copilot Chat in Outlook 7. Exercise - create an inbox rule 8. Knowledge check 9. Summary

---

## Draft a campaign brief using Copilot in Word
**URL:** https://learn.microsoft.com/en-us/training/modules/draft-a-campaign-brief/
**Level:** Beginner | **Units:** 6
**Summary:** Discover how to use Copilot in Word to generate and revise a campaign brief efficiently. Explore how AI assistance can support structured planning, reduce manual edits, and improve team coordination.
**Objectives:**
- Write a complete campaign brief faster using Copilot in Word.
- Understand what goes into a strong campaign brief, including goals, audience, messaging, and how success is measured.
- Use Copilot to organize and improve your writing, like adjusting tone, adding missing details, or pulling in data from other documents.
**Prerequisites:** None
**Unit titles:** 1. Introduction 2. Understand the structure and purpose of a campaign brief 3. Use Copilot in Word to accelerate campaign brief creation 4. Use Copilot in Word to create a campaign brief 5. Knowledge check 6. Summary

---

## Microsoft 365 Copilot and Copilot agents
**URL:** https://learn.microsoft.com/en-us/training/modules/copilot-and-copilot-agents/
**Level:** Beginner | **Units:** 7
**Summary:** Explore Microsoft 365 Copilot and Copilot agents to understand what they are, how they work, and the value they bring to organizations.
**Objectives:**
- Differentiate between Microsoft 365 Copilot and Copilot agents
- List the benefits they bring to organizations, such as improved efficiency and enhanced overall productivity
- Assess whether Microsoft 365 Copilot and Copilot agents are appropriate for a specific organization
**Prerequisites:** None
**Unit titles:** 1. Support organizational success 2. Microsoft 365 Copilot 3. Microsoft 365 Copilot agents 4. Types of Copilot agents 5. How can I build agents? 6. More resources 7. Unlock the power of AI

---

## Introduction to Microsoft AI agent solutions
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-microsoft-ai-agent-solutions/
**Level:** Beginner | **Units:** 8
**Summary:** Explore Microsoft AI agent solutions and gain clarity on when to adopt, extend, or develop custom agent solutions based on your scenario and objectives.
**Objectives:**
- Identify core use cases for the out-of-the-box capabilities of Microsoft 365 Copilot, Copilot Chat, and first-party agents.
- Describe options for customizing and extending Microsoft 365 Copilot.
- Identify scenarios where building fully custom AI agents or generative AI applications is appropriate.
- Identify the key Microsoft development tools available for designing, building, extending, and deploying AI agents.
- Evaluate which Microsoft AI agent path best fits a given scenario.
**Prerequisites:** Familiarity with Microsoft 365 Copilot; basic knowledge of generative AI concepts (agent, model, orchestration, etc.); familiarity with core Microsoft Cloud platforms (Microsoft 365, Power Platform, and Azure)
**Unit titles:** 1. Introduction 2. The Microsoft AI agent ecosystem 3. Maximize Microsoft 365 Copilot, Copilot Chat, and agents 4. Customize and extend Microsoft 365 Copilot 5. Build custom AI agents and applications 6. Compare AI agent solutions 7. Module assessment 8. Summary

---

## Extend declarative agents with connector tools in Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/extend-declarative-agents-connector-actions-copilot-studio/
**Level:** Intermediate | **Units:** 6
**Summary:** Connect your declarative agent to external services and data using connector tools. Configure out-of-the-box connectors and add them to agents that extend Microsoft 365 Copilot.
**Objectives:**
- Create a new connector tool.
- Configure a connector tool.
- Add a connector tool to a declarative agent.
- Test a connector tool.
**Prerequisites:** Basic knowledge of what Microsoft 365 Copilot is and how it works; basic understanding of declarative agents; a Microsoft 365 tenant with Microsoft 365 Copilot; access to Copilot Studio with permission to create agents; ability to create a new declarative agent in Copilot Studio
**Unit titles:** 1. Introduction 2. What are connector tools? 3. Create and configure connector tools 4. Exercise - Create a connector tool 5. Module assessment 6. Summary

---

## Explore prebuilt Microsoft 365 Copilot agents
**URL:** https://learn.microsoft.com/en-us/training/modules/explore-prebuilt-microsoft-365-copilot-agents/
**Level:** Beginner | **Units:** 11
**Summary:** This module introduces several prebuilt agents in Microsoft 365 Copilot Chat and explains when to use each one for research, analysis, writing, ideation, and prompt refinement.
**Objectives:**
- Interact with the prebuilt agents in Microsoft 365 Copilot Chat.
- Describe what each of the prebuilt agents do.
- Provide practical examples of how each prebuilt agent can help in your day-to-day work.
- Describe the limitations of each prebuilt agent.
**Prerequisites:** Students should have basic functional experience with Microsoft 365 services; students must have a proficient understanding of general IT practices.
**Unit titles:** 1. Introduction 2. Examine the Analyst agent 3. Exercise - Use the Analyst agent 4. Examine the Researcher agent 5. Exercise - Use the Researcher agent 6. Examine the Prompt Coach agent 7. Examine the Idea Coach agent 8. Examine the Writing Coach agent 9. Exercise - Use an agent of your choice 10. Module assessment 11. Summary

---

## Employ Copilot Chat as your AI assistant
**URL:** https://learn.microsoft.com/en-us/training/modules/employ-copilot-assistant/
**Level:** Beginner | **Units:** 7
**Summary:** Learn about Microsoft 365 Copilot Chat, a tool that leverages generative AI to enhance productivity and streamline workflows.
**Objectives:**
- Craft effective prompts based on techniques that improve Copilot's responses.
- Delete prompts you no longer need, keeping your workspace efficient and up-to-date.
- Identify and manage scheduled prompts in the Copilot window.
- Understand how organizational settings impact the availability of scheduled prompts.
- Apply scheduled prompts to automate daily, midweek, and end-of-day business activities for improved productivity.
- Understand how to create and configure an agent
**Prerequisites:** Familiarity with basic AI concepts and terminology, and basic understanding of Microsoft 365 applications and services.
**Unit titles:** 1. Introduction 2. What is Copilot Chat? 3. Write effective prompts to optimize Copilot responses 4. Manage prompts and conversations in Copilot Chat 5. What are AI agents? 6. Knowledge check 7. Summary

---

## Develop marketing skills with AI agents
**URL:** https://learn.microsoft.com/en-us/training/modules/agent-speed-skills-marketing/
**Level:** Beginner | **Units:** 7
**Summary:** Learn how AI agents can enhance marketing workflows and decision-making.
**Objectives:**
- Use AI agents to analyze market trends and audience insights.
- Refine customer story prompts for effective narratives.
- Develop reusable campaign prompts for marketing strategies.
- Discover internal insights to inform marketing decisions.
**Prerequisites:** Access to Microsoft 365 Copilot and Microsoft 365 apps; a OneDrive account and Exchange Online mailbox
**Unit titles:** 1. Introduction 2. Analyze market trends using Researcher agent 3. Transform customer story prompts using the Prompt Coach agent 4. Develop a campaign prompt using the Prompt Coach agent 5. Discover internal insights using the Researcher agent 6. Module assessment 7. Summary

---

## Scale how you work by creating AI agents
**URL:** https://learn.microsoft.com/en-us/training/modules/scale-work-creating-ai-agents/
**Level:** Intermediate | **Units:** 6
**Summary:** This module explores how business users with no technical or programming experience can create AI agents in Microsoft 365 Copilot Chat that will increase their productivity and extend their impact.
**Objectives:**
- Describe the tools used to create agents
- Create an agent in Copilot Chat
**Prerequisites:** None
**Unit titles:** 1. Introduction 2. Examine the tools used to create agents 3. Create an agent in Copilot Chat 4. Exercise: Create a Copilot Chat agent 5. Module assessment 6. Summary

---

## Choose the best Microsoft 365 Copilot extensibility path for your scenario
**URL:** https://learn.microsoft.com/en-us/training/modules/choose-microsoft-365-copilot-extensibility-path/
**Level:** Beginner | **Units:** 9
**Summary:** Explore development options for extending Microsoft 365 Copilot with custom data, logic, and actions. Determine the best approach for your scenario.
**Objectives:**
- Identify the different extensibility options available for Microsoft 365 Copilot.
- Compare the strengths and limitations of Copilot connectors, declarative agents, and custom agents.
- Evaluate which extensibility approach best fits a given business scenario.
- Understand the technical and organizational requirements for extending Microsoft 365 Copilot.
**Prerequisites:** A basic understanding of Microsoft 365 and Microsoft 365 apps; familiarity with generative AI and AI agents; familiarity with Microsoft tools for AI agent development (Copilot Studio, Microsoft Foundry, Microsoft 365 Agents Toolkit, etc.)
**Unit titles:** 1. Introduction 2. Identify extensibility options 3. Analyze the decision criteria 4. Extend Copilot's knowledge with Copilot connectors 5. Build declarative agents in Copilot Studio 6. Build declarative agents with Visual Studio Code and Microsoft 365 Agents Toolkit 7. Deploy custom agents to Microsoft 365 Copilot 8. Module assessment 9. Summary

---

## Develop sales skills with AI agents
**URL:** https://learn.microsoft.com/en-us/training/modules/agent-speed-skills-sales/
**Level:** Beginner | **Units:** 6
**Summary:** Learn how to use AI agents in Microsoft 365 Copilot to improve sales workflows, address objections, and tailor messaging for better outcomes.
**Objectives:**
- Use AI agents to uncover the cost of inaction in stalled deals.
- Prepare evidence-based responses to common sales objections.
- Tailor final-stage deal messaging to align with customer priorities.
**Prerequisites:** Access to Microsoft 365 Copilot and Microsoft 365 apps; a OneDrive account and an Exchange Online mailbox
**Unit titles:** 1. Introduction 2. Turn stalled conversations into action using the Researcher agent 3. Prepare for deal objections using Researcher agent 4. Tailor final-stage deal messaging with Researcher agent 5. Module assessment 6. Summary

---

## Turn information into decisions with AI agents
**URL:** https://learn.microsoft.com/en-us/training/modules/turn-info-into-decisions-ai-agents/
**Level:** Beginner | **Units:** 9
**Summary:** Discover how to use the Researcher, Analyst, and Idea Coach agents in Microsoft 365 Copilot to gather information, uncover insights, and turn data into actionable decisions.
**Objectives:**
- Gather information using the Researcher agent
- Generate insights using the Analyst agent
- Examine how the Idea Coach agent supports creative thinking
- Apply AI agents to real-world decision-making tasks
**Prerequisites:** Familiarity with basic AI concepts and terminology, and basic understanding of Microsoft 365 applications and services.
**Unit titles:** 1. Introduction 2. Gather information using the Researcher agent 3. Exercise - Use the Researcher agent 4. Generate insights using the Analyst agent 5. Exercise - Use the Analyst agent 6. Examine the Idea Coach agent 7. Exercise - Use an agent of your choice 8. Module assessment 9. Summary

---

## Build and manage an agent
**URL:** https://learn.microsoft.com/en-us/training/modules/build-manage-no-code-copilot-agent-sharepoint/
**Level:** Beginner | **Units:** 12
**Note:** Not re-fetched — this module is already fully documented in `ms-learn-copilot-agent-sharepoint-module.md` in this same folder (SharePoint + Copilot Chat no-code agent building: Agent Builder vs. the SharePoint Copilot agent tool, agent components, creation/testing/management, module assessment). See that file for the full unit-by-unit breakdown.
**Summary:** This module guides you through the foundational concepts and practical steps required to create, test, and manage agents in Microsoft 365 Copilot Chat and SharePoint.

---

## Introduction to tools for declarative agents in Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-copilot-studio-actions/
**Level:** Intermediate | **Units:** 7
**Summary:** Explore how to create and configure tools in Copilot Studio to expand the capabilities of your declarative agents. Connect your declarative agent to external data sources and customize generative responses.
**Objectives:**
- Describe tools in Copilot Studio.
- Identify the types of tools that can extend a declarative agent in Copilot Studio.
- Describe scenarios for adding tools to an agent.
- Describe technical considerations for configuring tools in Copilot Studio.
**Prerequisites:** Basic knowledge of what Microsoft 365 Copilot is and how it works; basic understanding of declarative agents; a Microsoft 365 tenant with Microsoft 365 Copilot; access to Copilot Studio with permission to create agents; ability to create a new declarative agent in Copilot Studio
**Unit titles:** 1. Introduction 2. Tools and agents 3. Types of agent tools 4. Tool development considerations 5. Add tools to declarative agents 6. Module assessment 7. Summary

---

## Explore Microsoft 365 Copilot and agents
**URL:** https://learn.microsoft.com/en-us/training/modules/explore-microsoft-365-copilot-agents/
**Level:** Beginner | **Units:** 9
**Summary:** This module provides a comprehensive introduction to Microsoft 365 Copilot and agents, explaining their architecture, capabilities, licensing models, deployment strategies, and practical use cases.
**Objectives:**
- Explain the architecture and key components of Microsoft 365 Copilot, including Microsoft Graph, orchestration services, and large language models.
- Describe the differences between Copilot and agents, and identify scenarios where each is most effective for productivity and automation.
- Understand the various types of agents available in Microsoft 365, including prebuilt, custom, SharePoint, and advanced agents, and their roles in supporting business workflows.
- Summarize the licensing models and deployment strategies for Microsoft 365 Copilot and agents, including feature enablement and administrative controls.
- Recognize best practices for planning, configuring, and governing Copilot and agents to ensure security, compliance, and effective adoption.
- Identify real-world use cases for Copilot and agents and select the right tool for specific business needs within the Microsoft 365 ecosystem.
**Prerequisites:** Students should have basic functional experience with Microsoft 365 services; students must have a proficient understanding of general IT practices.
**Unit titles:** 1. Introduction 2. Introduction to Microsoft 365 Copilot 3. What are agents? 4. Compare Microsoft 365 Copilot and agents 5. Compare Microsoft 365 Copilot licensing models 6. Plan and deploy Microsoft 365 Copilot and agents 7. Explore real-world use cases for Copilot and agents 8. Module assessment 9. Summary

---

## Introduction to developing AI agents
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-develop-ai-agents/
**Level:** Beginner | **Units:** 6
**Summary:** Explore what AI agents are, understand their core components, and discover a range of impactful use cases driving AI-powered transformation.
**Objectives:**
- Define AI agents
- Explain the business value of AI agents.
- Identify common use cases for AI agents.
- Define the core components of AI agents.
**Prerequisites:** None
**Unit titles:** 1. Introduction 2. AI transformation and agents 3. AI agent use cases 4. AI agent components 5. Module assessment 6. Summary

---

## Craft a compelling product pitch using AI
**URL:** https://learn.microsoft.com/en-us/training/modules/craft-compelling-product-pitch-using-ai/
**Level:** Beginner | **Units:** 13
**Summary:** Use Microsoft Copilot to develop and deliver a compelling product pitch. Learn how Copilot can accelerate your creative process — from brainstorming and journey mapping to presentation design and stakeholder prep.
**Objectives:**
- Use Copilot to brainstorm and shape product ideas.
- Create user journeys and visuals with Copilot.
- Build and refine pitch presentations using Copilot in PowerPoint.
- Draft supporting content like personas and testimonials with Copilot.
- Prepare for stakeholder questions using Copilot-generated insights.
**Prerequisites:** Basic understanding of Microsoft 365 tools like Word, PowerPoint, and OneDrive; access to Microsoft Copilot and a Microsoft 365 subscription.
**Unit titles:** 1. Introduction 2. Understand product-led growth strategies 3. Develop a product idea and create an elevator pitch 4. Conduct market analysis and create user personas 5. Visualize product-led growth in action 6. Showcase growth with data-driven metrics 7. Build trust with testimonials and social proof 8. Create your ask and prepare for tough questions 9. Create a product visual to showcase its value 10. Create a presentation outline for your product pitch 11. Turn your pitch into a visual story 12. Module assessment 13. Summary

---

## Develop finance skills with AI agents
**URL:** https://learn.microsoft.com/en-us/training/modules/agent-speed-skills-finance/
**Level:** Beginner | **Units:** 6
**Summary:** Learn to analyze financial data, identify variances, and create executive-ready insights using Microsoft 365 Copilot.
**Objectives:**
- Use Microsoft 365 Copilot's Analyst agent to analyze financial data and identify key variances.
- Create executive-ready summaries and visuals to support leadership decision-making.
- Apply storytelling frameworks to communicate financial insights effectively.
**Prerequisites:** Access to Microsoft 365 Copilot and Microsoft 365 apps; a OneDrive account and Exchange Online mailbox
**Unit titles:** 1. Introduction 2. Create executive-ready financial stories using Researcher agent 3. Analyze budget actuals and explain variances using Analyst agent 4. Explore and explain financial variance using Analyst agent 5. Module assessment 6. Summary

---

## Extend declarative agents with prompt tools in Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/extend-declarative-agents-prompt-actions-copilot-studio/
**Level:** Intermediate | **Units:** 6
**Summary:** Customize your declarative agent's generative responses by extending your agent with prompt tools. Craft custom prompts, test your prompts against the LLM, and add prompt tools to declarative agents that extend Microsoft 365 Copilot.
**Objectives:**
- Configure a prompt tool in Copilot Studio.
- Test a prompt in Copilot Studio.
- Add a prompt tool to a declarative agent in Copilot Studio.
**Prerequisites:** Basic knowledge of what Microsoft 365 Copilot is and how it works; basic understanding of declarative agents; a Microsoft 365 tenant with Microsoft 365 Copilot; access to Copilot Studio with permission to create agents; ability to create a new declarative agent in Copilot Studio
**Unit titles:** 1. Introduction 2. What are prompt tools? 3. Create a prompt tool 4. Exercise - Create a prompt tool 5. Module assessment 6. Summary

---

## Understand AI agents and prompting
**URL:** https://learn.microsoft.com/en-us/training/modules/understand-ai-agents-prompting/
**Level:** Beginner | **Units:** 5
**Summary:** Learn about AI Agents in Microsoft 365 Copilot, how they can assist with everyday tasks, and how to craft effective prompts to get the best results from Copilot.
**Objectives:**
- Define what AI Agents are
- Understand how to create and configure an agent
- Craft effective prompts to get the best results from Copilot
**Prerequisites:** Familiarity with basic AI concepts and terminology, and basic understanding of Microsoft 365 applications and services.
**Unit titles:** 1. Introduction to AI agents and prompting 2. What are AI agents? 3. Write effective prompts to optimize Copilot responses 4. Module assessment 5. Summary

---

## Build your first declarative agent for Microsoft 365 Copilot by using Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/build-your-first-agent-microsoft-365-copilot-use-copilot-studio/
**Level:** Intermediate | **Units:** 9
**Summary:** Create an agent tailored to a specific scenario to extend Microsoft 365 Copilot. Your declarative agent provides relevant and accurate responses using custom knowledge.
**Objectives:**
- Design a declarative agent to solve a business problem.
- Implement a declarative agent with custom knowledge.
- Publish and use a declarative agent in Microsoft 365 Copilot to validate the results.
**Prerequisites:** Basic knowledge of what Microsoft 365 Copilot is and how it works; basic understanding of declarative agents; a Microsoft 365 tenant with Microsoft 365 Copilot; access to Copilot Studio with permission to create agents
**Unit titles:** 1. Introduction 2. Create a declarative agent 3. Exercise - Create a declarative agent 4. Add custom knowledge 5. Exercise - Add custom knowledge 6. Add suggested prompts 7. Exercise - Add suggested prompts 8. Module assessment 9. Summary

---

## Perform basic administrative tasks for Microsoft 365 Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/perform-admin-tasks-microsoft-365-copilot/
**Level:** Beginner | **Units:** 8
**Summary:** This module guides administrators on how to manage Microsoft 365 Copilot, including licensing and access control, billing and usage monitoring, prompt governance, and strategies for tracking and driving user adoption.
**Objectives:**
- Manage Microsoft 365 Copilot licenses and pay-as-you-go billing.
- Monitor and adjust pay-as-you-go Copilot usage.
- Track Microsoft 365 Copilot user adoption.
- Use Copilot Analytics to monitor usage patterns and adoption trends.
- Manage and govern prompts in Microsoft 365 Copilot.
- Employ operational best practices, such as troubleshooting common issues and communicating changes to end users.
**Prerequisites:** Students should have basic functional experience with Microsoft 365 services; students must have a proficient understanding of general IT practices.
**Unit titles:** 1. Introduction 2. Manage Copilot licenses and pay-as-you-go billing 3. Monitor and adjust pay-as-you-go Copilot usage 4. Monitor Microsoft 365 Copilot usage and adoption 5. Manage and govern Microsoft 365 Copilot prompts 6. Apply operational best practices for Microsoft 365 Copilot 7. Module assessment 8. Summary

---

## Other modules (catalog data only)

*35 modules — the parallel solution-architect "AI business solution architecture" series, education/nonprofit/Surface verticals, generic non-AI Outlook UI training, generic gen-AI overviews, and Copilot Studio "Challenge project" exercises. Catalog metadata only; page-level detail was not fetched for these to keep scope tractable.*

- **[Integrate your agent with Microsoft 365](https://learn.microsoft.com/en-us/training/modules/integrate-foundry-agent-with-m365/)** — Intermediate, 74 min, 9 units. uid: `learn.wwl.integrate-foundry-agent-with-m365`. Learn how to publish Microsoft Foundry agents to Microsoft Teams and Microsoft 365 Copilot, access workplace data with Work IQ, and test your integrated agents. *(Borderline exclude — Foundry custom-engine agent development, a different product/track from Copilot Studio's declarative agents.)*
- **[Leverage AI tools and resources for your business](https://learn.microsoft.com/en-us/training/modules/leverage-ai-tools/)** — Beginner, 42 min, 9 units. uid: `learn.wwl.leverage-ai-tools`. Learn how to use AI tools and resources for your business.
- **[Define a Microsoft AI strategy to create business value in nonprofit](https://learn.microsoft.com/en-us/training/modules/define-microsoft-ai-strategy-create-business-value-nonprofit/)** — Beginner, 38 min, 9 units. uid: `learn.wwl.define-microsoft-ai-strategy-create-business-value-nonprofit`. Discover AI use cases and scenarios for nonprofit organizations. Get familiar with Microsoft AI tools and services for nonprofit. Learn from real success stories.
- **[Design ALM process for AI-powered business solutions](https://learn.microsoft.com/en-us/training/modules/design-alm-process-ai-powered-business-solutions/)** — Intermediate, 46 min, 9 units. uid: `learn.wwl.design-alm-process-ai-powered-business-solutions`. Learn to design ALM processes for AI solutions, ensuring governance, security, and consistency across development, testing, and production. *(Part of the excluded solution-architect series.)*
- **[Design extensibility of AI solutions](https://learn.microsoft.com/en-us/training/modules/design-extensibility-ai-solutions/)** — Advanced, 48 min, 10 units. uid: `learn.wwl.design-extensibility-ai-solutions`. Learn to design scalable, secure, and customizable AI solutions using Microsoft platforms. Explore extensibility strategies for enterprise AI. *(Part of the excluded solution-architect series.)*
- **[Monitor, analyze, and tune AI agents](https://learn.microsoft.com/en-us/training/modules/analyze-monitor-tune-ai-powered-business-solutions/)** — Advanced, 36 min, 8 units. uid: `learn.analyze-monitor-tune-ai-powered-business-solutions`. Learn to monitor, analyze, and tune AI agents for reliability, performance, and continuous improvement in enterprise environments. *(Part of the excluded solution-architect series.)*
- **[Unlock productivity with generative AI](https://learn.microsoft.com/en-us/training/modules/generative-ai-productivity/)** — Beginner, 18 min, 5 units. uid: `learn.dpu.generative-ai-productivity`. Learn how generative AI enhances productivity, ensures responsible use, and empowers innovation through Microsoft tools like Copilot Studio and Azure AI. *(Borderline exclude — generic gen-AI overview, not a Copilot skill-building module.)*
- **[Plan your organization's AI skilling journey with Microsoft 365 Copilot](https://learn.microsoft.com/en-us/training/modules/plan-ai-skilling-journey/)** — Beginner, 23 min, 8 units. uid: `learn.dpu.plan-ai-skilling-journey`. Learn how to plan and sustain an AI skilling journey that connects individual curiosity with organizational goals. *(Borderline exclude — org change-management/skilling strategy, not hands-on tool usage.)*
- **[Personalize learning for students with disabilities using AI](https://learn.microsoft.com/en-us/training/modules/personalize-learning-students-disabilities-using-ai/)** — Beginner, 24 min, 8 units. uid: `learn.wwl.use-ai-personalize-learning-students-disabilities`. Educators will learn how to use AI and accessibility tools to personalize learning for students with disabilities. *(Education vertical.)*
- **[Introduction to agentic AI business solutions](https://learn.microsoft.com/en-us/training/modules/introduction-agentic-ai-business-solution-architecture/)** — Advanced, 24 min, 8 units. uid: `learn.wwl.introduction-agentic-ai-business-solution-architecture`. Learn how to align AI solutions with business goals, scale AI adoption, and use Microsoft AI technologies for enterprise success. *(Part of the excluded solution-architect series.)*
- **[Manage testing AI-powered business solutions](https://learn.microsoft.com/en-us/training/modules/manage-testing-ai-powered-business-solutions/)** — Advanced, 35 min, 8 units. uid: `learn.wwl.manage-testing-ai-powered-business-solutions`. Learn to validate and maintain AI-powered business solutions with structured testing frameworks, metrics, and governance for enterprise reliability. *(Part of the excluded solution-architect series.)*
- **[Analyze requirements for AI-powered business solutions](https://learn.microsoft.com/en-us/training/modules/analyze-requirements-ai-powered-business-solutions/)** — Advanced, 25 min, 6 units. uid: `learn.wwl.analyze-requirements-ai-powered-business-solutions`. Learn to analyze, design, and implement AI-powered business solutions using agents, generative AI, and Microsoft Copilot for productivity. *(Part of the excluded solution-architect series.)*
- **[Streamline administrative tasks with AI tools](https://learn.microsoft.com/en-us/training/modules/streamline-administrative-tasks-ai/)** — Intermediate, 21 min, 7 units. uid: `learn.wwl.streamline-administrative-tasks-ai`. Special educators will learn how and when to use Teach and/or Copilot to streamline administrative tasks, support professional judgment, and maintain accuracy and compliance. *(Education vertical.)*
- **[Design AI agents for business solutions](https://learn.microsoft.com/en-us/training/modules/design-ai-agents-business-solutions/)** — Advanced, 161 min, 21 units. uid: `learn.wwl.design-ai-agents-business-solutions`. Learn to design AI agents tailored to business needs using Dynamics 365 and Copilot. Explore Responsible AI, custom connectors, and integration strategies. *(Part of the excluded solution-architect series.)*
- **[Maximize Microsoft 365 with Surface for Business](https://learn.microsoft.com/en-us/training/modules/maximize-surface/)** — Beginner, 19 min, 7 units. uid: `learn.dpu.surface-microsoft-365`. Use Microsoft 365 Copilot on a Surface device to create a professional presentation efficiently, and collaborate using Microsoft 365 apps while making the most of Copilot's AI capabilities. *(Surface hardware vertical.)*
- **[Orchestrate configuration of prebuilt agents and apps](https://learn.microsoft.com/en-us/training/modules/orchestrate-configuration-prebuilt-agents-apps/)** — Intermediate, 57 min, 10 units. uid: `learn.wwl.orchestrate-configuration-prebuilt-agents-apps`. Learn to orchestrate, configure, and extend AI-driven experiences in Dynamics 365 and Microsoft 365 Copilot for finance, supply chain, and customer service. *(Borderline exclude — Dynamics 365 enterprise config, shares the excluded solution-architect series' product/role tags.)*
- **[Apply AI tools in special education environments](https://learn.microsoft.com/en-us/training/modules/introduction-ai-special-education/)** — Beginner, 15 min, 7 units. uid: `learn.wwl.introduction-ai-special-education`. Explore practical AI tools to enhance teaching, boost student outcomes, and streamline work in special education environments responsibly. *(Education vertical.)*
- **[Design responsible AI security, governance, risk management, and compliance](https://learn.microsoft.com/en-us/training/modules/design-responsible-ai-security-governance-risk-management-compliance/)** — Advanced, 53 min, 11 units. uid: `learn.wwl.design-responsible-ai-security-governance-risk-management-compliance`. Learn to design secure, governed, and compliant AI systems that align with organizational policies and Responsible AI principles. *(Part of the excluded solution-architect series.)*
- **[Support multilingual and accessible family communication](https://learn.microsoft.com/en-us/training/modules/support-multilingual-accessible-family-communication/)** — Beginner, 21 min, 7 units. uid: `learn.wwl.support-multilingual-accessible-family-communication`. Learn to use AI tools to simplify and translate educational communications, ensuring inclusivity and accessibility for diverse families. *(Education vertical.)*
- **[Design overall AI strategy for business solutions](https://learn.microsoft.com/en-us/training/modules/design-overall-ai-strategy-business-solutions/)** — Advanced, 165 min, 19 units. uid: `learn.wwl.design-overall-ai-strategy-business-solutions`. Learn to design an enterprise AI strategy using Azure's Cloud Adoption Framework. Align AI agent lifecycle with business goals for operational excellence. *(Part of the excluded solution-architect series.)*
- **[Evaluate costs and benefits of AI solutions](https://learn.microsoft.com/en-us/training/modules/evaluate-costs-benefits-ai-powered-business-solution/)** — Advanced, 34 min, 7 units. uid: `learn.wwl.evaluate-costs-benefits-ai-powered-business-solution`. Learn to assess costs and benefits of AI solutions. Develop ROI analyses, evaluate TCO, and decide to build, buy, or extend AI components. *(Part of the excluded solution-architect series.)*
- **[Manage People in new Outlook for Windows](https://learn.microsoft.com/en-us/training/modules/manage-people-new-outlook-windows/)** — Beginner, 19 min, 6 units. uid: `learn.wwl.manage-people-new-outlook-windows`. Learn how to effectively manage your contacts in the new Outlook for Windows. *(Generic non-AI Outlook UI training.)*
- **[Customize new Outlook for Windows](https://learn.microsoft.com/en-us/training/modules/customize-new-outlook-windows/)** — Beginner, 28 min, 8 units. uid: `learn.wwl.customize-new-outlook-windows`. Personalize your settings, notifications, and layout to create an environment that works the way you do. *(Generic non-AI Outlook UI training.)*
- **[Challenge project - Build a declarative agent to chat with your docs](https://learn.microsoft.com/en-us/training/modules/copilot-declarative-agent-challenge-chat-with-docs/)** — Intermediate, 53 min, 6 units. uid: `learn.copilot-declarative-agent-challenge-chat-with-docs`. Demonstrate your ability to create a declarative agent for Microsoft 365 Copilot that can answer questions using information from documents. *(Challenge project — hands-on, lower priority than core lessons.)*
- **[Challenge project - Build a declarative agent to chat with your data](https://learn.microsoft.com/en-us/training/modules/copilot-declarative-agent-challenge-chat-with-data/)** — Intermediate, 93 min, 8 units. uid: `learn.copilot-declarative-agent-challenge-chat-with-data`. Demonstrate your ability to create a declarative agent for Microsoft 365 Copilot that accesses data from an external API. *(Challenge project.)*
- **[Understand the foundations of generative AI for business leaders](https://learn.microsoft.com/en-us/training/modules/understand-foundations-generative-ai-business-leaders/)** — Beginner, 34 min, 8 units. uid: `learn.wwl.understand-foundations-generative-ai-business-leaders`. Generative AI is reshaping business operations. Explore core concepts, compare solution types, and align AI capabilities with strategic goals. *(Generic gen-AI overview.)*
- **[Drive business value with Microsoft Copilot solutions](https://learn.microsoft.com/en-us/training/modules/business-value-microsoft-copilot-solutions/)** — Beginner, 38 min, 9 units. uid: `learn.wwl.drive-business-value-microsoft-copilot-solutions`. Understand how Microsoft Copilot solutions can drive business value by enhancing productivity, improving decision-making, and fostering innovation. *(Borderline exclude — business-value narrative for leaders, not a hands-on skill.)*
- **[Build effective generative AI solutions in your organization](https://learn.microsoft.com/en-us/training/modules/build-effective-generative-ai-solutions-organization/)** — Beginner, 28 min, 7 units. uid: `learn.wwl.build-effective-generative-ai-solutions-organization`. Discover how to make generative AI work for your organization: essential elements of building reliable, responsible AI solutions. *(Generic gen-AI overview.)*
- **[Protect and govern Microsoft 365 data](https://learn.microsoft.com/en-us/training/modules/protect-govern-data-microsoft-365/)** — Beginner, 62 min, 8 units. uid: `learn.wwl.protect-govern-data-microsoft-365`. A comprehensive overview of data protection and governance in Microsoft 365: sensitive information, compliance, risk, and secure collaboration. *(Borderline exclude — generic M365 data governance, not Copilot-specific the way the Purview module above is.)*
- **[Challenge project - Build a declarative agent to chat with your external data ingested to Microsoft 365](https://learn.microsoft.com/en-us/training/modules/copilot-declarative-agent-challenge-chat-with-external-data/)** — Intermediate, 70 min, 7 units. uid: `learn.copilot-declarative-agent-challenge-chat-with-external-data`. Demonstrate your ability to create a declarative agent that can chat with your external data ingested to Microsoft 365. *(Challenge project.)*
- **[What is generative AI?](https://learn.microsoft.com/en-us/training/modules/what-generative-ai/)** — Beginner, 30 min, 6 units. uid: `learn-m365.what-generative-ai`. Learn about generative AI — a technology that uses machine learning models to generate new content, ideas, or solutions based on existing data. *(Generic gen-AI overview.)*
- **[Compose and send mail in new Outlook for Windows](https://learn.microsoft.com/en-us/training/modules/compose-send-mail-new-outlook-windows/)** — Beginner, 28 min, 6 units. uid: `learn.wwl.compose-send-mail-new-outlook-windows`. Learn how to compose emails, handle attachments, and organize your inbox in the new Outlook. *(Generic non-AI Outlook UI training.)*
- **[Organize your inbox in new Outlook for Windows](https://learn.microsoft.com/en-us/training/modules/organize-your-inbox-new-outlook-windows/)** — Beginner, 28 min, 6 units. uid: `learn.wwl.organize-your-inbox-new-outlook-windows`. Unlock the full potential of your inbox: Focused Inbox, pinning messages, categories, and advanced search. *(Generic non-AI Outlook UI training.)*
- **[Manage your calendar in new Outlook for Windows](https://learn.microsoft.com/en-us/training/modules/manage-calendar-new-outlook-windows/)** — Beginner, 36 min, 7 units. uid: `learn.wwl.manage-calendar-new-outlook-windows`. Learn how to effectively manage your calendar in the new Outlook for Windows. *(Generic non-AI Outlook UI training.)*
- **[Deploy and manage Agent 365 in education (Partner Success Series)](https://learn.microsoft.com/en-us/training/modules/deploy-manage-agent-365-education/)** — Beginner, 16 min, 9 units. uid: `learn.mec.deploy-manage-agent-365-education`. Education system administrators can deploy, configure, and manage AI agents in Microsoft 365 using Agent 365, the control plane for agents. *(Education vertical.)*

---

## Learning paths (catalog data only, not modules)

*17 learning paths matched product=microsoft-365-copilot. Listed for completeness; not in scope for page-level module fetching.*

- **[Windows 11 Pro Accreditation 2026](https://learn.microsoft.com/en-us/training/paths/windows-11-pro-accreditation-2026/)** — Beginner, 114 min, 4 modules. uid: `learn.dpu.windows-11-pro-accreditation-2026`. Introduces Windows 11 Pro as a secure, high-performance platform designed to support AI-enabled work, including intelligent workflows with AI and agents.
- **[Architect AI solutions for business productivity](https://learn.microsoft.com/en-us/training/paths/architect-agentic-ai-business-solutions/)** — Advanced, 684 min, 11 modules. uid: `learn.wwl.architect-agentic-ai-business-solutions`. Learn how to design AI-powered business solutions using agents, generative AI, and Microsoft Copilot to enhance productivity and efficiency. (The solution-architect series aggregated into a path.)
- **[AI in special education](https://learn.microsoft.com/en-us/training/paths/ai-in-special-education/)** — Beginner, 120 min, 5 modules. uid: `learn.wwl.ai-in-special-education`. Supports educators in exploring how Microsoft AI tools can be thoughtfully used in special education environments.
- **[Protect information in a Microsoft 365 Copilot environment using Microsoft Purview](https://learn.microsoft.com/en-us/training/paths/purview-protect-microsoft-365-copilot-environment/)** — Intermediate, 175 min, 3 modules. uid: `learn.wwl.purview-protect-microsoft-365-copilot-environment`. Learn how to use Microsoft Purview audit, sensitivity labels, and DLP to investigate, classify, and protect data in a Copilot-enabled environment.
- **[Discover AI for leaders in nonprofit](https://learn.microsoft.com/en-us/training/paths/discover-ai-leaders-nonprofit/)** — Beginner, 192 min, 5 modules. uid: `learn.wwl.discover-ai-leaders-nonprofit`. Discover AI for leaders in nonprofit.
- **[Microsoft Education Accreditation 2026](https://learn.microsoft.com/en-us/training/paths/microsoft-education-accreditation-2026/)** — Beginner, 108 min, 4 modules. uid: `learn.dpu.microsoft-education-accreditation-2026`. Introduces the latest Microsoft Education solutions for K–12 and higher education institutions.
- **[Secure AI interactions and environments with Microsoft Purview](https://learn.microsoft.com/en-us/training/paths/purview-protect-ai/)** — Intermediate, 210 min, 4 modules. uid: `learn.wwl.purview-protect-ai`. Explore how Microsoft Purview protects sensitive information in AI-enabled environments across Microsoft 365 Copilot, non-Microsoft AI apps, and developer AI scenarios. Aligns with exam SC-401.
- **[Secure and govern Microsoft 365 Copilot interactions with Microsoft Purview](https://learn.microsoft.com/en-us/training/paths/purview-secure-govern-copilot-interactions/)** — Intermediate, 371 min, 7 modules. uid: `learn.wwl.purview-secure-govern-copilot-interactions`. Learn how Microsoft Purview helps you gain visibility into AI activity, protect sensitive information, detect risky behavior, and govern Microsoft 365 Copilot interactions.
- **[Explore Microsoft 365 Copilot and agent administration](https://learn.microsoft.com/en-us/training/paths/explore-microsoft-365-copilot-agent-administration/)** — Beginner, 199 min, 3 modules. uid: `learn.wwl.explore-microsoft-365-copilot-agent-administration`. Explores how to boost productivity and security in Microsoft 365 by using Copilot and AI-powered agents, while managing, customizing, and governing them.
- **[Transform your everyday business processes with agents](https://learn.microsoft.com/en-us/training/paths/implement-no-code-copilot-agents-microsoft-365-sharepoint/)** — Beginner, 232 min, 4 modules. uid: `learn.wwl.implement-no-code-copilot-agents-microsoft-365-sharepoint`. Learn how to use agents in Microsoft Copilot and SharePoint to automate tasks, surface information, and streamline everyday business processes (MS-4019). Includes the "Build and manage an agent" module documented elsewhere in this folder.
- **[Build a foundation to build AI agents and extend Microsoft 365 Copilot](https://learn.microsoft.com/en-us/training/paths/build-foundation-extend-microsoft-365-copilot/)** — Beginner, 104 min, 4 modules. uid: `learn.wwl.build-foundation-extend-microsoft-365-copilot`. Prepare to build AI agents and extend Microsoft 365 Copilot using Copilot Studio, Microsoft Foundry, Microsoft 365 Agents Toolkit, and more. Home path for several of this file's Copilot Studio orientation modules ("Introduction to Microsoft AI agent solutions," "Introduction to developing AI agents," "Choose the best Microsoft 365 Copilot extensibility path for your scenario").
- **[Explore the business value of generative AI solutions](https://learn.microsoft.com/en-us/training/paths/explore-business-value-generative-ai-solutions/)** — Beginner, 62 min, 2 modules. uid: `learn.wwl.explore-business-value-generative-ai-solutions`. Discover how generative AI can transform your business processes and drive innovation.
- **[Explore role-based AI agent skills for business users](https://learn.microsoft.com/en-us/training/paths/explore-role-based-ai-agent-skills-business-users/)** — Beginner, 100 min, 3 modules. uid: `agent-speed-skills-business-users`. Explore how role-based AI agents in Microsoft 365 Copilot can help business professionals work faster on research, analysis, and executive communication. Home path for the marketing/sales/finance "Develop ... skills with AI agents" modules in this file.
- **[Discover new Outlook for Windows](https://learn.microsoft.com/en-us/training/paths/discover-new-outlook-windows/)** — Beginner, 139 min, 5 modules. uid: `learn.wwl.discover-new-outlook-windows`. Take control of your inbox, calendar, and contacts in the new Outlook for Windows experience.
- **[Drive business value with AI solutions](https://learn.microsoft.com/en-us/training/paths/drive-value-generative-ai-solutions/)** — Beginner, 68 min, 2 modules. uid: `learn.wwl.drive-value-generative-ai-solutions`. Discover how Copilot and Azure AI can transform work across your organization.
- **[Enhance your productivity with prebuilt Microsoft 365 Copilot agents](https://learn.microsoft.com/en-us/training/paths/enhance-productivity-prebuilt-agents/)** — Beginner, 72 min, 1 module. uid: `learn.wwl.enhance-productivity-prebuilt-agents`. Explores how prebuilt agents in Microsoft 365 Copilot enable users to streamline tasks and retrieve information through AI-powered conversational tools.
- **[Extend Microsoft 365 Copilot in Copilot Studio](https://learn.microsoft.com/en-us/training/paths/extend-microsoft-365-copilot-studio/)** — Intermediate, 182 min, 5 modules. uid: `learn.wwl.extend-microsoft-365-copilot-studio`. Build agents that extend Microsoft 365 Copilot with additional knowledge and capabilities: build declarative agents, add knowledge, add tools, and publish to Microsoft 365 Copilot. **This is the single most directly reusable learning path for the Copilot Studio sub-module** — it's the official MS Learn path bundling exactly the declarative-agent-building modules documented in full above (introduction to Copilot Studio tools, connector tools, prompt tools, and building your first declarative agent).

---

## Structure not retrieved (catalog data only)

*None. All 23 freshly targeted modules in the "directly relevant" set resolved successfully on first fetch (no 404s or failures encountered). The 24th relevant module ("Build and manage an agent") was intentionally not re-fetched because full detail already exists in `ms-learn-copilot-agent-sharepoint-module.md`.*
