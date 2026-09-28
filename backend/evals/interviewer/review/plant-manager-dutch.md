# Review: plant-manager-dutch

Tags: language

## Assessment
```json
{
  "job_title": "Plant Manager",
  "department": "Production",
  "b_freq": "WEEKLY",
  "b_tools": [
    "COPILOT"
  ],
  "b_setup": [
    "NONE"
  ],
  "b_barriers": [
    "NO_TIME"
  ],
  "q_timesink": "Consolideren van shift reports voor de wekelijkse productie-meeting, elke week opnieuw",
  "q_excitement": "Minder tijd kwijt aan het overtypen van dezelfde shift cijfers in Excel",
  "c1_code": "PARTIAL",
  "c2_code": "PARTIAL",
  "c3_code": "PARTIAL",
  "c4_code": "HAVE",
  "c5_codes": [
    "APPROVED_PASTE"
  ],
  "c6_code": "PARTIAL",
  "score_level": "practitioner",
  "usage_band": "occasional",
  "effective_level": "practitioner",
  "learning_status": "not_started"
}
```

## Persona (simulator brief, not shown to the interviewer)
Hendrik De Wilde is Plant Manager at a food production site (ready meals, three shifts). He mostly answers in English but slips into Dutch mid-sentence when he is being precise or a bit frustrated, saying things like 'eigenlijk is het gewoon' before switching back, and once or twice answers a whole question mostly in Dutch before returning to English. He tracks shift output in SAP and consolidates the numbers into Excel every week for the production meeting. He is direct and a little impatient about repetitive work, describes his real week concretely regardless of which language he is using at that moment, and stops once he has covered his main tasks, typically after 6-7 answers.

## Transcript
**assistant:** Hi Hendrik, good to have you here. From your assessment, I've got you as a Plant Manager in Production, using Copilot most weeks, and your biggest time-sink is consolidating shift reports for the weekly production meeting, retyping the same shift numbers into Excel each week. Does that still sound right?

**user:** Ja, that's right. Every week, same story. I pull the numbers from SAP — output per line, downtime, waste percentages, all that — and then I have to retype it into my Excel sheet for the meeting. Three shifts, five production lines, so it's a lot of copying numbers by hand. Eigenlijk is het gewoon dom werk, you know, it's not difficult, it just takes time. An hour, sometimes more if something went wrong on a shift and I need to dig into SAP to find out why.

**assistant:** That's a clear one, thanks Hendrik. So walk me through the actual mechanics for a second: when you pull output per line and downtime from SAP, are you looking at a screen and typing what you see, or exporting something and copying from there?

**user:** Both, actually. For the output numbers I export a report from SAP, it comes out as a kind of table, and I copy-paste that part into my Excel. But the downtime reasons and the waste — that I often just read off the screen, because the export doesn't always give me the comments the shift leader typed in. So I have two windows open, SAP and Excel, and I'm typing what I see for the downtime notes. That part is slower, because I have to interpret what the shift leader meant sometimes — hun notities zijn niet altijd duidelijk, so I have to think about how to summarize it.

**assistant:** Interesting, so it's really two different tasks: one is copying numbers, the other is interpreting messy notes. Are those shift leader notes typed into SAP directly, or do they come from somewhere else first, like a paper log or a separate sheet?

**user:** No, they type it directly into SAP, into a free text field, at the end of the shift. But you know how it is — some shift leaders write a full sentence, "line 3 stopped 40 minutes because of a packaging jam, changed the film roll," and others just write "stop, technical." So I have to go back and forth sometimes, ask them on WhatsApp what they meant, if the number looks strange. That's the annoying part, not the typing itself but chasing people for clarification.

**assistant:** That's a good second pain, distinct from the retyping itself: chasing shift leaders for clarification when the notes are too thin. How often does that happen, roughly, out of your five lines across three shifts in a week?

**user:** Eh, maybe five, six times a week that I really have to chase someone. Not every shift, but often enough that it interrupts my day — I'm in a meeting or walking the floor, and I get a WhatsApp back an hour later, and I've already moved on, so I have to come back to it. Some weeks it's worse, if we had a bad week with a lot of downtime, then almost every line has something I need to ask about.

**assistant:** That's a real interruption cost on top of the hour of consolidation. Now, besides you, who actually reads that final consolidated report, is it just for the weekly meeting or does it go further, like to a plant director or quality team?

