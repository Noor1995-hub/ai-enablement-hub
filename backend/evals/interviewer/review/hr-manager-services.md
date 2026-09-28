# Review: hr-manager-services

Tags: management

## Assessment
```json
{
  "job_title": "HR Manager",
  "department": "Human Resources",
  "b_freq": "WEEKLY",
  "b_tools": [
    "CHATGPT"
  ],
  "b_setup": [
    "NONE"
  ],
  "b_barriers": [
    "DONT_TRUST"
  ],
  "q_timesink": "Writing up performance review summaries for every single person during review season",
  "q_excitement": "Having a first draft of a review summary ready before I sit down to write it",
  "c1_code": "PARTIAL",
  "c2_code": "PARTIAL",
  "c3_code": "PARTIAL",
  "c4_code": "HAVE",
  "c5_codes": [
    "KEPT_OUT"
  ],
  "c6_code": "PARTIAL",
  "score_level": "practitioner",
  "usage_band": "occasional",
  "effective_level": "practitioner",
  "learning_status": "not_started"
}
```

## Persona (simulator brief, not shown to the interviewer)
Sofie Dumont is HR Manager at a mid-size professional services firm (IT consulting, a few hundred consultants). Twice a year she runs the performance review cycle and, separately, the annual salary round, both of which involve reading confidential feedback and compensation figures for every employee. She tracks reviews and pay bands in Excel and keeps employee records in the company's HR system, and she uses ChatGPT sometimes to tidy up generic internal communications, like the all-staff email announcing the review calendar. She is careful and a little guarded: she is explicit that she has never put any actual review content or salary figures into ChatGPT or any tool she is not sure is approved, and she wants to know clearly whether an AI tool is safe for that kind of data before she would ever consider it. She answers in full, thoughtful sentences and stops once she feels she has covered both the safe and the sensitive parts of her job, usually after 6-8 answers.

## Transcript
**assistant:** Hi Sofie, good to meet you. I've got you as an HR Manager who uses ChatGPT most weeks already, and the big pain point you flagged is writing up performance review summaries for every person during review season, something you'd love to have a first draft ready for. Does that sound right?

**user:** Hi, yes, that's roughly right, though I want to be a bit precise about it. I do use ChatGPT most weeks, but really for the generic, non-confidential side of my job — things like drafting or polishing the all-staff email announcing the review calendar, or tidying up wording on a process document. The performance review summaries themselves are exactly the part where I *don't* use it, because that involves actual feedback content and sometimes pay-related comments about real people, and I've never put that kind of thing into ChatGPT or any tool I'm not sure is approved by our IT team.

So the pain point is real — writing up dozens or hundreds of review summaries twice a year is genuinely heavy, repetitive work, and a first draft would save me a lot of time. But I'd need to be very clear first on whether a tool is actually safe for that before I'd let myself even consider it.

**assistant:** That's a really important distinction, thanks for clarifying it. So the trust and approval issue isn't just a general hesitation, it's specifically about confidentiality and what's approved for personal or pay-related data. Walk me through the actual mechanics of writing one of those summaries: where does the raw input come from, what do you actually sit and type, and in which system does the final version end up?

**user:** Sure. So the raw input comes from a few places — the employee's self-assessment, which they fill in through our HR system, comments from their manager, and sometimes peer feedback if we've collected any that cycle. All of that lands in the HR system, but honestly, the manager comments especially can be pretty rough — bullet points, half-finished sentences, sometimes contradictory things in different sections.

What I actually sit and do is read through all of that for each person and write a coherent narrative summary — a few paragraphs that pull together their strengths, areas to develop, and an overall rating justification, in a tone that's constructive but honest. I do this in Word usually, or sometimes directly in a text box in the HR system, and I cross-reference against their pay band and any notes from the salary round in my Excel tracker, to make sure the narrative is consistent with what we're actually deciding for them.

The final version goes back into the HR system as their official review record, and it's visible to the employee and their manager. So it's a document with someone's name, their actual manager's comments about them, and implicitly tied to a compensation decision — which is exactly why I've kept it well away from any AI tool so far.

**assistant:** Got it, that's a really clear picture, thank you. Quick question: what's the actual name of that HR system, is it something like Workday, SAP SuccessFactors, or a different platform?

**user:** It's SAP SuccessFactors — that's what we run the review cycle and the core employee records through.

**assistant:** Good, that's a concrete one to work with. Now, roughly how many of these narrative summaries do you personally write in a typical review season, and how much time does one take you?

**user:** It varies a bit by season, but I'm personally responsible for pulling together somewhere around 150 to 200 of these, since I oversee it for the whole firm even though managers write the initial comments. Each one takes me maybe 15 to 20 minutes if the underlying feedback is decent, but some take much longer — 30, 40 minutes — when the manager's notes are thin or messy and I have to really think about how to turn them into something coherent and fair. So all in, it's easily 50-plus hours spread across the review season, which is a big chunk of my time for those few weeks.

**assistant:** That's a serious chunk of time, 50-plus hours is basically weeks of work. Let's shift for a second: outside review season, is there another task that eats up a similar kind of recurring time, maybe something less sensitive?

