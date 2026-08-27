# MS Learn — Modules tagged GitHub / VS Code

**Source:** https://learn.microsoft.com/en-us/training/browse/?products=github%2Cvs-code (catalog API: `product=github&product=vs-code&type=modules,learningPaths`)

**Scraped:** 2026-07-09

**Total modules found:** 231 (matches product=github OR product=vs-code — the catalog API unions multiple `product=` values, it does not intersect them) | **Learning paths found:** 49


> **Note on scope vs. original estimate:** An earlier WebFetch-based pass at this same catalog URL estimated "60 modules, 0 learning paths" — that number was an artifact of the fetch tool's summarization model skimming a large (~470 KB) JSON payload, not a real filtered count. This version was built by downloading the raw catalog JSON directly (`curl` + local parsing), which is authoritative: the catalog actually returns **231 modules** and **49 learning paths** for this URL (OR semantics across the two `product` values — only 16 modules carry *both* `github` and `vs-code` tags). Of the 231 modules, **51** are directly about GitHub Copilot / agentic AI / MCP and got full page-level detail (objectives, prerequisites, unit titles) via live fetches of each module page. The remaining **180** modules are generic Azure/C#/DevOps/migration content only tangentially related to the curriculum's focus — these are listed with catalog metadata only (no page fetch) to keep this reference tractable. The 49 learning paths are listed by title/summary only (out of scope for page-level fetching here; none of them are tagged with both github and vs-code).

---

## Directly agent/Copilot/AI-relevant modules (full detail fetched)

*51 modules — GitHub Copilot, agentic AI/DevOps, MCP, Copilot SDK, spec-driven development, GenAIOps, vibe coding, etc.*

## Governance, guardrails, and operations
**URL:** https://learn.microsoft.com/en-us/training/modules/governance-guardrails-operations/
**Level:** Intermediate | **Units:** 9
**Summary:** Agent systems must operate within clear governance frameworks to ensure security, compliance, and accountability. This module covers designing secure and compliant agent governance using GitHub-native controls, human-in-the-loop approvals, and least-privilege access, plus operational safeguards for reliability and accountability.
**Objectives:**
- Define risk-based autonomy and action boundaries for agent systems
- Enforce governance using GitHub-native controls such as rulesets, checks, CODEOWNERS, and environments
- Design human-in-the-loop workflows for high-risk actions
- Control agent capabilities using least-privilege permissions
- Make agent actions observable, traceable, and auditable
- Maintain governance and operational reliability over time
**Prerequisites:** A GitHub account; basic understanding of repositories, branches, and pull requests; familiarity with GitHub Actions; general understanding of agent workflows in GitHub, IDE, or CLI environments
**Unit titles:** 1. Introduction 2. Define risk-based autonomy and action boundaries 3. Enforce governance with GitHub controls 4. Design human-in-the-loop workflows 5. Control agent capabilities using least privilege 6. Make actions observable, traceable, and auditable 7. Maintain governance and operational reliability 8. Knowledge check 9. Summary

---

## Challenge project - Build a minigame with GitHub Copilot and .NET
**URL:** https://learn.microsoft.com/en-us/training/modules/challenge-project-create-mini-game-with-copilot-dotnet/
**Level:** Beginner | **Units:** 6
**Summary:** Demonstrate your ability to analyze, create, and use different methods to develop a console minigame in .NET with GitHub Codespaces and GitHub Copilot.
**Objectives:**
- Experience GitHub Codespaces as a development environment
- Develop input and output routines in a .NET console application
- Use GitHub Copilot as an assistant
**Prerequisites:** A GitHub account and basic knowledge of Git commands to execute the routines (add, commit and push); basics of .NET to work with variables, lists, loops, conditionals and print messages on the console
**Unit titles:** 1. Introduction 2. Prepare for challenge 3. Exercise - Add the GitHub Copilot extension 4. Exercise - Create the game logic 5. Module assessment 6. Summary

---

## Responsible AI with GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/responsible-ai-with-github-copilot/
**Level:** Beginner | **Units:** 5
**Summary:** This module explores the responsible use of AI in the context of GitHub Copilot, a generative AI tool for developers, equipping learners to use Copilot effectively while mitigating ethical and operational risks.
**Objectives:**
- Understand and apply the principles of Responsible AI usage
- Identify limitations and mitigate risks associated with AI
- Learn best practices for ensuring AI-generated code aligns with ethical standards and project-specific requirements
- Recognize the importance of transparency and accountability in AI systems to build trust and maintain user confidence
**Prerequisites:** A basic understanding of generative AI
**Unit titles:** 1. Introduction 2. Mitigate AI risks 3. Microsoft and GitHub's six principles of responsible AI 4. Module assessment 5. Summary

---

## Use GitHub Copilot for cloud operations
**URL:** https://learn.microsoft.com/en-us/training/modules/use-github-copilot-cloud-operations/
**Level:** Intermediate | **Units:** 11
**Summary:** Learn how to use GitHub Copilot to accelerate Infrastructure as Code authoring, apply effective prompt engineering techniques for Bicep templates, and generate and translate Azure CLI and PowerShell scripts for cloud operations tasks.
**Objectives:**
- Explain what Infrastructure as Code is and how GitHub Copilot changes the IaC authoring workflow
- Apply prompt engineering techniques to generate and refine Bicep templates using GitHub Copilot
- Generate, enhance, and translate Azure CLI and Azure PowerShell scripts using GitHub Copilot
- Generate simple and complex Bicep templates using GitHub Copilot, and improve output quality with the Bicep MCP server
- Generate production-grade Dockerfiles and Kubernetes manifests for AKS using GitHub Copilot
- Use GitHub Copilot to generate multi-stage Azure DevOps pipelines and GitHub Actions workflows for IaC deployment
- Generate architecture documentation, parameter reference tables, Mermaid diagrams, and change summaries from Bicep templates
- Use GitHub Copilot to analyze Azure Firewall logs, troubleshoot deployment failures, and generate KQL queries for Azure Monitor
**Prerequisites:** Basic understanding of GitHub and version control; familiarity with Azure cloud services and Azure resource types; access to GitHub Copilot; Visual Studio Code installed with the GitHub Copilot extension
**Unit titles:** 1. Introduction 2. Prompt engineering for Infrastructure as Code 3. Azure CLI and PowerShell assistance with GitHub Copilot 4. Generating Bicep templates with GitHub Copilot 5. Container infrastructure with GitHub Copilot 6. CI/CD pipeline generation with GitHub Copilot 7. Documentation generation from infrastructure code 8. Log and configuration analysis with GitHub Copilot 9. Exercise - Use GitHub Copilot for cloud operations 10. Module assessment 11. Summary

---

## Introduction to agentic DevOps using Microsoft tools on Azure
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-agentic-devops-microsoft-tools-azure/
**Level:** Advanced | **Units:** 7
**Summary:** Describe where agentic approaches improve DevOps outcomes in Azure environments, evaluating role-aligned use cases, autonomy boundaries, and human-in-the-loop patterns across Microsoft DevOps toolchains.
**Objectives:**
- Define agentic DevOps in a Microsoft and Azure context
- Identify high-value DevOps tasks that benefit from agentic support
- Distinguish assistant, semi-autonomous, and autonomous operating modes
- Explain human oversight requirements for production-facing operations
**Prerequisites:** Experience designing and managing CI/CD pipelines in Azure Pipelines or GitHub Actions; familiarity with Infrastructure as Code using Bicep or similar tooling; working knowledge of Azure resource governance, monitoring, and incident response; familiarity with GitHub Copilot in Visual Studio Code
**Unit titles:** 1. Introduction to agentic DevOps for Microsoft environments 2. Define agentic DevOps for Microsoft environments 3. Map day-to-day DevOps work to agentic opportunities 4. Set autonomy boundaries and human control points 5. Exercise: Classify a DevOps backlog by autonomy level 6. Module assessment 7. Summary

---

## Introduction to GitHub Copilot Business
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-to-github-copilot-for-business/
**Level:** Beginner | **Units:** 6
**Summary:** GitHub Copilot Business builds the power of generative AI into an editor extension that suggests code in real-time, and this module covers how it differs from GitHub Copilot Individuals, its use cases and customer stories, and how to enable it.
**Objectives:**
- Understand the difference between GitHub Copilot Business versus GitHub Copilot Individuals
- Learn about specific use cases for GitHub Copilot Business and hear how customers are enhancing their productivity
- Review how to enable GitHub Copilot Business
**Prerequisites:** Basic understanding of GitHub fundamentals; a GitHub Enterprise Cloud account
**Unit titles:** 1. Introduction 2. About GitHub Copilot for Business 3. GitHub Copilot for Business use cases and customer stories 4. How to get started with GitHub Copilot for Business 5. Module assessment 6. Summary

---

## Designing Agent Architecture and SDLC Integration
**URL:** https://learn.microsoft.com/en-us/training/modules/design-agent-architecture-integration/
**Level:** Intermediate | **Units:** 9
**Summary:** Learn how agentic systems use GitHub workflows such as branches, pull requests, checks, and repository rules to safely build and maintain software, including how to structure agent tasks and operate them reliably.
**Objectives:**
- Map agent responsibilities to SDLC stages and define architectural boundaries
- Define structured agent tasks using inputs, outputs, and success criteria
- Separate planning, reasoning, and execution to create inspectable and reliable workflows
- Implement pull request-based governance using templates, checks, CODEOWNERS, rules, and environments
- Design reliable workflows using outputs, contexts, triggers, and cross-job handoffs
- Operate agent systems safely using observability, tool governance, secrets boundaries, hooks, and reliability patterns
**Prerequisites:** A GitHub account and familiarity with repositories, branches, and pull requests; basic experience with GitHub Actions workflows and status checks; a general understanding of the software development lifecycle (SDLC); awareness of repository governance concepts such as required reviews, CODEOWNERS, and branch protection
**Unit titles:** 1. Introduction 2. Map agent responsibilities to the SDLC 3. Define inputs, outputs, and success criteria 4. Separate planning, reasoning, and execution 5. Examples of implementing PR governance with templates, checks, CODEOWNERS, rules, and environment gates 6. Build reliable workflows - outputs, contexts, triggers, and cross-job handoffs 7. Control and operate agents - observability, tools, MCP, secrets, hooks, and reliability 8. Knowledge Check 9. Summary

---

## Foundations of Agentic AI in GitHub
**URL:** https://learn.microsoft.com/en-us/training/modules/foundations-agentic-ai/
**Level:** Intermediate | **Units:** 8
**Summary:** Explore how agentic AI changes the developer role from only writing code to guiding, reviewing, and validating systems that can take action across the SDLC, and understand GitHub's role as the system of record and control plane for safe, traceable agent workflows.
**Objectives:**
- Define agentic AI in the SDLC and distinguish agents from assistants
- Explain and apply the plan → act → evaluate lifecycle in agent workflows
- Describe how GitHub functions as the system of record and control plane for agent activity
- Identify responsibilities, risks, anti-patterns, and traceability requirements in agent systems
- Apply the contributor model to evaluate agent-generated work
**Prerequisites:** A GitHub account and familiarity with repositories, branches, and pull requests; basic experience with GitHub Actions and status checks; a general understanding of the software development lifecycle (SDLC); familiarity with AI-assisted development tools (such as GitHub Copilot); awareness of basic repository governance concepts (for example, reviews, CODEOWNERS, and branch protection)
**Unit titles:** 1. Introduction 2. Define agentic AI in the SDLC 3. Explain the agent lifecycle - plan, act, evaluate 4. Describe GitHub as the system of record and control plane 5. Identify responsibilities, risks, anti-patterns, and traceability needs 6. Apply the contributor model to agent-generated work 7. Knowledge Check 8. Summary

---

## Introduction to Copilot Spaces
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-copilot-spaces/
**Level:** Intermediate | **Units:** 7
**Summary:** Learn how to use GitHub Copilot Spaces to get context-aware, reliable answers, configure custom instructions, and optimize interactions for repositories, issues, and pull requests, guiding developers and PMs to create and use Spaces effectively.
**Objectives:**
- Explain what Spaces are and when to use them versus general Copilot Chat
- Create, configure, and iterate on a Space with targeted context and custom instructions
- Apply best practices for high-quality, grounded answers within model context limits
**Prerequisites:** GitHub account with an active Copilot subscription; access to the Spaces feature in your environment (availability may vary); basic familiarity with repositories, issues, and pull requests
**Unit titles:** 1. Introduction 2. Creating your first space 3. Sharing, Discoverability, and Governance 4. Do's and Don'ts of Working in a Space 5. Exercise - Democratize tribal knowledge using Copilot Spaces 6. Module assessment 7. Summary

---

## Automatic function calling
**URL:** https://learn.microsoft.com/en-us/training/modules/automatic-function-calling/
**Level:** Intermediate | **Units:** 5
**Summary:** This module introduces automatically invoking functions using the Semantic Kernel SDK. It covers how to let Semantic Kernel automatically invoke the right functions to complete a user's request, without manual function-selection logic.
**Objectives:**
- Learn how to use Semantic Kernel SDK to automatically invoke functions.
**Prerequisites:** Experience programming in C#; Visual Studio Code IDE installed; familiarity with Azure and the Azure portal; access to Azure OpenAI services.
**Unit titles:** 1. Introduction 2. Automatically invoke functions 3. Exercise - Automatically invoke functions 4. Exercise - Automatically invoke functions 5. Summary

---

## Get started with GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/get-started-github-copilot/
**Level:** Intermediate | **Units:** 14
**Summary:** This module introduces developers to the GitHub Copilot products, the benefits GitHub Copilot provides, GitHub Copilot and Copilot Chat product features, and the GitHub Copilot extensions for Visual Studio Code.
**Objectives:**
- Explain what GitHub Copilot is and the advantages it provides.
- Install the GitHub Copilot Chat extension for Visual Studio Code.
- Explain the features of the GitHub Copilot Chat extension for Visual Studio Code and how to use them.
- Configure the GitHub Copilot Chat extension for Visual Studio Code.
**Prerequisites:** An active subscription for GitHub Copilot, either a personal GitHub account or one managed by an organization/enterprise; a GitHub Copilot Free plan is sufficient for this training.
**Unit titles:** 1. Introduction 2. Examine AI tools from GitHub, OpenAI, and Microsoft 3. Compare GitHub Copilot plans 4. Review GitHub Copilot features 5. Examine GitHub Copilot's setup process 6. Configure GitHub Copilot settings in Visual Studio Code 7. Manage GitHub Copilot policies, features, and extensions for individuals 8. Examine GitHub Copilot's code completion features 9. Examine GitHub Copilot's AI assistance features 10. Examine GitHub Copilot Chat view features 11. Examine GitHub Copilot inline chat, smart actions, and quick chat 12. Exercise - Examine GitHub Copilot settings and user interface features 13. Module assessment 14. Summary

---

## Resolve GitHub issues using GitHub Copilot Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/resolve-github-issues-github-copilot-agent/
**Level:** Intermediate | **Units:** 9
**Summary:** This module covers how to identify and remediate GitHub issues using GitHub Copilot's Ask and Agent modes, with a focus on security vulnerabilities such as SQL injection, encryption, logging, and path traversal problems.
**Objectives:**
- Describe several common categories of code security vulnerabilities and the associated GitHub issues.
- Describe the lifecycle of a GitHub issue from creation to resolution.
- Use GitHub Copilot's Ask mode to analyze the code vulnerabilities associated with a GitHub issue and suggest potential fixes.
- Use GitHub Copilot's Agent mode to fix code vulnerabilities and resolve GitHub issues.
**Prerequisites:** Experience using Git and GitHub for version control; experience using GitHub Copilot in Visual Studio Code; experience developing C# applications.
**Unit titles:** 1. Introduction 2. Get started with GitHub issues 3. Examine common code security issues 4. Prevent issues using GitHub Copilot 5. Analyze issues using GitHub Copilot's Ask mode 6. Remediate issues using GitHub Copilot's Agent mode 7. Exercise - Resolve GitHub issues using GitHub Copilot 8. Module assessment 9. Summary

---

## Implement CI/CD pipelines for multi-agent systems with GitHub Actions
**URL:** https://learn.microsoft.com/en-us/training/modules/aaai-implement-cicd-multi-agent-systems-github-actions/
**Level:** Advanced | **Units:** 7
**Summary:** Implement enterprise CI/CD pipelines for multi-agent systems using GitHub Actions and Microsoft Foundry, including coordinated deployment pipelines with agent version compatibility validation, canary/blue-green deployment strategies, multi-environment configuration, and automated rollback triggered by quality regression detection.
**Objectives:**
- Design CI/CD pipelines that validate version compatibility across interdependent multi-agent systems
- Implement progressive deployment strategies including canary releases and blue-green deployment for agent updates
- Configure multi-environment deployment strategies for agent ecosystems from development through production
- Automate rollback procedures triggered by quality regression detection
**Prerequisites:** Experience with GitHub Actions for CI/CD workflows in AI projects; familiarity with Microsoft Foundry project deployment; understanding of infrastructure as code with Bicep or Terraform; experience with GenAIOps practices (from the Operationalize generative AI applications learning path or equivalent); proficiency in Python and YAML.
**Unit titles:** 1. Introduction 2. Design multi-agent deployment pipelines 3. Implement progressive deployment strategies 4. Configure multi-environment agent deployment strategies 5. Automate rollback procedures 6. Module assessment 7. Summary

---

## Developer use cases for AI with GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/developer-use-cases-for-ai-with-github-copilot/
**Level:** Intermediate | **Units:** 7
**Summary:** This module explores how GitHub Copilot streamlines developer productivity through AI-powered features, how it enhances the Software Development Life Cycle, aligns with developer preferences, and where its limitations lie, while also covering how to measure productivity gains.
**Objectives:**
- Identify specific ways GitHub Copilot integrates seamlessly into developer workflows, enhancing the overall development experience and supporting individual coding preferences.
- Explore GitHub Copilot's potential impact on different stages of the Software Development Lifecycle.
- Evaluate the limitations of AI-assisted coding and measure its impact on development efficiency.
**Prerequisites:** Basic understanding of software development concepts and practices; familiarity with at least one programming language; a GitHub account and basic knowledge of GitHub functionalities; access to GitHub Copilot (the Free option is sufficient for learning purposes).
**Unit titles:** 1. Introduction 2. Boost developer productivity with AI 3. Align with developer preferences 4. AI in the Software Development Lifecycle (SDLC) 5. Understand limitations and measure impact 6. Module assessment 7. Summary

