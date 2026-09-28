# Review: food-safety-coordinator

Tags: operational

## Assessment
```json
{
  "job_title": "Food Safety Coordinator",
  "department": "Quality",
  "b_freq": "NEVER",
  "b_tools": [
    "NONE_YET"
  ],
  "b_setup": [
    "NONE"
  ],
  "b_barriers": [
    "NO_ACCESS",
    "POLICY_RESTRICTS"
  ],
  "q_timesink": "Typing HACCP log entries into the quality system by hand every shift",
  "q_excitement": "Anything that saves me re-typing the same log entries",
  "c1_code": "MISSING",
  "c2_code": "MISSING",
  "c3_code": "MISSING",
  "c4_code": "PARTIAL",
  "c5_codes": [
    "NO_USE"
  ],
  "c6_code": "MISSING",
  "score_level": "explore",
  "usage_band": "dormant",
  "effective_level": "explore",
  "learning_status": "not_started"
}
```

## Persona (simulator brief, not shown to the interviewer)
Nele Peeters is a Food Safety Coordinator at a dairy processing plant. Her PC is locked down and validated, nothing can be installed without IT approval, and she is not sure she is even allowed to open a public AI tool on it. She logs HACCP checks into the quality management system by hand every shift and keeps her own audit-prep notes in Excel, and she describes both in concrete detail when asked. She answers questions carefully and honestly, and when asked what she could realistically start using tomorrow she is doubtful that anything is actually available to her given the IT restrictions, saying so plainly rather than pretending otherwise. She wraps up once she has covered her actual daily tasks, typically after 6-7 answers.

## Transcript
**assistant:** Hi Nele, good to have you here. From your assessment I've got you as a Food Safety Coordinator in Quality, currently not using any AI tools, with the log entry typing into the quality system as your biggest time-sink, is that right?

**user:** Yes, that's right. Every shift I go through the HACCP checkpoints — CCPs, pasteurization temps, cooling times, sanitation verification — and I type each one into the quality management system by hand. It's not complicated work, it's just repetitive, and if something's slightly out of range I have to write a deviation note explaining what happened and what corrective action was taken. That part especially eats time because I have to phrase it carefully so it holds up if an auditor reads it later.

**assistant:** That's a really clear picture, thank you. Quick question first: what's the quality management system called, the one you're typing these into?

**user:** It's called MasterControl — that's the system we log the HACCP checks and deviations into. I don't administer it or anything, I just use the forms IT and QA set up for us.

**assistant:** Good to know, that's a specific one. Before I dig into MasterControl more, where do the raw numbers actually come from first, like the pasteurization temps and cooling times, are they on paper on the floor before they reach you?

**user:** Some of it's automatic — the pasteurizer has a chart recorder and a digital readout that logs temps continuously, so I check that against the printed strip. But cooling times, sanitation checks, things like allergen line clearance, those I still write down on a paper checklist as I walk the floor. Then I go back to the office and transfer everything from the paper sheet and the chart recorder into MasterControl by hand.

**assistant:** Now that makes sense, so paper checklist plus chart recorder readings, then a manual retype into MasterControl. Roughly how long does that transfer step take you, and how many times a shift or a day does it happen?

**user:** I do rounds four times a shift, so four checklists, and each one takes me maybe 15-20 minutes to transfer in — a bit longer if there's a deviation to write up. So call it an hour, hour and a half total per shift just on data entry, on top of the actual walking-the-floor time.

**assistant:** That's a solid chunk of time, an hour to ninety minutes every shift just moving numbers from paper into MasterControl. Let's shift for a second, when a deviation happens and you have to write that corrective action note, walk me through the last time that happened, what triggered it and what you actually typed.

**user:** Last one was maybe two weeks ago — the cooling tank on line 2 was reading a couple degrees above spec on my afternoon round. So I noted the actual temp, the time, then I had to go find the line operator and ask what happened. Turned out a valve hadn't fully closed after a wash cycle. I wrote it up as something like: temp deviation observed at [time], root cause identified as valve X not fully seated after CIP, corrective action taken — valve reseated, product held and retested, temp back in spec by [time], no product released outside parameters. Then I flagged it for my supervisor to countersign. That one took a while because I had to track down the operator first before I could even write the note properly.

