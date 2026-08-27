# MS Learn — Modules tagged Power Platform / Power Automate / Power Apps

**Source:** https://learn.microsoft.com/en-us/training/browse/?products=power-platform%2Cpower-automate%2Cpower-apps (catalog API: `product=power-platform&product=power-automate&product=power-apps&type=modules,learningPaths`)

**Scraped:** 2026-07-09

**Total modules found:** 334 (union of product=power-platform OR product=power-automate OR product=power-apps — the catalog API unions multiple `product=` values, it does not intersect them) | **Learning paths found:** 93

> **Note on methodology:** Following the same rule established during the GitHub/VS Code scrape — never trust a WebFetch of the human-facing `/training/browse/?products=...` page, since it is a JS-rendered browse UI and a fetch-and-summarize pass will undercount the real catalog — this catalog was pulled directly from the raw JSON API via `curl` and parsed locally with Node:
> ```
> curl -s "https://learn.microsoft.com/api/catalog/?type=modules,learningPaths&product=power-platform,power-automate,power-apps&locale=en-us" -o pp_catalog.json
> ```
> Entries were deduplicated by `uid`, since `power-platform`, `power-automate`, and `power-apps` are heavily overlapping tags (most Power Automate and Power Apps modules also carry the umbrella `power-platform` tag). Unlike the GitHub/VS Code scrape — where deduplication mattered only marginally (16 of 231 modules carried both tags) — here deduplication found **zero duplicate uids**: 334 raw module entries in, 334 unique out; 93 raw learning-path entries in, 93 unique out. The catalog API's own filtering evidently already returns each matching module/path exactly once even when it satisfies more than one of the OR'd `product=` values, so no records were removed. This is a useful negative-result confirmation that "union the filters, then dedup by uid defensively" is the right general procedure — it just happened not to change the count this time.
>
> Of the 334 modules, **75** are genuinely maker-level Power Automate / Power Apps / Power Platform governance-and-DLP / Microsoft Copilot Studio agent-building content, directly relevant to this curriculum's 6-lesson Power Platform track (orientation, building an automation with Power Automate, building a no-code app with Power Apps, governance/DLP as the safe-use lesson, and an app+automation capstone) and to the curriculum's separate Copilot Studio module. These 75 got full page-level detail (objectives, prerequisites, ordered unit titles) via live fetches of each module page. The remaining **259** modules are catalog metadata only — explicitly out of scope per the triage brief: SAP/Azure integration, FinOps, commercial marketplace, Power BI/semantic models (not one of this curriculum's 7 tracks), PL-1xx/PL-2xx/MB-xxx certification exam-prep, "Solution Architect series" and "AI-powered business solutions" enterprise-architecture/ALM/strategy modules (a parallel curriculum aimed at consultants and architects, not end-user makers), Dynamics 365 functional-consultant and industry/education-vertical content, and developer-only Power Platform content (component framework, Web APIs, custom-connector development, ALM/DevOps pipelines). The 93 learning paths are listed by title/summary only (out of scope for page-level fetching here).

---

## Directly relevant modules (full detail fetched)

*75 modules — Power Platform/Power Apps/Power Automate maker-level orientation and build content, Power Platform governance/DLP/administration, and Microsoft Copilot Studio agent-building content (this catalog's Copilot Studio coverage overlaps with, but is not the primary source for, the curriculum's separate Copilot Studio module). A few clusters are worth flagging explicitly before the full list, because they read as pre-built curricula the track can draw from directly:*

- **Strongest direct-reuse candidate:** *"Challenge Project - Build a booking requests app with Power Apps and Power Automate"* is a combined data-model + canvas-app + flow project, delivered as high-level specs with no step-by-step hand-holding (the learner does the synthesis). This is functionally identical in shape to what the track's app+automation capstone lesson needs — concrete scenario (booking requests), all three build skills (Dataverse table, canvas app, Power Automate flow) in one exercise, and it's explicitly framed as a challenge rather than a walkthrough.
- **Runner-up capstone candidates:** *"Challenge project - Build applications and automation solutions"* (model-driven app + canvas app + cloud flow, same "high-level spec, no walkthrough" format) and the four-module **"machine ordering" Online Workshop series** — *Create a machine ordering Power Apps canvas app*, *Create a Dataverse table for the machine ordering app*, *Create a model-driven Power Apps app for machine ordering*, and *Integrate a Power Apps app with Power Automate* — which follows one fictional company/scenario across all four modules and culminates in wiring the canvas app to a Power Automate approval flow. Either series could anchor the capstone lesson; the booking-requests challenge project is more self-contained, the machine-ordering workshop series is more scaffolded/step-by-step.
- **"Like a pro" mini-series** (*Plan your project like a pro* → *Design your app like a pro* → *Make your app like a pro* → *Deploy and refine your app like a pro* → *Document and test your Power Apps application*): a five-module, sequential app-building lifecycle — plan, design, build, deploy, document — built around one running app idea. Strong direct-reuse candidate for the track's Power Apps build lesson specifically, since it maps cleanly onto a "how to actually build an app, start to finish" narrative.
- **"Real estate solution" series** (*Build a Power Apps canvas app for a real estate solution with Copilot in Power Apps* → *Build flows for a real estate solution using Copilot in Power Automate*, plus a Power Pages equivalent that's out of this track's scope and left catalog-only): demonstrates Copilot-assisted building across Power Apps and Power Automate using one continuous scenario. Good concrete illustration of "Copilot as a maker accelerant" if the track wants to touch on that.
- **Governance/DLP cluster:** *Introduction to Microsoft Power Platform security and governance*, *Manage environmental changes*, *Plan and manage your Microsoft Power Platform environment*, and *Implementation recommendations for Microsoft Power Platform environments* all center on Data Loss Prevention (DLP) policy design, communication, and change management — this is exactly the track's governance/safe-use lesson, and the four modules together sketch a natural progression (what DLP is → plan policies → manage change → implement recommended policies for common scenarios).
- **Copilot Studio overlap:** the Copilot Studio entries here (*Build effective agents*, *Ground agents with enterprise knowledge using connectors and Azure AI Search*, *Take action in external systems using connector and REST API agent tools*, *Integrate agents with external systems via MCP*, *Design integration strategies for agents*, *Add structured automation to agents*) are genuinely useful source material for the curriculum's separate Copilot Studio module, even though Copilot Studio isn't this track's primary focus — several explicitly cover connecting agents to Power Platform connectors, which is the natural bridge between the two curriculum areas.

---

## Get started with Microsoft Power Platform for app makers
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-power-platform-app-makers/
**Level:** Intermediate | **Units:** 8
**Summary:** This module introduces the core Microsoft Power Platform functionality that you should be aware of as a maker, and provides scenarios on where you might use each element.
**Objectives:**
- How to identify which Microsoft Power Platform component to use based on a specific scenario.
- How to determine what type of app you should create based on your needs.
- Dataverse and directions on when and how to apply it.
- Environments and how makers use them.
- Copilot and why it matters to you as a maker.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Identify components 3. Create apps 4. Get started with Microsoft Dataverse 5. Introduction to environments 6. Work with Copilot in Microsoft Power Platform 7. Check your knowledge 8. Summary

---

## Describe the business value of Microsoft Power Platform services
**URL:** https://learn.microsoft.com/en-us/training/modules/describe-business-value-microsoft-power-platform-services/
**Level:** Beginner | **Units:** 11
**Summary:** This module focuses on the challenges organizations face in building efficient solutions, automating workflows, and analyzing data, and how Microsoft Power Platform addresses these needs with its suite of low-code tools, including Power Apps, Power Automate, Power BI, Power Pages, Dataverse, Power Fx, and Copilot.
**Objectives:**
- Describe Power Platform.
- Describe the business value of Power Platform.
- Describe connectors in Power Platform.
- Describe using Microsoft Dataverse to organize business data.
- Describe the value of Power Fx.
- Describe how Power Platform services work together.
- Describe the value of Copilots and generative AI features in Power Platform.
- Describe how to write effective prompts for Power Platform.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Explore Microsoft Power Platform 3. Describe the value of Microsoft Power Platform 4. Describe the value of connectors in integrating services and data 5. Describe the value of Microsoft Dataverse in organizing business data 6. Describe the value of Power Fx as a low-code solution 7. Describe how Power Platform services work together 8. Describe the value of Copilots and generative AI features in Power Platform 9. Write effective Copilot prompts for Microsoft Power Platform 10. Module assessment 11. Summary and resources

---

## Describe the business value of extending business solutions by using Microsoft Power Platform
**URL:** https://learn.microsoft.com/en-us/training/modules/describe-business-value-extend-business-solutions-microsoft-power-platform/
**Level:** Beginner | **Units:** 7
**Summary:** This module covers the native integration of Power Platform with Microsoft 365 services and how it connects to on-premises environments, including Copilot Studio and the Plan Designer.
**Objectives:**
- How to integrate Microsoft Power Platform with Microsoft 365 and Teams.
- The features of Microsoft Copilot Studio and its functionality.
- Methods to integrate on-premises systems with Microsoft Power Platform.
- The basics of the Plan Designer in Power Apps.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Describe how Microsoft Power Platform business solutions work together with Microsoft 365 apps and services 3. Describe the value of Microsoft Copilot Studio 4. Describe how Power Platform works with on-premises solutions 5. Describe the capabilities of the Plan Designer 6. Module assessment 7. Summary and resources

---

## Identify basic Microsoft Power Apps capabilities
**URL:** https://learn.microsoft.com/en-us/training/modules/identify-basic-microsoft-power-apps-capabilities/
**Level:** Beginner | **Units:** 8
**Summary:** This module introduces learners to Power Apps, which lets users build custom canvas or model-driven apps without needing extensive coding.
**Objectives:**
- Describe Power apps and data integration.
- Describe canvas apps use cases.
- Describe model-driven apps use cases and core features.
- Choose between canvas and model-driven apps based on your business need.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Describe Power Apps 3. Describe use cases of canvas apps 4. Describe use cases of model-driven apps 5. Explore model-driven app features 6. Describe the differences between canvas apps and model-driven apps 7. Module assessment 8. Summary and resources

---

## Understanding Low Code as a Traditional Developer
**URL:** https://learn.microsoft.com/en-us/training/modules/understanding-low-code-as-a-traditional-developer/
**Level:** Beginner | **Units:** 6
**Summary:** Power Apps can be a powerful tool for citizen developers and traditional developers alike. Upon finishing this module, a traditional developer will have learned how Power Apps work, what the formula language is, and how to create an app using Power Apps.
**Objectives:**
- Understand what Power Fx is and how to use it.
- Create an app using Power Apps.
- Modify an app using Power Fx.
**Prerequisites:** Access to Microsoft Excel and OneDrive.
**Unit titles:** 1. Introduction 2. What is low code? 3. Understand Power Fx 4. Exercise - Create Your First Power Apps app as a Traditional Developer 5. Module assessment 6. Summary

---

## Transform business software authoring with fusion development teams
**URL:** https://learn.microsoft.com/en-us/training/modules/transform-business-software-authoring-with-fusion-dev/
**Level:** Beginner | **Units:** 6
**Summary:** A new software development paradigm called Fusion Development teams can help software development, IT, and business teams work better together to build better apps, faster, and free citizen developers to create applications for their ever-changing needs.
**Objectives:**
- Grow productivity across business units with fusion development teams
- Increase tech intensity with a fusion development team
- Organize business and IT professionals into a fusion development team
**Prerequisites:** None specified
**Unit titles:** 1. Meet the team 2. What is tech intensity? 3. The current field inventory management system 4. Fusion team development process 5. Module assessment 6. Summary

---

## Introduction to Copilot in Microsoft Power Platform
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-copilot-power-platform/
**Level:** Beginner | **Units:** 6
**Summary:** Copilot in Microsoft Power Platform assists app makers, allowing them to quickly solve business problems. This module introduces Microsoft Copilot concepts.
**Objectives:**
- What a copilot can do
- Copilots for users and copilots for makers
- Applying critical thinking to planning and using copilots
**Prerequisites:** Basic understanding of Microsoft Power Platform
**Unit titles:** 1. Introduction 2. Accelerate solution building with Copilot 3. Get the most from Copilot 4. Design and plan with Copilot 5. Check your knowledge 6. Summary

---

## Get started with Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-flows/
**Level:** Beginner | **Units:** 9
**Summary:** Power Automate is an online workflow service that automates actions across the most common apps and services.
**Objectives:**
- Create a flow that automatically saves email attachments.
- Learn how to create a button flow to send yourself a reminder.
**Prerequisites:** Signed up for Power Automate; have OneDrive for work or school.
**Unit titles:** 1. Introducing Power Automate 2. Create a cloud flow 3. Exercise - Create recurring flows 4. Exercise - Monitor incoming emails 5. Exercise - Share flows 6. Troubleshoot flows 7. Convert a flow to an agent flow 8. Module assessment 9. Summary

---

## Build a Microsoft Power Automate flow
**URL:** https://learn.microsoft.com/en-us/training/modules/build-microsoft-power-automate-flow/
**Level:** Beginner | **Units:** 11
**Summary:** This module introduces learners to the process of building, modifying, testing, monitoring, troubleshooting, and sharing a Power Automate cloud flow, including use of Copilot for flow creation and troubleshooting and "Record with Copilot" for desktop automation.
**Objectives:**
- Describe triggers in Power Automate.
- Use Microsoft Copilot to create and modify flows in Power Automate.
- Create and test a cloud flow using Microsoft Copilot in Power Automate.
- Test Power Automate cloud flows.
- Monitor, analyze, and optimize cloud flows in Power Automate.
- Share and manage access to flows in Power Automate.
- Enhance automation with Copilot in Power Automate.
- Automate desktop workflows using Record with Copilot in Power Automate.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Create a cloud flow by using an instant, automated, or scheduled trigger 3. Create and modify cloud flows by using Copilot in Power Automate 4. Exercise - Create a cloud flow using Copilot 5. Test a cloud flow 6. Run and monitor a cloud flow 7. Share a cloud flow 8. Describe an existing cloud flow using Copilot 9. Build a basic desktop flow by using Record with Copilot 10. Module assessment 11. Summary and resources

---

## Identify Microsoft Power Automate components
**URL:** https://learn.microsoft.com/en-us/training/modules/identify-microsoft-power-automate-components/
**Level:** Beginner | **Units:** 11
**Summary:** This module introduces the core concepts of Power Automate, including workflow automation use cases, cloud flow templates, and the role of triggers and actions, plus process mining, loops and branching, approvals, and Power Automate apps.
**Objectives:**
- Describe some use cases for Power Automate workflow automation.
- Describe process mining.
- Describe cloud flow templates.
- Describe triggers, actions, and connectors in Power Automate.
- Describe loops and branching in Power Automate cloud flows.
- Discuss approval actions.
- Describe the Power Automate home page, the Power Automate mobile app, and Copilot features.
- Describe the use of flow control actions in Power Automate for Desktop.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Describe process mining 3. Describe use cases for cloud and desktop flows 4. Describe use cases for cloud flow templates 5. Describe how Power Automate cloud flows use connector triggers and actions 6. Describe loops and branching in cloud flows 7. Describe Power Automate use cases for approvals 8. Describe the Power Automate apps 9. Describe actions for Power Automate desktop flows 10. Module assessment 11. Summary and resources

---

## Build approval flows with Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/build-approval-flows/
**Level:** Beginner | **Units:** 6
**Summary:** Power Automate is an online workflow service that automates actions across the most common apps and services. In this module, you build approval flows to streamline your business, save time, and work more efficiently.
**Objectives:**
- Create and process approval requests.
- Build a flow that runs at recurring time intervals.
- Create a business process flow with conditions.
**Prerequisites:** You must be signed up for Power Automate, and have a OneDrive account.
**Unit titles:** 1. Introduction to approval flows 2. Build an approval request 3. Create a business process flow 4. Create a business process flow with conditions 5. Check your knowledge 6. Summary

---

## Automate an approval process in Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/approvals-power-automate/
**Level:** Beginner | **Units:** 7
**Summary:** Typically, a workflow process undergoes an approval step, requiring approval from a single user or multiple users, and capturing the responses so you can make decisions for the next step. This module explores the Approvals connector, approval actions and responses, captured metadata, and known issues.
**Objectives:**
- Gain insights into the Approvals connector.
- Discover the types of approval actions.
- Learn how to respond to an approval.
- Learn about the metadata that is captured from approvals.
- Review the known issues and limits.
**Prerequisites:** Basic understanding of how to create flows with SharePoint as the trigger
**Unit titles:** 1. Introduction 2. Types of approval actions 3. Respond to an approval 4. Metadata from approvals 5. Known issues and limits 6. Check your knowledge 7. Summary

---

## Email with Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/email-power-automate/
**Level:** Beginner | **Units:** 7
**Summary:** With Microsoft Power Automate, you can create emails that are sent automatically when new data is added or existing data is updated, and have email metadata captured in SharePoint automatically. This module explains how to use email actions in Power Automate with SharePoint as the data source.
**Objectives:**
- Learn about the SharePoint Connector for Power Automate.
- Use SharePoint triggers.
- Send emails by using Microsoft 365 Outlook.
- Send emails by using the Mail connector.
- Save email content to SharePoint.
**Prerequisites:** Basic understanding of how to create flows with SharePoint as the trigger
**Unit titles:** 1. Introduction 2. SharePoint triggers 3. Send emails by using Microsoft 365 Outlook 4. Send email by using Mail 5. Save email content to SharePoint 6. Check your knowledge 7. Summary

---

## Share a cloud flow with Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/share-cloud-flow/
**Level:** Beginner | **Units:** 8
**Summary:** When you create a new Power Automate cloud flow, you're the only one who can view, edit, and run it. By sharing a cloud flow, you can allow other users within your organization to run or help edit your automation. This module covers how and when to share cloud flows and which types to use.
**Objectives:**
- Learn the ways that you can share a cloud flow and the benefits of each.
- Discover whom you can share cloud flows with.
- Learn the differences in sharing various types of cloud flows.
- Learn how connections are handled when you share cloud flows.
- Find out about different options for sharing through co-ownership.
- Learn about run-only permissions.
- Discover the differences between sharing solution and non-solution cloud flows.
**Prerequisites:** Basic Power Automate experience
**Unit titles:** 1. Introduction 2. Share by using co-ownership 3. Share by using the run-only option 4. Use the Send a copy feature 5. Exercise - Send a copy 6. Solutions and sharing 7. Check your knowledge 8. Summary

---

## Streamline SharePoint processes with Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/streamline-processes/
**Level:** Beginner | **Units:** 7
**Summary:** The SharePoint Connector in Power Automate offers a powerful way to enhance your SharePoint processes, letting you automate file management, streamline list operations, and improve team collaboration, from simple notifications to more complex workflows like scheduled data archiving.
**Objectives:**
- Explore triggers and actions in the SharePoint Connector.
- Send a Teams message when someone adds an item to SharePoint.
- Archive a SharePoint list on a schedule.
- Troubleshoot the connector.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Explore triggers and actions in the SharePoint Connector 3. Exercise - Send a Teams message when an item is added to SharePoint 4. Exercise - Archive a SharePoint list on a schedule 5. Troubleshoot the connector 6. Check your knowledge 7. Summary

---

## Enhance productivity with Power Automate and the Office 365 Outlook Connector
**URL:** https://learn.microsoft.com/en-us/training/modules/enhance-productivity/
**Level:** Beginner | **Units:** 7
**Summary:** This module explains the core capabilities of the Office 365 Outlook Connector, starting with how to integrate it seamlessly into your Power Automate flows. It provides real-world examples, such as sending emails based on SharePoint activity, sending approval requests, and automating follow-up responses, and covers how to configure and customize actions like Send an email (V2) and Get calendar events (V2).
**Objectives:**
- Explore triggers and actions in the SharePoint Connector
- Send an email with attachments
- Create a meeting request based on a SharePoint list update
- Troubleshoot the connector
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Explore triggers and actions in the SharePoint Connector 3. Exercise - Send an email with attachments 4. Exercise - Create a meeting request based on a SharePoint list update 5. Troubleshoot the connector 6. Check your knowledge 7. Summary

---

## Approvals Kit in Power Automate workshop overview
**URL:** https://learn.microsoft.com/en-us/training/modules/approvals-kit-workshop/
**Level:** Intermediate | **Units:** 9
**Summary:** When handling business processes that require multiple levels of approval and conditional logic based on input data, the Power Automate Approvals connector can be a valuable tool in your Microsoft Power Platform solution—but building these complex approval processes can be time-consuming and challenging. The Approvals Kit in Power Automate is a starter solution that provides a no-code method to model your business approval process and start approvals using a Power Platform connector, making automation of approval processes easier.
**Objectives:**
- The Approvals Kit and its benefits
- How to define a business approval process with a single stage and node
- How to trigger a business approval process from a Power Automate cloud flow
- How to extend the approvals process with conditional logic
- How to define multiple stages for the approval process
- How to handle cases when approvers are out of office
- Known issues and limitations of the Approvals Kit
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Import the Contoso Coffee solution 3. Work with Contoso Coffee 4. Create your first Approval Kit workflow 5. Trigger a defined approval 6. Add conditionals and stages 7. Approvals delegation and out of office 8. Check your knowledge 9. Summary

---

## Best practices for error handling in Power Automate flows
**URL:** https://learn.microsoft.com/en-us/training/modules/error-handling/
**Level:** Intermediate | **Units:** 5
**Summary:** Getting notifications when a flow fails is critical to maintaining business continuity, and the notification should provide the cause of the error so you can resolve it quickly. This module focuses on how to use Configure run after, an option available for flow actions, to help isolate errors, and it also overviews Power Automate's built-in error reports.
**Objectives:**
- Gain insight into the settings options for flow actions
- Learn about the Configure run after option
- Use the Configure run after option to handle errors
- Discover Microsoft Power Automate analytics
**Prerequisites:** Basic understanding of how to create flows with SharePoint as the trigger
**Unit titles:** 1. Introduction 2. Configure run after option 3. Power Automate analytics 4. Check your knowledge 5. Summary

---

## Use Copilot in Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/use-copilot-power-automate/
**Level:** Beginner | **Units:** 6
**Summary:** Use Copilot while building Power Automate flows to quickly build or understand flows, understand Power Fx, and observe what Copilot can do for your business process.
**Objectives:**
- Create a flow by describing what you want it to do
- Build prompts to modify flows by using Copilot for Power Automate
- Use Copilot to help guide makers with flow how-to explanations
- Create a cloud flow with Copilot assistance
**Prerequisites:** Basic understanding of how to create Power Automate flows; access to an environment with Dataverse that has sample apps installed
**Unit titles:** 1. Introduction 2. Describe and refine your flow 3. Edit a flow with Copilot 4. Exercise - Build a cloud flow by using Copilot for Power Automate 5. Check your knowledge 6. Summary

---

## Take your first steps with Power Automate desktop app
**URL:** https://learn.microsoft.com/en-us/training/modules/pad-first-steps/
**Level:** Beginner | **Units:** 7
**Summary:** Learn how to get started with the Microsoft Power Automate desktop app console and flow designer. The console helps you create and handle flows, while the flow designer is the development environment of the platform.
**Objectives:**
- Explore the console and the flow designer
- Learn how to use the core features of the Power Automate desktop app platform
- Create and run a flow
**Prerequisites:** Power Automate desktop app should be installed
**Unit titles:** 1. Introduction to Power Automate desktop app 2. Console overview 3. Flow designer overview 4. Create a simple flow 5. Exercise - Create and run a simple flow 6. Check your knowledge 7. Summary

---

## Build your first Power Automate for desktop flow
**URL:** https://learn.microsoft.com/en-us/training/modules/build-first-desktop-flow/
**Level:** Beginner | **Units:** 8
**Summary:** Learn the basics of Power Automate for desktop flows. This module also covers how to build your first flow to help automate a repetitive task, freeing up time for more important endeavors.
**Objectives:**
- Learn how to use Power Automate to create a new desktop flow
- Record actions that are performed in a desktop-based application
- Perform a test run of the new desktop flow
**Prerequisites:** Basic understanding of Microsoft Power Automate; recommended to view lab instructions on a separate device or in a printout
**Unit titles:** 1. Introduction 2. Set up the environment 3. Explore Power Automate for desktop 4. Create your first Power Automate for desktop flow 5. Record Power Automate for desktop actions 6. Edit and test recorded actions 7. Check your knowledge 8. Summary

---

## Get started with Power Apps canvas apps
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-with-powerapps/
**Level:** Beginner | **Units:** 9
**Summary:** Power Apps lets you build three types of apps: canvas apps, model-driven apps, and Power Pages sites. This module focuses on canvas apps—the flexible, screen-based apps you design pixel-by-pixel and connect to virtually any data source—exploring the canvas app maker portal, how app controls and data sources work together, and building your first canvas app from an Excel spreadsheet.
**Objectives:**
- Describe what canvas apps are and how they differ from other Power Apps app types
- Navigate the Power Apps maker portal and identify key canvas app creation options
- Connect a canvas app to a data source and use gallery and form controls to display and edit data
- Build a canvas app from an Excel workbook using both the template path and a blank canvas
- Use Copilot to generate a canvas app from an uploaded file
**Prerequisites:** Access to Microsoft Power Apps, Excel, and OneDrive
**Unit titles:** 1. Introduction to Power Apps 2. Start Power Apps 3. Exercise - Create your first app in Power Apps 4. Power Apps data sources 5. Exercise - Create an app from Excel using Copilot 6. Use Power Apps with Power Automate and Power BI 7. Designing a Power Apps app 8. Check your knowledge 9. Summary

---

## Build your first canvas app with Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/build-first-canvas-app/
**Level:** Beginner | **Units:** 7
**Summary:** Power Apps allows you to easily develop mobile and web apps for any business need—even if you have no technical or development experience. This module explains the process of creating your first app with Power Apps, additional considerations for first-time app creators, and the related technologies you can apply to create a more complete and automated business solution.
**Objectives:**
- Create an app from a template
- Discover the related technologies that you can use in Power Apps
- Learn about the various Power Apps data sources and basic data modeling
**Prerequisites:** Microsoft Office 365 license/access to an Office 365 environment and a Microsoft Power Apps license/trial
**Unit titles:** 1. Introduction 2. Power Apps building blocks 3. Exercise - Create an expenses app for your organization 4. Manage and maintain your app 5. Build a more complete Power Apps solution 6. Check your knowledge 7. Summary

---

## Build a canvas app
**URL:** https://learn.microsoft.com/en-us/training/modules/build-canvas-app/
**Level:** Beginner | **Units:** 13
**Summary:** This module covers how to build and share canvas apps in Power Apps by connecting to data, using common controls, and designing responsive layouts with containers. It introduces creating and editing apps through natural language with Copilot, explores Copilot controls and agent builder use cases, and includes a hands-on exercise to build a canvas app with Copilot.
**Objectives:**
- Choose and connect data sources for Power Apps canvas apps
- Create canvas apps using Excel data
- Describe and use controls
- Build responsive layouts with containers
- Build and edit apps with Copilot
- Integrate and customize Copilot controls
- Automate business processes with Agent builder
- Preview, test, and publish a canvas app
- Manage and share canvas apps
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Connect to data sources by using connectors 3. Create an app from data 4. Describe common controls 5. Build responsive pages using containers 6. Create and modify an app through conversation 7. Exercise - Create a canvas app 8. Describe the capabilities of Copilot controls 9. Describe use cases for Agent Builder 10. Preview, test, and publish an app 11. Share a canvas app 12. Module assessment 13. Summary and resources

---

## Customize a canvas app in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/customize-apps-in-powerapps/
**Level:** Beginner | **Units:** 9
**Summary:** A working app is just the starting point. In this module, you shape how your canvas app looks, behaves, and scales—customizing gallery layouts, writing Power Fx formulas, building screen navigation, adding AI capabilities, and creating reusable components that work across your entire solution.
**Objectives:**
- Customize gallery and form controls to display and edit data the way your users need it
- Build screen navigation using Power Fx Navigate() and Back() formulas
- Apply Power Fx formulas to control appearance, filter data, and handle errors
- Add AI capabilities to your app using Microsoft 365 Copilot controls
- Create named formulas, user-defined functions, and reusable component libraries
**Prerequisites:** Basic experience with developing canvas apps
**Unit titles:** 1. Introduction 2. Improve your app by making basic customizations 3. Explore controls and screens in canvas apps 4. Apply Power Fx formulas to canvas app controls 5. Work with Power Fx formulas in canvas apps 6. Create screen navigation in a canvas app 7. Build reusable components and formulas in canvas apps 8. Check your knowledge 9. Summary

---

## Manage apps in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/manage-apps-in-powerapps/
**Level:** Beginner | **Units:** 7
**Summary:** Manage app versions, app sharing, and environments in Power Apps.
**Objectives:**
- Learn how to view and restore app versions
- Explore how to share an app, including permissions and notifications
- Learn about what environments are, how to create them, and how to manage security
- Find more information about Power Apps
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Exercise - Manage app versions in Power Apps 3. Exercise - Share apps in Power Apps 4. Exercise - Understand environments in Power Apps 5. Review of managing Power Apps 6. Check your knowledge 7. Summary

---

## Connect to other data in a Power Apps canvas app
**URL:** https://learn.microsoft.com/en-us/training/modules/connect-to-other-data-in-powerapps-canvas-app/
**Level:** Intermediate | **Units:** 5
**Summary:** Do you need to connect to data that isn't tabular? This module will help with that, covering action-based connectors, Power Automate (Flow), and user data.
**Objectives:**
- Understand and use action-based connectors
- Integrate user information and user-profile information into a canvas app
- Use Power Automate with Power Apps
**Prerequisites:** A basic understanding of how to create a Power Apps canvas app
**Unit titles:** 1. Overview of the different data sources 2. Work with action data 3. Power Automate is a companion to Power Apps 4. Module assessment 5. Summary

---

## Write data in a Power Apps canvas app
**URL:** https://learn.microsoft.com/en-us/training/modules/write-data/
**Level:** Intermediate | **Units:** 8
**Summary:** Forms can be used to view, edit, and create records. This module demonstrates how to use forms to write data to your data source, covering form setup, the different form modes, and how to configure a submit button.
**Objectives:**
- Understand how to work with forms in canvas apps
- Configure a submit button to write data
- Use and understand the different form modes
**Prerequisites:** A basic understanding of how to create a Power Apps canvas app
**Unit titles:** 1. Introduction to forms 2. Form modes 3. Adding and customizing an Edit form 4. Submit your form 5. Special properties 6. Exercise - Working with forms 7. Module assessment 8. Summary

---

## Work with external data in a Power Apps canvas app
**URL:** https://learn.microsoft.com/en-us/training/modules/work-with-external-data/
**Level:** Intermediate | **Units:** 9
**Summary:** Do you need to connect an app to access data? Then this module is for you. It focuses on connecting your app to a data source.
**Objectives:**
- Understand data sources for canvas apps in Power Apps
- Use the Collect function
**Prerequisites:** A basic understanding of how to create a canvas app in Power Apps
**Unit titles:** 1. Introduction 2. Data-source overview 3. Add a data source 4. Add Office 365 users to your application 5. Display and interact with your data in a gallery 6. Move data between collections and data sources by using Collect 7. Exercise - Work with external data in a canvas app 8. Module assessment 9. Summary

---

## Get started with Power Fx functions
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-power-fx/
**Level:** Intermediate | **Units:** 7
**Summary:** Learn how Power Fx functions in Dataverse simplify business logic with a low-code way to build reusable, real-time logic that helps improve performance, standardize processes, and integrate across Microsoft Power Platform.
**Objectives:**
- Basics of Power Fx functions
- Business value of using Power Fx functions
- Common business problems that Power Fx functions can address
- How to create and test a simple Power Fx function
**Prerequisites:** System customizer security role membership in the Power Platform environment; access to Microsoft Dataverse; basic understanding of Power Fx
**Unit titles:** 1. Introduction 2. Overview of Power Fx functions 3. Simplify business logic 4. Improve data architecture with Power Fx functions 5. Exercise - Build and test a Power Fx function 6. Check your knowledge 7. Summary

---

## Build Power Fx functions
**URL:** https://learn.microsoft.com/en-us/training/modules/build-power-fx/
**Level:** Intermediate | **Units:** 8
**Summary:** Streamline business logic by using Power Fx functions. Run your function from Power Apps and Power Automate to perform calculations in real time.
**Objectives:**
- Apply the value of Power Fx functions in building robust business applications.
- Build Power Fx functions to use in Microsoft Power Platform.
- Analyze and troubleshoot Power Fx functions.
**Prerequisites:** System customizer security role membership in the Microsoft Power Platform environment; access to Microsoft Dataverse; basic understanding of Power Fx; basic knowledge of Power Apps and Power Automate
**Unit titles:** 1. Introduction 2. Basics of building Power Fx functions 3. Explore business scenarios for Power Fx functions 4. Exercise - Build a Power Fx function and integrate with a canvas app 5. Exercise - Build a Power Fx function and integrate with a Power Automate flow 6. Troubleshoot a Power Fx function 7. Check your knowledge 8. Summary

---

## Use and understand Controls in a canvas app in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/controls-canvas-apps/
**Level:** Intermediate | **Units:** 11
**Summary:** Controls help create a better experience for the user and collect the appropriate data. This module helps you understand and use Controls.
**Objectives:**
- Understand how to use controls in a canvas app
- Use the different types of controls
- Understand how Galleries and Forms relate to controls
**Prerequisites:** Basic knowledge of how to create a Power Apps canvas app.
**Unit titles:** 1. Introduction to controls 2. Core properties of controls 3. Entering and displaying data with text controls 4. Additional controls for enhancing your app's usability 5. Media 6. Modern controls 7. Work with component libraries 8. Exercise - Create a canvas app with unique controls 9. Exercise - Upload file to SharePoint document library 10. Module assessment 11. Summary

---

## How to build the User Interface in a canvas app in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/how-to-build-ui-canvas-app/
**Level:** Intermediate | **Units:** 9
**Summary:** In this module, learners will learn how to build UI for their app including theming, icons, images, personalization, form factors, and controls. In their learning path, thus far, learners have used basic controls with little to no customization. This unit shows how to make an app more personal and help it fit branding or personal requirements.
**Objectives:**
- Understand the basics of building the UI through themes, icons, control customization, and images.
- Use personalization in a canvas app.
- Learn how to preview and modify an app to fit different form factors.
**Prerequisites:** A basic understanding of how to create a Power Apps canvas app. General knowledge of Controls is also helpful but not required.
**Unit titles:** 1. Use themes to quickly change the appearance of your app 2. Brand a control 3. Icons 4. Images 5. Personalization 6. Build for phones or tablets 7. Exercise - Create and adjust UI for a new canvas app 8. Module assessment 9. Summary

---

## Build a mobile-optimized app from Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/build-mobile-optimized/
**Level:** Beginner | **Units:** 7
**Summary:** Microsoft Power Apps is a powerful platform for building applications that can run on a user's desktop or mobile device. Depending on the requirements of the application, the canvas app from Power Apps might be used on mobile devices exclusively. In those instances, the canvas app must be mobile-optimized to provide the best user experience possible, which you can achieve through various design factors that will be covered in this module.
**Objectives:**
- Learn about the concept of a mobile-optimized application.
- Discover the components of a mobile-optimized canvas app.
- Build a mobile-optimized canvas app.
- Review the performance considerations in a canvas app.
- Monitor the performance of a canvas app.
**Prerequisites:** Access to Microsoft Power Apps; access to Microsoft Excel
**Unit titles:** 1. Introduction 2. Learn about mobile-optimized apps 3. Identify components to make a canvas app mobile-optimized 4. Create a mobile-optimized app that uses responsive designs 5. Identify performance considerations for a mobile-optimized canvas app 6. Check your knowledge 7. Summary

---

## Publish, share, and maintain a canvas app
**URL:** https://learn.microsoft.com/en-us/training/modules/publish-share-maintain-app/
**Level:** Beginner | **Units:** 7
**Summary:** You've built your first app. Now, it's time to publish, share it with others, and maintain subsequent versions of the app.
**Objectives:**
- Introduce the primary app build.
- Launch future iterations of the app.
- Manage versions and publish your app.
**Prerequisites:** Basic understanding of Microsoft Power Apps canvas apps and Microsoft Dataverse
**Unit titles:** 1. Introduction 2. Publish your app 3. Share your app 4. Maintain your app 5. Application lifecycle management 6. Check your knowledge 7. Summary

---

## Get started with Power Apps and SharePoint
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-power-apps-sharepoint/
**Level:** Beginner | **Units:** 8
**Summary:** SharePoint Online is one of the best data sources for Power Apps in terms of compatibility and ease of use. This module describes how to use Power Apps and SharePoint together as a simple introduction into the larger Microsoft Power Platform.
**Objectives:**
- Learn about Power Apps canvas apps.
- Learn how to relate a SharePoint list to a Power Apps application.
- Discover the uses and benefits of SharePoint as a data source for Power Apps.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Benefits of using Power Apps with SharePoint 3. Create your first Power Apps application with SharePoint 4. Customize your Power Apps with SharePoint 5. Exercise - Build an inventory app with SharePoint 6. Share, publish, govern, and secure Power Apps and SharePoint 7. Check your knowledge 8. Summary

---

## Build your first app with Power Apps and Dataverse for Teams
**URL:** https://learn.microsoft.com/en-us/training/modules/build-app-dataverse-teams/
**Level:** Beginner | **Units:** 7
**Summary:** Today's business problems increasingly require modern digital solutions. With a low-code platform, anyone with a great idea can build a digital app. Dataverse for Teams allows you to build modern digital apps and deploy them to help you and your team solve those problems.
**Objectives:**
- Create an app by using the hero template.
- Customize and publish your app.
- Install templates.
**Prerequisites:** Familiarity with Microsoft Teams
**Unit titles:** 1. Introduction 2. Create your first app with the hero template 3. Customize your app with Power Apps Studio 4. Publish your app 5. Install template apps 6. Check your knowledge 7. Summary

---

## Use Copilot in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/use-copilot-power-apps/
**Level:** Beginner | **Units:** 9
**Summary:** Copilot can help you start building a canvas app with a natural language description of your needs. It's also available as you modify those apps to help you more efficiently make a Power Apps application. Additionally, you can set up copilots in your apps so that people can use the copilot in the context of the app data.
**Objectives:**
- Start building apps by using Copilot in Power Apps.
- Refine your initial app design by using Copilot prompts.
- Use Copilot to help you modify apps.
- Add a copilot for users of Power Apps.
**Prerequisites:** Basic understanding of Power Apps; basic understanding of Dataverse tables; access to an environment that has Dataverse sample apps installed
**Unit titles:** 1. Introduction 2. Describe and refine your app 3. Work with screens and controls 4. Exercise - Use Copilot to build a canvas app 5. Copilots for users in canvas apps 6. Simulation - Copilots for users in model-driven apps 7. Exercise - Add Copilot to a model-driven app 8. Check your knowledge 9. Summary

---

## Build a Power Apps canvas app for a real estate solution with Copilot in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/build-canvas-app-real-estate-power-apps-copilot/
**Level:** Beginner | **Units:** 4
**Summary:** In this module, you explore Copilot in Power Apps generating a Dataverse table of data from natural language and create a new app within Power Apps based on that data.
**Objectives:**
- Create a canvas app by using Copilot in Power Apps.
- Customize the Dataverse table data that Copilot generates.
- Add more data to the table.
**Prerequisites:** A Power Apps developer environment (based in the United States region) with a licensed user to complete these exercises; complete the previous module in this learning path
**Unit titles:** 1. Introduction 2. Exercise – Create a canvas app with Copilot in Power Apps 3. Check your knowledge 4. Summary

---

## Build flows for a real estate solution using Copilot in Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/build-real-estate-power-automate-copilot/
**Level:** Beginner | **Units:** 5
**Summary:** This module covers how to create flows by using Copilot in Power Automate. Learn how to refine your flow by using Copilot and how to use the format through example AI capabilities. Copilot in Power Automate helps you automate tedious tasks and save time.
**Objectives:**
- Features and capabilities of Copilot in Power Automate.
- How to create and manage flows with Copilot in Power Automate.
**Prerequisites:** A Power Automate license; a Microsoft Power Platform environment in a US preview region; complete the previous module in this learning path
**Unit titles:** 1. Introduction 2. Exercise - Create an approval flow with Copilot in Power Automate 3. When to use Copilot in Power Automate 4. Check your knowledge 5. Summary

---

## Plan your project like a pro
**URL:** https://learn.microsoft.com/en-us/training/modules/plan-app-project/
**Level:** Beginner | **Units:** 8
**Summary:** Professionals don't start building an app from Power Apps without proper planning. Crafting an effective plan saves you time, energy, and costs because you're able to answer essential questions before starting to build your app. The planning phase is the most critical step in the application lifecycle management (ALM) cycle.
**Objectives:**
- Identify the problem that the app resolves.
- Determine who will use the app.
- List the goals and objectives that your app will meet for users.
**Prerequisites:** Basic solutions and delivery process experience
**Unit titles:** 1. Introduction 2. Identify the business problem to solve 3. Analyze the current business process 4. Optimize the business process with your solution 5. Example - Identify automation opportunities 6. Create a project plan 7. Check your knowledge 8. Summary

---

## Design your app like a pro
**URL:** https://learn.microsoft.com/en-us/training/modules/design-app/
**Level:** Beginner | **Units:** 7
**Summary:** You've identified the problem that you're trying to resolve, and you've focused on creating a project plan to deliver that solution effectively. Now, your next task is to design the app.
**Objectives:**
- Analyze the different tasks to be done when using the app.
- Prepare the specifications and designs of your app.
- Decide what the user experience will be.
**Prerequisites:** Basic solutions and delivery process experience
**Unit titles:** 1. Introduction 2. Design your data structure 3. Determine which type of app to make 4. Determine the type of app to make and the placement of logic 5. Secure the data 6. Check your knowledge 7. Summary

---

## Make your app like a pro
**URL:** https://learn.microsoft.com/en-us/training/modules/make-app/
**Level:** Beginner | **Units:** 12
**Summary:** You've planned and designed your app. Now, you use the available tools to help make your design a reality.
**Objectives:**
- Set up data sources.
- Create a solution.
- Set up automation.
- Make your app more secure.
**Prerequisites:** Basic Microsoft Dataverse experience
**Unit titles:** 1. Introduction 2. Set up tables and data connectors 3. Work with solutions 4. Exercise - Prepare for the Dive Center canvas app 5. Make a canvas app 6. Exercise - Create the Dive Center canvas app 7. Make a model-driven app 8. Create Power Automate flows 9. Exercise - Connect a flow to an app 10. Exercise - App authorization 11. Check your knowledge 12. Summary

---

## Deploy and refine your app like a pro
**URL:** https://learn.microsoft.com/en-us/training/modules/deploy-refine-app/
**Level:** Intermediate | **Units:** 8
**Summary:** Your app has been tested and is ready to go. Now, it's time to deploy and share it with your users. After apps have been deployed, it's common for them to evolve and improve over time as people begin using the app.
**Objectives:**
- Deploy your app and help users discover it.
- Get feedback and usage information to help refine your app.
**Prerequisites:** Basic Power Apps experience
**Unit titles:** 1. Introduction 2. Publish the app 3. Share the app 4. Use QR codes 5. Exercise - Embed your app into other Microsoft applications 6. Collect feedback and analyze telemetry 7. Check your knowledge 8. Summary

---

## Document and test your Power Apps application
**URL:** https://learn.microsoft.com/en-us/training/modules/document-test-powerapps-app/
**Level:** Beginner | **Units:** 7
**Summary:** In this module, you'll learn best practices around testing and documenting your Power Apps application.
**Objectives:**
- Learn about the different types of test plans and components of a good test plan
- Identify and discuss optimization tools and performance tuning
- Learn about the benefits of documenting your application
**Prerequisites:** None specified
**Unit titles:** 1. Create test plans 2. User interface testing 3. Performance optimization 4. Diagnostics and analytics 5. Documentation and the customer 6. Module assessment 7. Summary

---

## Get started with model-driven apps in Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-with-model-driven-apps-in-powerapps/
**Level:** Beginner | **Units:** 13
**Summary:** Model-driven app design is an approach that focuses on quickly adding components to your apps, including dashboards, forms, views, and charts, with little to no code. Unlike canvas app development, where the designer has total control over layout, much of the layout in model-driven apps is determined by the components you add, emphasizing quick access to business data for decision-making.
**Objectives:**
- Model-driven app design
- Creating a model-driven app
**Prerequisites:** A Microsoft Power Apps account. If you don't already have a Power Apps account, select the "Get started free" link on the Power Apps home page.
**Unit titles:** 1. Introducing model-driven apps 2. Components of model-driven apps 3. Design model-driven apps 4. Exercise - Create a model-driven app 5. Build pages with generative AI 6. Exercise - Control security when sharing model-driven apps 7. Incorporate business process flows 8. Add logic to commands with Power Fx 9. Exercise - Create a model-driven app 10. Enable Copilot chat for app users 11. Add agents to your model-driven app 12. Module assessment 13. Summary

---

## Build a model-driven app
**URL:** https://learn.microsoft.com/en-us/training/modules/build-model-driven-app/
**Level:** Beginner | **Units:** 9
**Summary:** This module guides learners through building, modifying, and sharing model-driven apps using Microsoft Power Apps with the assistance of Copilot. It covers creating apps from Dataverse tables, modifying forms and views, and sharing model-driven apps effectively within an organization.
**Objectives:**
- Describe the components of a model-driven app
- Create a data model for a model-driven app using Microsoft Dataverse
- Create and modify forms in model-driven apps
- Customize views in model-driven apps; build and customize a model-driven app using Power Apps
- Describe role-based security and sharing in model-driven apps
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Components of model-driven-apps 3. Create a model-driven app from tables 4. Modify forms 5. Create and modify views 6. Exercise - Create a model-driven app 7. Share a model-driven app 8. Module assessment 9. Summary and resources

---

## How to build your first model-driven app with Dataverse
**URL:** https://learn.microsoft.com/en-us/training/modules/build-first-model-driven-app-dataverse/
**Level:** Beginner | **Units:** 6
**Summary:** This module focuses on the building blocks of Dataverse and model-driven apps for learners who want to quickly build apps with little to no code. These key components help you build quick business apps in your organization.
**Objectives:**
- Discover the value and key features of Dataverse
- Learn about the value and key features of model-driven apps
- Explore sample model-driven template apps
**Prerequisites:** A basic understanding of Power Apps and Dataverse
**Unit titles:** 1. Introduction to Dataverse 2. Introduction to model-driven apps 3. Model-driven apps, powered by Microsoft Dataverse 4. Explore sample apps 5. Check your knowledge 6. Summary

---

## Customize views and forms for model-driven apps
**URL:** https://learn.microsoft.com/en-us/training/modules/customize-view-forms/
**Level:** Beginner | **Units:** 6
**Summary:** Learn how to adapt tables by using the two form types, views and forms. These form types consume data from your tables, aided by relationships, allowing the app maker to display data and letting app users interact with it.
**Objectives:**
- Discover the difference between views and forms
- Learn how to modify table views
- Learn how to modify table forms
**Prerequisites:** Basic understanding of Microsoft model-driven apps and Microsoft Dataverse
**Unit titles:** 1. Introduction 2. Exercise - Modify table views 3. Modify table forms in Dataverse 4. Exercise - Model table forms 5. Check your knowledge 6. Summary

---

## Transform a business process to a model-driven app
**URL:** https://learn.microsoft.com/en-us/training/modules/model-driven-app-solution/
**Level:** Beginner | **Units:** 5
**Summary:** A difficult aspect of becoming a maker in Microsoft Power Platform is knowing how to start with your company's existing data and translate it into a model-driven app. This module introduces the data and business scenario the solution will address, helping you think of a model-driven app, built on Power Apps and Dataverse, as the solution.
**Objectives:**
- Learn about the data and solution that is being built with this learning path
- Learn how to relate a Microsoft Excel-based solution to model-driven apps from Power Apps
- Gain insight into model-driven app design decisions
**Prerequisites:** Basic understanding of Microsoft model-driven apps and Microsoft Dataverse
**Unit titles:** 1. Introduction 2. Complete model-driven app solution 3. Model-driven app data model 4. Check your knowledge 5. Summary

---

## Create a machine ordering Power Apps canvas app - Online Workshop
**URL:** https://learn.microsoft.com/en-us/training/modules/power-apps-canvas-app-online-workshop/
**Level:** Beginner | **Units:** 6
**Summary:** In this module, you begin building a Microsoft Power Platform solution, starting with a Power Apps canvas app for machine ordering that allows different Contoso locations to order coffee machines. In later exercises you build the data model, a model-driven app, and add automation with a Power Automate cloud flow for approvals.
**Objectives:**
- Create a canvas app
- Add screens to your app
- Use Power Fx formulas in your app
- Navigate between screens
- Customize galleries on your screens
- Capture a collection from your app
**Prerequisites:** Designed for use with the App in a Day instructor-led course. Requires an environment with a licensed user to complete the exercises, completion of prior setup steps, and the Microsoft Excel file used in the exercises.
**Unit titles:** 1. Introduction 2. Exercise - Create the app in Power Apps 3. Exercise - Add a machine gallery and connect to the data source 4. Exercise - Add the compare screen 5. Check your knowledge 6. Summary

---

## Create a model-driven Power Apps app for machine ordering - Online Workshop
**URL:** https://learn.microsoft.com/en-us/training/modules/power-apps-model-driven-apps-online-workshop/
**Level:** Beginner | **Units:** 7
**Summary:** Continuing the machine-ordering scenario, this module has you build a Power Apps model-driven app for the back-office staff who fulfill machine requests submitted through the earlier canvas app. Using the model-driven app style lets you take advantage of business process flows to keep back-office staff on track for each request.
**Objectives:**
- Create a standalone model-driven app
- Customize forms for the model-driven app
- Use a business process flow to guide users through a process
**Prerequisites:** Recommended to complete in sequence within the "Create a machine ordering app with Power Apps - Online Workshop" learning path; designed for use with the App in a Day instructor-led course.
**Unit titles:** 1. Introduction 2. Exercise - Create an app and add columns to the Machine Order table 3. Exercise - Add a business process flow 4. Exercise - Modify the form and view 5. Exercise - Test the application 6. Check your knowledge 7. Summary

---

## Create a Dataverse table for the machine ordering app - Online workshop
**URL:** https://learn.microsoft.com/en-us/training/modules/dataverse-lab-manual-online-workshop/
**Level:** Beginner | **Units:** 7
**Summary:** Microsoft Dataverse adds scalable, straightforward data storage and modeling to Power Apps. In this module, you use Dataverse to model and store data from the machine-ordering canvas app built in a previous module, using the same technology framework that Dynamics 365 apps are built on.
**Objectives:**
- Create a custom table and add custom columns to it
- Use the Power Apps form control to populate the table
- View the table data
- Create a calculated column
- Implement a server-side business rule
**Prerequisites:** Recommended to complete in sequence within the "Create a machine ordering app with Power Apps - Online Workshop" learning path; designed for use with the App in a Day instructor-led course.
**Unit titles:** 1. Introduction 2. Exercise - Explore Microsoft Dataverse 3. Exercise - Create custom tables and columns 4. Exercise - Connect data from the canvas app 5. Exercise - Building apps with Copilot 6. Check your knowledge 7. Summary

---

## Integrate a Power Apps app with Power Automate - Online Workshop
**URL:** https://learn.microsoft.com/en-us/training/modules/integrate-power-apps-online-workshop/
**Level:** Beginner | **Units:** 8
**Summary:** In this module, you create a flow that uses the Modern Approvals service to automate an approval workflow: it sends an email to the selected approver and takes an action based on their response.
**Objectives:**
- Create a flow that triggers when a new Microsoft Dataverse row is created
- Automate sending approval requests
- Customize the approval based on the Microsoft Dataverse row
- Use the Approval center
**Prerequisites:** You should already have a canvas app with two screens (built in earlier modules). Recommended to complete in sequence within the "Create a machine ordering app with Power Apps - Online Workshop" learning path; designed for use with the App in a Day instructor-led course.
**Unit titles:** 1. Introduction 2. Exercise - Create an approval request flow 3. Exercise - Create conditional logic 4. Exercise - Test the cloud flow 5. Exercise - Update the flow 6. Optional exercise - Add a Teams notification 7. Check your knowledge 8. Summary

---

## Guided Project - Create and manage canvas apps with Power Apps
**URL:** https://learn.microsoft.com/en-us/training/modules/guided-project-create-manage-canvas-apps/
**Level:** Intermediate | **Units:** 5
**Summary:** Create your own data model and canvas app to support a scenario for a fictional company. You're provided high-level specifications on the custom tables, columns, and canvas app needed to complete this project. This is a Guided Project module where you complete an end-to-end project by following step-by-step instructions.
**Objectives:**
- Connect to data sources in canvas apps
- Build canvas app screens
- Select appropriate assets and components
- Add canvas app assets and components to screens
**Prerequisites:** You should understand application development, writing formulas such as those in Excel, and creating, reading, updating, and deleting data.
**Unit titles:** 1. Introduction 2. Prepare 3. Exercise - Create a canvas app that connects to a data source 4. Module assessment 5. Summary

---

## Guided Project - Create and manage automated processes with Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/create-manage-automated-processes-with-power-automate/
**Level:** Beginner | **Units:** 5
**Summary:** Create your own data model and flow to support a scenario for a fictional company. You'll be provided with high-level specifications on the custom tables, columns, and flow needed to complete this project.
**Objectives:**
- Customize a Dataverse database to meet business requirements
- Create a Power Automate flow based on provided specifications
**Prerequisites:** Experience creating custom tables and columns in Dataverse; experience building Power Automate cloud flows
**Unit titles:** 1. Introduction 2. Prepare 3. Exercise - Build a Power Automate flow to send automated emails 4. Module assessment 5. Summary

---

## Challenge project - Build applications and automation solutions
**URL:** https://learn.microsoft.com/en-us/training/modules/challenge-project-build-applications-automation-solutions/
**Level:** Intermediate | **Units:** 8
**Summary:** Configure your own Microsoft Power Platform model-driven app, canvas app, and Power Automate cloud flow to support a scenario for a fictional company, based on high-level specifications for the company's applications and automation requirements. This is a Challenge Project module where you complete an end-to-end project using high-level guidance; there are no step-by-step instructions.
**Objectives:**
- Evaluate requirements
- Perform gap analysis of existing assets
- Create needed assets from the stated requirements
- Compose apps and automation
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Prepare 3. Exercise - Create Microsoft Dataverse tables, columns, and additional assets 4. Exercise - Compose a model-driven app 5. Exercise - Build a canvas app 6. Exercise - Automate with a cloud flow 7. Module assessment 8. Summary

---

## Challenge Project - Build a booking requests app with Power Apps and Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/challenge-project-build-booking-requests-app-with-power-apps-power-automate/
**Level:** Intermediate | **Units:** 6
**Summary:** Create your own data model, app, and flow to support a scenario for a fictional company, based on high-level specifications for the custom tables, columns, canvas app, and flows needed. This is a Challenge Project module where you complete an end-to-end project using high-level guidance; there are no step-by-step instructions.
**Objectives:**
- Customize a Dataverse database to meet business requirements
- Create a Power Apps canvas app based on provided specifications
- Create a Power Automate flow based on provided specifications
**Prerequisites:** Experience creating custom tables and columns in Dataverse; experience building Power Apps canvas apps; experience building Power Automate cloud flows
**Unit titles:** 1. Introduction 2. Prepare 3. Exercise - Build a data model and create a canvas app 4. Exercise - Build Power Automate flows to send automated emails 5. Module assessment 6. Summary

---

## Challenge project - Create Microsoft Power Platform solutions
**URL:** https://learn.microsoft.com/en-us/training/modules/challenge-project-create-microsoft-power-platform-solutions/
**Level:** Intermediate | **Units:** 5
**Summary:** In this challenge project, you create your own solutions to stated problems for a customer, analyzing and architecting solutions based on a series of sheets in a planning workbook.
**Objectives:**
- Choose a customer based on a provided industry
- Get to know the customer
- Evaluate the current state of technology
- Compare to the stated needs
- Perform discovery and planning exercises
- Complete the project workbook
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Prepare 3. Exercise - Create solutions for customers using Power Platform 4. Module assessment 5. Summary

---

## Guided Project - Create document process model and email approval with AI Builder and Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/guided-project-document-process-model-email-approval-ai-builder/
**Level:** Intermediate | **Units:** 6
**Summary:** In this module, practice building a system that extracts data from scanned invoices and creates an approval email system. The lab offers interactive practice with real-world scenarios for business-specific challenges.
**Objectives:**
- Create a document processing model
- Create a Power Automate flow that consumes your document processing model for approvals
**Prerequisites:** A Power Apps or Power Automate license; access to Microsoft Dataverse; an AI Builder add-on or trial
**Unit titles:** 1. Introduction 2. Prepare for the project 3. Exercise - Create the invoice Processing Model 4. Exercise - Build an approval email that uses the Invoice Processor model 5. Module assessment 6. Summary

---

## Describe Microsoft Power Platform administration and governance
**URL:** https://learn.microsoft.com/en-us/training/modules/describe-microsoft-power-platform-administration-governance/
**Level:** Beginner | **Units:** 8
**Summary:** This module introduces Microsoft Power Platform's security model, environments, admin centers, and portals. It also covers data privacy, accessibility compliance, and application lifecycle management (ALM) practices within the platform.
**Objectives:**
- Describe the Power Platform security model.
- Describe Power Platform environments.
- Describe Power Platform administrative portals and experiences.
- Describe Application Lifecycle Management (ALM) in Power Platform.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Describe the Power Platform security model 3. Describe Power Platform environments 4. Describe the Power Platform admin centers and portals 5. Describe how Power Platform supports data privacy and accessibility guidelines 6. Describe Application lifecycle Management (ALM) in Power Platform 7. Module assessment 8. Summary and resources

---

## Introduction to Microsoft Power Platform security and governance
**URL:** https://learn.microsoft.com/en-us/training/modules/security-governance-intro/
**Level:** Intermediate | **Units:** 7
**Summary:** This module focuses on introducing Microsoft Power Platform environments and their role in creating Data Loss Prevention (DLP) policies by using examples and use cases, plus an overview of Power Platform and Power Automate admin experiences and the Center of Excellence (CoE) toolkit.
**Objectives:**
- Access Microsoft Power Platform admin experiences.
- Create simple environment and tenant-wide DLP policies.
- Discover and identify the differences between the Business data group and the No-business data group.
- Learn about the differences between out-of-the-box Power Automate Admin experiences and Microsoft Power Platform Center of Excellence toolkit.
**Prerequisites:** A basic understanding of Power Apps and Power Automate, including their purpose and how these tools are used within an organization.
**Unit titles:** 1. Introduction 2. Identify Microsoft Power Platform environments 3. Data Loss Prevention policies 4. Microsoft Power Platform Center of Excellence Starter Kit 5. Exercise - Create a Power Platform environment 6. Check your knowledge 7. Summary

---

## Use templates to enforce governance policies in Microsoft Power Platform
**URL:** https://learn.microsoft.com/en-us/training/modules/templates-governance-policies/
**Level:** Intermediate | **Units:** 6
**Summary:** Microsoft provides many templates in Power Platform that administrators can use to enforce governance policies and increase visibility of assets created within a tenant. This module identifies existing templates that provide administrators with greater visibility.
**Objectives:**
- Identify existing templates that aid in security and governance processes.
- Implement templates and configure them for personal use.
- Respond to alerts that are generated by these templates.
**Prerequisites:** A basic understanding of Power Apps and Power Automate, including their purpose and how these tools are used within an organization. Students should also understand how connectors are used within apps and flows to exchange data across source and destination systems. Prior experience with Power Automated Templates is beneficial, but not required.
**Unit titles:** 1. Introduction to Power Automate flow templates 2. Prerequisites 3. Discover and implement Power Automate governance templates 4. Exercise - Build a digital tracking user list 5. Check your knowledge 6. Summary

---

## Manage environmental changes in Microsoft Power Platform
**URL:** https://learn.microsoft.com/en-us/training/modules/manage-environmental-changes/
**Level:** Intermediate | **Units:** 8
**Summary:** Learn best practices for communicating changes to Data Loss Prevention (DLP) policies, how people are using Power Platform, who is creating and sharing flows, what connectors are being used, and how connections are established within Power Automate environments.
**Objectives:**
- Identify best practices for communicating changes to DLP policies.
- Learn how people in your organization are using Microsoft Power Platform.
- Discover who in your organization is creating and sharing flows.
- Learn what connectors are being used within your Microsoft Power Platform environments.
- Observe how connections are being established within your Microsoft Power Platform environments.
**Prerequisites:** A basic understanding of Power Apps and Power Automate, including their purpose and how these tools are used within an organization. Learners should understand how connectors are used within apps and flows to exchange data across source and destination systems. You also need an account that has environment or tenant admin privileges for Microsoft Power Platform.
**Unit titles:** 1. Introduction and best practices for building DLP change management plans 2. Prerequisites for Microsoft Power Platform governance and change management 3. Implement best practices for building DLP change management plans 4. View Microsoft Power Platform Admin Analytics 5. Gain visibility by using Power Automate PowerShell cmdlets 6. Exercise - List connections in a tenant 7. Check your knowledge 8. Summary

---

## Plan and manage your Microsoft Power Platform environment
**URL:** https://learn.microsoft.com/en-us/training/modules/plan-manage-environment/
**Level:** Intermediate | **Units:** 9
**Summary:** Every organization has unique requirements based on size, location, data residency, and desired access to tools like Power Apps and Power Automate. This module discusses considerations that impact how an organization chooses to secure and govern its Power Platform environments.
**Objectives:**
- Identify cyber security risks and mitigation paths for those risks.
- Plan for environment variance, including handling exceptions.
- Layer Data Loss Prevention (DLP) policies for environments and the tenant.
- Discover how to prevent cross-tenant connections.
- Build DLP policy communication plans.
**Prerequisites:** A basic understanding of Power Apps and Power Automate, including their purpose and how these tools are used within an organization. In addition, students should be familiar with Microsoft Entra ID as an authentication source and a cursory understanding of establishing connections by using Microsoft Entra ID. Participants should have environment or tenant-wide administrative access to Microsoft Power Platform Admin center and Power Automate Admin center.
**Unit titles:** 1. Introduction 2. Prerequisites for Microsoft Power Platform DLP 3. Establish risk assessments and mitigation paths 4. Create a policy communication plan 5. Plan environments and variance 6. Layer Data Loss Prevention policies 7. Exercise - Create a Microsoft 365 environment-specific Data Loss Prevention policy 8. Check your knowledge 9. Summary

---

## Use the Admin center to manage environments and data policies in Power Automate
**URL:** https://learn.microsoft.com/en-us/training/modules/administer-flows/
**Level:** Beginner | **Units:** 5
**Summary:** Tenant and environment admins use the Power Automate Admin center to manage data policies and environments for Power Automate deployments.
**Objectives:**
- The Admin center
- Importing and exporting flows
- Sharing flows
**Prerequisites:** Signed up for Power Automate and a working mobile device with the Power Automate mobile app loaded.
**Unit titles:** 1. Administer flows 2. Export and import flows 3. Learn how to distribute button flows 4. Module assessment 5. Summary

---

## Get started with Microsoft Power Platform Center of Excellence
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-center-excellence/
**Level:** Intermediate | **Units:** 7
**Summary:** This module focuses on getting started with the initial configuration of the Microsoft Power Platform Center of Excellence (CoE) kit in your tenant, covering core setup components, governance components, audit log data, and the Power BI report.
**Objectives:**
- Set up core components.
- Set up governance components.
- Set up audit log connectors.
- Set up Power BI reports.
**Prerequisites:** Familiarity with Microsoft Power Platform.
**Unit titles:** 1. Introduction to Center of Excellence 2. Set up core components 3. Set up governance components 4. Exercise - Set up the audit log connector 5. Set up the Power BI report 6. Check your knowledge 7. Summary

---

## Implementation recommendations for Microsoft Power Platform environments
**URL:** https://learn.microsoft.com/en-us/training/modules/implementation-recommendations/
**Level:** Intermediate | **Units:** 10
**Summary:** This module provides prescriptive recommendations for how organizations should implement security and governance, based on popular use cases including Microsoft 365 and Dynamics 365 configurations, edge cases such as custom and HTTP connectors, and tooling such as the DLP Editor Tool from the CoE toolkit.
**Objectives:**
- Build a recommended Data Loss Prevention (DLP) policy for Office 365 scenarios.
- Build a recommended DLP policy for Dynamics 365 scenarios.
- Configure DLP policies that manage custom connectors.
- Configure DLP policies that manage HTTP connectors.
**Prerequisites:** A basic understanding of Power Apps and Power Automate, including their purpose and how these tools are used within an organization. Students should also understand how connectors are used within apps and flows to exchange data across source and destination systems. Participants should have environment or tenant-wide administrative access to Microsoft Power Platform Admin center and Power Automate Admin center. The Power Apps PowerShell cmdlets and Microsoft Power Platform Management Connector are also used.
**Unit titles:** 1. Introduction 2. Prerequisites for Microsoft Power Platform DLP 3. Use DLP data groups to protect important data 4. Recommended DLP policy settings for the default environment 5. Recommended DLP policy settings for Dynamics 365 environments 6. Use Flow for directional data governance 7. Manage HTTP connectors with a DLP policy 8. Exercise - Manage a custom connector with a DLP policy 9. Check your knowledge 10. Summary

---

## Build effective agents with Microsoft Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/build-effective-bots/
**Level:** Intermediate | **Units:** 10
**Summary:** Learn the design principles and best practices you can use when designing agents with Microsoft Copilot Studio.
**Objectives:**
- Examine techniques for planning agents.
- Explore design elements for creating successful agents.
- Review the different conversation types and why they're important.
- Examine best practices for creating good trigger phrases.
- Explore different techniques for building conversational agents.
- Review how to use analytics to improve your agent performance.
**Prerequisites:** None specified
**Unit titles:** 1. Introduction 2. Use cases 3. Plan for agents 4. Topics 5. Design your agent 6. Build solutions 7. Build a conversational agent 8. Validate and iterate on your design 9. Check your knowledge 10. Summary

---

## Ground agents with enterprise knowledge using connectors and Azure AI Search in Microsoft Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/ground-agents-enterprise-knowledge-connectors-azure-ai-search-copilot-studio/
**Level:** Advanced | **Units:** 7
**Summary:** Ground your Copilot Studio agents in enterprise knowledge by connecting to Copilot connectors, Power Platform connectors as real-time knowledge sources, and Azure AI Search vector indexes. Distinguish between index-based and real-time knowledge approaches and configure authentication settings for publishing knowledge-grounded agents.
**Objectives:**
- Distinguish between Copilot connectors and Power Platform connectors as knowledge sources
- Add a Copilot connector as a knowledge source to an agent
- Configure Power Platform connectors as real-time knowledge sources
- Connect an agent to an Azure AI Search vector index as a knowledge source
- Configure authentication settings required for knowledge source–based publishing
**Prerequisites:** Ability to create, configure, and publish agents in Copilot Studio; familiarity with SharePoint and Dataverse as knowledge sources for agents in Copilot Studio; access to Microsoft Copilot Studio; permissions to create solutions and agents in a Power Platform environment; access to an Azure subscription
**Unit titles:** 1. Introduction 2. Choose between Copilot connector and Power Platform connector knowledge sources 3. Add Copilot connectors as knowledge sources 4. Configure Power Platform connectors as real-time knowledge sources 5. Connect an agent to Azure AI Search 6. Module assessment 7. Summary

---

## Take action in external systems using connector and REST API agent tools in Microsoft Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/take-action-external-systems-connector-rest-api-tools-copilot-studio/
**Level:** Intermediate | **Units:** 7
**Summary:** Configure Power Platform connectors and REST APIs as tools for your Copilot Studio agents. Learn to add prebuilt and custom connectors, upload OpenAPI specifications to create REST API tools, and configure authentication to integrate your agent with external services.
**Objectives:**
- Add a prebuilt Power Platform connector as a tool to an agent
- Add an existing custom connector as a tool to an agent
- Configure connector credentials using maker-provided and user-provided authentication
- Add a REST API tool to an agent using an OpenAPI specification
- Configure authentication for a REST API tool
**Prerequisites:** Familiarity with Copilot Studio integration patterns, including the distinction between tools and knowledge sources; access to Microsoft Copilot Studio; permissions to create solutions and agents in a Power Platform environment; familiarity with REST APIs
**Unit titles:** 1. Introduction 2. Understand connector and REST API tools in Copilot Studio 3. Add prebuilt and custom connector tools to an agent 4. Configure authentication for connector tools 5. Add a REST API tool using an OpenAPI specification 6. Module assessment 7. Summary

---

## Integrate agents with external systems via MCP in Microsoft Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/integrate-agents-external-systems-mcp-copilot-studio/
**Level:** Advanced | **Units:** 7
**Summary:** Connect your agent to Model Context Protocol (MCP) servers to access standardized tools and resources. Learn to use the MCP onboarding wizard, configure API key and OAuth 2.0 authentication, manage tool selection, and determine when MCP is the right integration approach compared to connectors or REST APIs.
**Objectives:**
- Explain how MCP enables standardized tool integration for agents
- Connect an agent to an existing MCP server using the onboarding wizard
- Configure authentication for an MCP server connection
- Enable and selectively configure MCP tools on an agent
- Describe when to use MCP versus connectors or REST APIs
**Prerequisites:** Understanding of Copilot Studio agent integration patterns, including the distinction between tools and knowledge sources; ability to create and configure agents in Copilot Studio; access to Microsoft Copilot Studio; permissions to create solutions and agents in a Power Platform environment
**Unit titles:** 1. Introduction 2. Understand MCP and its role in Copilot Studio integration 3. Connect an agent to an existing MCP server 4. Configure authentication for MCP server connections 5. Enable and manage MCP tools on an agent 6. Module assessment 7. Summary

---

## Design integration strategies for agents in Microsoft Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/design-enterprise-integration-strategies-agents-copilot-studio/
**Level:** Intermediate | **Units:** 7
**Summary:** Learn to evaluate and select integration patterns for your Copilot Studio agents. Explore tools, knowledge sources, and agents as integration options and identify appropriate authentication models to design integrations that meet your enterprise requirements.
**Objectives:**
- Distinguish between integrating agents with tools, knowledge sources, and other agents
- Evaluate the appropriate integration approach for a given enterprise scenario
- Identify authentication models used across integration types
**Prerequisites:** Ability to create, configure, and publish an agent in Microsoft Copilot Studio; conceptual familiarity with REST APIs and web services
**Unit titles:** 1. Introduction 2. Explore the Copilot Studio integration landscape 3. Compare action integration patterns 4. Authenticate and govern agent integrations 5. Select integration patterns for enterprise scenarios 6. Module assessment 7. Summary

---

## Add structured automation to agents in Microsoft Copilot Studio
**URL:** https://learn.microsoft.com/en-us/training/modules/copilot-studio-structured-automation/
**Level:** Intermediate | **Units:** 9
**Summary:** Learn how to add structured automation to your Copilot Studio agents by using deterministic workflows as tools. You'll create workflow tools, add them to agents and topics, and validate their behavior in test sessions.
**Objectives:**
- Explain how workflow tools add structured automation to Copilot Studio agents.
- Create and configure Copilot Studio workflows as tools.
- Add workflow tools at both the agent and topic levels.
- Use input and output variables to pass data between topics and workflows.
- Test and validate workflow tool behavior by using the activity map and run history.
**Prerequisites:** Ability to create and edit agents in Microsoft Copilot Studio; basic familiarity with tools and topics in Copilot Studio; access to a Power Platform environment where you can create workflows
**Unit titles:** 1. Introduction 2. Overview of Copilot Studio workflows as tools 3. Create Copilot Studio workflows as tools 4. Design Copilot Studio workflow tools 5. Add Copilot Studio workflows as tools to agents 6. Add Copilot Studio workflows as tools to topics 7. Test workflow tools in Copilot Studio 8. Module assessment 9. Summary

---

## Create a copilot to help promote your podcast
**URL:** https://learn.microsoft.com/en-us/training/modules/create-copilot-podcast/
**Level:** Intermediate | **Units:** 10
**Summary:** If you produce podcasts and want to create marketing material for each episode, consider using Microsoft Azure OpenAI, .NET, and Microsoft Power Platform to create a solution that generates this material by using AI capabilities.
**Objectives:**
- Use Azure OpenAI Service to interact with GPT models.
- Create a Microsoft Power Platform custom connector for your .NET application programming interface (API).
- Integrate a custom connector in a Power Apps canvas app.
- Create a copilot in Copilot Studio that integrates with a Power Automate cloud flow that's using a custom connector.
**Prerequisites:** A Power Apps license and environment; Azure OpenAI Service; Copilot Studio; Visual Studio
**Unit titles:** 1. Introduction 2. Azure OpenAI Service 3. Prepare for the exercises - Set up your environment 4. Exercise - Configure Azure OpenAI Service to generate information about your podcast 5. How .NET API and custom connectors bridge the gap with Microsoft Power Platform 6. Exercise - Create a custom connector for your copilot 7. Integrate custom connectors in Microsoft Power Platform tools 8. Exercise - Test your custom connector in Microsoft Power Platform 9. Check your knowledge 10. Summary

---


## Other Power Platform modules (catalog data only)

*259 modules — SAP/Azure integration, FinOps, commercial marketplace, Power BI/semantic models, PL-1xx/PL-2xx/MB-xxx exam-prep, Solution Architect series and AI-powered-business-solutions architecture modules, Dynamics 365 functional-consultant and industry/education-vertical content, developer-only Power Platform content (component framework, Web APIs, custom connectors, ALM/DevOps pipelines), Power Automate for desktop granular skill-building units, and other Power Platform catalog content not specifically about maker-level Power Automate/Power Apps building, governance/DLP, or Copilot Studio agent-building. Catalog metadata only; page-level detail was not fetched for these to keep scope tractable.*

- **[Access Dataverse in Power Pages websites](https://learn.microsoft.com/en-us/training/modules/power-pages-dataverse/)** — Advanced, 52 min, 6 units. uid: `learn-bizapps.power-pages-dataverse`. Learn about the several techniques and methods for displaying and interacting with Dataverse data on Power Pages websites.
- **[Active Directory handling in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-active-directory/)** — Advanced, 32 min, 5 units. uid: `learn-bizapps.pad-active-directory`. Learn about the Active Directory actions in Power Automate for desktop.
- **[Add an AI model to process invoice forms - Online workshop](https://learn.microsoft.com/en-us/training/modules/add-ai-model-process-invoice-online-workshop/)** — Beginner, 45 min, 5 units. uid: `learn-bizapps.add-ai-model-process-invoice-online-workshop`. Learn how to add an AI model to process invoice forms.
- **[Add intelligence to a real estate solution with AI Builder's GPT prompts](https://learn.microsoft.com/en-us/training/modules/add-intelligence-ai-copilot/)** — Beginner, 20 min, 5 units. uid: `learn-bizapps.add-intelligence-ai-copilot`. This module introduces the Create text with GPT using a prompt capability in AI Builder.
- **[Adjust process behavior using conditional actions with Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-conditionals/)** — Beginner, 40 min, 7 units. uid: `learn-bizapps.pad-conditionals`. Learn how to use conditional actions to configure a flow to vary behavior at runtime-based information in the environment.
- **[Administer Microsoft Power Platform subscriptions](https://learn.microsoft.com/en-us/training/modules/administrating-power-platform-subscriptions/)** — Intermediate, 49 min, 9 units. uid: `learn-dynamics.administrating-power-platform-subscriptions`. Learn about the default capabilities that you have access to with your Microsoft Power Platform subscriptions.
- **[Adopt FinOps on Azure](https://learn.microsoft.com/en-us/training/modules/adopt-finops-on-azure/)** — Intermediate, 179 min, 8 units. uid: `learn.azure.adopt-finops-on-azure`. Learn how to implement FinOps on Azure.
- **[Advanced command bar concepts](https://learn.microsoft.com/en-us/training/modules/command-bar-advanced/)** — Intermediate, 47 min, 8 units. uid: `learn-bizapps.command-bar-advanced`. Explore advanced customization techniques for command bars in Power Apps model-driven apps, including JavaScript implementation and AutoSave features.
- **[Analyze processes with the Power Automate Process Mining desktop app](https://learn.microsoft.com/en-us/training/modules/analyze-processes-process-mining/)** — Beginner, 39 min, 8 units. uid: `learn-bizapps.analyze-processes-process-mining`. Learn how to analyze processes with the Power Automate Process Mining desktop app.
- **[Analyze requirements for AI-powered business solutions](https://learn.microsoft.com/en-us/training/modules/analyze-requirements-ai-powered-business-solutions/)** — Advanced, 25 min, 6 units. uid: `learn.wwl.analyze-requirements-ai-powered-business-solutions`. Learn to analyze, design, and implement AI-powered business solutions using agents, generative AI, and Microsoft Copilot for productivity.
- **[Analyze the sentiment of text with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder-sentiment-analysis/)** — Beginner, 28 min, 5 units. uid: `learn-bizapps.get-started-with-ai-builder-sentiment-analysis`. Learn about AI Builder Sentiment analysis and how to use it with other Microsoft Power Platform products.
- **[Application lifecycle management for Dynamics 365](https://learn.microsoft.com/en-us/training/modules/application-lifecycle-management-dynamics-365/)** — Beginner, 97 min, 10 units. uid: `learn-dynamics.application-lifecycle-management-dynamics-365`. Explore the application of Application lifecycle management (ALM)  in Dynamics 365 projects, learn participation in ALM processes, and understand different environments.
- **[Authentication and user management in Power Pages](https://learn.microsoft.com/en-us/training/modules/power-pages-authentication-user-management/)** — Intermediate, 55 min, 8 units. uid: `learn-bizapps.power-pages-authentication-user-management`. Learn how to authenticate with Power Pages.
- **[Author a basic formula that uses tables and records in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/author-basic-formula-tables-records-powerapps/)** — Intermediate, 58 min, 9 units. uid: `learn-bizapps.author-basic-formula-tables-records-powerapps`. Learn how to author a basic formula that uses tables and records in a Power Apps canvas app.
- **[Automate business process flows with client script](https://learn.microsoft.com/en-us/training/modules/power-platform-automate-client-script/)** — Advanced, 41 min, 6 units. uid: `learn-bizapps.power-platform-automate-client-script`. This module focuses on educating developers on how to perform common techniques in regard to automating business processes using client scripting, along with explaining the context of when these scenarios might be applied.
- **[Automate repetitive tasks using loops in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-loops/)** — Beginner, 45 min, 8 units. uid: `learn-bizapps.pad-loops`. Learn how to use loops to repeat blocks of actions in a flow.
- **[Automate system, workstation, and services actions in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-system-services-actions/)** — Beginner, 22 min, 5 units. uid: `learn-bizapps.pad-system-services-actions`. Learn about the system, workstation, and services actions in Power Automate for desktop.
- **[Automate the processing of documents with the AI Builder prepackaged solution](https://learn.microsoft.com/en-us/training/modules/get-started-ai-builder-document-automation/)** — Beginner, 23 min, 6 units. uid: `learn-bizapps.get-started-ai-builder-document-automation`. Discover the benefits of document automation and how it can streamline your workflow.
- **[Automating email handling in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-email/)** — Beginner, 46 min, 7 units. uid: `learn-bizapps.pad-email`. In this module, we'll discuss how to automate email handling in Power Automate desktop app.
- **[Becoming a solution architect for Dynamics 365 and Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/becoming-solution-architect/)** — Advanced, 74 min, 7 units. uid: `learn-dynamics.becoming-solution-architect`. Learn how to become a solution architect.
- **[Best practices for email in SharePoint and Power Automate](https://learn.microsoft.com/en-us/training/modules/best-practices-email/)** — Intermediate, 20 min, 7 units. uid: `learn-bizapps.best-practices-email`. Email continues to be the primary and preferred method of communication for many businesses. In some situations, emails are also received as official electronic forms of approval. This module will provide you with a list of best practices that you can follow by using Microsoft Power Automate for outgoing and incoming emails.
- **[Build a 3D mobile app with Power Apps in mixed reality](https://learn.microsoft.com/en-us/training/modules/power-apps-tutorial/)** — Beginner, 64 min, 10 units. uid: `learn.azure.power-apps-tutorial`. Learn about all the foundational elements required to build a mixed reality application using Power Apps.
- **[Build a Power Apps canvas app for a real estate solution with data from Excel](https://learn.microsoft.com/en-us/training/modules/build-canvas-app-real-estate-excel/)** — Beginner, 39 min, 4 units. uid: `learn-bizapps.build-canvas-app-real-estate-excel`. Learn how to build a Power Apps canvas app for a real estate solution by using data from Excel.
- **[Build a Power Apps component](https://learn.microsoft.com/en-us/training/modules/build-power-apps-component/)** — Intermediate, 47 min, 5 units. uid: `learn-bizapps.build-power-apps-component`. Learn how to build a custom Power Apps component, create a code component solution package, and then test and debug a code component.
- **[Build a Power Pages website for a real estate solution with Copilot in Power Pages](https://learn.microsoft.com/en-us/training/modules/build-website-real-estate-power-pages-copilot/)** — Beginner, 89 min, 6 units. uid: `learn-bizapps.build-website-real-estate-power-pages-copilot`. Learn how to build a Power Pages website for a real estate solution by using Copilot in Power Pages to generate pages, sections, forms, data, and text.
- **[Build flows to manage user information](https://learn.microsoft.com/en-us/training/modules/manage-user-information/)** — Beginner, 23 min, 6 units. uid: `learn-bizapps.manage-user-information`. Learn to build flows to manage user information.
- **[Build the Dataverse table schema for the model-driven app](https://learn.microsoft.com/en-us/training/modules/build-dataverse-table-structure/)** — Beginner, 37 min, 7 units. uid: `learn-bizapps.build-dataverse-table-structure`. Learn to create tables and establish relationships for building an employee accident tracking model-driven app.
- **[Build your first workflow with Power Automate and Dataverse for Teams](https://learn.microsoft.com/en-us/training/modules/build-first-workflow/)** — Beginner, 25 min, 7 units. uid: `learn-bizapps.build-first-workflow`. Bring automation and workflows to Microsoft Teams by using Microsoft Power Automate and Microsoft Dataverse for Teams.
- **[Business process mapping for Dynamics 365](https://learn.microsoft.com/en-us/training/modules/business-process-mapping-dynamics-365/)** — Beginner, 53 min, 7 units. uid: `learn-dynamics.business-process-mapping-dynamics-365`. Discover how to implement business applications effectively, using techniques like shadowing and mapping processes into Dynamics 365.
- **[Challenge project - Build a speech translator app](https://learn.microsoft.com/en-us/training/modules/challenge-project-build-speech-translator-app/)** — Beginner, 166 min, 7 units. uid: `learn.student-evangelism.challenge-project-build-speech-translator-app`. Learn how to build a speech translation app by using Microsoft Power Apps and integrate it with AI.
- **[Choose a content distribution method](https://learn.microsoft.com/en-us/training/modules/choose-content-distribution-method/)** — Intermediate, 31 min, 8 units. uid: `learn-bizapps.choose-content-distribution-method`. Choose a content distribution method for Power BI.
- **[Clean, transform, and load data in Power BI](https://learn.microsoft.com/en-us/training/modules/clean-data-power-bi/)** — Intermediate, 121 min, 10 units. uid: `learn-bizapps.clean-data-power-bi`. Use Power Query to clean and prepare data for analysis. Learn to simplify models, change data types, rename objects, pivot data, and profile columns to identify valuable data for deeper analytics.
- **[Combine Power Automate desktop and cloud flows](https://learn.microsoft.com/en-us/training/modules/pad-powerautomate/)** — Beginner, 42 min, 5 units. uid: `learn-bizapps.pad-power-automate`. This module describes how to combine a Power Automate desktop flow with a Power Automate cloud flow.
- **[Common command bar scenarios](https://learn.microsoft.com/en-us/training/modules/command-bar-scenarios/)** — Intermediate, 33 min, 7 units. uid: `learn-bizapps.command-bar-scenarios`. Explore customization of command bars in Power Apps using Power Fx logic, enhancing user experience and meeting unique requirements.
- **[Communicate using message boxes in Power Automate for desktop flows](https://learn.microsoft.com/en-us/training/modules/pad-message-boxes/)** — Beginner, 17 min, 5 units. uid: `learn-bizapps.pad-message-boxes`. In this module, we discuss the use of message boxes in automated flows.
- **[Complete testing and performance checks in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/testing-performance-checks-powerapps/)** — Advanced, 38 min, 6 units. uid: `learn-bizapps.testing-performance-checks`. Do you want to test your app and improve its performance? This module helps you understand how to test an app and improve performance.
- **[Configure custom connectors with authenticated APIs in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/configure-custom-connectors-api/)** — Intermediate, 50 min, 8 units. uid: `learn-bizapps.configure-custom-connectors-api`. Learn how to configure custom connectors with authenticated APIs.
- **[Configure exception and error handling in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-exception-handling/)** — Intermediate, 30 min, 6 units. uid: `learn-bizapps.pad-exception-handling`. In this module, we'll discuss how to configure exception handling behavior.
- **[Configure flow control in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-flow-control/)** — Beginner, 15 min, 4 units. uid: `learn-bizapps.pad-flow-control`. Learn about the flow control actions in Power Automate for desktop.
- **[Configure forms, charts, and dashboards in model-driven apps](https://learn.microsoft.com/en-us/training/modules/configure-model-driven-apps-customer-engagement-apps/)** — Intermediate, 69 min, 9 units. uid: `learn-dynamics.configure-model-driven-apps-customer-engagement`. Learn how to configure forms, charts, and dashboards.
- **[Configure policy templates for custom connectors in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/policy-templates-custom-connectors/)** — Intermediate, 35 min, 8 units. uid: `learn-bizapps.policy-templates-custom-connectors`. Discover how to modify custom connector behavior at runtime using policies for data conversion, routing requests, and setting parameters.
- **[Connect a cloud flow to desktop flows in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/connect-cloud-desktop-flow/)** — Intermediate, 25 min, 7 units. uid: `learn-bizapps.connect-cloud-desktop-flow`. Learn how to create cloud flows in Microsoft Power Automate for desktop.
- **[Connect Power Platform to SAP on Azure](https://learn.microsoft.com/en-us/training/modules/connect-power-platform-to-sap-azure/)** — Advanced, 33 min, 8 units. uid: `learn.wwl.connect-power-platform-to-sap-azure`. Connect Power Platform to SAP on Azure
- **[Control file and folder handling in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-files-folders-handling/)** — Beginner, 53 min, 6 units. uid: `learn-bizapps.pad-files-folders-handling`. Learn about the files and folders actions in Microsoft Power Automate for desktop.
- **[Core components of Power Pages](https://learn.microsoft.com/en-us/training/modules/power-pages-intro/)** — Intermediate, 48 min, 7 units. uid: `learn-bizapps.power-pages-intro`. Use Power Pages to create modern data-driven external-facing business websites. Extend Dataverse data to external and internal audiences such as customers, partners, and employees. Empower anyone inside or outside your organization to interact with the business by using Power Pages sites.
- **[Create a pipeline in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/create-pipeline/)** — Beginner, 35 min, 7 units. uid: `learn-bizapps.create-pipeline`. This module explores how you can quickly create a pipeline and automatically deploy a solution in another environment.
- **[Create a relationship between tables in Dataverse](https://learn.microsoft.com/en-us/training/modules/create-relationship-between-cds-entities/)** — Intermediate, 55 min, 8 units. uid: `learn-dynamics.create-relationship-between-cds-entities`. Do you need to create relationships between tables? This module will show how and why you can separate data into tables and how to relate between tables to build complex and robust business solutions. It will also explain the different kinds of relationships that you can define between tables in Dataverse.
- **[Create AI Builder prompts using your own Dataverse data](https://learn.microsoft.com/en-us/training/modules/ai-builder-grounded-prompts/)** — Intermediate, 34 min, 7 units. uid: `learn-bizapps.ai-builder-grounded-prompts`. Learn how to create and use grounded prompts in AI Builder.
- **[Create and define calculation or rollup columns in Dataverse](https://learn.microsoft.com/en-us/training/modules/create-define-calculation-rollup-fields/)** — Intermediate, 44 min, 9 units. uid: `learn-dynamics.create-define-calculation-rollup-fields`. Do you want to use rollup or calculation columns? This module shows you how to build calculations or rollups that are defined and triggered within the data in Dataverse, regardless of the app that accesses that data set.
- **[Create and manage columns within a table in Dataverse](https://learn.microsoft.com/en-us/training/modules/create-manage-fields-within-entity/)** — Beginner, 74 min, 11 units. uid: `learn-dynamics.create-manage-fields-within-entity`. Learn how to create and manage table columns in Dataverse.
- **[Create and manage environments in Dataverse](https://learn.microsoft.com/en-us/training/modules/create-manage-environments/)** — Beginner, 54 min, 9 units. uid: `learn-dynamics.create-manage-environments`. An environment is a space to store, manage, and share your organization's business data that is stored within an instance of a Dataverse database.  You can set up one or many environments, depending on the needs of your organization. This module explores these environments and how you can use them with instances of Dataverse databases.
- **[Create dashboards in Power BI](https://learn.microsoft.com/en-us/training/modules/create-dashboards-power-bi/)** — Intermediate, 59 min, 10 units. uid: `learn-bizapps.create-dashboards-power-bi`. Microsoft Power BI dashboards are different than Power BI reports. Dashboards allow report consumers to create a single artifact of directed data that is personalized just for them. Dashboards can be composed of pinned visuals that are taken from different reports. Where a Power BI report uses data from a single semantic model, a Power BI dashboard can contain visuals from different semantic models.
- **[Create formulas that use tables, records, and collections in a canvas app in Power Apps](https://learn.microsoft.com/en-us/training/modules/author-advanced-formulas-powerapps/)** — Advanced, 39 min, 7 units. uid: `learn-bizapps.author-advanced-formulas`. Do you have need for complex formulas in your app? This module can help you write those formulas.
- **[Create formulas to change behaviors in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/author-basic-formula-change-behaviors-powerapps/)** — Intermediate, 40 min, 8 units. uid: `learn-bizapps.author-basic-forumla-change-behaviors-powerapps`. Learn how to enhance and customize your Power Apps canvas app using basic formulas.
- **[Create formulas to change properties in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/author-basic-formula-change-properties-powerapps/)** — Intermediate, 54 min, 8 units. uid: `learn-bizapps.author-basic-formula-change-properties-powerapps`. Enhance and customize your Power Apps canvas app with easy-to-write formulas. Learn how to change formats, do math calculations, and implement conditional formatting.
- **[Create Microsoft Power Platform OpenAPI custom connectors](https://learn.microsoft.com/en-us/training/modules/custom-connectors-open-api/)** — Intermediate, 30 min, 7 units. uid: `learn-bizapps.custom-connectors-open-api`. Learn about Power Platform OpenAPI custom connectors.
- **[Create Power BI reports with Power Automate Process Mining](https://learn.microsoft.com/en-us/training/modules/create-reports-process-mining/)** — Beginner, 22 min, 6 units. uid: `learn-bizapps.create-reports-process-mining`. Learn how to create Power BI reports with Power Automate Process Mining.
- **[Create reports with Power BI and Dataverse for Teams](https://learn.microsoft.com/en-us/training/modules/dataverse-teams-power-bi/)** — Beginner, 35 min, 7 units. uid: `learn-bizapps.dataverse-teams-power-bi`. Learn how to build your first report with Microsoft Power BI and Dataverse for Teams.
- **[Create subflows and web automation with Power Automate for desktop - Online workshop](https://learn.microsoft.com/en-us/training/modules/create-subflows-web-automation-online-workshop/)** — Beginner, 46 min, 6 units. uid: `learn-bizapps.create-subflows-web-automation-online-workshop`. Discover how to use Power Automate for desktop app to build subflows, automate web tasks, convert currencies, and log data into Excel.
- **[Create tables in Dataverse](https://learn.microsoft.com/en-us/training/modules/get-started-with-powerapps-common-data-service/)** — Beginner, 87 min, 12 units. uid: `learn-bizapps.powerapps-common-data-service`. Explore secure data management with Dataverse, learning how to create tables and import data into a cloud-based storage system.
- **[Create triggers for custom connectors for Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/create-triggers-custom-connectors/)** — Intermediate, 56 min, 9 units. uid: `learn-bizapps.create-triggers-custom-connectors`. Unlock the power of the Dataverse Web API by mastering OAuth authorization and harnessing OData for seamless data querying.
- **[Create your first desktop flow - Online workshop](https://learn.microsoft.com/en-us/training/modules/create-first-desktop-flow-online-workshop/)** — Beginner, 39 min, 5 units. uid: `learn-bizapps.create-first-desktop-flow-online-workshop`. Follow the steps to create your first desktop flow.
- **[Customize the command bar](https://learn.microsoft.com/en-us/training/modules/command-bar-customize/)** — Intermediate, 35 min, 7 units. uid: `learn-bizapps.command-bar-customize`. Learn to customize the command bar in Power Apps.
- **[Database handling in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-database-handling/)** — Intermediate, 24 min, 4 units. uid: `learn-bizapps.pad-database-handling`. Learn about the database actions in Power Automate desktop app.
- **[Define a Microsoft AI strategy to create business value in nonprofit](https://learn.microsoft.com/en-us/training/modules/define-microsoft-ai-strategy-create-business-value-nonprofit/)** — Beginner, 38 min, 9 units. uid: `learn.wwl.define-microsoft-ai-strategy-create-business-value-nonprofit`. Discover AI use cases and scenarios for nonprofit organizations. Get familiar with Microsoft AI tools and services for nonprofit. Learn from real success stories.
- **[Define and create business rules in Dataverse](https://learn.microsoft.com/en-us/training/modules/define-create-business-rules/)** — Intermediate, 44 min, 6 units. uid: `learn-dynamics.define-create-business-rules`. The ability to build business rules that ensure consistent business logic whatever app is accessing that data set is imperative to a successful business operation. This module will show you how you can build business rules that are triggered anytime they're used within Dataverse.
- **[Define input and output parameters in Power Automate](https://learn.microsoft.com/en-us/training/modules/input-parameters/)** — Beginner, 29 min, 8 units. uid: `learn-bizapps.input-parameters`. This module defines input and output parameters for desktop flows, which allow your flows to be more comprehensive and useful.
- **[Describe Microsoft Dataverse](https://learn.microsoft.com/en-us/training/modules/describe-microsoft-dataverse/)** — Beginner, 38 min, 9 units. uid: `learn.wwl.describe-microsoft-dataverse`. In this module, you explore Microsoft Dataverse as the intelligent data platform at the core of Microsoft Power Platform. You learn how Dataverse differs from traditional databases, how to work with its structural components, how to implement business logic, and how to use Copilot to build data models through natural language. PL-900
- **[Describe reporting and integration capabilities in Dynamics 365 finance and operations apps](https://learn.microsoft.com/en-us/training/modules/describe-report-integration/)** — Beginner, 84 min, 10 units. uid: `learn.wwl.describe-reporting-integration`. Understand reporting and integration features for finance and operations apps with Power BI, Microsoft 365, and business events to enhance data analysis
- **[Describe shared capabilities in Dynamics 365 customer engagement apps](https://learn.microsoft.com/en-us/training/modules/describe-shared-capabilities/)** — Beginner, 94 min, 9 units. uid: `learn.wwl.describe-shared-capabilities`. Learn how Dynamics 365 integrates with Microsoft 365 apps, leverages Power Platform, and uses AI solutions like Copilot for enhanced productivity.
- **[Design AI agents for business solutions](https://learn.microsoft.com/en-us/training/modules/design-ai-agents-business-solutions/)** — Advanced, 161 min, 21 units. uid: `learn.wwl.design-ai-agents-business-solutions`. Learn to design AI agents tailored to business needs using Dynamics 365 and Copilot. Explore Responsible AI, custom connectors, and integration strategies.
- **[Design AI-powered business solutions with Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/design-ai-powered-solutions-power-platform/)** — Intermediate, 33 min, 7 units. uid: `learn.wwl.design-ai-powered-solutions-power-platform`. Learn to think like an AI-first architect: choose the right components, map processes to intelligent patterns, and know when to extend the platform for advanced scenarios.
- **[Design ALM process for AI-powered business solutions](https://learn.microsoft.com/en-us/training/modules/design-alm-process-ai-powered-business-solutions/)** — Intermediate, 46 min, 9 units. uid: `learn.wwl.design-alm-process-ai-powered-business-solutions`. Learn to design ALM processes for AI solutions, ensuring governance, security, and consistency across development, testing, and production.
- **[Design extensibility of AI solutions](https://learn.microsoft.com/en-us/training/modules/design-extensibility-ai-solutions/)** — Advanced, 48 min, 10 units. uid: `learn.wwl.design-extensibility-ai-solutions`. Learn to design scalable, secure, and customizable AI solutions using Microsoft platforms. Explore extensibility strategies for enterprise AI.
- **[Design for accessibility in Dynamics 365](https://learn.microsoft.com/en-us/training/modules/design-accessibility-dynamics-365/)** — Beginner, 46 min, 7 units. uid: `learn-dynamics.design-accessibility-dynamics-365`. Explore the importance of accessibility in technology, learn about Microsoft's approach, and discover tools for improvement.
- **[Design human-in-the-loop approval workflows with Power Automate and Microsoft Teams](https://learn.microsoft.com/en-us/training/modules/aaai-design-human-in-loop-approval-workflows/)** — Advanced, 41 min, 7 units. uid: `learn.wwl.design-human-in-loop-approval-workflows`. Design human-in-the-loop systems for production multi-agent workflows using Power Automate and Microsoft Teams. Implement confidence-threshold escalation architectures, design asynchronous approval workflows for high-stakes agent actions, build human feedback collection and active learning pipelines, and configure audit workflows that provide complete human oversight records for regulated environments.
- **[Design overall AI strategy for business solutions](https://learn.microsoft.com/en-us/training/modules/design-overall-ai-strategy-business-solutions/)** — Advanced, 165 min, 19 units. uid: `learn.wwl.design-overall-ai-strategy-business-solutions`. Learn to design an enterprise AI strategy using Azure's Cloud Adoption Framework. Align AI agent lifecycle with business goals for operational excellence.
- **[Design Power BI reports](https://learn.microsoft.com/en-us/training/modules/power-bi-effective-reports/)** — Intermediate, 115 min, 11 units. uid: `learn-bizapps.power-bi-effective-reports`. Design effective Power BI reports that are visually appealing and easy to understand with consistent report structure, interactive objects, and filtering.
- **[Design responsible AI security, governance, risk management, and compliance](https://learn.microsoft.com/en-us/training/modules/design-responsible-ai-security-governance-risk-management-compliance/)** — Advanced, 53 min, 11 units. uid: `learn.wwl.design-responsible-ai-security-governance-risk-management-compliance`. Learn to design secure, governed, and compliant AI systems that align with organizational policies and Responsible AI principles.
- **[Design the Dynamics 365 deployment](https://learn.microsoft.com/en-us/training/modules/design-dynamics-365-deployment/)** — Beginner, 83 min, 9 units. uid: `learn-dynamics.design-dynamics-365-deployment`. Explore Dynamics 365 customization, focusing on user needs, problem evaluation from multiple perspectives, and successful solution design.
- **[Detect objects with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder-object-detection/)** — Beginner, 25 min, 5 units. uid: `learn-bizapps.get-started-with-ai-builder-object-detection`. Learn the basics of AI Builder Object detection and how it can benefit your organization.
- **[Determine the implementation approach for your Dynamics 365 project](https://learn.microsoft.com/en-us/training/modules/determine-implementation-approach-dynamics-365/)** — Beginner, 76 min, 7 units. uid: `learn-dynamics.determine-implementation-approach-dynamics-365`. Explore the importance of adopting an implementation methodology for successful Dynamics 365 projects, including common types and approaches.
- **[Digitally transform with Dynamics 365](https://learn.microsoft.com/en-us/training/modules/digitally-transform-with-dynamics-365/)** — Beginner, 83 min, 13 units. uid: `learn-dynamics.digitally-transform-with-dynamics-365`. Explore how Dynamics 365 business applications simplify CRM and ERP systems, aiding digital transformation for organizations.
- **[Discover and use Web APIs with Power Apps](https://learn.microsoft.com/en-us/training/modules/discover-web-apis-power-apps/)** — Beginner, 57 min, 11 units. uid: `learn-bizapps.powerapps.discover-web-apis-power-apps`. Build a custom connector using an OpenAPI document or Azure API Management to send data to and receive data from web APIs.
- **[Discover customer needs as a Solution Architect for Dynamics 365 and Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/discover-customer-needs/)** — Advanced, 36 min, 6 units. uid: `learn-dynamics.discover-customer-needs`. Learn how to ask customers questions about their business processes and feature requirements to create a viable solution.
- **[Discover data analysis](https://learn.microsoft.com/en-us/training/modules/data-analytics-microsoft/)** — Intermediate, 36 min, 6 units. uid: `learn-bizapps.data-analytics-microsoft`. Would you like to explore the journey of a data analyst and learn how a data analyst tells a story with data? In this module, you explore the different roles in data and learn the different tasks of a data analyst.
- **[Discover Power Apps for Educators and reclaim your time 101](https://learn.microsoft.com/en-us/training/modules/discover-power-apps-educators-reclaim-time/)** — Intermediate, 69 min, 10 units. uid: `learn.mec.discover-power-apps-educators-reclaim-time`. Educators learn how to use Power Apps by creating apps for themselves that help save time and create administrative efficiencies.
- **[Discover the Dynamics 365 landscape](https://learn.microsoft.com/en-us/training/modules/discover-dynamics-365-landscape/)** — Beginner, 72 min, 8 units. uid: `learn-dynamics.discover-dynamics-365-landscape`. Explore the capabilities, deployment options, and potential integrations of Dynamics 365 business applications.
- **[Document your Dynamics 365 solution for the customer](https://learn.microsoft.com/en-us/training/modules/document-dynamics-365-solution-customer/)** — Beginner, 45 min, 6 units. uid: `learn-dynamics.document-dynamics-365-solution-customer`. Explore the process of creating and maintaining Dynamics 365 system documentation for various audiences in this module.
- **[Enhance communication using Power Automate and the Office 365 Users Connector](https://learn.microsoft.com/en-us/training/modules/enhance-communication/)** — Beginner, 49 min, 7 units. uid: `learn-bizapps.enhance-communication`. Efficient communication and data access are key to workplace productivity, and the Office 365 Users Connector in Power Automate offers a powerful way to streamline workflows that involve user data. Whether you need to search for users by department, dynamically pull manager details for approval workflows, or customize notifications with user-specific data, this connector simplifies access to Office 365 user information.
- **[Enhance public sector services with generative AI](https://learn.microsoft.com/en-us/training/modules/enhance-public-sector-services-generative-ai/)** — Intermediate, 60 min, 9 units. uid: `learn.mec.enhance-public-sector-services-generative-ai`. Discover the potential of generative AI for transforming public sector organizations and responsible AI practices for the public sector.
- **[Evaluate costs and benefits of AI solutions](https://learn.microsoft.com/en-us/training/modules/evaluate-costs-benefits-ai-powered-business-solution/)** — Advanced, 34 min, 7 units. uid: `learn.wwl.evaluate-costs-benefits-ai-powered-business-solution`. Learn to assess costs and benefits of AI solutions. Develop ROI analyses, evaluate TCO, and decide to build, buy, or extend AI components.
- **[Evaluate requirements for Dynamics 365 projects](https://learn.microsoft.com/en-us/training/modules/evaluate-requirements-dynamics-365-projects/)** — Beginner, 62 min, 9 units. uid: `learn-dynamics.evaluate-requirements-dynamics-365-projects`. Discover effective techniques for collecting and evaluating project requirements to enhance solution building for Dynamics 365.
- **[Excel automation in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-excel-automation/)** — Beginner/intermediate, 52 min, 9 units. uid: `learn-bizapps.pad-excel-automation`. Learn how to use Power Automate desktop app to open, read, and manipulate Excel files with various Microsoft Excel actions.
- **[Explore Power Automate architecture](https://learn.microsoft.com/en-us/training/modules/power-automate-architecture/)** — Advanced, 34 min, 8 units. uid: `learn-bizapps.power-automate-architecture`. Explore the architecture of Microsoft Power Automate.
- **[Explore Power Pages design studio](https://learn.microsoft.com/en-us/training/modules/power-pages-studio/)** — Intermediate, 49 min, 9 units. uid: `learn-bizapps.power-pages-studio`. Power Pages makers spend most of their time building sites in Power Pages design studio. It's important that makers have a full understanding of the capabilities and also the limitations of the design studio. This module focuses on understanding and using the design studio to create and customize sites — including adding and configuring pages, components, CSS, and forms, securing the site with the Security workspace, and using Copilot and AI-powered agents to accelerate site development and enhance the visitor experience.
- **[Explore Power Pages design studio data and security features](https://learn.microsoft.com/en-us/training/modules/power-pages-studio-data-security/)** — Intermediate, 31 min, 6 units. uid: `learn-bizapps.power-pages-studio-data-security`. Power Pages makers spend most their time building sites in Power Pages design studio. It's important that makers understand design studio capabilities as well as its limitations. Power Pages design studio includes Data workspace to create and manage business data and Set up workspace to configure site security and behavior. This module will focus on using the design studio to build secure Dataverse data-driven pages.
- **[Explore Power Pages templates](https://learn.microsoft.com/en-us/training/modules/power-pages-templates/)** — Intermediate, 25 min, 6 units. uid: `learn-bizapps.power-pages-templates`. Learn about Power Pages templates, pre-configured solutions that are available to help accelerate deployment.
- **[Export data from Dataverse and use Microsoft Excel to edit records](https://learn.microsoft.com/en-us/training/modules/export-dataverse-excel/)** — Beginner, 28 min, 7 units. uid: `learn-bizapps.export-dataverse-excel`. Discover how to export and edit Microsoft Dataverse table data using Excel files, while understanding security concepts.
- **[Extend Dataverse with Power Automate](https://learn.microsoft.com/en-us/training/modules/extend-dataverse-power-automate/)** — Intermediate, 36 min, 7 units. uid: `learn-bizapps.extend-dataverse-power-automate`. Learn how to extend Microsoft Dataverse with Microsoft Power Automate.
- **[Extend Dynamics 365 apps with Power Platform and Copilot Studio](https://learn.microsoft.com/en-us/training/modules/extend-dynamics365-apps-power-platform/)** — Intermediate, 61 min, 9 units. uid: `learn-dynamics.extend-dynamics365-apps-power-platform`. Learn how to unlock the full potential of Dynamics 365 Sales, Customer Service, Contact Center, Customer Insights, and Field Service by extending them with Power Automate, Power Apps, Power BI, Power Pages, Copilot Studio, and Model Context Protocol.
- **[Extend plug-ins in Power Platform](https://learn.microsoft.com/en-us/training/modules/extend-plug-ins/)** — Intermediate, 56 min, 6 units. uid: `learn-bizapps.extend-plug-ins`. The purpose of this module is to provide an in-depth overview of plug-ins as it relates to Microsoft Power Platform development. This module will review how and when plug-ins are implemented, how they're registered and deployed, and the various configuration options that are available during plug-in registration.
- **[Extend Power Pages websites](https://learn.microsoft.com/en-us/training/modules/power-pages-extend/)** — Advanced, 67 min, 8 units. uid: `learn-bizapps.power-pages-extend`. Extend website functionality by using software development and deploying Power Pages websites with ALM techniques.
- **[Extract event log data for process mining](https://learn.microsoft.com/en-us/training/modules/extract-event-log/)** — Beginner, 59 min, 9 units. uid: `learn-bizapps.extract-event-log`. Learn how to extract event log data for process mining.
- **[Extract information from business cards with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-business-card-reader/)** — Beginner, 41 min, 6 units. uid: `learn-bizapps.get-started-with-ai-business-card-reader`. Learn about AI Builder Business card reader and how to use it in Microsoft Power Apps and Power Automate.
- **[Extract invoice data with AI Builder’s prebuilt model](https://learn.microsoft.com/en-us/training/modules/ai-builder-invoice-processing/)** — Beginner, 10 min, 4 units. uid: `learn-bizapps.ai-builder-invoice-processing`. Create a seamless flow with Microsoft Power Automate using invoice processing.
- **[Functional Consultant skills](https://learn.microsoft.com/en-us/training/modules/functional-consultant-skills/)** — Intermediate, 74 min, 14 units. uid: `learn.wwl.functional-consultant-skills`. Learn about the functional consultant role and the key skills needed to be successful in this role on a Microsoft Power Platform project.
- **[Generate Power Automate for desktop flows by recording](https://learn.microsoft.com/en-us/training/modules/pad-power-automate-desktop-recording-features/)** — Beginner, 35 min, 6 units. uid: `learn-bizapps.pad-power-automate-desktop-recording-features`. In this module, we'll examine the ways in which users can automate tasks by performing them manually and recording the flow.
- **[Get data in Power BI](https://learn.microsoft.com/en-us/training/modules/get-data/)** — Intermediate, 106 min, 13 units. uid: `learn-bizapps.get-data`. Connect to data sources including Excel, relational databases, and NoSQL stores in Power BI. Learn techniques to optimize performance and resolve common import errors.
- **[Get started with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder/)** — Beginner, 30 min, 6 units. uid: `learn-bizapps.get-started-with-ai-builder`. This self-paced module helps you build an AI model from the beginning and shows how you can use it in your business without writing a single line of code.
- **[Get started with AI Builder category classification](https://learn.microsoft.com/en-us/training/modules/ai-builder-category-classification/)** — Beginner, 26 min, 5 units. uid: `learn-bizapps.ai-builder-category-classification`. Discover how to utilize AI Builder category classification to tag text with category labels, like emails.
- **[Get started with AI Builder entity extraction](https://learn.microsoft.com/en-us/training/modules/ai-builder-entity-extraction/)** — Beginner, 20 min, 5 units. uid: `learn-bizapps.ai-builder-entity-extraction`. Explore AI Builder entity extraction, its application in business scenarios, and use in Power Automate.
- **[Get started with AI Builder licensing](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder-licensing/)** — Beginner, 40 min, 6 units. uid: `learn-bizapps.get-started-with-ai-builder-licensing`. Learn about AI Builder licensing, including the two levels of licensing, how to purchase the product add-on, and how to manage AI Builder capacity.
- **[Get started with AI Builder prediction](https://learn.microsoft.com/en-us/training/modules/ai-builder-prediction/)** — Beginner, 24 min, 5 units. uid: `learn-bizapps.ai-builder-prediction`. Discover the AI Builder prediction model and its different outcome patterns.
- **[Get started with Copilot in Power BI](https://learn.microsoft.com/en-us/training/modules/power-bi-copilot/)** — Intermediate, 27 min, 6 units. uid: `learn-bizapps.power-bi-copilot`. Copilot in Power BI allows you to interact with your data using natural language to gain insights. Copilot also increases productivity when create reports using Power BI.
- **[Get started with custom connectors in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/get-started-custom-connector/)** — Intermediate, 45 min, 8 units. uid: `learn-bizapps.get-started-custom-connector`. Learn how to configure and use custom connectors with Microsoft Power Apps, Microsoft Power Automate, and Microsoft Azure Logic Apps.
- **[Get started with FinOps](https://learn.microsoft.com/en-us/training/modules/get-started-with-finops/)** — Beginner, 20 min, 9 units. uid: `learn.azure.get-started-with-finops`. Learn about the FinOps Framework and the impact of transitioning from a CapEx to an OpEx model.
- **[Get started with Microsoft Dataverse for Teams](https://learn.microsoft.com/en-us/training/modules/get-started-dataverse-teams/)** — Beginner, 21 min, 6 units. uid: `learn-bizapps.get-started-dataverse-teams`. This module introduces Microsoft Dataverse for Teams and how you can build apps, workflows, chatbots, and dashboards in it. You'll learn how to provision Dataverse for Teams and then create a table for your data.
- **[Get started with Power Apps component framework](https://learn.microsoft.com/en-us/training/modules/get-started-power-apps-component-framework/)** — Intermediate, 46 min, 7 units. uid: `learn-bizapps.get-started-power-apps-component-framework`. Explore Microsoft Power Apps component framework and its architecture, along with tooling techniques.
- **[Get started with security concepts in Dataverse](https://learn.microsoft.com/en-us/training/modules/get-started-security-concepts/)** — Intermediate, 54 min, 9 units. uid: `learn-bizapps.get-started-security-concepts`. Learn about getting started with security concepts in Microsoft Dataverse.
- **[Get started with security roles in Dataverse](https://learn.microsoft.com/en-us/training/modules/get-started-security-roles/)** — Intermediate, 41 min, 10 units. uid: `learn-dynamics.get-started-security-roles`. Learn how you can set permissions to limit access to an environment, or limit which users can view, edit, or delete data in an environment within Dataverse.
- **[Get started with the Power Automate Process Mining desktop app](https://learn.microsoft.com/en-us/training/modules/process-mining-desktop-app/)** — Beginner, 41 min, 10 units. uid: `learn-bizapps.process-mining-desktop-app`. Learn how to get started with the Power Automate Process Mining desktop app.
- **[Get tips and tricks for teaching PL-100 Microsoft Power Platform App Maker](https://learn.microsoft.com/en-us/training/modules/get-tips-tricks-teach-pl-100-microsoft-power-platform-app-maker/)** — Beginner, 33 min, 12 units. uid: `learn.wwl.get-tips-tricks-teach-pl-100-microsoft-power-platform-app-maker`. Learn tips and tricks about preparing for your first teaching session, which labs to use, when and how to introduce technical topics, as well as other resources and materials.
- **[Get tips and tricks for teaching PL-200: Microsoft Power Platform Functional Consultant](https://learn.microsoft.com/en-us/training/modules/get-tips-tricks-for-teaching-microsoft-power-platform-functional-consultant/)** — Beginner, 60 min, 15 units. uid: `learn.wwl.get-tips-tricks-for-teaching-microsoft-power-platform-functional-consultant`. Learn tips and tricks about preparing for your first teaching session, which labs to use, when and how to introduce technical topics, as well as other resources and materials.
- **[Get tips and tricks for teaching PL-900 Microsoft Power-platform Fundamentals](https://learn.microsoft.com/en-us/training/modules/get-tips-tricks-teach-pl-900-microsoft-power-platform-fundamentals/)** — Beginner, 44 min, 12 units. uid: `learn.wwl.get-tips-tricks-teach-pl-900-microsoft-power-platform-fundamentals`. Learn tips and tricks about preparing for your first teaching session, which labs to use, when and how to introduce technical topics, as well as other resources and materials.
- **[Get to know the project team for Dynamics 365 implementations](https://learn.microsoft.com/en-us/training/modules/project-team-dynamics-365-implementation/)** — Beginner, 62 min, 7 units. uid: `learn-dynamics.project-team-dynamics-365-implementation`. Discover the complexities of implementing Dynamics 365 projects, understanding team roles and the importance of coordination.
- **[Get to know your Dynamics 365 customers](https://learn.microsoft.com/en-us/training/modules/get-know-dynamics-365-customers/)** — Beginner, 95 min, 9 units. uid: `learn-dynamics.get-know-dynamics-365-customers`. Discover skills and techniques to be an effective Dynamics 365 functional consultant by understanding your customer.
- **[Go to market through the commercial marketplace](https://learn.microsoft.com/en-us/training/modules/go-to-market-commercial-marketplace/)** — Beginner, 31 min, 8 units. uid: `learn.go-to-market-commercial-marketplace`. This module provides tips and best practices to help organizations create their business plan for success in the commercial marketplace
- **[Governance for process mining](https://learn.microsoft.com/en-us/training/modules/governance-process-mining/)** — Beginner, 20 min, 6 units. uid: `learn-bizapps.governance-process-mining`. Learn about governance for process mining.
- **[Handle variables in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-variables/)** — Beginner, 55 min, 10 units. uid: `learn-bizapps.pad-variables`. In this module, we'll discuss how to create, access, edit and manipulate variables in Power Automate desktop app.
- **[Hyperautomation with insights from process mining](https://learn.microsoft.com/en-us/training/modules/hyperautomation-process-mining/)** — Beginner, 30 min, 8 units. uid: `learn-bizapps.hyperautomation-process-mining`. Learn about hyperautomation with insights from process mining.
- **[Identify key phrases with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder-key-phrase-extraction/)** — Beginner, 25 min, 5 units. uid: `learn-bizapps.get-started-with-ai-builder-key-phrase-extraction`. Explore the AI Builder Key phrase extraction model and learn how to use it with other Microsoft Power Platform products.
- **[Identify the language of text with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder-language-detection/)** — Beginner, 28 min, 5 units. uid: `learn-bizapps.get-started-with-ai-builder-language-detection`. Explore AI Builder Language detection and learn how to use it with other Microsoft Power Platform products.
- **[Import and export solutions with cloud flows](https://learn.microsoft.com/en-us/training/modules/import-export-solutions/)** — Beginner, 48 min, 7 units. uid: `learn-bizapps.import-export-solutions`. Discover the basics of using solutions with cloud flows, including manual and automated options, benefits, and import/export procedures.
- **[Improve SAP seller productivity with Microsoft Teams and Power Platform](https://learn.microsoft.com/en-us/training/modules/improve-sap-seller-productivity-microsoft-teams-power-platform/)** — Intermediate, 38 min, 7 units. uid: `learn.wwl.improve-sap-seller-productivity-microsoft-teams-power-platform`. Integrate applications from SAP with the Microsoft 365 applications. Enable productivity and collaboration in "SAP Sales and Service Core" Teams app to support sales by building Power Automate flows.
- **[Innovate using RISE with SAP on the Microsoft Cloud](https://learn.microsoft.com/en-us/training/modules/innovate-rise-sap-microsoft-cloud/)** — Intermediate, 26 min, 5 units. uid: `learn.wwl.innovate-rise-sap-microsoft-cloud`. Explore how to leverage both RISE with SAP and Microsoft Cloud to optimize workflows, automate tasks, enhance decision-making, and improve team communication and collaboration.
- **[Install required software for Power Automate: Automation - Online workshop](https://learn.microsoft.com/en-us/training/modules/install-required-software-online-workshop/)** — Beginner, 46 min, 8 units. uid: `learn-bizapps.install-required-software-online-workshop`. Learn how to install required software.
- **[Integrate Dataverse Azure solutions](https://learn.microsoft.com/en-us/training/modules/integrate-dataverse-azure-solutions/)** — Advanced, 121 min, 7 units. uid: `learn-bizapps.integrate-dataverse-azure-solutions`. Gain an in-depth overview of options available within Dataverse to integrate data and events to Azure.
- **[Integrate desktop flows with Outlook connector in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/integrate-flow-outlook/)** — Intermediate, 23 min, 6 units. uid: `learn-bizapps.integrate-flow-outlook`. Learn how to integrate desktop flows with Microsoft Outlook in Power Automate for desktop.
- **[Integrate other Microsoft products with Dynamics 365 Customer Engagement apps](https://learn.microsoft.com/en-us/training/modules/integrating-office-customer-engagement-apps/)** — Beginner, 45 min, 7 units. uid: `learn-dynamics.integrating-office-and-dynamics-365-customer-engagement`. Work with templates and integrate other products to expand the capability of Dynamics 365 Customer Engagement apps.
- **[Integrate Power Pages websites with Dataverse](https://learn.microsoft.com/en-us/training/modules/power-pages-integrate-dataverse/)** — Intermediate, 58 min, 8 units. uid: `learn-bizapps.power-pages-integrate-dataverse`. Explore techniques for implementing Dataverse data on Power Pages websites, including setting up lists, forms, and multistep form processes.
- **[Integrate Power Pages with web-based technologies](https://learn.microsoft.com/en-us/training/modules/power-pages-integration/)** — Intermediate, 26 min, 6 units. uid: `learn-bizapps.power-pages-integration`. Learn how to integrate Power Pages with web-based technologies.
- **[Integrate with cloud flows - Online workshop](https://learn.microsoft.com/en-us/training/modules/integrate-cloud-flows-online-workshop/)** — Beginner, 64 min, 8 units. uid: `learn-bizapps.integrate-cloud-flows-online-workshop`. Learn how to integrate with cloud flows.
- **[Integrate with Microsoft Teams to get approvals - Online workshop](https://learn.microsoft.com/en-us/training/modules/integrate-teams-approval-online-workshop/)** — Beginner, 29 min, 5 units. uid: `learn-bizapps.integrate-teams-approval-online-workshop`. Explore automation in invoice processing with Teams integration, human approval mechanisms, and Outlook-based notifications.
- **[Interact, share, and collaborate Power BI dashboards – Online workshop](https://learn.microsoft.com/en-us/training/modules/interact-share-power-bi/)** — Beginner, 82 min, 6 units. uid: `learn-bizapps.interact-share-power-bi`. Learn how to share Power BI dashboards, collaborate with other users, and access a dashboard on a mobile device.
- **[Introduction and prerequisites for Power BI – Online workshop](https://learn.microsoft.com/en-us/training/modules/intro-power-bi/)** — Beginner, 35 min, 6 units. uid: `learn-bizapps.intro-power-bi`. Steps of installing the required software on your computer so that you can complete this course.
- **[Introduction and prerequisites for Power Pages - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-introduction-online-workshop/)** — Intermediate, 43 min, 7 units. uid: `learn-bizapps.power-pages-introduction-online-workshop`. Explore how to simplify order updates for Contoso Coffee's suppliers using Power Apps in this extended learning path/workshop.
- **[Introduction to agentic AI business solutions](https://learn.microsoft.com/en-us/training/modules/introduction-agentic-ai-business-solution-architecture/)** — Advanced, 24 min, 8 units. uid: `learn.wwl.introduction-agentic-ai-business-solution-architecture`. Learn how to align AI solutions with business goals, scale AI adoption, and use Microsoft AI technologies for enterprise success.
- **[Introduction to becoming a business applications professional](https://learn.microsoft.com/en-us/training/modules/introduction-business-applications-professional/)** — Beginner, 56 min, 6 units. uid: `learn-dynamics.introduction-business-applications-professional`. Discover the role of a Business Applications professional, explore Dynamics 365 community resources, and learn about relevant certifications.
- **[Introduction to Dataverse for developers](https://learn.microsoft.com/en-us/training/modules/introduction-dataverse-developers/)** — Intermediate, 30 min, 5 units. uid: `learn-bizapps.introduction-dataverse-developers`. The goal of this module is to give an introductory overview of Microsoft Power Platform SDKs that are available from Microsoft via NuGet.
- **[Introduction to email processing with Dynamics 365 Customer Engagement apps](https://learn.microsoft.com/en-us/training/modules/introduction-integration-customer-engagement-apps/)** — Beginner, 53 min, 7 units. uid: `learn-dynamics.introduction-to-integration-with-dynamics-365-customer-engagement`. Configure Dynamics 365 Customer Engagement apps to work with your email and manage your mailboxes.
- **[Introduction to expressions in Power Automate](https://learn.microsoft.com/en-us/training/modules/introduction-expressions/)** — Intermediate, 37 min, 8 units. uid: `learn-bizapps.introduction-expressions`. Learn how to write expressions in Power Automate.
- **[Introduction to extending Power Platform](https://learn.microsoft.com/en-us/training/modules/introduction-power-platform-extend/)** — Advanced, 39 min, 7 units. uid: `learn-bizapps.introduction-power-platform-extend`. This module will focus on the underlying solution architecture from a technical perspective and what extensibility options exist. It will also cover the ever-important element of Microsoft Power Platform development, which is the decision-making process of determining when to use configuration versus code.
- **[Introduction to Microsoft Power Platform developer resources](https://learn.microsoft.com/en-us/training/modules/introduction-power-platform-developer-resources/)** — Advanced, 53 min, 7 units. uid: `learn-bizapps.introduction-power-platform-developer-resources`. The goal of this module is to give a broad-scoped overview of the developer experience as it relates to Microsoft Power Platform.  It will cover a high-level introduction how the ecosystem is represented, with the intended audience being a software developer with limited experience in working with Microsoft Power Platform.
- **[Introduction to Power Apps cards](https://learn.microsoft.com/en-us/training/modules/introduction-power-apps-cards/)** — Beginner, 26 min, 7 units. uid: `learn-bizapps.introduction-power-apps-cards`. Watch videos and follow exercises that introduce you to Power Apps cards.
- **[Introduction to Power Automate process mining](https://learn.microsoft.com/en-us/training/modules/intro-process-mining/)** — Beginner, 39 min, 8 units. uid: `learn-bizapps.intro-process-mining`. Learn about the basics of process mining in Power Automate.
- **[Introduction to Power Pages administration](https://learn.microsoft.com/en-us/training/modules/power-pages-admin-intro/)** — Intermediate, 49 min, 6 units. uid: `learn-bizapps.power-pages-admin-intro`. Learn about Power Pages administration and explore how Power Pages tools can help you accomplish administrative tasks.
- **[Introduction to solutions for Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/introduction-solutions/)** — Beginner, 13 min, 6 units. uid: `learn-bizapps.introduction-solutions`. Learn how to transport an existing app and components from one environment to another.
- **[Introduction to the Microsoft commercial marketplace](https://learn.microsoft.com/en-us/training/modules/intro-commercial-marketplace/)** — Beginner, 30 min, 7 units. uid: `learn.intro-commercial-marketplace`. Learn about the Microsoft commercial marketplace, including Microsoft AppSource, Azure Marketplace, offer types, and Marketplace Rewards.
- **[Link your Dataverse environment to Microsoft Fabric](https://learn.microsoft.com/en-us/training/modules/link-dataverse-fabric/)** — Beginner, 29 min, 8 units. uid: `learn-bizapps.link-dataverse-fabric`. Learn how to link your Dataverse environment to Microsoft Fabric.
- **[Load/export data and create data views in Dataverse](https://learn.microsoft.com/en-us/training/modules/load-export-data-create-data-views/)** — Beginner, 52 min, 10 units. uid: `learn-dynamics.load-export-data-create-data-views`. Learn how to view, load, and export data in Dataverse tables.
- **[Manage Microsoft Power Platform deployments](https://learn.microsoft.com/en-us/training/modules/designing-power-platform-deployments/)** — Intermediate, 54 min, 9 units. uid: `learn-dynamics.designing-power-platform-deployments`. Learn about managing Microsoft Power Platform deployments
- **[Manage models in AI Builder](https://learn.microsoft.com/en-us/training/modules/manage-models/)** — Beginner, 17 min, 5 units. uid: `learn-bizapps.manage-models`. Learn how to manage models in AI Builder.
- **[Manage process mining projects](https://learn.microsoft.com/en-us/training/modules/manage-process-mining/)** — Beginner, 43 min, 9 units. uid: `learn-bizapps.manage-process-mining`. Learn how to manage process mining projects.
- **[Manage semantic models in Power BI](https://learn.microsoft.com/en-us/training/modules/manage-datasets-power-bi/)** — Intermediate, 25 min, 9 units. uid: `learn-bizapps.manage-datasets-power-bi`. Semantic models are the foundation for report development in Power BI. Efficient management ensures data connectivity and improves report performance and accuracy.
- **[Manage solutions in Power Apps and Power Automate](https://learn.microsoft.com/en-us/training/modules/manage-solutions-power-automate/)** — Intermediate, 52 min, 8 units. uid: `learn-bizapps.manage-solutions-power-automate`. Learn how to manage solutions in Microsoft Power Apps and Power Automate.
- **[Manage tables in Dataverse](https://learn.microsoft.com/en-us/training/modules/create-manage-entities/)** — Beginner, 44 min, 7 units. uid: `learn-dynamics.create-manage-entities`. Dataverse tables are similar to tables in a database. Every instance of a Dataverse database includes a base set of tables that provide structure for data that is commonly used by business applications.
- **[Manage testing AI-powered business solutions](https://learn.microsoft.com/en-us/training/modules/manage-testing-ai-powered-business-solutions/)** — Advanced, 35 min, 8 units. uid: `learn.wwl.manage-testing-ai-powered-business-solutions`. Learn to validate and maintain AI-powered business solutions with structured testing frameworks, metrics, and governance for enterprise reliability.
- **[Manage workspaces in Power BI service](https://learn.microsoft.com/en-us/training/modules/manage-workspaces-power-bi-service/)** — Intermediate, 20 min, 6 units. uid: `learn-bizapps.manage-workspaces-power-bi-service`. Explore the Power BI service, create and manage workspaces, and distribute reports to users.
- **[Monitor, analyze, and tune AI agents](https://learn.microsoft.com/en-us/training/modules/analyze-monitor-tune-ai-powered-business-solutions/)** — Advanced, 36 min, 8 units. uid: `learn.analyze-monitor-tune-ai-powered-business-solutions`. Learn to monitor, analyze, and tune AI agents for reliability, performance, and continuous improvement in enterprise environments.
- **[Navigation in a canvas app in Power Apps](https://learn.microsoft.com/en-us/training/modules/navigation-canvas-app/)** — Intermediate, 54 min, 6 units. uid: `learn-bizapps.navigation-canvas-app`. In this module, learners do an in-depth exploration of navigation in Power Apps.
- **[OCR technologies in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-ocr/)** — Intermediate, 22 min, 5 units. uid: `learn-bizapps.pad-ocr`. This module covers the OCR actions in Power Automate for desktop.
- **[Optimize a model for performance in Power BI](https://learn.microsoft.com/en-us/training/modules/optimize-model-power-bi/)** — Intermediate, 69 min, 9 units. uid: `learn-bizapps.optimize-model-power-bi`. Performance optimization, also known as performance tuning, involves making changes to the current state of the semantic model so that it runs more efficiently. Essentially, when your semantic model is optimized, it performs better.
- **[Optimize app load time](https://learn.microsoft.com/en-us/training/modules/optimize-app-load-time/)** — Intermediate, 30 min, 6 units. uid: `learn-bizapps.optimize-app-load-time`. Learn how you can evaluate and improve app load times. By regularly reviewing and measuring your app, you can proactively identify and remediate startup performance problems.
- **[Optimize your business process with process advisor](https://learn.microsoft.com/en-us/training/modules/business-process-optimization-process-advisor/)** — Beginner, 26 min, 8 units. uid: `learn-bizapps.business-process-optimization-process-advisor`. Learn how to optimize your business process with the process advisor capability in Microsoft Power Automate.
- **[Orchestrate configuration of prebuilt agents and apps](https://learn.microsoft.com/en-us/training/modules/orchestrate-configuration-prebuilt-agents-apps/)** — Intermediate, 57 min, 10 units. uid: `learn.wwl.orchestrate-configuration-prebuilt-agents-apps`. Learn to orchestrate, configure, and extend AI-driven experiences in Dynamics 365 and Microsoft 365 Copilot for finance, supply chain, and customer service.
- **[Overview of HTTP connectors in Power Automate](https://learn.microsoft.com/en-us/training/modules/http-connectors/)** — Intermediate, 20 min, 6 units. uid: `learn-bizapps.http-connectors`. Interact directly with data using web requests with HTTP connectors in Power Automate flows.
- **[Perform common actions with client script in Power Platform](https://learn.microsoft.com/en-us/training/modules/actions-client-script-power-platform/)** — Intermediate, 44 min, 8 units. uid: `learn-bizapps.actions-client-script-power-platform`. The goal of this module is to review how to achieve common user experience automation procedures through Client Script. This module is intended to serve as a practical guide for how to solve real-world scenarios that are frequently encountered during Microsoft Power Platform implementations.
- **[Perform custom updates in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/perform-custom-updates-powerapps-canvas-app/)** — Intermediate, 38 min, 6 units. uid: `learn-bizapps.perform-custom-updates`. With some Power Apps canvas apps, a form isn't the solution. This module focuses on how to perform custom updates when your data isn't in a form.
- **[Perform fit gap analysis](https://learn.microsoft.com/en-us/training/modules/fit-gap-analysis/)** — Advanced, 44 min, 7 units. uid: `learn-dynamics.fit-gap-analysis`. Learn about performing a fit gap analysis as a solution architect for Dynamics 365 and Microsoft Power Platform.
- **[Power Automate desktop app development essentials](https://learn.microsoft.com/en-us/training/modules/pad-power-automate-desktop-development-essentials/)** — Beginner, 30 min, 9 units. uid: `learn-bizapps.pad-power-automate-desktop-development-essentials`. This module covers the basic development features available in Power Automate desktop app.
- **[Power Automate's deep integration across multiple data sources](https://learn.microsoft.com/en-us/training/modules/multiple-data-sources/)** — Beginner, 49 min, 7 units. uid: `learn-bizapps.multiple-data-sources`. Learn to build flows across multiple data sources.
- **[Power Pages administration](https://learn.microsoft.com/en-us/training/modules/power-pages-administration/)** — Intermediate, 39 min, 6 units. uid: `learn-bizapps.power-pages-administration`. This module focuses on Microsoft Power Pages administration and using the Microsoft Power Platform admin center. Additionally, other actions and features are available for you to use to enhance website functionality.
- **[Power Pages data workspace - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-data-workspace-online-workshop/)** — Intermediate, 18 min, 4 units. uid: `learn-bizapps.power-pages-data-workspace-online-workshop`. Learn about the data workspace in Power Pages.
- **[Power Pages maintenance and troubleshooting](https://learn.microsoft.com/en-us/training/modules/power-pages-maintenance-troubleshooting/)** — Intermediate, 31 min, 6 units. uid: `learn-bizapps.power-pages-maintenance-troubleshooting`. Learn about Power Pages maintenance and troubleshooting.
- **[Power Pages solution explorer - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-solution-explorer-online-workshop/)** — Intermediate, 28 min, 6 units. uid: `learn-bizapps.power-pages-solution-explorer-online-workshop`. Learn how to set up a solution in Power Pages solution explorer.
- **[Power Pages styling workspace - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-styling-workspace-online-workshop/)** — Intermediate, 18 min, 4 units. uid: `learn-bizapps.power-pages-styling-workspace-online-workshop`. Learn about the styling workspace in Power Pages.
- **[Power Pages workspace data components - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-workspace-data-components-online-workshop/)** — Intermediate, 37 min, 9 units. uid: `learn-bizapps.power-pages-workspace-data-components-online-workshop`. Learn to set up your site according to Contoso Coffee's use case, including creating webpages and lists, and modifying table permissions.
- **[Power Pages workspace setup - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-workspace-setup-online-workshop/)** — Intermediate, 13 min, 5 units. uid: `learn-bizapps.power-pages-workspace-setup-online-workshop`. Learn about Power Pages workspace setup.
- **[Power Pages workspace site design - Online workshop](https://learn.microsoft.com/en-us/training/modules/power-pages-workspace-site-design-online-workshop/)** — Intermediate, 31 min, 5 units. uid: `learn-bizapps.power-pages-workspace-site-design-online-workshop`. Learn about workspace site design in Power Pages.
- **[Present Business Applications designs to stakeholders](https://learn.microsoft.com/en-us/training/modules/present-business-applications-designs/)** — Beginner, 93 min, 11 units. uid: `learn-dynamics.present-business-applications-designs`. Discover effective strategies for presenting to stakeholders, handling presentation issues, and communicating Business Applications designs.
- **[Process custom documents with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-form-processing/)** — Beginner, 32 min, 5 units. uid: `learn-dynamics.get-started-with-form-processing`. Explore the fundamentals of AI Builder's Document processing, its benefits to your organization, and its integration with Power Apps.
- **[Process receipts with AI Builder](https://learn.microsoft.com/en-us/training/modules/ai-builder-receipt-processing/)** — Beginner, 15 min, 6 units. uid: `learn-bizapps.ai-builder-receipt-processing`. Learn the basics of receipt processing in AI Builder and how it can benefit your organization.
- **[Propose a solution as a Solution Architect for Microsoft Power Platform and Dynamics 365](https://learn.microsoft.com/en-us/training/modules/propose-solution/)** — Advanced, 40 min, 7 units. uid: `learn-dynamics.propose-solution`. Learn how to propose a solution.
- **[Publish and access reports in Power BI service – Online workshop](https://learn.microsoft.com/en-us/training/modules/publish-access-reports/)** — Beginner, 86 min, 6 units. uid: `learn-bizapps.publish-access-reports`. Learn how to use Power BI to create a mobile view, publish a report, build a dashboard, and use storytelling with Power BI within PowerPoint.
- **[Recognize text with AI Builder](https://learn.microsoft.com/en-us/training/modules/get-started-with-ai-builder-text-recognition/)** — Beginner, 34 min, 6 units. uid: `learn-bizapps.get-started-with-ai-builder-text-recognition`. Learn about AI Builder Text recognition and how to use it with other Microsoft Power Platform products.
- **[Reduce complexity in your data model with Dataverse table relationships](https://learn.microsoft.com/en-us/training/modules/reduce-complexity-dataverse-table/)** — Intermediate, 44 min, 6 units. uid: `learn-bizapps.reduce-complexity-dataverse-table`. Learn how to use Microsoft Dataverse relationships in canvas apps from Microsoft Power Apps.
- **[Run a Power Automate for desktop flow in unattended mode](https://learn.microsoft.com/en-us/training/modules/flow-unattended-mode/)** — Intermediate, 14 min, 7 units. uid: `learn-bizapps.flow-unattended-mode`. Learn how to run an unattended Microsoft Power Automate for desktop flow.
- **[Scope report design requirements](https://learn.microsoft.com/en-us/training/modules/power-bi-effective-requirements/)** — Intermediate, 29 min, 8 units. uid: `learn-bizapps.power-bi-effective-requirements`. Identify your audience, choose suitable report types, and define interface and experience requirements to effectively plan your report design.
- **[Scripting in Power Automate desktop app](https://learn.microsoft.com/en-us/training/modules/pad-scripting/)** — Advanced, 33 min, 6 units. uid: `learn-bizapps.pad-scripting`. Explore Power Automate desktop app, enabling automation of complex scenarios using VBScript, JavaScript, PowerShell, and Python.
- **[Secure data access in Power BI](https://learn.microsoft.com/en-us/training/modules/row-level-security-power-bi/)** — Intermediate, 39 min, 8 units. uid: `learn-bizapps.row-level-security-power-bi`. Row-level security (RLS) and Object-level security (OLS) allows you to create a single or a set of reports that targets data for a specific user. In this module, you'll learn how to implement RLS by using either a static or dynamic method and how Microsoft Power BI simplifies testing RLS in Power BI Desktop and Power BI service.
- **[Securely connect to SAP on Azure](https://learn.microsoft.com/en-us/training/modules/protect-azure-for-sap-workloads/)** — Intermediate, 29 min, 8 units. uid: `learn.wwl.protect-azure-for-sap-workloads`. Learn to describe Azure Networking services and components for connecting and securing SAP S/4 HANA in Azure, and learn how different requirements might adjust networking services requirements.
- **[Set up low-code plug-ins](https://learn.microsoft.com/en-us/training/modules/configure-low-code/)** — Beginner, 47 min, 9 units. uid: `learn-bizapps.configure-low-code`. Learn how to set up low-code plug-ins.
- **[Set up pipeline environments in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/set-up-pipeline-environments/)** — Intermediate, 23 min, 7 units. uid: `learn-bizapps.set-up-pipeline-environments`. Learn how to set up pipeline environments in Microsoft Power Platform.
- **[Set up Power Pages security](https://learn.microsoft.com/en-us/training/modules/power-pages-configure-security/)** — Intermediate, 47 min, 6 units. uid: `learn-bizapps.power-pages-configure-security`. Learn how to set up Power Pages security.
- **[Shape data in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/shape-data/)** — Intermediate, 58 min, 7 units. uid: `learn-bizapps.shape-data`. When you create a canvas app, do you need to show the user all the data? What if you want to show only the data that is relevant to them? This module will help you address this issue.
- **[Simulate mouse and keyboard actions by using Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-mouse-keyboard/)** — Beginner, 26 min, 5 units. uid: `learn-bizapps.pad-mouse-keyboard`. Learn to automate simulated mouse movement, clicks, typing, and key presses in Power Automate. Also, discover how to select and locate images or areas on the screen.
- **[Solution Architect series: Evaluate Power Platform analytics and AI](https://learn.microsoft.com/en-us/training/modules/architect-analytics/)** — Advanced, 41 min, 9 units. uid: `learn-bizapps.architect-analytics`. Learn about reporting and analytics in Microsoft Power Platform.
- **[Solution Architect series: Explore Power Apps architecture](https://learn.microsoft.com/en-us/training/modules/power-apps-architecture/)** — Advanced, 40 min, 9 units. uid: `learn-bizapps.power-apps-architecture`. Explore the architecture of Microsoft Power Apps.
- **[Solution architect series: Explore robotic process automation](https://learn.microsoft.com/en-us/training/modules/robotic-process-automation/)** — Advanced, 27 min, 7 units. uid: `learn-bizapps.robotic-process-automation`. Learn about Microsoft Power Automate for desktop and its capabilities.
- **[Solution Architect series: Implement integrations with Power Platform](https://learn.microsoft.com/en-us/training/modules/integrations/)** — Advanced, 27 min, 6 units. uid: `learn-bizapps.integrations`. Learn how to implement integrations in Microsoft Power Platform solutions.
- **[Solution Architect series: Implement project governance for Power Platform and Dynamics 365](https://learn.microsoft.com/en-us/training/modules/project-governannce/)** — Advanced, 28 min, 7 units. uid: `learn-bizapps.project-governance`. Learn about project governance as a solution architect.
- **[Solution architect series: Model data for Power Platform solutions](https://learn.microsoft.com/en-us/training/modules/data-modeling/)** — Intermediate/advanced, 72 min, 13 units. uid: `learn-bizapps.data-modeling`. Explore the role of solution architects in data modeling for Power Platform, including data types and relationships.
- **[Solution architect series: Model security for Power Platform solutions](https://learn.microsoft.com/en-us/training/modules/model-security/)** — Advanced, 58 min, 8 units. uid: `learn-bizapps.model-security`. Lean about security functionality within Microsoft Dataverse.
- **[Solution Architect series: Plan application lifecycle management for Power Platform](https://learn.microsoft.com/en-us/training/modules/application-lifecycle-management-architect/)** — Advanced, 39 min, 8 units. uid: `learn-bizapps.application-lifecycle-management-architect`. Solution architects for Microsoft Power Platform need to define the environment strategy and application lifecycle management (ALM) for transporting work from development to test to production.
- **[Solution Architect series: Power Platform architecture](https://learn.microsoft.com/en-us/training/modules/power-platform-architecture/)** — Advanced, 54 min, 9 units. uid: `learn-bizapps.power-platform-architecture`. Explore the role of solution architects in designing Power Platform-based solutions, emphasizing understanding its architecture.
- **[Solution Architect series: Testing and go-live](https://learn.microsoft.com/en-us/training/modules/project-test-process/)** — Advanced, 22 min, 6 units. uid: `learn-bizapps.project-test-process`. The solution architect role is continuous; they must also deploy the solution.
- **[Test your Dynamics 365 implementation](https://learn.microsoft.com/en-us/training/modules/test-dynamics-365-implementation/)** — Beginner, 70 min, 9 units. uid: `learn-dynamics.test-dynamics-365-implementation`. Discover the importance of testing in building business applications with Dynamics 365, including types of tests and automation usage.
- **[Text manipulation in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-text-manipulation/)** — Intermediate, 27 min, 6 units. uid: `learn-bizapps.pad-text-manipulation`. Learn how to manipulate text and datetime values in Power Automate for desktop.
- **[The Principles of Sustainable Software Engineering](https://learn.microsoft.com/en-us/training/modules/sustainable-software-engineering-overview/)** — Beginner, 25 min, 10 units. uid: `learn.azure.sustainable-software-engineering-overview`. Sustainable Software Engineering is an emerging discipline at the intersection of climate science, software, hardware, electricity markets, and data center design. The Principles of Sustainable Software Engineering are a core set of competencies needed to define, build, and run sustainable software applications.
- **[Transform and load event log data for process mining](https://learn.microsoft.com/en-us/training/modules/transform-load-event-log/)** — Beginner, 43 min, 7 units. uid: `learn-bizapps.transform-load-event-log`. Learn how to transform and load event log data for process mining.
- **[Troubleshoot slow-running flows in Power Automate](https://learn.microsoft.com/en-us/training/modules/troubleshoot-slow-flows/)** — Intermediate, 23 min, 7 units. uid: `learn-bizapps.troubleshoot-slow-flows`. Learn how to troubleshoot slow-running flows in Microsoft Power Automate.
- **[Turn business ideas into Power Platform solutions with Plans](https://learn.microsoft.com/en-us/training/modules/turn-business-ideas-power-platform-solutions-plans/)** — Beginner, 38 min, 8 units. uid: `learn.wwl.turn-business-ideas-power-platform-solutions-plans`. Use plans in Power Apps to describe a business problem in natural language and let AI agents generate user requirements, a data model, and a technology proposal — then build the complete solution.
- **[Turn insight into action by combining SAP and other data](https://learn.microsoft.com/en-us/training/modules/turn-insight-into-action-combine-sap-other-data/)** — Beginner, 30 min, 10 units. uid: `learn.wwl.turn-insight-into-action-combine-sap-other-data`. Explore Microsoft solutions and products that can help you address analytics needs that include both SAP and other data. You’ll learn about using the Azure Synapse Analytics platform to combine data from multiple sources and examine how Power Platform is used to display and analyze business data to turn insights into action.
- **[Use administration options for Dataverse](https://learn.microsoft.com/en-us/training/modules/use-admin-options-cds/)** — Intermediate, 64 min, 11 units. uid: `learn-dynamics.use-admin-options-cds`. Do you need to use administration options that are available for Dataverse? This module will show you how you can use solutions within Dataverse and administer environments.
- **[Use AI Builder in Power Automate](https://learn.microsoft.com/en-us/training/modules/ai-builder-power-automate/)** — Intermediate, 37 min, 7 units. uid: `learn-bizapps.ai-builder-power-automate`. Learn the basics of AI Builder usage in Microsoft Power Automate and how it can benefit your organization.
- **[Use AI Builder models in Power Apps](https://learn.microsoft.com/en-us/training/modules/use-ai-builder/)** — Beginner, 26 min, 7 units. uid: `learn-bizapps.use-ai-builder`. Explore AI Builder's ready-to-use models, enhancing Power Apps user experience and offering interactive controls.
- **[Use AI Builder to process invoice forms in Power Automate](https://learn.microsoft.com/en-us/training/modules/use-ai-builder-process-invoice/)** — Intermediate, 16 min, 8 units. uid: `learn-bizapps.use-ai-builder-process-invoice`. Learn how to use AI Builder to process invoice forms in Microsoft Power Automate.
- **[Use Azure and external tools to manipulate data](https://learn.microsoft.com/en-us/training/modules/understand-azure-dataverse/)** — Intermediate, 22 min, 5 units. uid: `learn-bizapps.understand-azure-dataverse`. Learn how to use Azure and external tools to manipulate data.
- **[Use common low-code plug-in scenarios](https://learn.microsoft.com/en-us/training/modules/common-low-code-plug-in/)** — Intermediate, 59 min, 9 units. uid: `learn-bizapps.common-low-code-plug-in`. Learn about using common low-code plug-in scenarios.
- **[Use Copilot in Power Pages](https://learn.microsoft.com/en-us/training/modules/use-copilot-power-pages/)** — Beginner, 29 min, 6 units. uid: `learn-bizapps.use-copilot-power-pages`. Learn how to use Copilot in Power Pages.
- **[Use custom code in custom connectors for Microsoft Power Platform](https://learn.microsoft.com/en-us/training/modules/custom-code-connectors/)** — Intermediate, 38 min, 6 units. uid: `learn-bizapps.custom-code-connectors`. Learn about custom code in custom connectors for Microsoft Power Platform.
- **[Use custom connectors in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/use-custom-connectors-in-powerapps-canvas-app/)** — Intermediate, 46 min, 5 units. uid: `learn-bizapps.custom-connectors`. Learn how to use custom connectors in a Power Apps canvas app.
- **[Use Dataverse choice columns with formulas](https://learn.microsoft.com/en-us/training/modules/choice-columns-formulas/)** — Intermediate, 42 min, 6 units. uid: `learn-bizapps.choice-columns-formulas`. Explore how you can use Power Fx formulas to work with Microsoft Dataverse choice and choices columns. These column data types present the user with a fixed list of values defined by the maker.
- **[Use Dataverse triggers and actions in Power Automate](https://learn.microsoft.com/en-us/training/modules/use-dataverse-triggers-actions/)** — Intermediate, 67 min, 7 units. uid: `learn-bizapps.use-dataverse-triggers-actions`. Extend Dataverse usability by integrating with Power Automate to reduce or eliminate repetitive business processes.
- **[Use developer tools to extend Power Platform](https://learn.microsoft.com/en-us/training/modules/developer-tools-extend/)** — Advanced, 47 min, 7 units. uid: `learn-bizapps.developer-tools-extend`. This module will focus on the available developer tools that can help you perform development activities with Power Platform.
- **[Use imperative development techniques for canvas apps in Power Apps](https://learn.microsoft.com/en-us/training/modules/use-imperative-dev-techniques-powerapps-canvas-app/)** — Advanced, 57 min, 9 units. uid: `learn-bizapps.use-imperative-dev-techniques`. Learn how to use imperative vs. declarative development.
- **[Use input and output variables - Online workshop](https://learn.microsoft.com/en-us/training/modules/use-input-output-online-workshop/)** — Beginner, 28 min, 5 units. uid: `learn-bizapps.use-input-output-online-workshop`. Learn how to use input and output variables for automatic invoice entry.
- **[Use Microsoft 365 services with model-driven apps and Microsoft Dataverse](https://learn.microsoft.com/en-us/training/modules/use-services-model-driven-apps/)** — Intermediate, 74 min, 10 units. uid: `learn-dynamics.use-services-model-driven-apps`. Learn how to use Microsoft 365 services with Power Apps model-driven apps and Dynamics 365 customer engagement apps.
- **[Use Microsoft Word and Excel templates with Dataverse](https://learn.microsoft.com/en-us/training/modules/use-word-excel-dataverse/)** — Beginner, 34 min, 7 units. uid: `learn-bizapps.use-word-excel-dataverse`. Explore how you can create data analysis and standardized documents by using Microsoft Dataverse data along with Microsoft Word and Excel templates.
- **[Use Monitor to troubleshoot Power Apps](https://learn.microsoft.com/en-us/training/modules/monitor-to-troubleshoot/)** — Intermediate, 40 min, 6 units. uid: `learn-bizapps.monitor-to-troubleshoot`. Learn how the Monitor tool from Power Apps Studio can help you proactively identify, troubleshoot, and resolve issues within your app.
- **[Use Outlook email to trigger desktop flows and pass inputs - Online workshop](https://learn.microsoft.com/en-us/training/modules/outlook-flows-online-workshop/)** — Beginner, 32 min, 5 units. uid: `learn-bizapps.outlook-flows-online-workshop`. Learn how to use Outlook email to trigger desktop flows and pass inputs.
- **[Use Power Apps Instrumentation with Application Insights](https://learn.microsoft.com/en-us/training/modules/instrumentation-app-insights/)** — Intermediate, 38 min, 7 units. uid: `learn-bizapps.instrumentation-app-insights`. This module explores how to set up a Microsoft Power Apps canvas app to send telemetry to Application Insights.
- **[Use Power Automate desktop app to interact with windows and applications](https://learn.microsoft.com/en-us/training/modules/pad-ui-automation/)** — Beginner, 18 min, 5 units. uid: `learn-bizapps.pad-ui-elements`. Learn how Power Automate desktop app identifies and interacts with UI elements and windows.
- **[Use Power Automate to increase productivity](https://learn.microsoft.com/en-us/training/modules/use-power-automate-increase-productivity/)** — Beginner, 58 min, 10 units. uid: `learn.mec.use-power-automate-increase-productivity`. Educators gain a greater understanding of what Power Automate is and explore what Power Automate can do. See how Power Automate can benefit educators simplify everyday tasks.
- **[Use Power Query to load data in Dataverse](https://learn.microsoft.com/en-us/training/modules/use-power-query/)** — Beginner, 29 min, 7 units. uid: `learn-bizapps.use-power-query`. Learn how to synchronize data from different sources to a Microsoft Dataverse table using Power Query and create dataflows in Power Apps.
- **[Use process mining in Power Automate web portal](https://learn.microsoft.com/en-us/training/modules/use-process-mining/)** — Beginner, 44 min, 7 units. uid: `learn-bizapps.use-process-mining`. Learn how to use process mining in the Power Automate web portal.
- **[Use specialized components in a model-driven form](https://learn.microsoft.com/en-us/training/modules/specialized-components-model-form/)** — Beginner, 47 min, 8 units. uid: `learn-bizapps.specialized-components-model-form`. Learn how to create a business process flow, embed a canvas app, add a timeline, and create a report in a model-driven form.
- **[Use text generation in AI Builder](https://learn.microsoft.com/en-us/training/modules/ai-builder-text-generation/)** — Intermediate, 40 min, 5 units. uid: `learn-bizapps.ai-builder-text-generation`. Try a template and write your own instructions with text generation in AI Builder.
- **[Use the Teams connector in Power Automate](https://learn.microsoft.com/en-us/training/modules/use-teams-connector/)** — Intermediate, 17 min, 8 units. uid: `learn-bizapps.use-teams-connector`. Learn how to use the Teams connector in Microsoft Power Automate.
- **[Visualize data with Dataverse views](https://learn.microsoft.com/en-us/training/modules/visualize-data/)** — Beginner, 28 min, 7 units. uid: `learn-bizapps.visualize-data`. Discover the different types of Dataverse views and how to create and edit them.
- **[Web automation in Power Automate for desktop](https://learn.microsoft.com/en-us/training/modules/pad-web/)** — Beginner, 66 min, 8 units. uid: `learn-bizapps.pad-web`. This module covers the browser automation actions in Power Automate for desktop.
- **[Work with choices in Dataverse](https://learn.microsoft.com/en-us/training/modules/working-with-option-sets/)** — Beginner, 21 min, 6 units. uid: `learn-dynamics.working-with-option-sets`. Do you want to create standardized choice lists that you can use across all of your Power Apps?  This module shows you how to create new or use standard choice lists called choices in Dataverse.
- **[Work with data source limits (delegation limits) in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/work-with-data-source-limits-powerapps-canvas-app/)** — Intermediate, 33 min, 5 units. uid: `learn-bizapps.data-source-limits`. Delegate data with Power Apps.
- **[Work with Dataverse Web API](https://learn.microsoft.com/en-us/training/modules/dataverse-web-api/)** — Advanced, 111 min, 10 units. uid: `learn-bizapps.dataverse-web-api`. Discover how to work with the Dataverse Web API, including authorizing with OAuth and using OData to query data.
- **[Work with Liquid template language in Power Pages](https://learn.microsoft.com/en-us/training/modules/power-pages-liquid/)** — Intermediate, 48 min, 7 units. uid: `learn-bizapps.power-pages-liquid`. Integrate Liquid into Power Pages for dynamic content and custom templates.
- **[Work with Power Pages metadata](https://learn.microsoft.com/en-us/training/modules/power-pages-metadata/)** — Intermediate, 54 min, 7 units. uid: `learn-bizapps.power-pages-metadata`. Explore Power Pages metadata components and learn how to use the Portal Management app for setting up unique website features.
- **[Work with relational data in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/modules/work-with-relational-data-powerapps-canvas-app/)** — Intermediate, 45 min, 6 units. uid: `learn-bizapps.work-with-relational-data`. Learn how to work with relational data in Power Apps canvas apps.
- **[Work with requirements for Microsoft Power Platform and Dynamics 365](https://learn.microsoft.com/en-us/training/modules/work-with-requirements/)** — Advanced, 23 min, 7 units. uid: `learn-dynamics.work-with-requirements`. Discover how to accurately capture customer needs, lead requirement sessions, and identify functional and non-functional requirements for Microsoft Power Platform and Dynamics 365.

---

## Learning paths (catalog data only, not modules)

*93 learning paths matched product=power-platform OR product=power-automate OR product=power-apps. Listed for completeness; not in scope for page-level module fetching.*

- **[Administer Power Pages](https://learn.microsoft.com/en-us/training/paths/administer-power-pages/)** — Advanced, 151 min, 4 modules. uid: `learn-bizapps.administer-power-pages`. Learn how to administer Power Pages sites.
- **[Advanced Canvas App Development in Power Apps: Mastering Formulas and Development Techniques](https://learn.microsoft.com/en-us/training/paths/advanced-canvas-app-development-mastering-formulas-techniques/)** — Intermediate, 96 min, 2 modules. uid: `learn.wwl.advanced-canvas-app-development-mastering-formulas-techniques`. This learning path teaches how to write complex formulas and apply imperative development techniques in Power Apps, including understanding various development methods and utilizing different types of variables.
- **[Advanced Model-Driven Apps with Power Apps: Configuration, Customization, and Deployment Techniques](https://learn.microsoft.com/en-us/training/paths/advanced-model-driven-apps-configuration-customization-deployment/)** — Intermediate, 220 min, 5 modules. uid: `learn.wwl.advanced-model-driven-apps-configuration-customization-deployment`. This learning path covers creating and customizing model-driven apps in Microsoft Power Platform, including using forms, views, and dashboards, deploying and evolving apps, and leveraging reporting, analytics, and command customization.
- **[Application lifecycle management for the Power Platform](https://learn.microsoft.com/en-us/training/paths/application-lifecycle-management/)** — Intermediate, 124 min, 4 modules. uid: `learn-bizapps.application-lifecycle-management`. Application lifecycle management (ALM) is important as the applications your organization builds becomes more complex and as more of your company depends on their stability. ALM is not a one size fits all concept, it can vary from organization to organization and even within based on the type of solution being built. This learning path can help you with ALM best practices.
- **[Architect AI solutions for business productivity](https://learn.microsoft.com/en-us/training/paths/architect-agentic-ai-business-solutions/)** — Advanced, 684 min, 11 modules. uid: `learn.wwl.architect-agentic-ai-business-solutions`. Learn how to design AI-powered business solutions using agents, generative AI, and Microsoft Copilot to enhance productivity and efficiency.
- **[Architect solutions for Dynamics 365 and Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/become-solution-architect/)** — Advanced, 217 min, 5 modules. uid: `learn-dynamics.become-solution-architect`. Becoming a Solution Architect for Dynamics 365 and Microsoft Power Platform.
- **[Automate a business process using Power Automate](https://learn.microsoft.com/en-us/training/paths/automate-process-power-automate/)** — Beginner, 277 min, 7 modules. uid: `learn-bizapps.automate-process-using-flow`. This learning path introduces you to Power Automate, teaches you how to build workflows, and how to administer flows.
- **[Automate a business process with expressions and Dataverse actions using Power Automate](https://learn.microsoft.com/en-us/training/paths/automate-business-process-expressions-dataverse-actions/)** — Beginner, 166 min, 3 modules. uid: `learn.wwl.automate-business-process-expressions-dataverse-actions`. Automate a business process with expressions and Dataverse actions using Power Automate
- **[Automate and extend your solutions with AI in Microsoft Power Automate](https://learn.microsoft.com/en-us/training/paths/automate-business-processes-power-automate/)** — Beginner/intermediate, 207 min, 4 modules. uid: `learn.wwl.automate-business-processes-power-automate`. Wire your Power Platform solutions with intelligent automation and generative AI capabilities. Create event-driven cloud flows, connect automation directly to your Dataverse data model, build approval flows that route decisions to the right people — then extend your solutions further by generating natural language responses from your own business data with AI Builder grounded prompts.
- **[Automate processes with Robotic Process Automation and Power Automate for desktop](https://learn.microsoft.com/en-us/training/paths/work-automation-flow/)** — Intermediate, 174 min, 8 modules. uid: `learn-bizapps.work-automation-flow`. Learn how use Robotic Process Automation to automate business processes.
- **[Basic application lifecycle management in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/basic-application-lifecycle-management-microsoft-power-platform/)** — Intermediate, 65 min, 2 modules. uid: `learn.wwl.basic-application-lifecycle-management-microsoft-power-platform`. Learn how to create and manage solutions, understand solution layering, and explore version control for solutions.
- **[Build and optimize cloud flows in Power Automate](https://learn.microsoft.com/en-us/training/paths/build-optimize-cloud-flows-power-automate/)** — Beginner, 159 min, 5 modules. uid: `learn.wwl.build-optimize-cloud-flows-power-automate`. Build and optimize cloud flows in Power Automate
- **[Build basic code components with the Power Apps Component Framework](https://learn.microsoft.com/en-us/training/paths/build-basic-code-components-power-apps-component-framework/)** — Beginner, 93 min, 2 modules. uid: `learn.wwl.build-basic-code-components-power-apps-component-framework`. Build basic code components with the Power Apps Component Framework
- **[Build custom connectors for Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/build-custom-connectors/)** — Intermediate, 254 min, 6 modules. uid: `learn-bizapps.build-custom-connectors`. Learn how to build custom connectors for Microsoft Power Platform.
- **[Build expertise with Power Automate desktop app](https://learn.microsoft.com/en-us/training/paths/pad-build-expertise/)** — Advanced, 153 min, 5 modules. uid: `learn-bizapps.pad-build-expertise`. Build expertise with using advanced actions in Power Automate desktop app.
- **[Build intelligent apps and portals with Microsoft Power Apps](https://learn.microsoft.com/en-us/training/paths/build-apps-portals-power-apps/)** — Beginner/intermediate, 426 min, 7 modules. uid: `learn.wwl.build-apps-portals-power-apps`. Build AI-ready apps and portals that surface intelligent, Dataverse-backed data. Create and customize canvas apps, configure model-driven apps for customer engagement, and build data-connected Power Pages portals for any audience.
- **[Build websites with Power Pages - Online Workshop](https://learn.microsoft.com/en-us/training/paths/power-pages-online-workshop/)** — Beginner, 188 min, 7 modules. uid: `learn-bizapps.power-pages-online-workshop`. Learn how to create websites with Power Pages.
- **[Build your data model with Microsoft Dataverse](https://learn.microsoft.com/en-us/training/paths/build-data-model-microsoft-dataverse/)** — Beginner/intermediate, 202 min, 3 modules. uid: `learn.wwl.build-data-model-microsoft-dataverse`. Build the data foundation that intelligent Power Platform solutions are built on. Learn how Dataverse tables and columns work, how to model your business data, apply security roles to control access, and encode business logic directly into the data layer with business rules.
- **[Connect and share cloud flow to desktop flows in Power Automate for desktop](https://learn.microsoft.com/en-us/training/paths/connect-share-cloud-flow-desktop-flows-power-automate/)** — Intermediate, 75 min, 2 modules. uid: `learn.wwl.connect-share-cloud-flow-desktop-flows-power-automate`. Connect and share cloud flow to desktop flows in Power Automate for desktop
- **[Create a canvas app in Power Apps](https://learn.microsoft.com/en-us/training/paths/create-powerapps/)** — Beginner, 319 min, 6 modules. uid: `learn-bizapps.create-powerapps`. Do you want to create apps to help make your business more efficient? Then, this path is for you. It introduces you to Power Apps, helps you create and customize an app, and then manage and distribute it.
- **[Create a machine ordering app with Power Apps - Online Workshop](https://learn.microsoft.com/en-us/training/paths/power-apps-online-workshop/)** — Beginner, 334 min, 4 modules. uid: `learn-bizapps.power-apps-online-workshop`. Learn how to create an app with Power Apps.
- **[Create a model-driven application in Power Apps](https://learn.microsoft.com/en-us/training/paths/create-app-models-business-processes/)** — Beginner, 273 min, 4 modules. uid: `learn-bizapps.create-app-models-business-processes`. This learning path introduces you to creating a model-driven app in Power Apps that uses Microsoft Dataverse.
- **[Create and Manage Automated Processes by using Power Automate](https://learn.microsoft.com/en-us/training/paths/create-manage-automated-processes-by-using-power-automate/)** — Intermediate, 217 min, 5 modules. uid: `learn.wwl.create-manage-automated-processes-by-using-power-automate`. In this learning path, you practice creating and managing automated processes by using Power Automate. PL-7002
- **[Create and manage canvas apps with Power Apps](https://learn.microsoft.com/en-us/training/paths/create-manage-canvas-apps-power-apps/)** — Intermediate, 374 min, 7 modules. uid: `learn.wwl.create-manage-canvas-apps-power-apps`. In this learning path, you practice creating and managing canvas apps with Power Apps. These skills  include connecting to data sources, building screens, selecting appropriate components and adding them to screens, and publishing and sharing canvas apps. (PL-7001)
- **[Create apps, copilots, flows, and more with Microsoft Dataverse and Teams](https://learn.microsoft.com/en-us/training/paths/work-power-platform-teams/)** — Beginner, 146 min, 5 modules. uid: `learn-bizapps.work-power-platform-teams`. Learn how to create apps, flows, and more with Microsoft Dataverse for Teams
- **[Create components with Power Apps Component Framework](https://learn.microsoft.com/en-us/training/paths/create-components-power-apps-component-framework/)** — Advanced, 93 min, 2 modules. uid: `learn-bizapps.create-components-power-apps-component-framework`. Learn how to build custom components and controls with Power Apps component framework.
- **[Create Power Platform solutions with AI and Copilot](https://learn.microsoft.com/en-us/training/paths/copilot-solutions/)** — Beginner, 252 min, 6 modules. uid: `learn-bizapps.copilot-solutions`. Learn how to create solutions for Power Platform with AI and Copilot.
- **[Create relationships, business rules, calculations, and rollups in Dataverse](https://learn.microsoft.com/en-us/training/paths/create-relationships-common-data-service/)** — Intermediate, 143 min, 3 modules. uid: `learn-dynamics.create-relationships-business-rules-calculations-and-rollups-in-common-data-service`. Do you need to create data relationships, business rules, calculations, and rollups in Dataverse? These modules help you use Dataverse to build powerful business solutions to transform your operations, processes, and your entire organization. The learning path Get started with Dataverse introduces you to Dataverse and many of the key concepts which include environment, entities, fields, and options sets.  This learning path continues and expands the exploration of Dataverse with an overview how to form relationships between entities, how to build business rules to perform logic based upon your organization's needs, and how to add calculations and rollup fields.
- **[Customize the command bar in Power Apps](https://learn.microsoft.com/en-us/training/paths/command-bar-power-apps/)** — Intermediate, 115 min, 3 modules. uid: `learn-bizapps.command-bar-power-apps`. Power Apps model-driven apps implement a consistent user experience. A key component of that experience is how users are presented and can interact with available commands. As part of designing the model-driven app, a maker can customize the bars to add commands, hide commands and modify their behavior. This learning path introduces you to how to customize the command bar. We also cover common scenarios and advanced concepts.
- **[Dashboard in a Day - Online workshop](https://learn.microsoft.com/en-us/training/paths/dashboard-in-a-day/)** — Beginner, 441 min, 8 modules. uid: `learn-bizapps.dashboard-in-a-day`. Learn how to create your first dashboard in Power BI.
- **[Demonstrate the capabilities of Microsoft Power Apps](https://learn.microsoft.com/en-us/training/paths/demonstrate-capabilities-power-apps/)** — Beginner, 201 min, 3 modules. uid: `learn.wwl.demonstrate-capabilities-power-apps`. This learning path introduces learners to Power apps. This includes a general discussion of capabilities and then specific focus on canvas apps and model-driven apps. PL-900
- **[Demonstrate the capabilities of Microsoft Power Automate](https://learn.microsoft.com/en-us/training/paths/demonstrate-capabilities-microsoft-power-automate/)** — Beginner, 135 min, 2 modules. uid: `learn.wwl.demonstrate-capabilities-microsoft-power-automate`. This learning path introduces makers to Power Automates cloud and desktop flows, covering key concepts like triggers, actions, loops, and branching. Learners explore real-world use cases across Microsoft 365 apps, leverage Copilot to build and describe flows, and gain hands-on experience with testing, monitoring, and sharing automations. The path also includes an introduction to Process Mining and desktop automation using Power Automate for Desktop. PL-900
- **[Describe the business value of Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/describe-business-value-microsoft-power-platform/)** — Beginner, 106 min, 2 modules. uid: `learn.wwl.describe-business-value-microsoft-power-platform`. This learning path serves as an introduction to the Power Platform. It discusses the Power Platform components: Power BI, Power Apps, Power Automate, Power Pages and Microsoft Copilot Studio. It covers Microsoft Dataverse as the common data foundation, and connectors that allow Power Platform apps to access a vast list of data sources. The learning path also discusses Power Platform's native integration with Microsoft 365 services, its ability to connect to on-premises systems, and the capabilities of the Plan Designer. PL-900
- **[Design an accident tracking app in Power Apps](https://learn.microsoft.com/en-us/training/paths/design-accident-tracking/)** — Beginner, 84 min, 3 modules. uid: `learn-bizapps.accident-tracking-app`. Learn how to build an employee accident tracking app from start to finish. In this learning path, you'll explore activities such as transforming a business process into a model-driven app, creating a data table, and adding a business process flow to the app.
- **[Design Dynamics 365 Solutions](https://learn.microsoft.com/en-us/training/paths/design-dynamics-365-solutions/)** — Beginner, 279 min, 5 modules. uid: `learn-dynamics.design-dynamics-365-solutions`. While the technology is important, designing solutions with Dynamics 365 is about more than the technology. You must know your customers and speak their industry language. You need to understand how to gather and document requirements. You'll explore and define the business processes and map them to functionality to implement solutions with Dynamics 365.
- **[Desktop flows and Robotic Process Automation in Power Automate](https://learn.microsoft.com/en-us/training/paths/desktop-flows-robotic-process-automation-power-automate/)** — Intermediate, 372 min, 10 modules. uid: `learn.wwl.desktop-flows-robotic-process-automation-power-automate`. Desktop flows and Robotic Process Automation in Power Automate
- **[Discover AI for leaders in nonprofit](https://learn.microsoft.com/en-us/training/paths/discover-ai-leaders-nonprofit/)** — Beginner, 192 min, 5 modules. uid: `learn.wwl.discover-ai-leaders-nonprofit`. Discover AI for leaders in nonprofit
- **[Enhance agents with autonomous capabilities](https://learn.microsoft.com/en-us/training/paths/enhance-autonomous-agents/)** — Intermediate, 120 min, 3 modules. uid: `learn-bizapps.enhance-autonomous-agents`. Learn how to configure agents to behave autonomously.
- **[Extend Dynamics 365 Sales with AI and Power Platform tools](https://learn.microsoft.com/en-us/training/paths/extend-d365-sales-ai-platforms/)** — Beginner, 192 min, 3 modules. uid: `learn.wwl.extend-d365-sales-ai-platforms`. Learn how to enhance Dynamics 365 Sales with AI tools and Power Platform capabilities, including mobile apps, automation, and analytics.
- **[Extend Power Pages](https://learn.microsoft.com/en-us/training/paths/extend-power-pages/)** — Advanced, 119 min, 2 modules. uid: `learn-bizapps.extend-power-pages`. Learn how to extend Power Pages.
- **[Extend Power Platform user experience with model-driven apps](https://learn.microsoft.com/en-us/training/paths/extend-power-platform-user-experience/)** — Advanced, 131 min, 3 modules. uid: `learn-bizapps.extend-power-platform-user-experience`. Learn how to extend Power Platform user experience with model-driven apps.
- **[Extend the user experience with client scripting and command bar customization](https://learn.microsoft.com/en-us/training/paths/extend-user-experience-client-scripting-command-bar-customization/)** — Intermediate, 120 min, 3 modules. uid: `learn.wwl.extend-user-experience-client-scripting-command-bar-customization`. Extend the user experience with client scripting and command bar customization
- **[Extending Power Platform Dataverse](https://learn.microsoft.com/en-us/training/paths/extend-power-platform-dataverse/)** — Intermediate, 197 min, 3 modules. uid: `learn-bizapps.extend-power-platform-dataverse`. Get started with extending Power Platform Dataverse.
- **[Get started using Dataverse](https://learn.microsoft.com/en-us/training/paths/get-started-cds/)** — Beginner, 364 min, 7 modules. uid: `learn-dynamics.get-started-using-common-data-service`. Do you want to learn how to build solutions that can use a standardized data structure, and work with other solutions sharing the same data model?  Do you want to extend the standard model to support custom solutions? This learning path explains the concepts behind and benefits of Dataverse. Creating an environment, entities, fields and options sets are also discussed.
- **[Get started with AI-first solutions in Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/design-model-solutions-power-platform/)** — Beginner, 91 min, 3 modules. uid: `learn.wwl.design-model-solutions-power-platform`. Establish the AI-first mindset and foundational skills you need to build intelligent Power Platform solutions. Learn to apply AI-first design patterns with Copilot, master prompt engineering to work effectively with generative AI, and use AI-powered Plans to translate business ideas into structured solution blueprints.
- **[Get started with Copilot for Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/copilot-power-platform/)** — Beginner, 157 min, 4 modules. uid: `learn-bizapps.copilot-power-platform`. Microsoft Copilot for Microsoft Power Platform helps makers of all skill levels accelerate the creation of Power Apps, Power Automate flows, Power Pages and Dataverse tables used by the apps and services.  Understanding how to best plan and use Copilot is essential for success.
- **[Get started with custom connectors for Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/get-started-custom-connectors-microsoft-power-platform/)** — Intermediate, 217 min, 5 modules. uid: `learn.wwl.get-started-custom-connectors-microsoft-power-platform`. Get started with custom connectors for Microsoft Power Platform
- **[Get started with Power Automate desktop app](https://learn.microsoft.com/en-us/training/paths/pad-get-started/)** — Beginner, 67 min, 2 modules. uid: `learn-bizapps.pad-get-started`. Learn the essentials of Power Automate desktop app.
- **[Get Started with Power Pages](https://learn.microsoft.com/en-us/training/paths/power-pages-get-started/)** — Intermediate, 230 min, 6 modules. uid: `learn-bizapps.power-pages-get-started`. Get started creating websites with Power Pages
- **[Get started with process mining in Power Automate](https://learn.microsoft.com/en-us/training/paths/introduction-process-advisor/)** — Beginner, 185 min, 5 modules. uid: `learn-bizapps.introduction-process-advisor`. Learn how to work with process mining in Power Automate
- **[Implement advanced logic in Power Automate for desktop](https://learn.microsoft.com/en-us/training/paths/pad-implement-advanced-logic/)** — Intermediate, 107 min, 5 modules. uid: `learn-bizapps.pad-implement-advanced-logic`. Learn how to develop advanced flows in Power Automate for desktop.
- **[Implement AI models with Microsoft Power Platform AI Builder](https://learn.microsoft.com/en-us/training/paths/implement-ai-models-microsoft-power-platform-ai-builder/)** — Intermediate, 192 min, 6 modules. uid: `learn.wwl.implement-ai-models-microsoft-power-platform-ai-builder`. Implement AI models with Microsoft Power Platform AI Builder
- **[Implement Dynamics 365 Projects](https://learn.microsoft.com/en-us/training/paths/implement-dynamics-365-projects/)** — Beginner, 388 min, 5 modules. uid: `learn-dynamics.implement-dynamics-365-projects`. As you implement Dynamics 365 solutions, you have many considerations. These include designing for users, sharing solutions and progress with stakeholders, testing and documenting the solutions, and participating in application lifecycle management that your team has put in place.
- **[Integrate Power Automate flows and Dataverse](https://learn.microsoft.com/en-us/training/paths/integrate-dataverse-power-automate/)** — Intermediate, 103 min, 2 modules. uid: `learn-bizapps.integrate-dataverse-power-automate`. Learn how you to Integrate Power Automate flows and Dataverse.
- **[Integrate SharePoint and Power Automate](https://learn.microsoft.com/en-us/training/paths/integrate-power-automate/)** — Intermediate, 138 min, 6 modules. uid: `learn-bizapps.integrate-power-automate`. Learn how SharePoint and Power Automate are integrated.
- **[Integrate with Dataverse and Azure](https://learn.microsoft.com/en-us/training/paths/integrate-dataverse-azure/)** — Intermediate, 179 min, 3 modules. uid: `learn.wwl.integrate-dataverse-azure`. Integrate with Dataverse and Azure
- **[Integrate with Power Platform and Dataverse](https://learn.microsoft.com/en-us/training/paths/integrate-power-platform-dataverse/)** — Advanced, 232 min, 2 modules. uid: `learn-bizapps.integrate-power-platform-dataverse`. Learn how to integrate Power Platform and Dataverse.
- **[Introduction to developing with Microsoft Power Platform](https://learn.microsoft.com/en-us/training/paths/introduction-development-power-platform/)** — Intermediate, 139 min, 3 modules. uid: `learn-bizapps.introduction-development-power-platform`. This learning path is the first step in learning about the platform, tools, and the ecosystem of Power Platform.
- **[Learn the fundamentals of Dynamics 365 projects](https://learn.microsoft.com/en-us/training/paths/learn-fundamentals-dynamics-365-projects/)** — Beginner, 349 min, 5 modules. uid: `learn-dynamics.learn-fundamentals-dynamics-365-projects`. Learn the fundamentals of Dynamics 365 projects, and better understand digital transformation, Dynamics 365 apps and services, project team members and stakeholders, and the types of implementation methodologies for Dynamics 365 projects.  This foundation will prepare you to continue your learning and prepare you for your first project
- **[Manage permissions and administration for Dataverse](https://learn.microsoft.com/en-us/training/paths/manage-permissions-administration-common-data-service/)** — Intermediate, 159 min, 3 modules. uid: `learn-dynamics.manage-permissions-and-administration-for-common-data-service`. Do you need to manage user access rights? In this learning path, you will learn how to manage permissions associated with environments and entities.  You will also learn about different administrative portals and how to access each.
- **[Manage the Microsoft Power Platform environment](https://learn.microsoft.com/en-us/training/paths/manage-microsoft-power-platform-environment/)** — Beginner, 84 min, 2 modules. uid: `learn.wwl.manage-microsoft-power-platform-environment`. This learning path covers the Microsoft Power Platform environment, equipping users with Dataverse—a scalable, secure data platform that supports relational data, business logic, and lifecycle management. It enables easy creation and modification of tables, relationships, and data flows. Additionally, it provides robust governance through role-based security, environment segmentation, admin centers, and compliance features, all supporting secure data handling and streamlined application lifecycle management (ALM). PL-900
- **[Monitor, evaluate, and operate multi-agent AI solutions in Azure](https://learn.microsoft.com/en-us/training/paths/aaai-4-monitor-evaluate-operate-multi-agent-ai-solutions-azure/)** — Advanced, 203 min, 5 modules. uid: `learn.wwl.monitor-evaluate-operate-multi-agent-ai-solutions-azure`. Learn how to operate production multi-agent solutions with comprehensive visibility, systematic quality assurance, cost control, and robust incident response. Learners advance from single-application monitoring and evaluation experiments to distributed multi-agent observability, LLM-as-judge evaluation for coordination quality, multi-agent cost optimization, enterprise human-in-the-loop approval workflows, and structured AI incident debugging procedures. AI-500
- **[Power Automate: Automation - Online Workshop](https://learn.microsoft.com/en-us/training/paths/robotic-process-automation-online-workshop/)** — Beginner, 329 min, 8 modules. uid: `learn-bizapps.robotic-process-automation-online-workshop`. Learn how to create robotic process automation flows.
- **[Power Platform Robotic Process Automation overview](https://learn.microsoft.com/en-us/training/paths/power-platform-robotic-process-automation-overview/)** — Intermediate, 170 min, 4 modules. uid: `learn.wwl.power-platform-robotic-process-automation-overview`. Power Platform Robotic Process Automation overview
- **[Power Platform Solution Management: Sharing, Customization, and Low-Code Development Essentials](https://learn.microsoft.com/en-us/training/paths/sharing-customization-low-code-development-essentials/)** — Intermediate, 146 min, 4 modules. uid: `learn.wwl.sharing-customization-low-code-development-essentials`. This learning path covers sharing Power Automate cloud flows, using Power Apps for app creation, managing solutions in Power Automate, and transporting and customizing apps within Microsoft Power Platform.
- **[Prepare to teach PL-100 Microsoft Power Platform App Maker](https://learn.microsoft.com/en-us/training/paths/teach-pl-100-microsoft-power-platform-app-maker/)** — Beginner, 204 min, 8 modules. uid: `learn.wwl.teach-pl-100-microsoft-power-platform-app-maker`. Learn about the Microsoft Learn for Educators program and how to best deliver its content to your students. Prepare to deliver Microsoft’s PL-100 Microsoft Power Platform App Maker in an academic program.
- **[Prepare to teach PL-200 Microsoft Power Platform Functional Consultant](https://learn.microsoft.com/en-us/training/paths/prepare-to-teach-pl-200-microsoft-power-platform-functional-consultant/)** — Beginner, 231 min, 8 modules. uid: `learn.wwl.prepare-to-teach-pl-200-microsoft-power-platform-functional-consultant`. Learn about the Microsoft Learn for Educators program and how to best deliver its content to your students. Prepare to deliver Microsoft’s PL-200 Microsoft Power Platform Functional Consultant in an academic program.
- **[Prepare to teach PL-900 Microsoft Power Platform fundamentals in academic programs](https://learn.microsoft.com/en-us/training/paths/prepare-teach-pl-900-fundamentals-academic-programs/)** — Beginner, 215 min, 8 modules. uid: `learn.wwl.prepare-teach-pl-900-fundamentals-academic-programs`. Prepare to teach PL-900 Microsoft Power Platform fundamentals in academic programs
- **[Process mining for the data wrangler](https://learn.microsoft.com/en-us/training/paths/process-mining-data-wrangler/)** — Beginner, 185 min, 4 modules. uid: `learn-bizapps.process-mining-data-wrangler`. Learn about process mining with Power Automate.
- **[Process mining for the process owner](https://learn.microsoft.com/en-us/training/paths/process-mining-process-owner/)** — Beginner/intermediate, 132 min, 4 modules. uid: `learn-bizapps.process-mining-process-owner`. Process mining in Power Automate can help organizations discover inefficiencies in their processes and enable them to gain a deeper understanding of what goes on within each process from start to finish.
- **[Sell through the commercial marketplace](https://learn.microsoft.com/en-us/training/paths/sell-through-commercial-marketplace/)** — Beginner, 126 min, 4 modules. uid: `learn.sell-through-commercial-marketplace`. The Microsoft commercial marketplace is a catalog of cloud applications and services that contains offerings from Microsoft and thousands of partners. In this learning path, you'll be introduced to concepts that will help your organization get ready to sell your cloud products and services through the commercial marketplace.
- **[Share and collaborate with Power Automate](https://learn.microsoft.com/en-us/training/paths/share-collaborate-power-automate/)** — Beginner, 98 min, 2 modules. uid: `learn-bizapps.share-collaborate-power-automate`. Learn how to effectively collaborate with others while working in Power Automate.
- **[Simplify Microsoft Power Platform deployments by using pipelines](https://learn.microsoft.com/en-us/training/paths/simplify-power-platform-deployments/)** — Intermediate, 58 min, 2 modules. uid: `learn.simplify-power-platform-deployments`. Learn pipeline concepts and how to set up, create, share, run, and extend pipelines.
- **[Solution Architect: Design Microsoft Power Platform solutions](https://learn.microsoft.com/en-us/training/paths/solution-architect-data/)** — Advanced, 488 min, 12 modules. uid: `learn-bizapps.solution-architect-design`. Learn how a solution architect designs solutions.
- **[Think like a Maker series: Plan and deploy your Power App](https://learn.microsoft.com/en-us/training/paths/plan-deploy/)** — Beginner, 173 min, 4 modules. uid: `learn-bizapps.plan-deploy-app`. Learn how to plan and deploy your Power App.
- **[Transform your business applications with fusion development](https://learn.microsoft.com/en-us/training/paths/transform-business-applications-with-fusion-development/)** — Beginner, 191 min, 5 modules. uid: `learn-bizapps.transform-with-fusion-dev`. Fusion development allows your business to build better applications, faster by bringing together professional developers with citizen, or low-code, developers. This learning path will teach you how a fusion development team functions, introduce low-code concepts for professional developers, and explain how a professional developer can enable their citizen developer counterparts to build amazing Power Apps applications using pro-code tools and frameworks they're already familiar and comfortable with, like JavaScript, ASP.NET Core web APIs, and Azure API Management.
- **[Use advance techniques in canvas apps to perform custom updates and optimization](https://learn.microsoft.com/en-us/training/paths/use-advance-techniques-canvas-apps-custom-updates-optimization/)** — Intermediate, 405 min, 10 modules. uid: `learn.wwl.use-advance-techniques-canvas-apps-custom-updates-optimization`. Use advance techniques in canvas apps to perform custom updates and optimization
- **[Use advanced data options and connectors in Power Apps](https://learn.microsoft.com/en-us/training/paths/advanced-data-options-and-connectors/)** — Advanced, 156 min, 4 modules. uid: `learn-bizapps.advanced-data-options-and-connectors`. Do you want to improve the user's experience in your canvas app? Do you want to use custom connectors to connect to data? This learning path will help you do both things. It will also focus on working with data source limits.
- **[Use advanced formula techniques and custom updates in Power Platform](https://learn.microsoft.com/en-us/training/paths/understand-advanced-topics/)** — Advanced, 220 min, 5 modules. uid: `learn-bizapps.understand-advanced-topics`. Do you want to use formulas in a more advanced way? This learning path will help you use advanced formulas and perform custom updates.
- **[Use basic formulas to make better Power Apps canvas apps](https://learn.microsoft.com/en-us/training/paths/use-basic-formulas-powerapps-canvas-app/)** — Intermediate, 152 min, 3 modules. uid: `learn-bizapps.use-basic-formulas-make-better-powerapps`. Do you want to use formulas to improve functionality and change a behavior in your Power Apps canvas app? This learning path can help you accomplish your goal.
- **[Use best practices to secure and govern Microsoft Power Platform environments](https://learn.microsoft.com/en-us/training/paths/best-practices-environments/)** — Intermediate, 410 min, 8 modules. uid: `learn-bizapps.best-practices-environments`. Learn how you can improve security posture and governance in Microsoft Power Platform.
- **[Use the UI and controls in a canvas app in Power Apps](https://learn.microsoft.com/en-us/training/paths/ui-controls-canvas-app-powerapps/)** — Intermediate, 223 min, 4 modules. uid: `learn-bizapps.ui-controls-canvas-app-powerapps`. The app user experience often defines the success of your app. This learning path will focus on how to provide the best app navigation, and build the best UI using themes, icons, images, personalization, different form factors, and controls.
- **[Validate your Microsoft Power Platform Solution Architect skills](https://learn.microsoft.com/en-us/training/paths/validate-power-platform-solution-architect-skills/)** — Intermediate, 280 min, 2 modules. uid: `learn.wwl.validate-power-platform-solution-architect-skills`. Validate your Microsoft Power Platform Solution Architect skills
- **[Validate your Power Platform Functional Consultant skills](https://learn.microsoft.com/en-us/training/paths/validate-power-platform-functional-consultant-skills/)** — Intermediate, 517 min, 5 modules. uid: `learn.wwl.validate-power-platform-functional-consultant-skills`. This learning path prepares you to complete the Microsoft Power Platform Functional Consultant challenge project and validate your skills. You should have already completed the following modules as part of the PL-200: Microsoft Power Platform Functional Consultant course. If you haven't, it's recommended that you take some time to complete these modules before beginning the challenge project.
- **[View, troubleshoot, and improve app performance for Power Apps canvas apps](https://learn.microsoft.com/en-us/training/paths/improve-app-performance/)** — Intermediate, 146 min, 4 modules. uid: `learn-bizapps.improve-app-performance`. Do you want to know how your app is performing and how to make it better? This learning path will help you identify your apps performance and share ways to troubleshoot your Power Apps canvas app.
- **[Visualize, import, and export Microsoft Dataverse data](https://learn.microsoft.com/en-us/training/paths/visualize-import-export-dataverse/)** — Intermediate, 141 min, 5 modules. uid: `learn-bizapps.visualize-import-export-data`. This learning path will show you how to use various Dataverse views, explore how Power Query can load data into Dataverse tables, and how to use Dataverse with third-party tools.
- **[Work with data in a Power Apps canvas app](https://learn.microsoft.com/en-us/training/paths/work-with-data-in-a-canvas-app/)** — Intermediate, 175 min, 3 modules. uid: `learn-bizapps.work-with-data-in-a-canvas-app`. Do you need to connect an app to access data? Then this learning path is for you. It will focus on how to connect to data sources. It also will show you how to use filtering, conditions, and other functions to shape your data and write data to your data source.
- **[Work with different technologies in Power Automate desktop app](https://learn.microsoft.com/en-us/training/paths/pad-work-different-technologies/)** — Intermediate, 257 min, 6 modules. uid: `learn-bizapps.pad-work-different-technologies`. This learning Path covers multiple technologies used with Power Automate desktop app.
- **[Work with Microsoft Power Platform tenants, environments, subscriptions, and Dynamics 365 apps](https://learn.microsoft.com/en-us/training/paths/implementing-customer-engagement-apps/)** — Intermediate, 103 min, 2 modules. uid: `learn-dynamics.implementing-customer-engagement-online`. Learn how to work with Microsoft Power Platform tenants, environments, subscriptions, and Dynamics 365 apps.
- **[Work with Power Automate desktop app](https://learn.microsoft.com/en-us/training/paths/pad-work/)** — Beginner, 220 min, 6 modules. uid: `learn-bizapps.pad-work`. Learn how to use features of Power Automate desktop app.
- **[Work with Power Automate error handling and expressions](https://learn.microsoft.com/en-us/training/paths/templates-error-handling-expressions-power-automate/)** — Intermediate, 54 min, 2 modules. uid: `learn.wwl.templates-error-handling-expressions-power-automate`. This learning path covers how to use your Power Automate skills to master error handling and expressions. Learn best practices for identifying and resolving flow failures efficiently using the flow actions and built-in error reports. Then, take your automation to the next level by leveraging expressions to manipulate and optimize your data. PL-200
- **[Work with Power Fx functions](https://learn.microsoft.com/en-us/training/paths/work-powerfx-functions/)** — Intermediate, 75 min, 2 modules. uid: `learn-bizapps.work-powerfx-functions`. Learn about Power Fx functions and build Power Fx functions.
- **[Work with Power Pages websites](https://learn.microsoft.com/en-us/training/paths/work-power-pages/)** — Advanced, 312 min, 7 modules. uid: `learn-bizapps.work-power-pages`. Learn how to work with Power Pages websites.

---

## Structure not retrieved (catalog data only)

*None. All 75 targeted modules in the "directly relevant" set resolved successfully on first fetch (no 404s or failures encountered).*