---

## Building applications with GitHub Copilot agent mode
**URL:** https://learn.microsoft.com/en-us/training/modules/github-copilot-agent-mode/
**Level:** Intermediate | **Units:** 6
**Summary:** GitHub Copilot Agent Mode is an AI-powered coding assistant that works autonomously to analyze your entire project and handle tricky coding tasks. This module covers prompting autonomous development tasks, using documentation for guidance, and how Agent Mode iteratively manages, refactors, and improves a codebase.
**Objectives:**
- Understand how to develop with VS Code IDE in a GitHub Codespace
- Prompt GitHub Copilot agent mode to create an application
- Leverage documentation files to instruct GitHub Copilot agent mode
- Understand how GitHub Copilot agent mode iterates over a code base to: fix errors, refactor code, develop new features
**Prerequisites:** A GitHub account and a fundamental understanding of GitHub Copilot.
**Unit titles:** 1. Introduction 2. What is GitHub Copilot Agent Mode? 3. Explore the power of autonomous development assistance 4. GitHub skills exercise 5. Module assessment 6. Summary

---

## Challenge project - Build a minigame with GitHub Copilot and Python
**URL:** https://learn.microsoft.com/en-us/training/modules/challenge-project-create-mini-game-with-copilot/
**Level:** Beginner | **Units:** 6
**Summary:** Demonstrate your ability to analyze, create, and use different methods to develop a console minigame in Python with GitHub Codespaces and GitHub Copilot.
**Objectives:**
- Experience GitHub Codespaces as a development environment.
- Develop input and output routines in a Python console application.
- Use GitHub Copilot as an assistant.
**Prerequisites:** A GitHub account and basic knowledge of Git commands (add, commit, push); basic Python knowledge to work with variables, lists, loops, conditionals, and print messages to the console.
**Unit titles:** 1. Introduction 2. Prepare for challenge 3. Exercise - Add the GitHub Copilot extension 4. Exercise - Create the game logic 5. Module assessment 6. Summary

---

## Implement code improvements using GitHub Copilot tools
**URL:** https://learn.microsoft.com/en-us/training/modules/implement-code-improvements-using-github-copilot-tools/
**Level:** Intermediate | **Units:** 10
**Summary:** This module explores using GitHub Copilot Chat to develop improvements for an existing codebase, with exercises providing practical experience implementing Copilot suggestions that improve code quality, reliability, performance, and security.
**Objectives:**
- Develop prompts/questions for GitHub Copilot Chat that help you improve the code in your existing code projects.
- Implement code update suggestions from GitHub Copilot Chat that improve existing code in the areas of code quality, reliability, performance, and security.
**Prerequisites:** One or more years of software development experience recommended; experience developing C# applications using Visual Studio Code and the C# Dev Kit extension recommended; an active GitHub Copilot subscription required (Free plan sufficient, or Pro with a one-time 30-day free trial); experience using GitHub Copilot in Visual Studio Code to explain, debug, and generate code.
**Unit titles:** 1. Introduction 2. Review GitHub Copilot's code improvement features 3. Examine GitHub Copilot's quick fix options 4. Review code refactoring scenarios and GitHub Copilot best practices 5. Refactor code using GitHub Copilot Inline Chat 6. Refactor code using GitHub Copilot Chat modes 7. Examine the GitHub Copilot code review features 8. Exercise - Refactor existing code using GitHub Copilot 9. Module assessment 10. Summary

---

## Improve code performance using GitHub Copilot Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/improve-code-performance-github-copilot-agent/
**Level:** Intermediate | **Units:** 9
**Summary:** This module examines how to profile .NET applications effectively, identify performance bottlenecks, and optimize code by using GitHub Copilot in Visual Studio Code.
**Objectives:**
- Describe what code profiling is and how improving code efficiency benefits users and businesses.
- Describe the tools, techniques, and processes used to implement profiling, locate bottlenecks, and improve code performance.
- Use GitHub Copilot's Ask mode to explain a codebase, suggest opportunities to improve code efficiency, and identify the risks associated with suggested performance optimizations.
- Use GitHub Copilot's Agent mode to refactor low performance code without negatively impacting code quality or code security.
**Prerequisites:** Experience using GitHub Copilot in Visual Studio Code; experience developing C# applications.
**Unit titles:** 1. Introduction 2. Examine performance profiling and code efficiency 3. Write efficient code without sacrificing readability 4. Measure code performance and establish baselines 5. Identify performance bottlenecks using GitHub Copilot's Ask mode 6. Refactor low performance code using GitHub Copilot's Agent mode 7. Exercise - Implement performance profiling using GitHub Copilot 8. Module assessment 9. Summary

---

## Manage prompts for agents in Microsoft Foundry with GitHub
**URL:** https://learn.microsoft.com/en-us/training/modules/prompt-versioning-genaiops/
**Level:** Intermediate | **Units:** 8
**Summary:** Learn to manage AI prompts as versioned, code-like assets using GitHub. Apply software engineering best practices to create, test, and promote prompt versions used by Microsoft Foundry agents as part of a GenAIOps workflow.
**Objectives:**
- Apply version control principles to manage prompts as code assets.
- Understand how prompts integrate with Microsoft Foundry agents and versioning strategies.
- Design a GitHub repository structure for prompt versioning and collaboration.
- Develop a workflow for testing and deploying prompts safely.
**Prerequisites:** Familiarity with fundamental generative AI concepts and services in Azure is recommended; consider completing "Fundamentals of Generative AI" first.
**Unit titles:** 1. Introduction 2. Apply version control to prompts 3. Understand Microsoft Foundry agents and prompt versioning 4. Organize prompts in GitHub repositories 5. Develop safe prompt deployment workflows 6. Exercise - Develop prompt and agent versions 7. Knowledge check 8. Summary

---

## GitHub Copilot Across Environments: IDE, Chat, GitHub.com, Command Line Techniques, and the GitHub Copilot App
**URL:** https://learn.microsoft.com/en-us/training/modules/github-copilot-across-environments/
**Level:** Intermediate | **Units:** 8
**Summary:** Explores the versatile integration of GitHub Copilot's AI-assisted coding across your entire development workflow — IDE auto-suggestions, Copilot Chat, GitHub.com, the command line, and the Copilot app — along with prompt optimization and customizing Copilot's behavior.
**Objectives:**
- Understand how to utilize GitHub Copilot's auto-suggestions, multiple suggestions pane, and its ability to adapt to different coding styles.
- Understand how to provide context to GitHub Copilot through inline/block comments and doc strings to enhance code generation accuracy.
- Understand how to interact with GitHub Copilot through natural language conversations to generate code, debug issues, and obtain explanations.
- Understand how to improve relevance of Copilot Chat's suggestions using scope referencing, slash commands, and agents.
- Understand how to use GitHub Copilot on GitHub.com for repo exploration, PR assistance, issue management, and code review.
- Understand how to interact with GitHub Copilot in CLI to get command explanations and automate terminal workflows.
- Understand how to interact with the GitHub Copilot App and its use cases.
**Prerequisites:** Basic coding knowledge; GitHub Copilot access (extension installed in Visual Studio, VS Code, Neovim, or a JetBrains IDE); a GitHub account connected to Copilot from your code editor.
**Unit titles:** 1. Introduction 2. Code completion with GitHub Copilot 3. GitHub Copilot Chat 4. GitHub Copilot on GitHub.com 5. GitHub Copilot for the Command Line 6. The GitHub Copilot app 7. Module assessment 8. Summary

---

## Introduction to MCP Server
**URL:** https://learn.microsoft.com/en-us/training/modules/mcp-server/
**Level:** Intermediate | **Units:** 7
**Summary:** Introduces GitHub MCP Server, a secure and scalable way to integrate GitHub features into AI tools. Covers what MCP is, how to configure GitHub MCP Server in VS Code, use it with Copilot Chat, and troubleshoot common issues.
**Objectives:**
- Understand what MCP and GitHub MCP Server are and why they're useful for developers.
- Set up and configure GitHub MCP Server in Visual Studio Code for your projects.
- Use the GitHub MCP Server with Copilot Chat to automate development tasks.
- Identify and resolve common issues when working with GitHub MCP Server.
**Prerequisites:** A GitHub account; Visual Studio Code or another MCP-compatible editor; the "MCP servers in Copilot" policy enabled if in a Copilot Business/Enterprise organization (optional); a GitHub Personal Access Token for advanced setup (optional); Docker installed if experimenting with a local server setup (optional).
**Unit titles:** 1. Introduction 2. Simplify your AI workflow with GitHub MCP Server 3. Configure, connect, and use GitHub MCP Server in VS Code 4. Using GitHub MCP Server with Copilot Chat 5. Exercise - Integrate MCP with GitHub Copilot 6. Knowledge check 7. Summary

---

## Simplify complex conditionals using GitHub Copilot Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/simplify-complex-conditionals-github-copilot-agent/
**Level:** Intermediate | **Units:** 9
**Summary:** Covers using GitHub Copilot's Agent mode to simplify complex, deeply nested conditional statements in code, with practical examples and exercises to enhance coding efficiency.
**Objectives:**
- Describe how complex conditionals evolve over time and the problems associated with complex and deeply nested conditional code.
- Describe the tools, techniques, and processes used to refactor complex and deeply nested conditional code.
- Use GitHub Copilot's Ask mode to explain a codebase and identify opportunities to simplify complex and deeply nested conditional code.
- Use GitHub Copilot's Agent mode to refactor complex and deeply nested conditional code.
**Prerequisites:** Experience using GitHub Copilot in Visual Studio Code; experience developing C# applications.
**Unit titles:** 1. Introduction 2. Review the impact of complex conditionals 3. Examine the characteristics of complex conditionals 4. Examine the techniques used to simplify complex conditionals 5. Analyze complex logic using GitHub Copilot's Ask mode 6. Refactor complex conditionals using GitHub Copilot's Agent mode 7. Exercise - Simplify complex conditionals using GitHub Copilot 8. Module assessment 9. Summary

---

## Manage Azure Boards by using GitHub Copilot integration
**URL:** https://learn.microsoft.com/en-us/training/modules/manage-azure-boards-using-github-copilot/
**Level:** Intermediate | **Units:** 15
**Summary:** Explains how to connect Azure Boards and GitHub, prepare high-quality work items, and use GitHub Copilot capabilities to accelerate delivery while preserving governance and traceability in Azure DevOps.
**Objectives:**
- Describe the Azure Boards and GitHub Copilot integration model.
- Configure the connection between Azure Boards and GitHub repositories.
- Prepare work items so GitHub Copilot can act on clear requirements.
- Delegate and supervise work through pull requests with human review.
- Apply governance, security, and adoption practices for AI-assisted planning.
**Prerequisites:** Familiarity with Azure Boards basics; familiarity with GitHub repositories and pull requests; access to an Azure DevOps project and a GitHub repository.
**Unit titles:** 1. Introduction 2. Understand the integration between Azure Boards and GitHub Copilot 3. Prepare environments, permissions, and prerequisites 4. Connect Azure Boards to GitHub repositories 5. Analyze backlog items with GitHub Copilot Chat 6. Refine work items for AI-assisted delegation 7. Delegate a single work item with GitHub Copilot 8. Steer and review Copilot-generated pull requests 9. Coordinate multiple work items with AI assistance 10. Maintain end-to-end traceability in Azure Boards 11. Apply governance and security for AI-assisted workflows 12. Drive adoption and continuous improvement 13. Exercise - AI-assisted work item management in Azure Boards 14. Module assessment 15. Summary

---

## Challenge GitHub Copilot with SQL
**URL:** https://learn.microsoft.com/en-us/training/modules/challenge-github-copilot-sql/
**Level:** Intermediate | **Units:** 5
**Summary:** Learn how to apply advanced GitHub Copilot features to interact with an application that uses complex SQL queries, iterating and refining prompts for more accurate suggestions.
**Objectives:**
- Demonstrate an understanding of how to use GitHub Copilot with existing application and SQL code.
- Use advanced GitHub Copilot interaction techniques to deal with complex problems regarding SQL queries.
- Iterate, validate, and refine answers to get better and more accurate suggestions.
- Gain an understanding of GitHub Copilot prompting techniques and how prompts impact the output from GitHub Copilot.
**Prerequisites:** A basic understanding of SQL and relational databases; familiarity with GitHub and GitHub Codespaces.
**Unit titles:** 1. Introduction to GitHub Copilot in GitHub Codespaces 2. Work with SQL using GitHub Copilot 3. Hands-on exercise - Challenging GitHub Copilot with SQL 4. Knowledge check 5. Summary

---

## Management and customization considerations with GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/github-copilot-management-and-customizations/
**Level:** Intermediate | **Units:** 7
**Summary:** Explores management and customization considerations with GitHub Copilot, helping you understand plan differences and features to select the right fit for your organization's needs.
**Objectives:**
- Understand the GitHub Copilot plans and their associated management and customization features.
- Gain insight into the contractual protections in GitHub Copilot and disabling matching public code.
- Know how to manage content exclusions.
- Recognize common problems with GitHub Copilot and their solutions.
**Prerequisites:** Basic understanding of GitHub fundamentals; basic understanding of GitHub Copilot.
**Unit titles:** 1. Introduction 2. Explore GitHub Copilot plans and their associated management and customization features 3. Explore contractual protections in GitHub Copilot and disabling matching public code 4. Manage content exclusions 5. Troubleshoot common problems with GitHub Copilot 6. Module assessment 7. Summary

---

## Refactor large functions using GitHub Copilot Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/refactor-large-functions-github-copilot/
**Level:** Intermediate | **Units:** 9
**Summary:** Covers identifying large, multi-purpose functions and refactoring them into smaller helper classes and static methods using GitHub Copilot in Visual Studio Code.
**Objectives:**
- Describe the problems introduced by large, multi-purpose functions and the benefits provided by small, single-purpose functions.
- Describe the tools, techniques, and processes used to refactor large functions into smaller functions.
- Use GitHub Copilot's Ask mode to explain a codebase and identify opportunities to convert large functions into smaller, single-purpose functions.
- Use GitHub Copilot's Agent mode to refactor large functions into smaller helper functions and static methods.
**Prerequisites:** Experience using GitHub Copilot in Visual Studio Code; experience developing C# applications.
**Unit titles:** 1. Introduction 2. Examine the impact of large multipurpose functions 3. Examine the characteristics of large functions 4. Identify and evaluate large functions using GitHub Copilot's Ask mode 5. Refactor large functions using GitHub Copilot's Agent mode 6. Test refactored code 7. Exercise - Refactor large functions using GitHub Copilot 8. Module assessment 9. Summary

---

## Tooling, MCP, and Agent Execution Environments
**URL:** https://learn.microsoft.com/en-us/training/modules/agent-tooling-mcp-execution-environments/
**Level:** Intermediate | **Units:** 7
**Summary:** Introduces how modern software agents interact with tools, APIs, and execution environments to perform tasks, covering the role of Model Context Protocol (MCP), GitHub Actions, agentic workflows, and how GitHub ensures security and governance through defined execution boundaries and safeguards.
**Objectives:**
- Understand how agents use tools and APIs to perform actions.
- Explain the role of MCP servers in extending agent capabilities.
- Configure execution environments using GitHub Actions and GitHub Agentic workflows.
- Define execution boundaries such as repository, branch, and workflow scope.
- Identify limits and protections that govern agent execution, including branch restrictions, pull request review, and environment safeguards.
**Prerequisites:** A GitHub account; basic understanding of repositories, branches, and pull requests; familiarity with GitHub Actions; general knowledge of CI and CD concepts.
**Unit titles:** 1. Introduction 2. How agents interact with GitHub APIs and workflows 3. Model Context Protocol (MCP) servers, registries, and allow lists 4. Execution context and boundaries 5. Agent execution limits and protections 6. Module assessment 7. Summary

---

## Multi-Agent Systems and Orchestration
**URL:** https://learn.microsoft.com/en-us/training/modules/multi-agent-systems-orchestration/
**Level:** Intermediate | **Units:** 9
**Summary:** Learn how to design reliable multi-agent systems in GitHub using observable workflows, coordinated artifacts, and safe recovery mechanisms — coordinating through GitHub-native artifacts, remaining observable through logs and workflow outputs, and recovering safely through retry, rollback, and human escalation.
**Objectives:**
- Define agent responsibilities and scope boundaries within the SDLC
- Coordinate multi-agent workflows using GitHub Actions events and orchestration patterns
- Isolate agent execution using branches, workflows, permissions, and concurrency controls
- Detect and resolve conflicts using GitHub-native validation and review mechanisms
- Ensure observability, attribution, and traceability of agent actions
- Diagnose failures and implement recovery strategies for reliable multi-agent systems
**Prerequisites:** A GitHub account; basic understanding of repositories, branches, and pull requests; familiarity with GitHub Actions; general understanding of agent workflows in GitHub, IDE, or CLI environments
**Unit titles:** 1. Introduction 2. Define multi-agent responsibilities in the SDLC 3. Orchestrate agents using GitHub workflows 4. Isolate execution - branches, workflows, permissions, and concurrency 5. Detect and resolve conflicts using GitHub-native arbitration 6. Make the system observable - attribution, evidence, and handoffs 7. Operate reliably at scale - diagnose failures and recover safely 8. Knowledge Check 9. Summary

---