**user:** It goes to my plant director, and a copy to quality and to the maintenance manager, so they see the downtime reasons too. Mostly it's for the production meeting on Monday, we go through it line by line, but yes, a few other people get it by email after. That's really it, I think, that's my main week — SAP, Excel, chasing people, meeting on Monday.

**assistant:** Good, that gives me the downstream picture: plant director, quality, maintenance manager all reading the same consolidated view. Now let's flip to what you already have in hand: when you use Copilot most weeks, what do you actually use it for, is it inside Excel, Outlook, Word, something else?

**user:** Mostly Outlook, honestly. I use it to help write my summary emails when I send the report out — the little text on top, "this week we had this issue on line 3," that kind of thing. It helps me write it faster and a bit more, eh, professional. I tried it once in Excel for the numbers but it didn't really save me time, the copy-pasting from SAP is still manual, so I mostly just use it for the writing part now.

**assistant:** That's useful, thank you. Given all this, and knowing SAP is where the raw numbers and notes live, what's your own gut feeling on where AI could actually help here, if you imagine it working the way you'd want?

**user:** If it could read the SAP export and the free text notes and just build my Excel table for me — put the numbers in the right cells, and maybe flag which lines have downtime notes that are too vague so I know who to message — that would save me the real time. I don't need it to write my email, I need it to do the boring part first. That's my honest opinion.

**assistant:** That's a sharp, concrete idea, and it also tells me something: you're not looking for AI to write things for you, you want it to handle the mechanical assembly and flag exceptions, which is a more advanced way of thinking about it than most people start with. Given the barrier you mentioned, no time to learn something new, has anyone in IT or elsewhere ever looked at connecting SAP exports to Excel automatically, even before AI comes into it?

**user:** We asked once, maybe two years ago, IT said it needs a proper project, some kind of interface, and it never went anywhere because everyone is busy with other things. Zo gaat dat dan — it's on a list somewhere, I'm sure, but nobody picks it up. I stopped asking, I just do it by hand now. That's honestly my whole week, I think we covered it.

**assistant:** That's a really telling blocker, thanks for being straight about it: not a technical wall exactly, more that it needed a formal IT project and just died on a list. One quick check before I wrap up my picture: today, without waiting on IT, do you have anything like Power Automate, or could you at least drop that SAP export file into Copilot or Excel yourself and ask it to sort rows, without needing permissions you don't have?

**user:** Eh, I don't know, honestly. I have Copilot on my laptop, same as everyone, but Power Automate I've never opened, I don't even know if I have access. That's more an IT question for you than for me. I think that's really my week, hè — SAP, Excel, chasing people, Monday meeting. I don't have much more to add.

**assistant:** Fair enough, that's a good honest answer, and it actually tells me something useful too, that the boundary of what you can reach today is fuzzy even to you.

I think I've got a solid picture now: SAP and Excel by name and what you do in each, the retyping pain as a concrete hour-plus weekly episode, the chasing-shift-leaders pain as a distinct five-to-six-times-a-week interruption, your own clear idea of what AI should actually do (assemble the table, flag vague notes) rather than write text, the dead-end IT blocker, and the downstream readers who'd benefit from a cleaner report too.

Here's what I'd suggest: let me build your playbook from this. You'll get a read on where you stand with AI right now, a few use-case ideas matched to your actual work in SAP and Excel (each with a before and after, and roughly how much effort each takes to get going), some clear next steps, and one thing you could try as soon as tomorrow. Sound good?

[[READY_TO_BUILD]]

## Ground truth (reconciled against the transcript)
```json
{
  "named_systems": [
    "SAP",
    "Excel",
    "Outlook",
    "WhatsApp",
    "Power Automate"
  ],
  "workstreams": [
    {
      "name": "shift reporting",
      "keywords": [
        "shift",
        "shift report"
      ]
    },
    {
      "name": "production meeting prep",
      "keywords": [
        "production meeting"
      ]
    },
    {
      "name": "shift leader clarification chasing",
      "keywords": [
        "chas",
        "WhatsApp"
      ]
    }
  ],
  "hesitations_voiced": [],
  "hesitations_withdrawn": [],
  "pronouns_stated": null
}
```

Named systems not found in the person's answers (remove at review if really unsaid): none

Possible systems the person named that are not in named_systems (add at review if they are systems): none

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
