### Lesson 2.2: Grounding Copilot on Your Organisation's Data

#### 1\. Defining Grounding: Moving Beyond General Knowledge

Grounding is the architectural bridge that transforms a general-purpose AI into a specialized enterprise asset. Its strategic value lies in anchoring every response within the unique reality of your business data. Rather than generating answers from a static training set, a grounded AI generates insights directly from your internal records, ensuring the output is contextually relevant and factually aligned with current operations.This process is governed by the  **Work IQ**  layer, which utilizes the  **Microsoft Graph**  to interpret organizational context. Beyond simply reading the content of a file, the Graph identifies the  **metadata of the relationship** —understanding the significance of a document based on who you collaborate with most, which meetings you attend, and which collaboration patterns define your current workstreams.

##### The Grounding Principle

Effective grounding is defined by two fundamental pillars:

* **Data Specificity:**  Copilot prioritizes the user's personal context, drawing from specific files, emails, and meetings. However, practitioners must account for structural limitations: grounding currently respects a  **2-level URL depth limit** . This means Copilot can typically only traverse two levels deep into a SharePoint or web structure to retrieve and index information.  
* **Permission Safety:**  Security is built into the architecture through permission-aware indexing. Copilot strictly adheres to existing Microsoft 365 Access Control Lists (ACLs). It cannot retrieve or reference any information that the user does not already have explicit permission to access, maintaining robust data boundaries.

##### Evaluation of Impact

Grounding replaces generic "AI fluff" with factual organizational truth. While a standard model might offer a generic template for a project update, a grounded Copilot synthesizes current progress reports and communications. This shift ensures the output supports high-stakes decision-making. While ad-hoc grounding is effective for one-off tasks, complex deliverables often require the persistent, noise-free environment of a Notebook.

#### 2\. Notebooks: Scoped Workspaces for Project Focus

Notebooks provide a "project-scoped grounding workspace" designed for sustained intellectual labor. Strategically, they offer a persistent environment for complex deliverables, ensuring the AI remains focused on a specific set of parameters over multiple sessions. Unlike a standard chat, which can become cluttered with unrelated queries, a Notebook acts as an isolated sandbox for a particular mission.A critical functional advantage of Notebooks is the prevention of  **Context Rot** . In standard chats, output quality degrades as the "Context Window" fills. When usage reaches the 65% "rotation point" or the 80% "auto-compaction zone," the AI may lose focus or struggle with detailed logic. Notebooks allow practitioners to stay within the  **"Healthy Zone"**  by maintaining a focused document set and preventing the AI from getting overwhelmed by the broader Graph noise.

##### Comparison: Ad-hoc Grounding vs. Notebooks

Feature,Ad-hoc Grounding,Notebooks  
Context Longevity,Fleeting; session-based interaction.,Persistent; stays locked to the project lifecycle.  
Data Scope,Broad access to all permitted Graph data.,Curated Environment  to exclude irrelevant Graph noise.  
Context Window,"High risk of ""Context Rot"" (80% compaction).","Optimized to stay in the ""Healthy Zone."""  
Primary Use Case,"Quick drafting, inbox triage, or simple queries.",Complex reports and long-term project synthesis.

##### Usage Guidance

Practitioners should transition to a Notebook when a task evolves from a simple query into a dedicated workstream. If a project requires constant reference to a specific group of strategy documents or budget files across several days, the isolated environment of a Notebook ensures the highest accuracy and logic retention. Within these workspaces, users can deploy specialized agents to handle different phases of the project.

#### 3\. The Researcher Agent: Synthesizing Information

The Researcher agent is the primary tool for the "discovery" phase, acting as a filter for organizational knowledge. Its strategic role is to eliminate "search fatigue" by identifying and consolidating relevant information that would otherwise require manual hunting through disparate SharePoint folders and email threads.

##### Core Capability

The Researcher’s function is the presence and synthesis of information across the organization. It "connects the dots" between multiple files to provide a cohesive summary of where a project stands. Unlike simple search, it interprets the contents of these sources to identify themes and relationships.

##### Concrete Scenario: Project Red Stapler Status

In a practical setting, a practitioner might use the Researcher to summarize a complex internal initiative. For example: "Summarize the current status of  **Project Red Stapler** , identifying key risks mentioned by team members and any upcoming deadlines from the last three months of status reports." The Researcher scans the relevant communications and files to produce a unified briefing, identifying specific concerns such as  **schedule variance**  while citing the source documents.While the Researcher excels at finding and summarizing information, evaluating the logic or financial data within those files requires the reasoning power of the Analyst.

#### 4\. The Analyst Agent: Reasoning Over Data

The Analyst agent is designed for deep reasoning and evaluation, providing critical decision support. While the Researcher confirms  *what*  information exists, the Analyst explains  *what it means* . It is the essential agent for moving from information gathering to the finalization of high-stakes deliverables.

##### Core Capability

The Analyst performs deep logical reasoning over specific data sets, such as spreadsheets or technical reports. It excels at performing calculations, identifying trends, and providing commentary on variances. Its focus is on the internal logic of the files rather than just the presence of keywords.

##### Evaluation and Impact

The Analyst's impact is highest when comparing complex datasets or validating financial logic. It can look inside a budget file to explain  *why*  a specific project is overspent, identifying the underlying reasoning rather than just noting that the figures exist.

##### Concrete Scenario: Budget Variance and Strategy Logic

A powerful application for the Analyst is evaluating financial performance or product strategy. For instance, a practitioner can task the Analyst with reasoning over a  **DG2000 Marketing Strategy**  or a budget spreadsheet to identify specific  **budget overspend**  patterns. The Analyst will analyze the figures, compare them against the forecast, and provide detailed commentary on the logic behind the shifts in expenditure.By combining grounding, the persistent structure of Notebooks, and specialized agents, the Practitioner can produce high-value work that is deeply anchored in organizational reality. Transitioning to Lesson 2.3, we will explore how to further personalize these interactions through Custom Instructions.  