## Implement spec-driven development using the GitHub Spec Kit
**URL:** https://learn.microsoft.com/en-us/training/modules/spec-driven-development-github-spec-kit-enterprise-developers/
**Level:** Intermediate | **Units:** 13
**Summary:** Implement the spec-driven development methodology using GitHub Spec Kit and GitHub Copilot in Visual Studio Code. Covers a brownfield scenario for enterprise developers, emphasizing an intent-first philosophy with living specifications.
**Objectives:**
- Explain spec-driven development methodology and why it benefits large-scale enterprise projects (upfront clarity, fewer regressions, easier maintenance)
- Implement the GitHub Spec Kit and GitHub Copilot in Visual Studio Code to generate project artifacts (specifications, plans, tasks) aligned with enterprise standards
- Apply the GitHub Spec Kit in an Azure-integrated scenario, encoding internal engineering guidelines (security, performance, compliance) in a project "Constitution"
- Execute a spec-driven workflow to build a new feature, from spec creation through automated code generation and iteration
- Describe how to integrate GitHub Spec Kit into team workflows and extend it for advanced scenarios (multi-agent collaboration, CI/CD integration)
**Prerequisites:** Experience using GitHub Copilot in Visual Studio Code; experience developing applications; general understanding of spec-driven development recommended; familiarity with GitHub Spec Kit recommended
**Unit titles:** 1. Introduction 2. Review the spec-driven development methodology 3. Examine GitHub Spec Kit workflows and optional commands 4. Create a constitution with principles, constraints, and standards 5. Generate a clear, precise, and effective spec 6. Create a detailed technical plan 7. Generate tasks and implement code 8. Examine the GitHub Spec Kit development environment 9. Exercise - Implement a product feature using GitHub Spec Kit 10. Scale spec-driven development for team collaboration 11. Integrate GitHub Spec Kit into CI/CD and DevOps practices 12. Module assessment 13. Summary

---

## Configure GitHub Copilot instructions and create custom agents
**URL:** https://learn.microsoft.com/en-us/training/modules/configure-customize-github-copilot-visual-studio-code/
**Level:** Intermediate | **Units:** 8
**Summary:** Covers how to configure and customize GitHub Copilot in Visual Studio Code using instruction files, prompt files, custom agents, and agent handoffs to create tailored AI-assisted development workflows.
**Objectives:**
- Customize GitHub Copilot's responses using instruction files and prompt files to enforce project-specific coding styles, best practices, and guidelines
- Create custom GitHub Copilot agents in Visual Studio Code with tailored instructions, tool permissions, and subagent configurations
- Configure and use agent handoffs to orchestrate multi-step development workflows
- Implement a real-world scenario by defining custom instructions and chaining multiple custom agents to collaboratively complete a coding task
**Prerequisites:** Experience using Git and GitHub for version control; experience using GitHub Copilot Chat in Visual Studio Code; experience developing C# applications
**Unit titles:** 1. Introduction 2. Examine the benefits of customizing GitHub Copilot 3. Customize GitHub Copilot responses using instruction files 4. Create custom GitHub Copilot agents in Visual Studio Code 5. Chain agents with handoffs for multi-step tasks 6. Exercise - Create and chain custom GitHub Copilot agents for a C# project 7. Module assessment 8. Summary

---

## Using GitHub Copilot with JavaScript
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-copilot-javascript/
**Level:** Beginner | **Units:** 7
**Summary:** Develop updates in a JavaScript application using GitHub Copilot with Visual Studio Code, an AI pair programmer that boosts productivity with autocomplete-style suggestions.
**Objectives:**
- Enable the GitHub Copilot extension in Visual Studio Code
- Craft prompts that can generate useful suggestions from GitHub Copilot
- Use GitHub Copilot to improve a JavaScript project
**Prerequisites:** Basic understanding of JavaScript, like variables and conditionals; ability to use Git and GitHub for version control; a GitHub account with an active subscription for GitHub Copilot (Copilot Free is sufficient).
**Unit titles:** 1. Introduction 2. What is GitHub Copilot 3. Exercise - Set up GitHub Copilot to work with Visual Studio Code 4. Use GitHub Copilot with JavaScript 5. Exercise - Update a JavaScript portfolio with GitHub Copilot 6. Module assessment 7. Summary

---

## Automate AI evaluations with Microsoft Foundry and GitHub Actions
**URL:** https://learn.microsoft.com/en-us/training/modules/automated-evaluation-genaiops/
**Level:** Intermediate | **Units:** 9
**Summary:** Learn how to implement automated evaluations for AI agent responses using Microsoft Foundry evaluators, create evaluation datasets from production data and synthetic generation, run batch evaluations with Python scripts, and integrate evaluation workflows into GitHub Actions for continuous quality assurance.
**Objectives:**
- Explain why automated evaluations complement human evaluations in AI quality assurance
- Select evaluators that align with human evaluation criteria for validation
- Create evaluation datasets with appropriate composition for comprehensive testing
- Implement batch evaluations using Python scripts with Microsoft Foundry
- Integrate automated evaluation workflows into GitHub Actions for continuous testing
**Prerequisites:** Familiarity with fundamental generative AI concepts and services in Azure (completing "Fundamentals of Generative AI" first is suggested); basic familiarity with Python and GitHub workflows recommended
**Unit titles:** 1. Introduction 2. Understand why automated evaluations matter 3. Align evaluators with human criteria 4. Create evaluation datasets 5. Implement batch evaluations with Python 6. Integrate evaluations into GitHub Actions 7. Exercise - Set up automated evaluations 8. Knowledge check 9. Summary

---

## Using GitHub Copilot with Python
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-copilot-python/
**Level:** Beginner | **Units:** 7
**Summary:** Make changes and updates to a Python application by using GitHub Copilot with Visual Studio Code — an AI pair programmer that offers autocomplete-style suggestions as you code.
**Objectives:**
- Enable the GitHub Copilot extension in Visual Studio Code
- Craft prompts that can generate useful suggestions from GitHub Copilot
- Use GitHub Copilot to improve a Python project
**Prerequisites:** Basic understanding of Python and text editors; basic comprehension of Git and GitHub fundamentals; a GitHub account with an active subscription for GitHub Copilot (Copilot Free is sufficient).
**Unit titles:** 1. Introduction 2. What is GitHub Copilot? 3. Exercise - Set up GitHub Copilot to work with Visual Studio Code 4. Use GitHub Copilot with Python 5. Exercise - Update a Python web API with GitHub Copilot 6. Module assessment 7. Summary

---

## Generate documentation using GitHub Copilot tools
**URL:** https://learn.microsoft.com/en-us/training/modules/generate-documentation-using-github-copilot-tools/
**Level:** Intermediate | **Units:** 9
**Summary:** Explores generation of code explanations, project documentation, and inline code comments using the GitHub Copilot Chat extension for Visual Studio Code.
**Objectives:**
- Generate explanations of code blocks, code files, and entire code workspaces using GitHub Copilot Chat
- Generate code project documentation using GitHub Copilot Chat
- Generate inline code documentation using GitHub Copilot Chat
**Prerequisites:** One or more years of software development experience recommended; experience developing C# applications using Visual Studio Code and the C# Dev Kit extension recommended; an active GitHub Copilot subscription (Free plan sufficient); basic understanding of using GitHub Copilot in Visual Studio Code.
**Unit titles:** 1. Introduction 2. Review GitHub Copilot's "explain" and "document" features 3. Examine GitHub Copilot prompts and keywords 4. Analyze and explain code using GitHub Copilot 5. Generate project documentation using GitHub Copilot 6. Generate inline code documentation using GitHub Copilot 7. Exercise - Analyze and document code using GitHub Copilot 8. Module assessment 9. Summary

---

## Use GitHub Copilot plan mode for cloud operations tasks
**URL:** https://learn.microsoft.com/en-us/training/modules/use-plan-mode-cloud-ops/
**Level:** Intermediate | **Units:** 8
**Summary:** Learn how to use GitHub Copilot plan mode to plan, organize, and implement cloud operations tasks such as infrastructure configuration, system administration, and operational automation.
**Objectives:**
- Describe what GitHub Copilot plan mode is and how it fits into an agentic DevOps workflow
- Create structured implementation plans for cloud infrastructure changes
- Use plan mode to break down complex system administration tasks into actionable steps
- Apply best practices for iterating on and refining Copilot-generated plans
**Prerequisites:** Basic understanding of GitHub and version control; familiarity with Azure cloud services or Windows Server administration; access to GitHub Copilot
**Unit titles:** 1. Introduction 2. What is GitHub Copilot plan mode 3. Plan cloud infrastructure changes with Copilot 4. Plan system administration tasks with Copilot 5. Best practices for effective plans 6. Exercise - Use GitHub Copilot plan mode for cloud operations 7. Module assessment 8. Summary

---

## Resolve GitHub Secret Scanning alerts using GitHub Copilot Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/resolve-github-secret-scanning-alerts-github-copilot-agent/
**Level:** Intermediate | **Units:** 11
**Summary:** Covers how to identify and remediate GitHub Secret Scanning alerts using GitHub Copilot's Ask and Agent modes, focusing on detecting hard-coded secrets in source code and implementing secure configuration patterns to replace them.
**Objectives:**
- Identify the tools that GitHub provides for security and code quality
- Explain the security risks of hard-coded secrets in source code
- Configure and use GitHub Secret Scanning and push protection
- Navigate and manage secret scanning alerts in GitHub repositories
- Analyze security alerts using GitHub Copilot's Ask mode
- Remediate hard-coded secrets using GitHub Copilot's Agent mode
**Prerequisites:** Experience using Git and GitHub for version control; experience using GitHub Copilot in Visual Studio Code; experience developing C# applications
**Unit titles:** 1. Introduction 2. Examine GitHub's security and code quality tools 3. Examine code secrets 4. Examine GitHub Secret Scanning 5. Examine GitHub Push Protection 6. Manage GitHub Security Alerts 7. Analyze GitHub Security Alerts using GitHub Copilot's Ask mode 8. Resolve GitHub Security Alerts using GitHub Copilot's Agent mode 9. Exercise - Resolve GitHub Security Alerts 10. Module assessment 11. Summary

---

## Using advanced GitHub Copilot features
**URL:** https://learn.microsoft.com/en-us/training/modules/advanced-github-copilot/
**Level:** Beginner | **Units:** 7
**Summary:** Use advanced GitHub Copilot features with Visual Studio Code to make changes and updates to a Python application, including slash commands, Copilot Chat, and agent-based queries.
**Objectives:**
- Apply slash commands to make code changes
- Interact with GitHub Copilot using the Chat feature
- Ask questions about your project using an agent
**Prerequisites:** Basic understanding of Python, like variables and conditionals; ability to use Git and GitHub for version control; access to the GitHub Copilot service
**Unit titles:** 1. Introduction 2. Advanced GitHub Copilot features 3. Exercise - Set up GitHub Copilot to work with Visual Studio Code 4. Applied GitHub Copilot techniques 5. Exercise - Update a web API with GitHub Copilot 6. Module assessment 7. Summary

---

## Develop unit tests using GitHub Copilot tools
**URL:** https://learn.microsoft.com/en-us/training/modules/develop-unit-tests-using-github-copilot-tools/
**Level:** Intermediate | **Units:** 8
**Summary:** Explores using GitHub Copilot and GitHub Copilot Chat to create unit tests, with exercises providing practical experience creating unit test projects and running unit tests in Visual Studio Code.
**Objectives:**
- Create unit tests using GitHub Copilot in Visual Studio Code
- Create unit tests that target edge cases and specific conditions using GitHub Copilot in Visual Studio Code
- Use Visual Studio Code, the .NET SDK, and the C# Dev Kit extension to create a test project and verify that your unit tests build and run successfully
**Prerequisites:** One or more years of software development experience recommended; experience developing C# applications using Visual Studio Code and the C# Dev Kit extension recommended; an active GitHub Copilot subscription required (Free plan sufficient); experience using GitHub Copilot in Visual Studio Code to explain, debug, and generate code
**Unit titles:** 1. Introduction 2. Examine Visual Studio Code support for unit testing 3. Generate unit tests with the GitHub Copilot Chat view 4. Plan and automate test workflows using the Plan and Agent modes 5. Extend tests with ghost text and fix failing tests 6. Exercise - Develop unit tests using GitHub Copilot 7. Module assessment 8. Summary

---

## Consolidate duplicate logic using GitHub Copilot Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/consolidate-duplicate-logic-github-copilot-agent/
**Level:** Intermediate | **Units:** 8
**Summary:** Covers identifying and consolidating duplicate logic in a codebase using GitHub Copilot Agent, focusing on best practices for refactoring and code quality improvement.
**Objectives:**
- Explain the negative effects of redundant/duplicate code and the benefits of consolidation
- Describe common refactoring patterns used to consolidate redundant/duplicate code
- Use GitHub Copilot's Ask mode to explain a codebase and identify redundant/duplicate code
- Use GitHub Copilot's Agent mode to consolidate redundant/duplicate code
**Prerequisites:** Experience using GitHub Copilot in Visual Studio Code; experience developing C# applications
**Unit titles:** 1. Introduction 2. Examine the negative effects of code duplication 3. Examine code extraction and refactoring techniques 4. Identify duplicate code using GitHub Copilot 5. Refactor duplicate code using GitHub Copilot Agent 6. Exercise - Consolidate duplicate code using GitHub Copilot 7. Module assessment 8. Summary

---

## Manage Azure DevOps by using MCP Server
**URL:** https://learn.microsoft.com/en-us/training/modules/manage-ado-mcp-server/
**Level:** Intermediate | **Units:** 14
**Summary:** Explains how to set up Azure DevOps MCP Server in Visual Studio Code, authenticate and authorize tool access, and perform common Azure DevOps operations with natural language prompts while preserving governance and quality.
**Objectives:**
- Explain the Azure DevOps MCP Server interaction model
- Configure Azure DevOps MCP Server in Visual Studio Code
- Use MCP tools to query and update work items
- Perform pull request and pipeline operations through GitHub Copilot
- Apply governance and safety controls for AI-assisted DevOps workflows
**Prerequisites:** Familiarity with Azure DevOps organizations, projects, and repositories; familiarity with GitHub Copilot Chat in Visual Studio Code; access to an Azure DevOps project with Contributor permissions; Node.js 18 or later and Visual Studio Code installed
**Unit titles:** 1. Introduction 2. Understand Azure DevOps MCP Server 3. Install and configure Azure DevOps MCP Server in Visual Studio Code 4. Authenticate and validate tools 5. Explore project and sprint context 6. Create and link work items 7. Update work items with batch operations 8. Manage pull requests 9. Run and monitor pipelines 10. Inspect build logs 11. Apply governance and security practices 12. Guided exercise - manage Azure DevOps by using MCP Server 13. Module assessment 14. Summary

---

## Get started with spec-driven development and GitHub Spec Kit
**URL:** https://learn.microsoft.com/en-us/training/modules/spec-driven-development-github-spec-kit-greenfield-intro/
**Level:** Beginner | **Units:** 11
**Summary:** Teaches the spec-driven development (SDD) methodology and GitHub Spec Kit, guiding learners through building a greenfield application using AI-assisted, spec-first workflows.
**Objectives:**
- Describe the principles and phases of the spec-driven development (SDD) methodology
- Use GitHub Spec Kit commands to create the constitution.md, spec.md, plan.md, and tasks.md files
- Implement a greenfield application from start to finish using GitHub Spec Kit's AI-assisted workflows
**Prerequisites:** Familiarity with GitHub and GitHub Copilot; basic understanding of software development workflows
**Unit titles:** 1. Introduction 2. What is spec-driven development? 3. Examine spec-driven development principles and processes 4. Compare spec-driven development to other methodologies 5. Examine spec-driven development workflow phases 6. What is GitHub Spec Kit? 7. Set up GitHub Spec Kit in your environment 8. Examine GitHub Spec Kit commands and results 9. Develop a greenfield application using GitHub Spec Kit 10. Module assessment 11. Summary

---

## Introduction to vibe coding
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-vibe-coding/
**Level:** Beginner | **Units:** 9
**Summary:** Examines the vibe coding approach to app development and how to implement a vibe coding process to create and refine an app using GitHub Copilot Agent.
**Objectives:**
- Explain vibe coding and the vibe coding approach to software development
- Create effective prompts for GitHub Copilot in a vibe coding process
- Generate product requirements and wireframe diagrams using GitHub Copilot
- Configure the GitHub Copilot environment for customized responses
- Create a prototype app using vibe coding and GitHub Copilot Agent
**Prerequisites:** Basic understanding of the software development process recommended; some experience developing prompts for large language models recommended
**Unit titles:** 1. Introduction 2. What is vibe coding? 3. Examine the vibe coding process 4. Create effective prompts for GitHub Copilot 5. Identify product requirements and coding guidelines 6. Customize GitHub Copilot Chat responses 7. Exercise - Get started with vibe coding using GitHub Copilot Agent 8. Module assessment 9. Summary

---

## Develop AI-enabled apps using the GitHub Copilot SDK
**URL:** https://learn.microsoft.com/en-us/training/modules/develop-ai-enabled-apps-using-github-copilot-sdk/
**Level:** Intermediate | **Units:** 10
**Summary:** Covers developing AI-enabled applications using the GitHub Copilot SDK — installing the SDK, exploring its features, and building AI agents with tools, memory, and guardrails that integrate into applications.
**Objectives:**
- Explain what AI agents are and how they differ from chatbots and automation scripts
- Describe the architecture and key features of the GitHub Copilot SDK
- Design an AI agent system with tools, memory, and guardrails
- Implement an AI agent using the GitHub Copilot SDK with custom tool definitions
**Prerequisites:** Experience using GitHub Copilot in Visual Studio Code; experience developing C# applications
**Unit titles:** 1. Introduction 2. What is an AI agent? 3. What is the GitHub Copilot SDK? 4. Examine AI agent use cases in business 5. Design AI agents using GitHub Copilot SDK 6. Implement AI agents using GitHub Copilot SDK 7. Adapt and extend AI agents for deployment 8. Exercise - Integrate AI agents into apps using GitHub Copilot SDK 9. Module assessment 10. Summary

---

## Introduction to GitHub Copilot Enterprise
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-to-github-copilot-enterprise/
**Level:** Beginner | **Units:** 5
**Summary:** Explains how GitHub Copilot Enterprise makes organizational institutional knowledge accessible, covering differences between Copilot Enterprise, Business, and Individual plans, key use cases, and how to enable it.
**Objectives:**
- Understand what the GitHub Copilot Enterprise plan is
- Understand the differences between GitHub Copilot Enterprise versus Business versus Individual
- Learn about specific use cases for GitHub Copilot Enterprise and hear how customers are enhancing their productivity
- Review how to enable GitHub Copilot Enterprise
**Prerequisites:** Basic understanding of GitHub fundamentals; a GitHub Enterprise Cloud administrator account; an existing Copilot for Business plan
**Unit titles:** 1. Introduction 2. About GitHub Copilot Enterprise 3. How to get started 4. Module assessment 5. Summary