**assistant:** That's a great concrete example, thank you. So two separate pains already: the routine paper-to-MasterControl retyping, and the deviation write-up which is slower because it needs the phrasing right AND tracking someone down first. Let's go to a different angle: aside from your supervisor countersigning, who else ever sees or uses what you type into MasterControl?

**user:** QA management pulls reports from it for trend review, and it's what auditors look at when they come through — whether that's a customer audit or a regulatory one like the FDA. So the wording really does matter, because someone outside the plant who has no context is going to read it eventually.

**assistant:** That's an important detail, the audience is often someone with zero floor context. Now, thinking about barriers, your assessment mentioned no access to AI tools and a company policy restricting it, what have you actually tried or heard that led you to believe it's off limits?

**user:** Honestly, nothing's been announced one way or the other — I just know my PC is locked down, IT has to approve any software install, and I've never seen anything about AI tools in our SOPs or policies. So I've assumed it's a no, rather than actually testing it and getting in trouble. I haven't tried opening anything like ChatGPT on my work computer, no.

**assistant:** That's a really useful distinction, an assumed no rather than a tested one. So on your work computer right now, without any new install or IT ticket, what could you actually open, is there a browser, email, anything like that already sitting there unrestricted?

**user:** There is a browser, and I can get to email and our intranet fine. But I genuinely don't know if a site like ChatGPT would even load, or if it's blocked at the network level, or if opening it would flag something with IT. I've never tried, so I couldn't tell you for sure what's realistically usable tomorrow without just testing it or asking IT directly first.

I think that covers the main parts of my day — the rounds, the MasterControl entries, and the deviation write-ups are really the core of what I do. That's probably a good place to stop.

**assistant:** That's a fair place to pause, and it's honest that you haven't tested the water there. I think I've got what I need: two clear pains (the routine paper-to-MasterControl retyping eating an hour to ninety minutes a shift, and the slower deviation write-ups that need careful phrasing plus tracking someone down first), the systems involved (MasterControl, paper checklists, the chart recorder), who reads the output (supervisor, QA management, auditors with no floor context), and the real blocker (an assumed rather than tested policy restriction, plus a locked-down PC).

Here's what I'd suggest: let me put together a playbook that gives you a read on where you stand with AI right now, a few use-cases matched specifically to the rounds, MasterControl entries, and deviation notes you described (each with a before and after, and roughly how much effort each would take to set up), some concrete next steps including how to actually find out what's usable on your current setup, and one small thing you could try as soon as tomorrow. Does that sound useful to build?

[[READY_TO_BUILD]]

## Ground truth (reconciled against the transcript)
```json
{
  "named_systems": [
    "quality management system",
    "MasterControl",
    "ChatGPT"
  ],
  "workstreams": [
    {
      "name": "HACCP logging",
      "keywords": [
        "haccp",
        "log entr"
      ]
    },
    {
      "name": "deviation write-ups",
      "keywords": [
        "deviation"
      ]
    }
  ],
  "hesitations_voiced": [
    "I've assumed it's a no, rather than actually testing it and getting in trouble"
  ],
  "hesitations_withdrawn": [],
  "pronouns_stated": null
}
```

Named systems not found in the person's answers (remove at review if really unsaid): none

Possible systems the person named that are not in named_systems (add at review if they are systems): HACCP, QA, CIP, FDA, PC, AI

Workstreams whose keywords never appear in the person's answers (fix keywords or remove at review): none

Empty learner replies replaced with the placeholder: none

Will build at run time: yes (offer present)

## Checklist before approving
- [ ] No real names, companies or identifying details anywhere above.
- [ ] Every `named_systems` entry was actually said in the transcript.
- [ ] Every system the person named in the transcript is listed in named_systems (add any missing).
- [ ] Every 'possible system' above that really is a system has been added to named_systems (or dismissed as not a system).
- [ ] Every workstream with no keyword hits above has been fixed or removed.
- [ ] The transcript reads like this persona, not a generic interview.
- [ ] The stop point matches the persona's stated stop rule.
- [ ] The 'Will build at run time' line says yes.