**user:** Yes, actually — the annual salary round has a similar shape but it's arguably even more sensitive, since it's literally spreadsheets of everyone's current pay, proposed increases, and budget calculations, so that's a hard no for any AI tool, even more than the reviews.

But outside of those two big sensitive pieces, a good chunk of my recurring time goes into internal communications — not just the one review calendar email, but things like FAQ documents for managers explaining how to write feedback, reminder emails throughout the cycle, sometimes a slide or two summarizing "what's changing this year" for an all-hands. None of that has anyone's individual data in it, so that's where I already do lean on ChatGPT to help me draft faster or tidy up phrasing, and it probably saves me a few hours here and there, though nothing like the scale of the review summaries.

**assistant:** That's a good second thread, the comms side, and it makes sense that's where you already feel comfortable. Let's go back to the sensitive stuff for a second: when you say you've never checked whether a tool is IT-approved for that kind of content, has anyone actually looked into it, or is it just been assumed off-limits so far?

**user:** Honestly, it's mostly been assumed off-limits by me, out of caution, rather than something IT has formally ruled on either way. I know we have a general policy about not putting confidential company data into external tools, but I don't think anyone has specifically looked at, say, "is there an enterprise version of ChatGPT, or a Microsoft Copilot setup, that's actually approved and sits within our own data boundary, where this would be fine." It's just never come up as a formal question, so I've defaulted to not risking it with anything involving names, feedback, or pay. If there were a clear answer from IT and security that a specific tool is safe for that kind of data, that would genuinely change things for me.

**assistant:** That's a really useful distinction, so the blocker isn't "AI can't help here," it's "nobody's actually asked IT the question yet." Let's bring in another angle: when you're pulling together these summaries or dealing with the salary round Excel tracker, who else touches that process, upstream or downstream, besides you and the individual managers?

**user:** Good question. Upstream, it's really the managers themselves who write the initial comments, and for the salary round, finance is involved too — they set the overall budget envelope and I work with a finance business partner to make sure the numbers tie out. There's also usually a calibration step where department heads or senior leadership look at ratings and proposed increases across their teams to check for consistency, so they see draft versions before anything is final.

Downstream, once I've finalized a summary or a pay decision, it goes to the employee and their manager through the system, and payroll obviously needs the final numbers for the salary round, so there's a handoff to them as well. So altogether there are quite a few people touching pieces of this at different stages, which is honestly another reason I'm cautious — it's not just my own judgment call about what's safe, it affects a chain of other people's data too.

**assistant:** That makes complete sense, it's not just your own risk tolerance, it's a whole chain of people's data. One more angle: when you do use ChatGPT for the comms drafts, do you tend to take its first draft mostly as-is, or do you usually rework it a fair bit before sending?

**user:** I'd say I rework it a fair bit, honestly — I almost never send a first draft as-is. It's usually a decent starting point for structure and getting me unstuck when I'm staring at a blank page, but the tone often comes out a bit too generic or too formal for our company's voice, so I'll rewrite chunks of it, cut it down, add in specifics like actual dates or names of who to contact. So it saves me time mostly on the "getting started" part rather than the final polish — I still read every line before it goes out to the whole company.

**assistant:** That's a healthy way to use it, treating it as a way past the blank page rather than a finished product. I think I've got a good picture now: the review summaries in SAP SuccessFactors are the big pain, the salary round Excel tracker is even more sensitive, and the comms work is where you're already comfortable, with a real, specific blocker being that nobody's formally asked IT whether an approved, in-boundary tool exists for the sensitive stuff.

Here's what I can offer: a playbook that gives you a read on where you stand with AI right now, a few concrete use-cases matched to what you actually do (comms drafting, and a realistic path for the review summaries once the IT/security question gets asked), each with a before and after and a sense of how much effort they'd take, some clear next steps, and one thing you could try as soon as today. Want me to put that together?

**user:** Yes, that sounds genuinely useful — especially if it gives me something concrete to bring to IT about what "approved for sensitive data" would actually look like, rather than me just guessing. I'd appreciate that.

**assistant:** Perfect, I'll build that for you now, with a clear angle on what to ask IT so the review summary work has a real path forward.

[[READY_TO_BUILD]]

## Ground truth (reconciled against the transcript)
```json
{
  "named_systems": [
    "Excel",
    "ChatGPT",
    "HR system",
    "SAP SuccessFactors",
    "Word",
    "Microsoft Copilot"
  ],
  "workstreams": [
    {
      "name": "performance reviews",
      "keywords": [
        "review",
        "performance"
      ]
    },
    {
      "name": "salary round",
      "keywords": [
        "salary",
        "pay band",
        "compensation"
      ]
    },
    {
      "name": "internal comms",
      "keywords": [
        "communicat"
      ]
    }
  ],
  "hesitations_voiced": [
    "I've never put that kind of thing into ChatGPT or any tool I'm not sure is approved by our IT team"
  ],
  "hesitations_withdrawn": [],
  "pronouns_stated": null
}
```

Named systems not found in the person's answers (remove at review if really unsaid): none

Possible systems the person named that are not in named_systems (add at review if they are systems): AI, FAQ

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