---

## Memory, State, and Evaluation
**URL:** https://learn.microsoft.com/en-us/training/modules/memory-state-evaluation/
**Level:** Intermediate | **Units:** 8
**Summary:** Introduces the foundations of agent memory, state management, and evaluation — structuring memory, persisting progress through GitHub artifacts, maintaining consistency across environments, and defining clear success signals.
**Objectives:**
- Learn agent memory strategies using short-term, long-term, and external memory
- Learn how to maintain and persist agent state and manage context drift
- Learn how to manage agent state across tools and environments
- Understand agent evaluation signals and success criteria
**Prerequisites:** A GitHub account; basic understanding of repositories, branches, and pull requests; familiarity with GitHub Actions; general understanding of agent workflows in GitHub, IDE, or CLI environments
**Unit titles:** 1. Introduction 2. Implement agent memory strategies 3. Persist agent state and manage context drift 4. Ensure continuity of agent memory and state across tools and environments 5. Define evaluation signals and enforce quality gates 6. Analyze agent failures and improve behavior 7. Knowledge Check 8. Summary

---

## Leveling up code reviews and pull requests with GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/code-reviews-pull-requests-github-copilot/
**Level:** Intermediate | **Units:** 7
**Summary:** This module shows how GitHub Copilot accelerates code review cycles, catches issues, and enforces best practices, covering both GitHub.com and IDE-based reviews, custom instructions, and Premium Request Units (PRUs) for deeper analysis.
**Objectives:**
- Explain how GitHub Copilot streamlines code reviews and pull requests.
- Identify the key features Copilot adds to the review process.
- Request and interpret Copilot reviews on GitHub.com and understand their limits.
- Run Copilot reviews locally in your IDE and apply custom instructions.
- Leverage Premium Request Units (PRUs) for deeper, context-rich analysis.
- Automate Copilot reviews across repositories with rulesets and status checks.
- Apply Copilot's suggestions responsibly, combining them with human judgment and testing.
**Prerequisites:** A GitHub account; GitHub Copilot enabled on your account (Copilot Pro, Copilot Pro+, Business, or Enterprise plan recommended for full code review features); basic familiarity with pull requests and code reviews.
**Unit titles:** 1. Introduction 2. What GitHub Copilot adds to the review process 3. Using Copilot as a reviewer in GitHub.com 4. Catching issues early and automating reviews with Copilot 5. Measuring impact and optimizing premium request units (PRUs) 6. Exercise - GitHub Copilot code review 7. Summary

---

## Accelerate development with GitHub Copilot Cloud Agent
**URL:** https://learn.microsoft.com/en-us/training/modules/github-copilot-code-agent/
**Level:** Intermediate | **Units:** 7
**Summary:** This module explains how to use GitHub Copilot Cloud Agent to assign tasks, streamline development, and combine automation with your team's expertise, covering enabling the agent, its protections and limits, task assignment/tracking, customization via MCP, and responsible use.
**Objectives:**
- Explain what the Copilot Cloud Agent is, how it differs from IDE assistants, and how to enable and budget for it.
- Describe the agent's built-in protections, main risks, mitigations, and its workflow and compatibility limits.
- Assign issues to Copilot, track its pull-request sessions, iterate with @copilot comments, and troubleshoot problems.
- Preconfigure the agent's environment, extend its capabilities with MCP, and test and validate its output before merging.
- Apply responsible-use practices, scope tasks effectively, secure environments, and improve performance.
**Prerequisites:** GitHub account with Copilot Pro, Copilot Pro+, Copilot Business, or Copilot Enterprise; repositories hosted on GitHub (agent does not work on non-GitHub hosts); basic familiarity with issues, pull requests, Actions, and repository rulesets.
**Unit titles:** 1. Understanding and enabling the GitHub Copilot Cloud Agent 2. Security, risks, and limitations of the Copilot Cloud Agent 3. Assigning, tracking, and troubleshooting Copilot Cloud Agent tasks 4. Customizing, extending, and validating the Copilot Cloud Agent 5. Responsible use of GitHub Copilot Cloud Agent on GitHub.com 6. Exercise - Expand your team with Copilot Cloud Agent 7. Summary

---

## Introduction to prompt engineering with GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-prompt-engineering-with-github-copilot/
**Level:** Beginner | **Units:** 7
**Summary:** Discover the core principles of prompt engineering with GitHub Copilot, including how to transform coding comments into precise, actionable code, and advanced techniques like role prompting and chat history management to accelerate development workflows.
**Objectives:**
- Craft effective prompts that optimize GitHub Copilot's performance, ensuring precision and relevance in every code suggestion.
- Understand the relationship between prompts and Copilot's responses, using best practices like role prompting and chat history management.
- Gain insights into how GitHub Copilot handles user prompts, from secure transmission to content filtering and context analysis.
**Prerequisites:** Basic coding knowledge; GitHub Copilot access (extension installed in Visual Studio, Visual Studio Code, Neovim, or JetBrains IDEs); a GitHub account to connect your code editor to Copilot.
**Unit titles:** 1. Introduction 2. Prompt engineering foundations and best practices 3. GitHub Copilot user prompt process flow 4. GitHub Copilot data 5. GitHub Copilot Large Language Models (LLMs) 6. Module assessment 7. Summary

---

## Transition from traditional ops to agentic DevOps workflows
**URL:** https://learn.microsoft.com/en-us/training/modules/transition-traditional-ops-agent-automation/
**Level:** Intermediate | **Units:** 8
**Summary:** Learn how to evolve traditional cloud administration and DevOps tasks into agentic AI workflows, covering the shift from manual/scripted ops to AI-assisted and agentic approaches, the four building blocks of agentic workflows (agents, skills, instructions, prompts), and multi-agent orchestration via the conductor pattern.
**Objectives:**
- Describe the evolution from manual operations through scripted automation and AI-assisted prompts to agentic workflows.
- Explain how multi-agent orchestration and the conductor pattern automate infrastructure operations.
- Identify the four building blocks of agentic workflows — agents, skills, instructions, and prompts.
- Design multi-agent pipelines for common ops tasks using artifact-based communication.
**Prerequisites:** Basic understanding of cloud administration concepts; familiarity with Azure CLI or infrastructure-as-code tools like Bicep or Terraform; experience using AI assistants such as GitHub Copilot.
**Unit titles:** 1. Introduction 2. Understand the shift from manual ops to AI-assisted workflows 3. Explore the agentic DevOps concept 4. Define agents with instructions, skills, and prompts 5. Design multi-agent workflows for infrastructure tasks 6. Exercise - Transition to agentic DevOps workflows 7. Module assessment 8. Summary

---

## Develop code features using GitHub Copilot tools
**URL:** https://learn.microsoft.com/en-us/training/modules/develop-code-features-using-github-copilot-tools/
**Level:** Intermediate | **Units:** 8
**Summary:** This module explores using GitHub Copilot and GitHub Copilot Chat to create new code in Visual Studio Code, covering autocompletion suggestions, chat-based code generation (Chat View, Inline Chat, Quick Chat, Smart Actions), and managing/accepting suggestions.
**Objectives:**
- Generate autocompletion suggestions based on code and code comments using the GitHub Copilot extension for Visual Studio Code.
- Manage autocompletion suggestions by accepting, partially accepting, and dismissing suggestions.
- Create chat prompts/questions using chat participants, slash commands, chat variables, and natural language text.
- Create new code using the Chat View, Inline Chat, Quick Chat, and Smart Actions features of GitHub Copilot Chat.
- Manage code update suggestions by accepting, partially accepting, editing, and discarding suggestions.
**Prerequisites:** One or more years of software development experience recommended; experience developing C# applications using Visual Studio Code and the C# Dev Kit extension recommended; an active GitHub Copilot subscription (Free plan sufficient); experience using GitHub Copilot in Visual Studio Code to explain and document code.
**Unit titles:** 1. Introduction 2. Examine the code development features of GitHub Copilot 3. Examine GitHub Copilot best practices 4. Generate code using GitHub Copilot code completion suggestions 5. Generate code using GitHub Copilot Chat 6. Exercise - Develop new code features using GitHub Copilot 7. Module assessment 8. Summary

---

## Introduction to GitHub Copilot
**URL:** https://learn.microsoft.com/en-us/training/modules/introduction-to-github-copilot/
**Level:** Beginner | **Units:** 7
**Summary:** GitHub Copilot is an AI-powered coding assistant that helps you generate, understand, refactor, and debug code in real time using both inline suggestions and a conversational chat experience, directly from your development environment.
**Objectives:**
- Learn how GitHub Copilot can help you code by offering code suggestions.
- Learn about the various ways to trigger GitHub Copilot.
- Learn about the differences among GitHub Copilot Individual, Business, and Enterprise.
- Learn how to configure GitHub Copilot.
- Troubleshoot GitHub Copilot.
**Prerequisites:** GitHub account; basic understanding of GitHub fundamentals.
**Unit titles:** 1. Introduction 2. GitHub Copilot, your AI pair programmer 3. Interact with Copilot 4. Set up, configure, and troubleshoot GitHub Copilot 5. Exercise - Develop with AI-powered code suggestions by using GitHub Copilot and VS Code 6. Module assessment 7. Summary

---

## Other GitHub/VS Code/DevOps modules (catalog data only)

*180 modules — generic Azure, C#/.NET/Python language fundamentals, Azure DevOps/Pipelines, migration, security, and MLOps content tagged github or vs-code but not specifically about Copilot/agentic AI. Catalog metadata only; page-level detail was not fetched for these to keep scope tractable.*

- **[Add decision logic to your code using `if`, `else`, and `else if` statements in C#](https://learn.microsoft.com/en-us/training/modules/csharp-if-elseif-else/)** — Beginner, 56 min, 7 units. uid: `learn.languages.csharp-if-elseif-else`. Learn to branch your code's execution path by evaluating Boolean expressions.
- **[Add looping logic to your code using the do-while and while statements in C#](https://learn.microsoft.com/en-us/training/modules/csharp-do-while/)** — Beginner, 55 min, 8 units. uid: `learn.languages.csharp-do-while`. Use the do-while and while statements to iterate as long as a Boolean expression evaluates to true.
- **[Advanced testing with pytest](https://learn.microsoft.com/en-us/training/modules/python-advanced-pytest/)** — Intermediate, 26 min, 6 units. uid: `learn.python-advanced-pytest`. Take advantage of the advanced features of pytest, a popular test framework used to write and run tests in Python.
- **[Apply interfaces in code](https://learn.microsoft.com/en-us/training/modules/apply-interfaces-code/)** — Beginner, 40 min, 7 units. uid: `learn.wwl.apply-interfaces-code`. Discover how default implementations in interfaces enable you to add new methods directly into an interface and provide a default implementation.
- **[Authenticate and authorize user identities on GitHub](https://learn.microsoft.com/en-us/training/modules/authenticate-authorize-user-identities-github/)** — Intermediate, 33 min, 7 units. uid: `learn.github.authenticate-authorize-user-identities-github`. Learn how to manage the authentication and authorization of user identities on GitHub.
- **[Automate development tasks by using GitHub Actions](https://learn.microsoft.com/en-us/training/modules/github-actions-automate-tasks/)** — Beginner, 56 min, 7 units. uid: `learn.github.github-actions-automate-tasks`. Create a basic GitHub Action and use that action in a workflow.
- **[Automate DevOps processes by using GitHub Apps](https://learn.microsoft.com/en-us/training/modules/automate-devops-github-apps/)** — Beginner, 43 min, 6 units. uid: `learn.github.automate-devops-github-apps`. Learn to automate DevOps processes by using GitHub Apps that handle repetitive tasks, enforce team policies, and maintain a tidy repository.
- **[Automate GitHub by using GitHub Script](https://learn.microsoft.com/en-us/training/modules/automate-github-using-github-script/)** — Beginner, 25 min, 5 units. uid: `learn.github.automate-github-using-github-script`. Learn to interact with the GitHub API from GitHub Actions by using GitHub Script.
- **[Automate inspection of health](https://learn.microsoft.com/en-us/training/modules/automate-inspection-health/)** — Advanced, 29 min, 12 units. uid: `learn.wwl.automate-inspection-of-health`. Learn to implement automated health monitoring, configure event notifications, set up service hooks for pipeline monitoring, and establish quality gates for comprehensive release management
- **[Automate machine learning workflows](https://learn.microsoft.com/en-us/training/modules/automate-machine-learning-workflows/)** — Beginner, 29 min, 6 units. uid: `learn.wwl.automate-machine-learning-workflows`. Learn about automation for machine learning, machine learning operations, and MLOps.
- **[Azure Devops to GitHub Enterprise Migrations Part II - Source Environment Assessment and Target Environment Setup](https://learn.microsoft.com/en-us/training/modules/ado-github-migrations-2/)** — Intermediate, 26 min, 6 units. uid: `learn.github.azure-devops-to-github-enterprise-migrations-part-ii-assessment-setup`. This module guides you through the critical preparation steps for migrating from Azure DevOps (ADO) to GitHub Enterprise Cloud (GHEC). You'll learn how to analyze the structure and dependencies of your ADO environment and translate that understanding into a secure, organized, and migration-ready GHEC setup.
- **[Azure Devops to GitHub Enterprise Migrations Part III - Migration Testing and Production Migration](https://learn.microsoft.com/en-us/training/modules/ado-github-migrations-3/)** — Intermediate, 19 min, 5 units. uid: `learn.github.azure-devops-to-github-enterprise-migrations-part-migration-testing-and-production-migration`. Learn how to complete the final stages of your Azure DevOps to GitHub Enterprise migration. This module helps you test your migration plan with real repositories and carry out a smooth production migration while keeping your data, communication, and business running safely.
- **[Azure DevOps to GitHub Enterprise Migrations Part IV - Post-Migration Stabilization, Enablement, and Operations](https://learn.microsoft.com/en-us/training/modules/ado-github-migrations-four/)** — Intermediate, 35 min, 7 units. uid: `learn.github.ado-github-migrations-four`. Transition from a completed migration to a sustainable developer platform by resolving identity mismatches, enforcing governance, validating integrations, enabling adoption, and retiring Azure DevOps.
- **[Become a Microsoft Learn contributor](https://learn.microsoft.com/en-us/training/modules/become-learn-contributor/)** — Beginner, 28 min, 8 units. uid: `$learn.become-learn-contributor`. Discover how to contribute to Microsoft Learn! Help improve documentation content, post in Microsoft Q&A, create a Collection, and share Microsoft Learn resources.
- **[Branch the flow of code using the switch-case construct in C#](https://learn.microsoft.com/en-us/training/modules/csharp-switch-case/)** — Beginner, 34 min, 6 units. uid: `learn.languages.csharp-switch-case`. Learn how to add branching logic that matches one variable or expression against many possible values.
- **[Build and deploy applications to Azure by using GitHub Actions](https://learn.microsoft.com/en-us/training/modules/github-actions-cd/)** — Intermediate, 179 min, 8 units. uid: `learn.github.github-actions-cd`. Create two deployment workflows using GitHub Actions and Microsoft Azure. Learn about triggering a CD workflow and storing credentials.
- **[Build continuous integration workflows by using GitHub Actions](https://learn.microsoft.com/en-us/training/modules/github-actions-ci/)** — Beginner, 81 min, 8 units. uid: `learn.github.github-actions-ci`. Learn how to create workflows to add continuous integration (CI) to your projects.
- **[Build serverless apps with Go](https://learn.microsoft.com/en-us/training/modules/serverless-go/)** — Beginner, 26 min, 8 units. uid: `learn.student-evangelism.serverless-go`. You can build serverless apps by using almost any programming language that supports HTTP primitives. By using custom handlers, you can choose a runtime that suits you.
- **[Build your first end-to-end test with Playwright](https://learn.microsoft.com/en-us/training/modules/build-with-playwright/)** — Beginner, 64 min, 8 units. uid: `learn.build-with-playwright`. In this module, you'll learn how to use Playwright to test a sample web application. You'll learn how to run tests, view test reports, and understand the structure of a Playwright project. You'll also learn how to use Visual Studio Code to run tests, debug tests, and record new tests.
- **[Build your first HTML webpage](https://learn.microsoft.com/en-us/training/modules/build-first-html-webpage/)** — Beginner, 31 min, 8 units. uid: `learn.wwl.build-first-html-webpage`. Illustrates basic programming techniques using Visual Studio Code to write HTML and CSS.
- **[Call methods from the .NET Class Library using C#](https://learn.microsoft.com/en-us/training/modules/csharp-call-methods/)** — Beginner, 54 min, 8 units. uid: `learn.languages.csharp-call-methods`. Use functionality in the .NET Class Library by calling methods that return values, accept input parameters, and more.
- **[Challenge project - Add image analysis and generation capabilities to your application](https://learn.microsoft.com/en-us/training/modules/challenge-project-add-image-analysis-generation-to-app/)** — Beginner, 80 min, 10 units. uid: `learn.student-evangelism.challenge-project-add-image-analysis-generation-to-app`. Add image analysis and generation capabilities to your application
- **[Challenge project - Create a mini-game](https://learn.microsoft.com/en-us/training/modules/challenge-project-create-mini-game/)** — Beginner, 45 min, 7 units. uid: `learn.wwl.challenge-project-create-mini-game`. Use methods with parameters and return values to develop the features of a console mini-game.
- **[Challenge project - Debug a C# console application using Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/challenge-project-debug-c-sharp-console-application/)** — Beginner, 37 min, 6 units. uid: `learn.wwl.challenge-project-debug-c-sharp-console-application`. This module helps you evaluate your debugging skills. You start with a C# console application that contains code logic issues and a specification that describes the requirements. You’re challenged to demonstrate your ability to identify and fix the issues using the Visual Studio Code debugger tools.
- **[Challenge project - Develop branching and looping structures in C#](https://learn.microsoft.com/en-us/training/modules/challenge-project-develop-branching-looping-structures-c-sharp/)** — Beginner, 68 min, 6 units. uid: `learn.wwl.challenge-project-develop-branching-looping-structures-c-sharp`. Demonstrate your ability to develop a console app that implements selection and iteration statements to achieve app specifications.
- **[Challenge project - Develop foreach and if-elseif-else structures to process array data in C#](https://learn.microsoft.com/en-us/training/modules/challenge-project-arrays-iteration-selection/)** — Beginner, 56 min, 6 units. uid: `learn.wwl.challenge-project-arrays-iteration-selection`. Demonstrate your ability to update a console app that implements arrays, foreach loops, and if statements in response to a user requested feature update.
- **[Challenge project - Work with variable data in C#](https://learn.microsoft.com/en-us/training/modules/challenge-project-work-variable-data-c-sharp/)** — Beginner, 43 min, 6 units. uid: `learn.wwl.challenge-project-work-variable-data-c-sharp`. A challenge project to test C# skills working with variable data.
- **[Choose the correct data type in your C# code](https://learn.microsoft.com/en-us/training/modules/csharp-choose-data-type/)** — Beginner, 47 min, 8 units. uid: `learn.languages.csharp-choose-data-type`. Choose the correct data type for your code from several basic types used in C#.
- **[Code scanning with GitHub CodeQL](https://learn.microsoft.com/en-us/training/modules/code-scanning-with-github-codeql/)** — Advanced, 81 min, 13 units. uid: `learn.code-scanning-with-github-codeql`. Learn how to use CodeQL, a powerful static analysis tool, to implement code scanning on GitHub.
- **[Code with GitHub Codespaces](https://learn.microsoft.com/en-us/training/modules/code-with-github-codespaces/)** — Beginner, 27 min, 7 units. uid: `learn.github.code-with-github-codespaces`. In this tutorial, you learn about GitHub Codespaces, its lifecycle, how to personalize your codespace, the differences between Codespaces and github.dev, and build a personalized and customized codespace with devcontainer.json files.
- **[Collaborate with pull requests in Azure Repos](https://learn.microsoft.com/en-us/training/modules/collaborate-pull-requests-azure-repos/)** — Advanced, 30 min, 5 units. uid: `learn.wwl.collaborate-pull-requests-azure-repos`. Collaborate with enterprise-grade pull request workflows, advanced collaboration patterns, and strategic code review practices in Azure Repos for scalable DevOps implementations.
- **[Communicate effectively on GitHub using Markdown](https://learn.microsoft.com/en-us/training/modules/communicate-using-markdown/)** — Beginner, 66 min, 5 units. uid: `learn.github.communicate-using-markdown`. Learn to use Markdown to communicate with brevity, clarity, and expression.
- **[Configure and Provision Environments](https://learn.microsoft.com/en-us/training/modules/configure-provision-environments/)** — Advanced, 120 min, 10 units. uid: `learn.wwl.configure-provision-environments`. Learn environment provisioning, service connection configuration, and automated testing infrastructure setup.
- **[Configure and use secret scanning in your GitHub repository](https://learn.microsoft.com/en-us/training/modules/configure-use-secret-scanning-github-repository/)** — Intermediate, 28 min, 7 units. uid: `learn.github.configure-and-use-secret-scanning-in-your-github-repository`. On completing this module, you'll understand how secret scanning works to configure and use it efficiently.
- **[Configure code scanning on GitHub](https://learn.microsoft.com/en-us/training/modules/configure-code-scanning/)** — Intermediate, 33 min, 7 units. uid: `learn.github.configure-code-scanning`. This module introduces you to code scanning and its features. You'll learn how to implement code scanning using CodeQL, third party tools, and GitHub Actions.
- **[Configure Dependabot security updates on your GitHub repo](https://learn.microsoft.com/en-us/training/modules/configure-dependabot-security-updates-on-github-repo/)** — Intermediate, 36 min, 9 units. uid: `learn.configure-dependabot-security-updates-on-github-repo`. Learn how to configure Dependabot security updates on your GitHub repo.
- **[Continuous deployment for machine learning](https://learn.microsoft.com/en-us/training/modules/continuous-deployment-for-machine-learning/)** — Beginner, 22 min, 5 units. uid: `learn.wwl.continuous-deployment-for-machine-learning`. Learn about continuous development for machine learning, machine learning operations, and MLOps.
- **[Contribute to an open-source project on GitHub](https://learn.microsoft.com/en-us/training/modules/contribute-open-source/)** — Beginner, 27 min, 7 units. uid: `learn.github.contribute-opensource`. Learn how to contribute to an open-source project on GitHub.
- **[Contribute to Microsoft Learn documentation in your browser](https://learn.microsoft.com/en-us/training/modules/contribute-to-docs-browser/)** — Beginner, 33 min, 9 units. uid: `learn.contribute-docs-browser`. Become a contributor to Microsoft Learn documentation by making edits with a web editor in GitHub. Make your changes, then create, validate, and submit pull requests to get your changes published.
- **[Control variable scope and logic using code blocks in C#](https://learn.microsoft.com/en-us/training/modules/csharp-code-blocks/)** — Beginner, 37 min, 7 units. uid: `learn.languages.csharp-code-blocks`. Use code blocks with more confidence, understanding how they impact the visibility and accessibility of both higher and lower-level constructs in your code.
- **[Convert data types using casting and conversion techniques in C#](https://learn.microsoft.com/en-us/training/modules/csharp-convert-cast/)** — Beginner, 62 min, 9 units. uid: `learn.languages.csharp-convert-cast`. Explore using C# techniques for casts and conversions.
- **[Create a Release Pipeline](https://learn.microsoft.com/en-us/training/modules/create-release-pipeline-devops/)** — Advanced, 102 min, 13 units. uid: `learn.wwl.create-release-pipeline`. Learn to create and configure release pipelines in Azure DevOps for automated deployment workflows.
- **[Create accessible web apps by using ASP.NET Core](https://learn.microsoft.com/en-us/training/modules/aspnet-core-accessibility/)** — Intermediate, 52 min, 10 units. uid: `learn.languages.aspnetcore-accessibility`. Diagnose and fix common web accessibility issues in an ASP.NET Core application.
- **[Create an open-source program by using GitHub best practices](https://learn.microsoft.com/en-us/training/modules/create-open-source-program-github/)** — Beginner, 91 min, 6 units. uid: `learn.github.create-open-source-program-github`. Learn to create a successful open-source program by establishing contributor guidance, following proven processes, and by using community standards.
- **[Create and host web sites by using GitHub Pages](https://learn.microsoft.com/en-us/training/modules/create-host-web-sites-github-pages/)** — Beginner, 72 min, 5 units. uid: `learn.github.create-host-web-sites-github-pages`. Learn how to host your personal, organization, and project sites for free with GitHub Pages.
- **[Create and manage events](https://learn.microsoft.com/en-us/training/modules/create-manage-events/)** — Beginner, 60 min, 8 units. uid: `learn.wwl.create-manage-events`. Discover how events facilitate communication between objects in C#, and how their integration with delegates creates robust, decoupled code.
- **[Create and publish custom GitHub actions](https://learn.microsoft.com/en-us/training/modules/create-custom-github-actions/)** — Intermediate, 26 min, 6 units. uid: `learn.github.create-custom-github-actions`. Learn how to create and publish custom GitHub actions.
- **[Create and throw exceptions in C# console applications](https://learn.microsoft.com/en-us/training/modules/create-throw-exceptions-c-sharp/)** — Beginner, 55 min, 7 units. uid: `learn.wwl.create-throw-exceptions-c-sharp`. This module explores the process for creating, throwing, and catching customized exceptions in a C# console application. Hands-on activities provide experience customizing exception properties, throwing exceptions, and using the exception properties to mitigate the exception within a catch block.
- **[Create Azure Resources by using Azure Resource Manager templates](https://learn.microsoft.com/en-us/training/modules/create-azure-resources-using-azure-resource-manager-templates/)** — Advanced, 29 min, 8 units. uid: `learn.wwl.create-azure-resources-using-azure-resource-manager-templates`. Learn how to create and deploy Azure resources using ARM templates and Bicep, including template components, dependencies, modularization, and secrets management for infrastructure as code.
- **[Create Azure Resources Using Azure CLI](https://learn.microsoft.com/en-us/training/modules/create-azure-resources-by-using-azure-cli/)** — Advanced, 37 min, 8 units. uid: `learn.wwl.create-azure-resources-by-using-azure-cli`. Learn how to install and use Azure CLI to create and manage Azure resources interactively and through Bash scripts. Learn CLI syntax, authentication, resource management, and troubleshooting for efficient cloud automation.
- **[Create C# methods that return values](https://learn.microsoft.com/en-us/training/modules/create-c-sharp-methods-return-values/)** — Beginner, 55 min, 10 units. uid: `learn.wwl.create-c-sharp-methods-return-values`. This module covers the return keyword and returning values from methods.
- **[Create C# methods with parameters](https://learn.microsoft.com/en-us/training/modules/create-c-sharp-methods-parameters/)** — Beginner, 52 min, 9 units. uid: `learn.wwl.create-c-sharp-methods-parameters`. This module covers method parameters, including pass-by-reference and pass-by-value parameter types. This module also covers optional and named arguments.
- **[Create readable code with conventions, whitespace, and comments in C#](https://learn.microsoft.com/en-us/training/modules/csharp-readable-code/)** — Beginner, 48 min, 8 units. uid: `learn.languages.csharp-readable-code`. Write code that is easier to read, update and support using naming conventions, comments and whitespace.
- **[Deliver with DevOps](https://learn.microsoft.com/en-us/training/modules/deliver-with-devops/)** — Beginner, 60 min, 8 units. uid: `learn.wwl.deliver-with-devops`. Build and run continuous integration and continuous delivery workflows using GitHub Actions.
- **[Deploy a cloud-native .NET microservice automatically with GitHub Actions and Azure Pipelines](https://learn.microsoft.com/en-us/training/modules/microservices-devops-aspnet-core/)** — Intermediate, 34 min, 7 units. uid: `learn.microservices-devops-aspnet-core`. Use a GitHub Actions CI/CD pipeline to build a container image and deploy it to Azure Kubernetes Service (AKS).
- **[Deploy a model with GitHub Actions](https://learn.microsoft.com/en-us/training/modules/deploy-model-github-actions/)** — Intermediate, 34 min, 7 units. uid: `learn.wwl.deploy-model-github-actions`. machine learning operations, MLOps, model deployment, online endpoint
- **[Deploy Azure infrastructure by using JSON ARM templates](https://learn.microsoft.com/en-us/training/modules/create-azure-resource-manager-template-vs-code/)** — Beginner, 43 min, 7 units. uid: `learn.azure.create-resource-manager-template-vs-code`. Write JSON Azure Resource Manager templates by using Visual Studio Code to deploy your infrastructure to Azure consistently and reliably.
- **[Describe pipelines and concurrency](https://learn.microsoft.com/en-us/training/modules/describe-pipelines-concurrency/)** — Advanced, 76 min, 9 units. uid: `learn.wwl.describe-pipelines-concurrency`. Learn about Azure Pipelines parallel jobs, concurrency management, Visual Designer, and YAML pipeline configurations for efficient CI/CD workflows.
- **[Design a container build strategy](https://learn.microsoft.com/en-us/training/modules/design-container-build-strategy/)** — Advanced, 60 min, 10 units. uid: `learn.wwl.design-container-build-strategy`. Design a Container Build Strategy
- **[Design and implement a pipeline strategy](https://learn.microsoft.com/en-us/training/modules/implement-pipeline-strategy/)** — Advanced, 34 min, 10 units. uid: `learn.wwl.implement-pipeline-strategy`. Learn how to design and implement effective pipeline strategies using Azure Pipelines, including multi-agent builds, source control integration, and comprehensive testing approaches.
- **[Design and implement branch strategies and workflows](https://learn.microsoft.com/en-us/training/modules/manage-git-branches-workflows/)** — Advanced, 92 min, 10 units. uid: `learn.wwl.manage-git-branches-workflows`. This module explores Git branching types, concepts, and models for the continuous delivery process. It helps companies defining their branching strategy and organization.
- **[Design processes to automate application analytics](https://learn.microsoft.com/en-us/training/modules/design-processes-automate-application-analytics/)** — Advanced, 32 min, 7 units. uid: `learn.wwl.design-processes-to-automate-application-analytics`. Learn to design automated application analytics processes using Azure Application Insights, telemetry integration, augmented search capabilities, and monitoring tools to improve DevOps efficiency and user experience.
- **[Design resilient code with interfaces](https://learn.microsoft.com/en-us/training/modules/design-resilient-code-interfaces/)** — Beginner, 58 min, 9 units. uid: `learn.wwl.design-resilient-code-interfaces`. In this module, you explore advanced concepts of interfaces in C#. You learn how to implement explicit interface members, combine multiple interfaces, and reduce code dependencies using interfaces.
- **[Design Secure and Scalable Platform Architectures](https://learn.microsoft.com/en-us/training/modules/design-secure-scalable-platform-architectures/)** — Advanced, 50 min, 7 units. uid: `learn.wwl.design-secure-scalable-platform-architectures`. In this module, learners will gain insights into designing platform architectures that are secure, scalable, and compliant with regulatory standards. The module covers capacity planning, cost optimization, and the role of automation in maintaining consistency and reducing manual errors. Learners will also explore strategies for building scalable solutions that can handle increasing demand and complex workflows.
- **[Develop monitor and status dashboards](https://learn.microsoft.com/en-us/training/modules/develop-monitor-status-dashboards/)** — Advanced, 51 min, 11 units. uid: `learn.wwl.develop-monitor-status-dashboards`. Learn to create comprehensive monitoring dashboards using Azure Dashboards, Azure Monitor Workbooks, Power BI, and GitHub monitoring tools. Track pipeline health metrics including failure rates, duration, and flaky tests. Optimize pipeline performance for cost and reliability. Explore visualization strategies and custom application development for DevOps monitoring at scale.
- **[Develop on a remote machine using SSH in Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/develop-on-remote-machine/)** — Beginner, 20 min, 9 units. uid: `learn.develop-on-remote-machine`. In this module, you'll learn how to seamlessly develop on a remote machine using the Visual Studio Code Remote - SSH extension. We'll explore how to run and debug code located on a remote machine, while locally using Visual Studio Code's full feature set.
- **[Develop with DevOps](https://learn.microsoft.com/en-us/training/modules/develop-with-devops/)** — Beginner, 59 min, 10 units. uid: `learn.wwl.develop-with-devops`. Streamline updates to your software development projects by applying version control with Git and GitHub. Your software lifecycle improves through the implementation of continuous integration, shift-left testing, and shift-left security.
- **[Developing in the Windows Subsystem for Linux with Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/developing-in-wsl/)** — Beginner, 21 min, 6 units. uid: `learn.developing-in-wsl`. In this module, you learn how to use the Windows Subsystem for Linux (WSL) with Visual Studio Code (VS Code). We explore the installation process and the basics of using WSL. Additionally, we install and utilize the Visual Studio Code WSL extension. Finally, we demonstrate how to debug and run Python code in VS Code within our WSL environment.
- **[Discover DevOps](https://learn.microsoft.com/en-us/training/modules/discover-devops/)** — Beginner, 26 min, 7 units. uid: `learn.wwl.discover-devops`. This module explores how DevOps practices optimize application lifecycle management for accelerated time to market and operational stability.
- **[Discover interfaces](https://learn.microsoft.com/en-us/training/modules/discover-interfaces/)** — Beginner, 42 min, 8 units. uid: `learn.wwl.discover-interfaces`. In this module, you learn how to design an interface with properties in C#, develop a class that implements the interface, and formulate property definitions within the interface.
- **[Edit code using any device with Visual Studio Code for the Web](https://learn.microsoft.com/en-us/training/modules/edit-code-using-any-device/)** — Beginner, 17 min, 9 units. uid: `learn.edit-code-using-any-device`. In this module, you'll learn how to use Visual Studio for the Web to develop from any device that is browser compatible. We'll explore how to make and review lightweight code edits using Visual Studio Code for the Web. Finally, we'll learn how to continue working in a different environment to get the full feature set of Visual Studio Code.
- **[Evaluate Boolean expressions to make decisions in C#](https://learn.microsoft.com/en-us/training/modules/csharp-evaluate-boolean-expressions/)** — Beginner, 50 min, 9 units. uid: `learn.languages.csharp-evaluate-boolean-expressions`. Learn the operators and techniques required to evaluate and compare values in your decision statements.
- **[Explore Azure Automation with DevOps](https://learn.microsoft.com/en-us/training/modules/explore-azure-automation-devops/)** — Advanced, 51 min, 13 units. uid: `learn.wwl.explore-azure-automation-devops`. Learn how to implement Azure Automation with DevOps using runbooks, webhooks, and PowerShell workflows. Understand automation accounts, shared resources, source control integration, and hybrid management for automated cloud operations.
- **[Explore Azure Pipelines](https://learn.microsoft.com/en-us/training/modules/explore-azure-pipelines/)** — Advanced, 17 min, 6 units. uid: `learn.wwl.explore-azure-pipelines`. Learn how Azure Pipelines helps you automate building, testing, and deploying your applications.
- **[Explore Git hooks](https://learn.microsoft.com/en-us/training/modules/explore-git-hooks/)** — Advanced, 14 min, 5 units. uid: `learn.wwl.explore-git-hooks`. Learn how to create Git hooks that automatically check code quality, scan for security issues, and help teams follow coding rules.
- **[Explore Infrastructure as Code and configuration management](https://learn.microsoft.com/en-us/training/modules/explore-infrastructure-code-configuration-management/)** — Advanced, 23 min, 7 units. uid: `learn.wwl.explore-infrastructure-as-code-configuration-management`. Learn Infrastructure as Code (IaC) foundational concepts, environment deployment strategies, configuration management approaches, and idempotent configuration principles for automated infrastructure operations.
- **[Explore package dependencies](https://learn.microsoft.com/en-us/training/modules/explore-package-dependencies/)** — Advanced, 29 min, 9 units. uid: `learn.wwl.explore-package-dependencies`. This module introduces you to organizing your build logic into different components and to dependency management.
- **[Explore release strategy recommendations](https://learn.microsoft.com/en-us/training/modules/explore-release-strategy-recommendations/)** — Advanced, 97 min, 9 units. uid: `learn.wwl.explore-release-strategy-recommendations`. Learn release strategy best practices, approval workflows, and gate configurations for automated deployments.
- **[Format alphanumeric data for presentation in C#](https://learn.microsoft.com/en-us/training/modules/csharp-format-strings/)** — Beginner, 58 min, 8 units. uid: `learn.languages.csharp-format-strings`. Explore basic methods in C# to format alphanumeric data.
- **[Foundations of Platform Engineering](https://learn.microsoft.com/en-us/training/modules/foundations-platform-engineering/)** — Advanced, 57 min, 7 units. uid: `learn.wwl.foundations-platform-engineering`. This module introduces the core concepts and importance of platform engineering. It explores how platform engineering enhances developer productivity, accelerates time to value, and supports digital transformation. Learners will understand the strategic value of platform engineering as the foundation for both technical success and alignment with broader business goals.
- **[Get started with classes and objects](https://learn.microsoft.com/en-us/training/modules/get-started-classes-objects/)** — Beginner, 71 min, 8 units. uid: `learn.wwl.get-started-classes-objects`. Learn how to create classes and instantiate objects that expose encapsulated field data by using class definitions, constructors, and the `new` operator.
- **[Get started with classes and objects in C#](https://learn.microsoft.com/en-us/training/modules/create-classes-objects-c-sharp/)** — Beginner, 71 min, 8 units. uid: `learn.wwl.create-classes-objects-c-sharp`. Learn how to create classes and instantiate objects that expose encapsulated field data by using class definitions, constructors, and the 'new' operator.
- **[Get started with Delegates](https://learn.microsoft.com/en-us/training/modules/get-started-delegates/)** — Beginner, 70 min, 8 units. uid: `learn.wwl.get-started-delegates`. Learn how to declare, instantiate, and invoke delegates for scenarios that require dynamic method invocation, such as callback methods and custom sorting or filtering. Learn how to use delegates to create flexible and extensible code that can adapt to changing requirements.
- **[Get started with file input and output](https://learn.microsoft.com/en-us/training/modules/get-started-file-input-output/)** — Beginner, 81 min, 9 units. uid: `learn.wwl.get-started-file-input-output`. Learn how to manage local files and directories using the System.IO classes, and how to store and retrieve C# objects using CSV files and the StreamReader and StreamWriter classes.
- **[Get started with generic and anonymous types](https://learn.microsoft.com/en-us/training/modules/get-started-generic-anonymous-types/)** — Beginner, 53 min, 7 units. uid: `learn.wwl.get-started-generic-anonymous-types`. Get started with generic and anonymous types in C#.
- **[Get started with web development using Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/get-started-with-web-development/)** — Beginner, 44 min, 7 units. uid: `learn-windows.introduction-to-web-development`. Practice the beginning steps of web development by creating a simple web project in Visual Studio Code that contains a web page, a CSS file, and a JavaScript file. Learn how to use developer tools in your browser to check your work.
- **[GitHub administration for enterprise support and adoption](https://learn.microsoft.com/en-us/training/modules/github-administration-for-enterprise-support-adoption/)** — Intermediate, 65 min, 7 units. uid: `learn.github-administration-for-enterprise-support-adoption`. Learn how GitHub Enterprise can make your administrative duties easier.
- **[GitHub administration for GitHub Advanced Security](https://learn.microsoft.com/en-us/training/modules/github-administration-github-advanced-security/)** — Advanced, 21 min, 7 units. uid: `learn.github-administration-github-advanced-security`. Understand where GitHub Advanced Security fits in your software development lifecycle and how to enable and roll it out in your organization.
- **[GitHub Enterprise Server fundamentals for developers](https://learn.microsoft.com/en-us/training/modules/github-enterprise-server-repository-workflows/)** — Intermediate, 31 min, 7 units. uid: `learn.github.github-enterprise-server-repository-workflows`. Overview of collaboration on GitHub Enterprise Server (GHES), focusing on governance, branch policies, and pull request workflows.
- **[GitHub Enterprise Server fundamentals for developers](https://learn.microsoft.com/en-us/training/modules/github-enterprise-server-developer-fundamentals/)** — Intermediate, 31 min, 7 units. uid: `learn.github.github-enterprise-server-developer-fundamentals`. Overview of GitHub Enterprise Server (GHES) and its self-managed GitHub experience for secure or regulated environments.
- **[Guided project - Debug and handle exceptions in a C# console application using Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/guided-project-debug-handle-exceptions-c-sharp-console-application/)** — Beginner, 50 min, 6 units. uid: `learn.wwl.guided-project-debug-handle-exceptions-c-sharp-console-application`. This module guides you through the code verification process for a C# console application. Hands-on activities provide experience identifying logic issues, debugging the application, and implementing exception handling. Step-by-step instructions are provided.
- **[Guided project - Develop conditional branching and looping structures in C#](https://learn.microsoft.com/en-us/training/modules/guided-project-develop-conditional-branching-looping/)** — Beginner, 100 min, 8 units. uid: `learn.wwl.guided-project-develop-conditional-branching-looping`. Gain experience developing a console app that implements selection and iteration statements to achieve app specifications.
- **[Guided project - Develop foreach and if-elseif-else structures to process array data in C#](https://learn.microsoft.com/en-us/training/modules/guided-project-arrays-iteration-selection/)** — Beginner, 93 min, 7 units. uid: `learn.wwl.guided-project-arrays-iteration-selection`. Gain experience developing a console app that implements arrays, foreach loops, and if statements to achieve app specifications.
- **[Guided project - Plan a Petting Zoo Visit](https://learn.microsoft.com/en-us/training/modules/guided-project-visit-petting-zoo/)** — Beginner, 28 min, 8 units. uid: `learn.wwl.guided-project-visit-petting-zoo`. Create an application that coordinates school visits to a petting zoo. This project requires the use of different methods with return types and parameters to complete the code.
- **[Guided project - Work with variable data in C#](https://learn.microsoft.com/en-us/training/modules/guided-project-work-variable-data-c-sharp/)** — Beginner, 38 min, 7 units. uid: `learn.wwl.guided-project-work-variable-data-c-sharp`. Complete a guided project to apply knowledge of variable data in C#.
- **[Identify security vulnerabilities in your codebase by using CodeQL](https://learn.microsoft.com/en-us/training/modules/codebase-representation-codeql/)** — Intermediate, 33 min, 7 units. uid: `learn.codebase-representation-codeql`. Learn how to use CodeQL to analyze the code in your GitHub repository and identify security vulnerabilities.
- **[Identify technical debt](https://learn.microsoft.com/en-us/training/modules/identify-technical-debt/)** — Advanced, 28 min, 10 units. uid: `learn.wwl.identify-technical-debt`. Learn how to find and manage technical debt in your code, use code quality tools, and plan effective code reviews.
- **[Implement a versioning strategy](https://learn.microsoft.com/en-us/training/modules/implement-versioning-strategy/)** — Advanced, 29 min, 8 units. uid: `learn.wwl.implement-versioning-strategy`. Learn to implement effective versioning strategies for packages using semantic versioning, package promotion workflows, and Azure Artifacts views to manage package quality and lifecycle.
- **[Implement A/B testing and progressive exposure deployment](https://learn.microsoft.com/en-us/training/modules/implement-test-progressive-exposure-deployment/)** — Advanced, 14 min, 5 units. uid: `learn.wwl.implement-testing-progressive-exposure-deployment`. Learn A/B testing methodologies, progressive exposure strategies, and ring-based deployment architectures for data-driven feature validation and controlled rollouts.
- **[Implement asynchronous tasks](https://learn.microsoft.com/en-us/training/modules/implement-asynchronous-tasks/)** — Beginner, 65 min, 9 units. uid: `learn.wwl.implement-asynchronous-tasks`. Learn how to implement asynchronous tasks in C# apps using the `async` and `await` keywords and how to run asynchronous tasks in parallel.
- **[Implement Azure Load Testing](https://learn.microsoft.com/en-us/training/modules/implement-azure-load-testing/)** — Intermediate, 71 min, 9 units. uid: `learn.wwl.implement-azure-load-testing`. Learn how to optimize application performance by simulating real-world loads with Azure Load Testing service. Learn how to automate load testing with GitHub Actions to ensure consistent application performance and scalability.
- **[Implement Bicep](https://learn.microsoft.com/en-us/training/modules/implement-bicep/)** — Advanced, 92 min, 10 units. uid: `learn.wwl.implement-bicep`. Learn to implement Bicep for infrastructure as code, including installation, template creation, deployment with Azure Pipelines and GitHub workflows, and integration with Azure Resource Manager.
- **[Implement blue-green deployment and feature toggles](https://learn.microsoft.com/en-us/training/modules/implement-blue-green-deployment-feature-toggles/)** — Advanced, 26 min, 7 units. uid: `learn.wwl.implement-blue-green-deployment-feature-toggles`. Learn blue-green deployment strategies, Azure deployment slot management, and feature toggle implementation for progressive delivery and risk mitigation.
- **[Implement canary releases and dark launching](https://learn.microsoft.com/en-us/training/modules/implement-canary-releases-dark-launching/)** — Advanced, 21 min, 6 units. uid: `learn.wwl.implement-canary-releases-dark-launching`. Learn canary release strategies, Azure Traffic Manager configuration, and dark launching techniques for progressive delivery and risk-controlled deployments.
- **[Implement class inheritance](https://learn.microsoft.com/en-us/training/modules/implement-class-inheritance/)** — Beginner, 88 min, 9 units. uid: `learn.wwl.implement-class-inheritance`. Learn how to create a class hierarchy using base and derived classes and how to hide or override members of a derived class by using `new`, `virtual`, `abstract`, and `override` keywords.
- **[Implement class properties and methods](https://learn.microsoft.com/en-us/training/modules/implement-class-properties-methods/)** — Beginner, 106 min, 10 units. uid: `learn.wwl.implement-class-properties-methods`. Learn how to implement read-write, read-only, and write-only class properties using property accessors and access modifiers, and how to implement methods and extension methods for a class.
- **[Implement Desired State Configuration (DSC)](https://learn.microsoft.com/en-us/training/modules/implement-desired-state-configuration-dsc/)** — Advanced, 28 min, 8 units. uid: `learn.wwl.implement-desired-state-configuration-dsc`. Learn to implement Desired State Configuration (DSC) with Azure Automation, including configuration drift management, DSC configurations, Linux automation, and hybrid management strategies.
- **[Implement Developer Self-Service](https://learn.microsoft.com/en-us/training/modules/implement-developer-self-service/)** — Advanced, 121 min, 10 units. uid: `learn.wwl.implement-developer-self-service`. This module focuses on enabling developers to independently manage their resources and workflows, fostering agility and innovation. Learners will understand the importance of combining flexibility with robust governance to ensure security, compliance, and operational consistency. The module also covers best practices for implementing and managing self-service capabilities within an organization.
- **[Implement enum, struct, and record types](https://learn.microsoft.com/en-us/training/modules/implement-enum-struct-record-types/)** — Beginner, 51 min, 7 units. uid: `learn.wwl.implement-enum-struct-record-types`. Learn to create organized, maintainable code with enum, struct, and record types in C#.
- **[Implement exception handling in C# console applications](https://learn.microsoft.com/en-us/training/modules/implement-exception-handling-c-sharp/)** — Beginner, 78 min, 11 units. uid: `learn.wwl.implement-exception-handling-c-sharp`. This module explores the use of exceptions and the exception handling process in C# console applications. Hands-on activities provide experience implementing exception handling patterns for various coding scenarios.
- **[Implement GitHub Actions](https://learn.microsoft.com/en-us/training/modules/implement-github-actions/)** — Intermediate, 60 min, 9 units. uid: `learn.wwl.implement-github-actions`. GitHub Actions is a powerful CI/CD platform that allows developers to automate their software development workflows. Learn how GitHub actions are implemented, how workflow files are structured, and how to control workflow execution.
- **[Implement GitHub Actions for Azure](https://learn.microsoft.com/en-us/training/modules/implement-github-actions-azure/)** — Intermediate, 61 min, 6 units. uid: `learn.wwl.implement-github-actions-azure`. Learn how to use GitHub Actions for Azure in your workflows and configure Azure with the necessary security principals to automate software development workflows between GitHub and Azure.
- **[Implement open-source software](https://learn.microsoft.com/en-us/training/modules/implement-open-source-software-azure/)** — Advanced, 66 min, 9 units. uid: `learn.wwl.implement-open-source-software-azure`. Learn how to implement open-source software securely, understand licensing implications, evaluate corporate concerns, and manage open-source components in enterprise environments.
- **[Implement polymorphic behavior](https://learn.microsoft.com/en-us/training/modules/implement-polymorphic-behavior/)** — Beginner, 73 min, 8 units. uid: `learn.wwl.implement-polymorphic-behavior`. Learn the principles of polymorphism, how to implement polymorphic behavior by using either class inheritance or interface implementation, and how to choose between inheritance-based and interface-based approaches to polymorphism.
- **[Implement the Visual Studio Code debugging tools for C#](https://learn.microsoft.com/en-us/training/modules/implement-visual-studio-code-debugging-tools/)** — Beginner, 81 min, 12 units. uid: `learn.wwl.implement-visual-studio-code-debugging-tools`. This module explores the tools and processes used to debug C# console applications in Visual Studio Code. Hands-on activities provide experience using breakpoints, conditional breakpoints, and the debugging resources in the RUN AND DEBUG view.
- **[Implement Tools to Track Usage and Flow](https://learn.microsoft.com/en-us/training/modules/implement-tools-track-usage-flow/)** — Advanced, 100 min, 11 units. uid: `learn.wwl.implement-tools-to-track-usage-flow`. Learn how to implement continuous monitoring tools to track application usage and flow. Explore Azure Monitor, Log Analytics, Kusto Query Language (KQL), and Application Insights for comprehensive telemetry, performance monitoring, and user behavior analysis.
- **[Install and configure Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/install-configure-visual-studio-code/)** — Beginner, 42 min, 9 units. uid: `learn.wwl.install-configure-visual-studio-code`. Learn how to configure Visual Studio Code for C# and how to use this professional IDE to create and run console applications.
- **[Integrate with Azure Pipelines](https://learn.microsoft.com/en-us/training/modules/integrate-azure-pipelines/)** — Advanced, 27 min, 9 units. uid: `learn.wwl.integrate-azure-pipelines`. Learn Azure Pipelines integration by exploring advanced pipeline anatomy, structure, templates, YAML resources, and multi-repository workflows for comprehensive CI/CD solutions.
- **[Integrate with identity management systems](https://learn.microsoft.com/en-us/training/modules/integrate-identity-management-systems/)** — Advanced, 30 min, 8 units. uid: `learn.wwl.integrate-identity-management-systems`. Master identity integration architectures including GitHub SSO, Microsoft Entra ID workload identities, service principals, and managed identities for secure DevOps authentication.
- **[Introduction to Azure DevOps to GitHub migration](https://learn.microsoft.com/en-us/training/modules/introduction-to-ado-to-github-migration/)** — Intermediate, 20 min, 4 units. uid: `learn.github.introduction-to-ado-to-github-migration`. This module is the first of four in this learning path that guides you through your Azure DevOps to GitHub Enterprise migration.
- **[Introduction to deployment patterns](https://learn.microsoft.com/en-us/training/modules/introduction-to-deployment-patterns/)** — Advanced, 22 min, 6 units. uid: `learn.wwl.introduction-to-deployment-patterns`. Explore deployment pattern architectures including microservices frameworks, classical deployment methodologies, and modern continuous delivery strategies for optimized software release cycles.
- **[Introduction to DevOps](https://learn.microsoft.com/en-us/training/modules/introduction-to-devops/)** — Beginner, 42 min, 15 units. uid: `learn.wwl.introduction-to-devops`. This foundational module provides a comprehensive overview of DevOps principles, practices, and transformation strategies. It covers what DevOps is, how organizations can begin their DevOps journey, and introduces key tools like Azure DevOps and GitHub.
- **[Introduction to DevOps principles for machine learning](https://learn.microsoft.com/en-us/training/modules/introduction-development-operations-principles-for-machine-learn/)** — Beginner, 33 min, 6 units. uid: `learn.wwl.introduction-development-operations-principles-for-machine-learn`. Learn about DevOps for machine learning, machine learning operations, and MLOps.
- **[Introduction to Git](https://learn.microsoft.com/en-us/training/modules/intro-to-git/)** — Beginner, 86 min, 6 units. uid: `learn.student-evangelism.introduction-to-git`. Use Git to track changes and collaborate with other developers.
- **[Introduction to GitHub](https://learn.microsoft.com/en-us/training/modules/introduction-to-github/)** — Beginner, 105 min, 8 units. uid: `learn.github.introduction-to-github`. Learn to use key GitHub features, including issues, notifications, branches, commits, and pull requests.
- **[Introduction to GitHub Actions](https://learn.microsoft.com/en-us/training/modules/introduction-to-github-actions/)** — Advanced, 30 min, 11 units. uid: `learn.wwl.introduction-to-github-actions`. Learn GitHub Actions fundamentals including workflows, events, jobs, and runners to automate your development processes
- **[Introduction to GitHub administration](https://learn.microsoft.com/en-us/training/modules/github-introduction-administration/)** — Intermediate, 36 min, 7 units. uid: `learn.github.github-introduction-administration`. Understand the security and control measures available to GitHub administrators within an organization or enterprise.
- **[Introduction to GitHub Advanced Security](https://learn.microsoft.com/en-us/training/modules/introduction-github-advanced-security/)** — Beginner, 26 min, 6 units. uid: `learn.introduction-github-advanced-security`. This module will help you become familiar with GitHub's Advanced Security features and best practices. As you learn about these features, you'll identify critical areas for eliminating security gaps.
- **[Introduction to GitHub Packages](https://learn.microsoft.com/en-us/training/modules/introduction-github-packages/)** — Advanced, 27 min, 7 units. uid: `learn.wwl.introduction-github-packages`. Learn how to use GitHub Packages to publish, install, delete, and restore packages. Explore package access control, visibility settings, and authentication methods for secure package management in GitHub repositories.
- **[Introduction to GitHub's products](https://learn.microsoft.com/en-us/training/modules/github-introduction-products/)** — Intermediate, 32 min, 9 units. uid: `learn.github.github-introduction-products`. Overview of GitHub's products, plans, associated features, and billing.
- **[Introduction to Secure DevOps](https://learn.microsoft.com/en-us/training/modules/introduction-to-secure-devops/)** — Advanced, 73 min, 10 units. uid: `learn.wwl.introduction-to-secure-devops`. Learn DevSecOps principles to integrate security throughout your development lifecycle. Understand common vulnerabilities like SQL injection, implement continuous security validation in pipelines, conduct threat modeling, and use tools like GitHub CodeQL for automated security analysis.
- **[Introduction to Visual Studio Code for Education](https://learn.microsoft.com/en-us/training/modules/visual-studio-code-education-introduction/)** — Beginner, 34 min, 7 units. uid: `learn.mec.visual-studio-code-education-introduction`. Evaluate whether Visual Studio Code for Education is the right tool to introduce your students to coding.
- **[Iterate through a code block using for statement in C#](https://learn.microsoft.com/en-us/training/modules/csharp-for/)** — Beginner, 37 min, 6 units. uid: `learn.languages.csharp-for`. Use the for iteration statement to loop a pre-set number of times and control the iteration process.
- **[Learn continuous integration with GitHub Actions](https://learn.microsoft.com/en-us/training/modules/learn-continuous-integration-github-actions/)** — Advanced, 70 min, 12 units. uid: `learn.wwl.learn-continuous-integration-github-actions`. Learn continuous integration with GitHub Actions through hands-on practice with workflows, environment variables, artifacts, secrets, and best practices for secure CI/CD pipelines.
- **[Leverage GitHub Actions to publish to GitHub Packages](https://learn.microsoft.com/en-us/training/modules/github-actions-packages/)** — Intermediate, 41 min, 8 units. uid: `learn.github.github-actions-packages`. Publish your code libraries or Docker images automatically and securely with GitHub Packages.
- **[Maintain a secure repository by using GitHub best practices](https://learn.microsoft.com/en-us/training/modules/maintain-secure-repository-github/)** — Beginner, 35 min, 6 units. uid: `learn.github.maintain-secure-repository-github`. Learn best practices for building, hosting, and maintaining a secure repository on GitHub.
- **[Manage alerts, blameless retrospectives and a just culture](https://learn.microsoft.com/en-us/training/modules/manage-alerts-blameless-retrospectives-just-culture/)** — Advanced, 56 min, 11 units. uid: `learn.wwl.manage-alerts-blameless-retrospectives-just-culture`. Learn to manage monitoring alerts effectively, conduct blameless retrospectives after incidents, and develop a just culture that promotes learning from failures. Improve application performance by reducing alert fatigue and understanding performance degradation patterns.
- **[Manage an InnerSource program by using GitHub](https://learn.microsoft.com/en-us/training/modules/manage-innersource-program-github/)** — Beginner, 50 min, 5 units. uid: `learn.github.manage-innersource-program-github`. Learn to manage a successful InnerSource program on GitHub through effective discoverability, guidance, and maintenance.
- **[Manage and configure repositories](https://learn.microsoft.com/en-us/training/modules/manage-git-repositories/)** — Advanced, 48 min, 15 units. uid: `learn.wwl.manage-git-repositories`. Learn how to work with large code repositories, clean up repository data, and manage releases using GitHub.
- **[Manage and Modularize Tasks and Templates](https://learn.microsoft.com/en-us/training/modules/manage-modularize-tasks-templates/)** — Advanced, 41 min, 6 units. uid: `learn.wwl.manage-modularize-tasks-templates`. Learn to create and manage task groups, variable groups, and custom build and release tasks for modular Azure pipelines
- **[Manage application configuration data](https://learn.microsoft.com/en-us/training/modules/manage-application-configuration-data/)** — Advanced, 140 min, 15 units. uid: `learn.wwl.manage-application-configuration-data`. Learn externalized configuration patterns, Azure App Configuration implementation, Key Vault integration, and feature flag management for secure, dynamic application settings
- **[Manage Azure Pipeline agents and pools](https://learn.microsoft.com/en-us/training/modules/manage-azure-pipeline-agents-pools/)** — Advanced, 82 min, 13 units. uid: `learn.wwl.manage-azure-pipeline-agents-pools`. Learn to configure and manage Azure Pipeline agents and pools, including Microsoft-hosted and self-hosted options, security considerations, and deployment strategies.
- **[Manage class implementations](https://learn.microsoft.com/en-us/training/modules/manage-class-implementations/)** — Beginner, 106 min, 10 units. uid: `learn.wwl.manage-class-implementations`. Learn how to implement classes using advanced techniques like static classes, partial classes, and object initializers that can improve the readability, maintainability, and organization of your code.
- **[Manage content in Microsoft Sentinel](https://learn.microsoft.com/en-us/training/modules/manage-content-microsoft-sentinel/)** — Intermediate, 15 min, 5 units. uid: `learn.wwl.manage-content-microsoft-sentinel`. Manage content in Microsoft Sentinel
- **[Manage GitHub Actions in the enterprise](https://learn.microsoft.com/en-us/training/modules/manage-github-actions-enterprise/)** — Intermediate, 61 min, 10 units. uid: `learn.github.manage-github-actions-enterprise`. Learn how to manage GitHub Actions in the enterprise.
- **[Manage repository changes by using pull requests on GitHub](https://learn.microsoft.com/en-us/training/modules/manage-changes-pull-requests-github/)** — Beginner, 56 min, 5 units. uid: `learn.github.manage-changes-pull-requests-github`. Learn how to manage changes to your repository source by using pull requests.
- **[Manage sensitive data and security policies within GitHub](https://learn.microsoft.com/en-us/training/modules/manage-sensitive-data-security-policies/)** — Intermediate, 96 min, 7 units. uid: `learn.github.manage-sensitive-data-security-policies`. Familiarize yourself with GitHub's basic security tools, which prepare repositories for secure development and industry-standard response to threats.
- **[Manage software delivery by using a release based workflow on GitHub](https://learn.microsoft.com/en-us/training/modules/release-based-workflow-github/)** — Beginner, 104 min, 5 units. uid: `learn.github.release-based-workflow-github`. Learn to implement a release based workflow on GitHub using project boards, branches, and releases.
- **[Manage your work with GitHub Projects](https://learn.microsoft.com/en-us/training/modules/manage-work-github-projects/)** — Beginner, 36 min, 8 units. uid: `learn.github.manage-work-github-projects`. Visualize large projects as spreadsheets or boards, and automate everything with code.
- **[Migrate your CI/CD pipelines to GitHub with GitHub Actions Importer](https://learn.microsoft.com/en-us/training/modules/migrate-cicd-pipelines-to-github-with-github-actions-importer/)** — Intermediate, 48 min, 5 units. uid: `learn.migrate-cicd-pipelines-to-github-with-github-actions-importer`. Learn about GitHub Actions Importer and how it can help facilitate migrations from your current CI/CD tool to GitHub Actions.
- **[Migrate your repository by using GitHub best practices](https://learn.microsoft.com/en-us/training/modules/migrate-repository-github/)** — Beginner, 43 min, 5 units. uid: `learn.github.migrate-repository-github`. Learn to move your existing project to GitHub from a legacy version control system.
- **[Migrate, consolidate, and secure artifacts](https://learn.microsoft.com/en-us/training/modules/migrate-consolidating-secure-artifacts/)** — Advanced, 37 min, 9 units. uid: `learn.wwl.migrate-consolidating-secure-artifacts`. Learn how to migrate and consolidate artifact repositories to Azure Artifacts, and implement comprehensive security including roles, permissions, and authentication to protect package feeds.
- **[Modify the content of strings using built-in string data type methods in C#](https://learn.microsoft.com/en-us/training/modules/csharp-modify-content/)** — Beginner, 75 min, 8 units. uid: `learn.languages.csharp-modify-content`. Explore using the built-in string data type methods in C# to modify strings.
- **[Observability and Continuous Improvement](https://learn.microsoft.com/en-us/training/modules/observability-continuous-improvement/)** — Advanced, 64 min, 9 units. uid: `learn.wwl.observability-continuous-improvement`. Learners will discover the significance of observability in providing real-time insights into system performance and identifying inefficiencies. This module emphasizes the importance of continuous improvement through feedback loops, performance monitoring, and market analysis. Learners will explore strategies for adapting to market trends and fostering a culture of innovation within platform engineering teams.
- **[Operate with DevOps](https://learn.microsoft.com/en-us/training/modules/operate-with-devops/)** — Beginner, 54 min, 10 units. uid: `learn.wwl.operate-with-devops`. Achieve operational excellence and enhance developer experience in your organization through DevOps. Your operational and development practices improve by implementing shift-right testing, observability through performance and security monitoring, Site Reliability Engineering and platform engineering.
- **[Perform operations on arrays using helper methods in C#](https://learn.microsoft.com/en-us/training/modules/csharp-arrays-operations/)** — Beginner, 58 min, 10 units. uid: `learn.languages.csharp-arrays-operations`. Use C# helper methods to perform reverse, resize, split and join operations on arrays.
- **[Personalize your remote development workflow with Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/personalize-remote-development-workflow/)** — Beginner, 23 min, 8 units. uid: `learn.personalize-remote-development-workflow`. Use features in VS Code to personalize your development experience for various remote environments.
- **[Plan Agile with GitHub Projects and Azure Boards](https://learn.microsoft.com/en-us/training/modules/plan-agile-github-projects-azure-boards/)** — Advanced, 94 min, 14 units. uid: `learn.wwl.plan-agile-github-projects-azure-boards`. Plan Agile with GitHub Projects and Azure Boards
- **[Plan to foster inner source](https://learn.microsoft.com/en-us/training/modules/plan-fostering-inner-source/)** — Advanced, 20 min, 6 units. uid: `learn.wwl.plan-foster-inner-source`. Learn how to use Git to foster inner source development across your organization and implement fork workflows.
- **[Plan with DevOps](https://learn.microsoft.com/en-us/training/modules/plan-with-devops/)** — Beginner, 70 min, 8 units. uid: `learn.wwl.plan-with-devops`. In this module you learn how to plan your software development projects agilely using GitHub Projects boards.
- **[Review the principles of code debugging and exception handling](https://learn.microsoft.com/en-us/training/modules/review-principles-code-debugging-exception-handling-c-sharp/)** — Beginner, 26 min, 6 units. uid: `learn.wwl.review-principles-code-debugging-exception-handling-c-sharp`. This module examines code validation using a combination of testing, debugging, and exception handling. The debugging process and benefits provided by code debugger are reviewed, along with the principals and processes behind exception handling.
- **[Search and organize repository history by using GitHub](https://learn.microsoft.com/en-us/training/modules/search-organize-repository-history-github/)** — Beginner, 38 min, 5 units. uid: `learn.github.search-organize-repository-history-github`. Learn to search and organize repository history by using filters, blame, and cross-linking on GitHub.
- **[Security monitoring and governance](https://learn.microsoft.com/en-us/training/modules/security-monitoring-and-governance/)** — Advanced, 120 min, 13 units. uid: `learn.wwl.security-monitoring-and-governance`. Learn security monitoring and governance with Microsoft Defender for Cloud, Azure Policy, resource locks, Microsoft Defender for Identity, and GitHub Advanced Security integration for comprehensive DevSecOps protection.
- **[Settle competing commits by using merge conflict resolution on GitHub](https://learn.microsoft.com/en-us/training/modules/resolve-merge-conflicts-github/)** — Beginner, 52 min, 5 units. uid: `learn.github.merge-conflict-resolution-github`. Learn to settle overlapping commits across branches by using merge conflict resolution.
- **[Share knowledge within teams](https://learn.microsoft.com/en-us/training/modules/share-knowledge-within-teams/)** — Advanced, 65 min, 7 units. uid: `learn.wwl.share-knowledge-within-teams`. Learn to share knowledge effectively within development teams using Azure DevOps Wikis, GitHub documentation, and Microsoft Teams integration. Explore documentation strategies, wiki creation and management, Markdown formatting with Mermaid diagrams, and real-time collaboration tools to preserve organizational knowledge and improve team productivity.
- **[Software Composition Analysis](https://learn.microsoft.com/en-us/training/modules/software-composition-analysis/)** — Advanced, 77 min, 10 units. uid: `learn.wwl.software-composition-analysis`. Learn Software Composition Analysis (SCA) to detect vulnerabilities and license compliance issues in open-source dependencies, implement GitHub Dependabot, integrate scanning tools into pipelines, and automate container security scanning.
- **[Source control for machine learning projects](https://learn.microsoft.com/en-us/training/modules/source-control-for-machine-learning-projects/)** — Beginner, 34 min, 7 units. uid: `learn.wwl.source-control-for-machine-learning-projects`. Learn about source control for machine learning, machine learning operations, and MLOps.
- **[Static analyzers](https://learn.microsoft.com/en-us/training/modules/static-analyzers/)** — Advanced, 71 min, 6 units. uid: `learn.wwl.static-analyzers`. Static analyzers
- **[Store and iterate through sequences of data using Arrays and the foreach statement in C#](https://learn.microsoft.com/en-us/training/modules/csharp-arrays/)** — Beginner, 51 min, 7 units. uid: `learn.languages.csharp-arrays`. Learn to create array variables and iterate through elements of the array.
- **[Store and retrieve JSON files](https://learn.microsoft.com/en-us/training/modules/store-retrieve-json-files/)** — Beginner, 72 min, 9 units. uid: `learn.wwl.store-retrieve-json-files`. Learn how to serialize and deserialize JavaScript Object Notation (JSON) strings using the JsonSerializer class, the JsonSerializerOptions class, and Data Transfer Objects.
- **[Strategic Platform Road Mapping](https://learn.microsoft.com/en-us/training/modules/strategic-platform-road-mapping/)** — Advanced, 70 min, 11 units. uid: `learn.wwl.strategic-platform-road-mapping`. This module covers the principles of strategic platform road mapping, including aligning platform initiatives with business objectives, preparing for technological advancements, and fostering innovation. Learners will understand how to develop actionable roadmaps that guide the platform’s evolution, ensuring it remains efficient, reliable, and capable of evolving with future innovations.
- **[Trigger Azure Machine Learning jobs with GitHub Actions](https://learn.microsoft.com/en-us/training/modules/trigger-azure-machine-learn-jobs-github-actions/)** — Intermediate, 35 min, 7 units. uid: `learn.wwl.trigger-azure-machine-learn-jobs-github-actions`. MLOps, machine learning operations
- **[Trigger GitHub Actions with feature-based development](https://learn.microsoft.com/en-us/training/modules/trigger-github-actions-trunk-based-development/)** — Intermediate, 35 min, 7 units. uid: `learn.wwl.trigger-github-actions-trunk-based-development`. Learn how to trigger GitHub Actions with feature-based development to achieve machine learning operations or MLOps.
- **[Understand package management](https://learn.microsoft.com/en-us/training/modules/understand-package-management/)** — Advanced, 87 min, 12 units. uid: `learn.wwl.understand-package-management`. Learn package management concepts including package feeds, feed managers, public and private sources, and how to consume, create, and publish packages using Azure Artifacts.
- **[Upload your project by using GitHub best practices](https://learn.microsoft.com/en-us/training/modules/upload-project-github/)** — Beginner, 43 min, 5 units. uid: `learn.github.upload-project-github`. Learn to upload your existing project to GitHub.
- **[Use a Docker container as a development environment with Visual Studio Code](https://learn.microsoft.com/en-us/training/modules/use-docker-container-dev-env-vs-code/)** — Beginner, 34 min, 10 units. uid: `learn.use-docker-container-dev-env-vs-code`. Create and configure a full-featured container-based development environment with the Visual Studio Code Dev Containers extension. Open any folder or repository in a container and take advantage of the full feature set of Visual Studio Code, like IntelliSense (completions), code navigation, and debugging.
- **[Use CSS styles in a webpage](https://learn.microsoft.com/en-us/training/modules/use-css-styles/)** — Beginner, 35 min, 8 units. uid: `learn.wwl.use-css-styles`. Discover how to use CSS styles in a webpage.
- **[Work with environments in GitHub Actions](https://learn.microsoft.com/en-us/training/modules/work-environments-github-actions/)** — Intermediate, 36 min, 7 units. uid: `learn.wwl.work-environments-github-actions`. machine learning operations, MLOps, environments
- **[Work with linting and unit testing in GitHub Actions](https://learn.microsoft.com/en-us/training/modules/work-linting-unit-test-github-actions/)** — Intermediate, 32 min, 7 units. uid: `learn.wwl.work-linting-unit-test-github-actions`. machine learning operations, MLOps, linter, linting, unit tests, code check
- **[Write your first C# method](https://learn.microsoft.com/en-us/training/modules/write-first-c-sharp-method/)** — Beginner, 55 min, 9 units. uid: `learn.wwl.write-first-c-sharp-method`. This module covers the syntax of creating and executing methods. Creating reusable code and structuring solutions using methods are reviewed.

---

## Learning paths (catalog data only, not modules)

*49 learning paths matched product=github OR product=vs-code. Listed for completeness; not in scope for page-level module fetching.*

- **[Access local files asynchronously](https://learn.microsoft.com/en-us/training/paths/access-local-files-asynchronously/)** — Beginner, 218 min, 3 modules. uid: `learn.wwl.access-local-files-asynchronously`. Learn how to&nbsp;manage local files using the System.IO namespace and how to asynchronously back up and restore application data using the System.Text.Json namespace.&nbsp;
- **[Add logic to C# console applications (Get started with C#, Part 3)](https://learn.microsoft.com/en-us/training/paths/get-started-c-sharp-part-3/)** — Beginner, 381 min, 7 modules. uid: `learn.wwl.get-started-c-sharp-part-3`. Deepen your experience with C# logic and iteration statements, Boolean expressions, and code blocks in this Learning Path.
- **[Automate Azure Load Testing by using GitHub](https://learn.microsoft.com/en-us/training/paths/automate-azure-load-testing-github/)** — Intermediate, 192 min, 3 modules. uid: `learn.wwl.automate-azure-load-testing-github`. Learn how to implement GitHub Actions and configure Azure Load Testing to automate testing app deployments.
- **[Automate your workflow with GitHub Actions Part 1 of 2](https://learn.microsoft.com/en-us/training/paths/github-actions/)** — Beginner/Intermediate, 341 min, 4 modules. uid: `learn.github-actions`. Learn how GitHub Actions enables you to automate your software development cycle.
- **[Automate your workflow with GitHub Actions Part 2 of 2](https://learn.microsoft.com/en-us/training/paths/github-actions-2/)** — Beginner/Intermediate, 128 min, 3 modules. uid: `learn.github-actions-2`. This is part two of a GitHub Action Learning Path. Learn how GitHub Actions enables you to automate your software development cycle.
- **[AZ-400: Design and implement a dependency management strategy](https://learn.microsoft.com/en-us/training/paths/az-400-design-implement-dependency-management-strategy/)** — Advanced, 209 min, 5 modules. uid: `learn.wwl.az-400-design-implement-dependency-management-strategy`. Learn how to design and implement a comprehensive dependency management strategy for DevOps. Explore package dependencies, package management, artifact security, versioning strategies, and GitHub Packages integration for efficient software development.
- **[AZ-400: Design and implement a release strategy](https://learn.microsoft.com/en-us/training/paths/az-400-design-implement-release-strategy/)** — Advanced, 389 min, 5 modules. uid: `learn.wwl.az-400-design-implement-release-strategy`. Learn advanced release strategy design and implementation through comprehensive continuous delivery frameworks, deployment orchestration, and automated quality assurance methodologies
- **[AZ-400: Development for Enterprise DevOps](https://learn.microsoft.com/en-us/training/paths/az-400-work-git-for-enterprise-devops/)** — Advanced, 368 min, 8 modules. uid: `learn.wwl.az-400-work-git-for-enterprise-devops`. Learn Git features and DevOps practices that help organizations build better software together.
- **[AZ-400: Implement a secure continuous deployment using Azure Pipelines](https://learn.microsoft.com/en-us/training/paths/az-400-implement-secure-continuous-deployment/)** — Advanced, 253 min, 6 modules. uid: `learn.wwl.az-400-implement-secure-continuous-deployment`. AZ-400: Implement a secure continuous deployment using Azure Pipelines
- **[AZ-400: Implement CI with Azure Pipelines and GitHub Actions](https://learn.microsoft.com/en-us/training/paths/az-400-implement-ci-azure-pipelines-github-actions/)** — Advanced, 396 min, 8 modules. uid: `learn.wwl.az-400-implement-ci-azure-pipelines-github-actions`. AZ-400: Implement CI with Azure Pipelines and GitHub Actions
- **[AZ-400: Implement continuous feedback](https://learn.microsoft.com/en-us/training/paths/az-400-implement-continuous-feedback/)** — Advanced, 304 min, 5 modules. uid: `learn.wwl.az-400-implement-continuous-feedback`. Learn to implement continuous feedback practices in DevOps using Azure Application Insights, monitoring dashboards, team knowledge sharing, automated analytics, and blameless retrospectives to create a culture of continuous improvement.
- **[AZ-400: Implement security and validate code bases for compliance](https://learn.microsoft.com/en-us/training/paths/az-400-implement-security-validate-code-bases-compliance/)** — Advanced, 336 min, 4 modules. uid: `learn.wwl.az-400-implement-security-validate-code-basescompliance`. AZ-400: Implement security and validate code bases for compliance - Learn DevSecOps practices, secure pipeline implementation, open-source software security, software composition analysis, and comprehensive security monitoring with Microsoft Defender for Cloud, Azure Policy, and GitHub Advanced Security.
- **[AZ-400: Manage infrastructure as code using Azure and DSC](https://learn.microsoft.com/en-us/training/paths/az-400-manage-infrastructure-as-code-using-azure/)** — Advanced, 260 min, 6 modules. uid: `learn.wwl.az-400-manage-infrastructure-as-code-using-azure`. AZ-400: Manage infrastructure as code using Azure and DSC
- **[Build community-driven software projects on GitHub](https://learn.microsoft.com/en-us/training/paths/build-community-driven-projects-github/)** — Beginner, 394 min, 7 modules. uid: `learn.build-community-driven-projects-github`. Learn how GitHub enables you to build communities that foster communication and collaboration while reinforcing recommended guidelines, codes of conduct, and security best practices.
- **[Build web pages with HTML and CSS for beginners](https://learn.microsoft.com/en-us/training/paths/build-web-pages-html-css-for-beginners/)** — Beginner, 81 min, 3 modules. uid: `learn.wwl.build-web-pages-html-css-for-beginners`. Write HTML and CSS code to create an accessible webpage using the browser-based version of Visual Studio code.
- **[Collaborate with others with Markdown and GitHub Pages](https://learn.microsoft.com/en-us/training/paths/collaborate-markdown-github-pages/)** — Beginner, 243 min, 3 modules. uid: `learn.collaborate-markdown-github-pages`. Learn how to use Markdown to effectively communicate with others in your GitHub issues, pull requests, comments, and documentation. Then learn how to build project sites and blog posts to promote your projects with GitHub Pages.
- **[Create and run simple C# console applications (Get started with C#, Part 2)](https://learn.microsoft.com/en-us/training/paths/get-started-c-sharp-part-2/)** — Beginner, 400 min, 7 modules. uid: `learn.wwl.get-started-c-sharp-part-2`. Use Visual Studio Code to develop C# console applications that implement arrays, foreach loops, and if statements.
- **[Create methods in C# console applications (Get started with C#, Part 5)](https://learn.microsoft.com/en-us/training/paths/get-started-c-sharp-part-5/)** — Beginner, 235 min, 5 modules. uid: `learn.wwl.get-started-c-sharp-part-5`. This learning path covers the syntax of creating and using methods in C# console applications.
- **[Debug C# console applications (Get started with C#, Part 6)](https://learn.microsoft.com/en-us/training/paths/get-started-c-sharp-part-6/)** — Beginner, 327 min, 6 modules. uid: `learn.wwl.get-started-c-sharp-part-6`. Debug C# console applications (Get started with C#, Part 6)
- **[Describe the purpose and use of source control](https://learn.microsoft.com/en-us/training/paths/describe-purpose-use-source-control/)** — Beginner, 96 min, 3 modules. uid: `learn.wwl.describe-purpose-use-source-control`. Introduction to source control as a concept with practical application in the final module.
- **[Design a machine learning solution](https://learn.microsoft.com/en-us/training/paths/design-machine-learning-solution/)** — Beginner, 127 min, 4 modules. uid: `learn.wwl.design-machine-learning-solution`. Design a machine learning solution with Azure Machine Learning v2
- **[Design and Implement Platform Engineering](https://learn.microsoft.com/en-us/training/paths/designing-implementing-platform-engineering/)** — Advanced, 362 min, 5 modules. uid: `learn.wwl.designing-implementing-platform-engineering`. This learning path provides a comprehensive guide to Design and Implement Platform Engineering within modern enterprises. It covers the foundational principles, strategic alignment with business goals, and the practical aspects of building scalable, secure, and future-proof platforms. By following this path, learners will gain the knowledge and skills needed to enhance developer productivity, ensure operational excellence, and drive continuous innovation.
- **[Develop agents and applications using agentic programming tools](https://learn.microsoft.com/en-us/training/paths/create-embed-custom-code-agents/)** — Intermediate, 490 min, 4 modules. uid: `learn.wwl.create-embed-custom-code-agents`. Learn how to develop applications using agentic programming tools and techniques. This training covers how to configure custom agents in the development environment, how to develop or update apps using the GitHub Spec Kit, and how to create AI-enabled apps with embedded agents using the GitHub Copilot SDK.
- **[Developing in Agentic AI Systems Part 1 of 2](https://learn.microsoft.com/en-us/training/paths/gh-developing-agentic-systems-1/)** — Beginner/Intermediate, 120 min, 3 modules. uid: `learn.github.developing-agentic-systems-1`. Learn how to design, deploy, and manage agentic AI systems within the software development lifecycle by integrating, orchestrating, and governing autonomous agents using GitHub to ensure safe, reliable, and scalable delivery.
- **[Developing in agentic AI systems part 2 of 2](https://learn.microsoft.com/en-us/training/paths/github-agentic-systems-part-two/github-agentic-systems-part-two/)** — Beginner/Intermediate, 140 min, 3 modules. uid: `learn.github.developing-agentic-systems-2`. This is part two of two part learning series to support our new certification, Developing in Agentic AI Systems. In this learning path you will learn how to design, deploy, and manage agentic AI systems within the software development lifecycle by integrating, orchestrating, and governing autonomous agents using GitHub to ensure safe, reliable, and scalable delivery.
- **[DevOps foundations: The core principles and practices](https://learn.microsoft.com/en-us/training/paths/devops-foundations-core-principles-practices/)** — Beginner, 269 min, 5 modules. uid: `learn.wwl.devops-foundations-core-principles-practices`. Explore DevOps practices using GitHub. Your development and operations teams will experience improved collaboration, agility, continuous integration, continuous delivery, automation, and operational excellence throughout all phases of the application lifecycle. (AZ-2008)
- **[Get started with AI-assisted development](https://learn.microsoft.com/en-us/training/paths/accelerate-app-development-using-github-copilot/)** — Intermediate, 479 min, 6 modules. uid: `learn.wwl.accelerate-app-development-using-github-copilot`. Learn how to use GitHub Copilot in a Visual Studio Code environment. This training covers code analysis, inline and project documentation, app development, unit testing, code refactoring, and provides an introduction to vibe coding. AZ-2007
- **[GitHub Advanced Security Part 1 of 2](https://learn.microsoft.com/en-us/training/paths/github-advanced-security/)** — Beginner/Intermediate, 123 min, 4 modules. uid: `learn.github-github-advanced-security`. Learn how to secure your code with advanced security features at every stage of your development lifecycle. GitHub Advanced Security is an add-on to GitHub Enterprise that allows you to use security features, such as secret scanning, code scanning, and dependency management on your private repositories.
- **[GitHub Advanced Security Part 2 of 2](https://learn.microsoft.com/en-us/training/paths/github-advanced-security-2/)** — Beginner/Intermediate, 231 min, 4 modules. uid: `learn.github-github-advanced-security-2`. Learn how to secure your code with advanced security features at every stage of your development lifecycle. GitHub Advanced Security is an add-on to GitHub Enterprise that allows you to use security features, such as secret scanning, code scanning, and dependency management on your private repositories. This is the second learning path out of two learning paths of GHAS.
- **[GitHub Copilot Fundamentals Part 1 of 2](https://learn.microsoft.com/en-us/training/paths/copilot/)** — Beginner/Intermediate, 317 min, 9 modules. uid: `learn.github-copilot`. Empower individual developers and businesses to enhance their productivity and foster innovation through a comprehensive exploration of the fundamental concepts of GitHub Copilot. Additionally, gain valuable insights on how to initiate the implementation of GitHub Copilot within your organization, enabling you to kickstart your own transformative journey. This is learning path is split into two and this is part one of two.
- **[GitHub Copilot Fundamentals Part 2 of 2](https://learn.microsoft.com/en-us/training/paths/gh-copilot-2/)** — Beginner/Intermediate, 199 min, 6 modules. uid: `learn.github-copilot-2`. Empower individual developers and businesses to enhance their productivity and foster innovation through a comprehensive exploration of the fundamental concepts of GitHub Copilot. Additionally, gain valuable insights on how to initiate the implementation of GitHub Copilot within your organization, enabling you to kickstart your own transformative journey.
- **[GitHub Foundations Part 1 of 2](https://learn.microsoft.com/en-us/training/paths/github-foundations/)** — Beginner/Intermediate, 404 min, 8 modules. uid: `learn.github-foundations`. The GitHub Foundations Learning Path Part 1 of 2 is a concise and beginner-friendly journey designed to introduce you to the fundamental concepts and products of GitHub.
- **[GitHub Foundations Part 2 of 2](https://learn.microsoft.com/en-us/training/paths/github-foundations-2/)** — Beginner/Intermediate, 297 min, 8 modules. uid: `learn.github-foundations-2`. The GitHub Foundations Learning Path Part 2 of 2 is a concise and beginner-friendly journey designed to introduce you to the fundamental concepts and products of GitHub.
- **[GitHub fundamentals - Administration basics and product features Part 1 of 2](https://learn.microsoft.com/en-us/training/paths/github-administration-products/)** — Intermediate, 208 min, 4 modules. uid: `learn.github.github-administration-products-1`. In this learning path, learn the basics of GitHub administration and discover the products that GitHub offers. This is the first learning path in a two part series.
- **[GitHub fundamentals - Administration basics and product features Part 2 of 2](https://learn.microsoft.com/en-us/training/paths/github-admin-2/github-admin-2/)** — Intermediate, 296 min, 5 modules. uid: `learn.github.github-administration-products-2`. In this learning path, learn the basics of GitHub administration and discover the products that GitHub offers. This is the second learning path in a two part series.
- **[GitHub responsible AI](https://learn.microsoft.com/en-us/training/paths/github-responsible-ai/)** — Beginner, 135 min, 3 modules. uid: `learn.github.responsible-ai`. Strengthen your AI knowledge through courses covering essential topics such as machine learning, facial recognition, generative AI, and responsible AI practices. Learn how AI tools detect and analyze faces, explore the creation of content with generative models, and embrace responsible considerations in AI development. These foundational classes build expertise in AI while focusing on responsible technology use.
- **[Implement classes, properties, and methods](https://learn.microsoft.com/en-us/training/paths/implement-classes-properties-and-methods/)** — Beginner, 283 min, 3 modules. uid: `learn.wwl.implement-classes-properties-and-methods`. Learn how to&nbsp;create classes and objects in C# and how to securely access and manage encapsulated data using class properties and methods.
- **[Implement delegates and events](https://learn.microsoft.com/en-us/training/paths/delegates-events-exceptions/)** — Beginner, 130 min, 2 modules. uid: `learn.wwl.delegates-events-exceptions`. Learn how to implement late binding using delegates, how to notify other classes or objects when something of interest occurs using events, and how to manage event publishers and subscribers in a C# application.
- **[Introduction to machine learning operations (MLOps)](https://learn.microsoft.com/en-us/training/paths/introduction-machine-learn-operations/)** — Beginner, 118 min, 4 modules. uid: `learn.wwl.introduction-machine-learn-operations`. Introduction to machine learning operations (MLOps)
- **[Manage source control](https://learn.microsoft.com/en-us/training/paths/az-400-manage-source-control/)** — Beginner, 920 min, 14 modules. uid: `learn.az-400-manage-source-control`. Use GitHub to build a modern source control strategy and prepare for Exam AZ-400: Designing and Implementing Microsoft DevOps Solutions.
- **[Manage the lifecycle of your projects on GitHub](https://learn.microsoft.com/en-us/training/paths/manage-project-lifecycle-github/)** — Intermediate, 398 min, 6 modules. uid: `learn.manage-project-lifecycle-github`. Through work planning and tracking, effective branching strategies, and extending GitHub through its API, manage releases all the way from idea to working software in the hands of your users.
- **[Operationalize generative AI applications (GenAIOps)](https://learn.microsoft.com/en-us/training/paths/operationalize-gen-ai-apps/)** — Intermediate, 368 min, 6 modules. uid: `learn.wwl.operationalize-gen-ai-apps`. Learn the full GenAIOps lifecycle for generative AI applications, from planning and prompt management to evaluation, automated testing, monitoring, and tracing in production.
- **[Operationalize machine learning models (MLOps)](https://learn.microsoft.com/en-us/training/paths/build-first-machine-operations-workflow/)** — Intermediate, 291 min, 7 modules. uid: `learn.wwl.build-first-machine-operations-workflow`. Learn the full MLOps lifecycle for machine learning models, from experimentation and pipeline automation to CI/CD, automated testing, and model deployment in production.
- **[Optimize DevOps with AI agents on Azure](https://learn.microsoft.com/en-us/training/paths/optimize-devops-ai-agents-azure/)** — Intermediate, 671 min, 7 modules. uid: `learn.wwl.optimize-devops-ai-agents-azure`. Learn the concepts of agentic DevOps. Next, learn how to use GitHub Copilot, Azure DevOps MCP Server, and Azure SRE Agent to accelerate delivery, automate operations, and improve reliability across your DevOps workflows.
- **[Perform code maintenance tasks using GitHub Copilot Agent](https://learn.microsoft.com/en-us/training/paths/perform-code-maintenance-tasks-github-copilot-agent/)** — Intermediate, 481 min, 6 modules. uid: `learn.wwl.perform-code-maintenance-tasks-github-copilot-agent`. Learn how to accelerate common code maintenance tasks using GitHub Copilot Agent. This training covers how to resolve issues quickly and accurately by using GitHub Copilot Agent to refactor code in a Visual Studio Code environment.
- **[Remote development with Visual Studio Code](https://learn.microsoft.com/en-us/training/paths/remote-development-vs-code/)** — Beginner, 139 min, 6 modules. uid: `learn.remote-development-vs-code`. Remote development provides benefits like consistent environments, the ability to use more powerful hardware, and the flexibility to develop on different platforms without impacting your local machine. Visual Studio Code provides tools for various remote development setups, such as using a container, a remote machine, or the Windows Subsystem for Linux (WSL). In this path, you'll learn about the different remote development offerings available in Visual Studio Code and practice using them.
- **[Understand ASP.NET Core fundamentals](https://learn.microsoft.com/en-us/training/paths/aspnet-core-fundamentals/)** — Intermediate, 122 min, 5 modules. uid: `learn.aspnet-core-fundamentals`. Learn the fundamentals of building web applications with ASP.NET Core. This learning path teaches the basics required for front-end and back-end development with ASP.NET Core.
- **[Use advanced formula techniques and custom updates in Power Platform](https://learn.microsoft.com/en-us/training/paths/understand-advanced-topics/)** — Advanced, 220 min, 5 modules. uid: `learn-bizapps.understand-advanced-topics`. Do you want to use formulas in a more advanced way? This learning path will help you use advanced formulas and perform custom updates.
- **[Work with variable data in C# console applications (Get started with C#, Part 4)](https://learn.microsoft.com/en-us/training/paths/get-started-c-sharp-part-4/)** — Beginner, 381 min, 7 modules. uid: `learn.wwl.get-started-c-sharp-part-4`. Work with variable data in C# console applications (Get started with C#, Part 4)

---

## Structure not retrieved (catalog data only)

*None. All 51 targeted modules in the "directly relevant" set resolved successfully on first fetch (no 404s or failures encountered).*
