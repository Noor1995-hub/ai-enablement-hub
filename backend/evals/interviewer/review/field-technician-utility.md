# Review: field-technician-utility

Tags: operational

## Assessment
```json
{
  "job_title": "Field Technician",
  "department": "Network Maintenance",
  "b_freq": "NEVER",
  "b_tools": [
    "NONE_YET"
  ],
  "b_setup": [
    "NONE"
  ],
  "b_barriers": [
    "NO_ACCESS",
    "DONT_SEE"
  ],
  "q_timesink": "Writing up the inspection report back at the depot after a full day on site",
  "q_excitement": "Can't really picture where AI would fit into what I do",
  "c1_code": "MISSING",
  "c2_code": "MISSING",
  "c3_code": "MISSING",
  "c4_code": "MISSING",
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
Dries Van Hoof is a Field Technician at a regional electricity network operator. Most of his week is spent on-site doing inspections and repairs on substations and lines, and he only sits at a desk briefly at the end of the day to write up the inspection report and check Outlook for the next day's job list. He does not see an obvious place for AI in his actual work, since the job is mostly physical and hands-on, and says so honestly rather than forcing an answer. He is straightforward and practical, gives clear but brief descriptions of his day, and stops once he has walked through a typical day, usually after 5-6 answers.

## Transcript
**assistant:** Hi Dries, good to meet you. From what I've got, you're a Field Technician in Network Maintenance, haven't really used AI tools yet, and the thing that eats your time is writing up the inspection report back at the depot after a full day on site. Sound about right?

**user:** Yeah, that's about right. Most of my day is out on site, and it's only at the end of it that I sit down and write everything up. That report writing does take a chunk of time, honestly - more than people probably think.

**assistant:** That makes sense, that gap between doing the work and documenting it always costs more than it looks like. Walk me through it, when you sit down at the depot, what are you actually working from, like notes, photos, memory?

**user:** It's a mix, really. I usually scribble notes on a pad while I'm out there - condition of the equipment, anything unusual, readings if I take any. I take photos too, especially if there's damage or something that needs follow-up. But a fair bit is just memory by the time I'm back at the depot, which isn't ideal if it's been a long day with multiple sites.

**assistant:** That's a real gap, relying on memory after multiple sites in one day. When you actually sit down to write it up, what system or format does that report go into, is it a form on a computer, a template in Word, something else?

**user:** It's a form on the computer, in our maintenance system. There's set fields for each inspection type - condition ratings, comments, that sort of thing. So I'm going through my notes and photos and typing it all into the right boxes, basically translating my own shorthand into proper sentences.

**assistant:** Good, now I know the system. What's it called, do you know the name of that maintenance system?

**user:** I think it's called Maximo, that's what everyone calls it anyway. Not sure if that's the full official name.

**assistant:** Good, Maximo, that's useful. Now let's think about frequency, roughly how many sites do you visit on a typical day, and how long does that whole write-up session at the depot take you?

**user:** Depends on the day. Usually it's anywhere from two to five sites, more if they're quick checks, fewer if there's actual repair work involved. The write-up at the end can take anywhere from half an hour to a good hour and a half, depending how much there is to put in.

**assistant:** That's a real chunk of the day, potentially. Let's shift a bit, is there anything else in your week, besides the report writing, that eats up time or annoys you, even something small?

**user:** Not really, no. Most of the rest of the week is just the actual work - driving between sites, doing the inspections and repairs. That's the job, I don't mind that. It's really just the paperwork at the end of the day that drags.

**assistant:** Fair enough, that tracks with a job that's mostly hands-on. Let's talk about the photos you take on site, what happens to them, do they get uploaded into Maximo too, or somewhere else?

**user:** They go into Maximo as well, attached to the relevant job. I just upload them from my phone when I'm doing the write-up, pick out the ones that are relevant.

**assistant:** Good to know, so it's all funnelling into one place. Now, when you're stuck on a tricky inspection or repair, is there anyone you call or check with, like a supervisor, another technician, a manual?

Powered by an open-source AI model

**user:** Usually I'd call one of the senior technicians or my supervisor if it's something out of the ordinary. There's also manuals and spec sheets back at the depot, but honestly it's quicker just to ring someone who's seen it before.

**assistant:** Good, that's useful, so there's a real network of people you lean on. Given all this, if you imagine some tool that could make any part of your day easier, even something small, what comes to mind, even a rough idea?

**user:** Honestly, the thing that'd help most is something that could turn my notes and photos into that report automatically, or at least most of it, so I'm not typing it all out from scratch every evening. That's really the only bit of the day where I think "there's got to be a better way." The rest of it, the actual fieldwork, I don't see AI coming into that much - it's hands-on, you need to be there looking at the equipment yourself.

**assistant:** That's a clear and grounded idea, and it lines up exactly with the pain you described. Just to check on access, do you have a phone or laptop on you during the day that you could use for something like that, or is everything strictly pen and paper until you're back at the depot?

**user:** I've got a work phone on me, that's what I use for the photos. I could probably use it for notes too, but I've just always done the pad and pen thing, it's quicker when you're up a pole or in a substation with gloves on.

**assistant:** That's a really practical constraint, gloves and a pole don't mix well with typing. Have you or anyone on your team ever tried using voice memos or dictation on the phone instead of the pad, even once?

**user:** No, never tried it myself. Can't say I've heard the other lads talk about it either. Might be worth a go, but like I said, when you're in the middle of a job it's just easier to jot it down quick than mess about with the phone.

**assistant:** That makes sense as a real-world constraint, not just habit. I think I've got a good picture now, one thing that would still sharpen this is understanding a bit more about the "no access to AI tools" barrier you mentioned in your assessment, is that about company policy blocking things, or more that nobody's ever given you a tool to try?

**user:** It's more that nobody's ever given us anything to try. I don't think there's a policy against it, it's just never come up - nobody's put a tool in front of me and said "use this." So it's less about being blocked and more that it's just not part of the picture out here.

**assistant:** That's a helpful distinction, it means the door isn't shut, it's just never been opened. I think I've got what I need: a clear picture of your day, Maximo as the system where everything lands, the report write-up as the real time-sink with a rough half hour to ninety minutes per day, a second minor thread around leaning on senior technicians and manuals when something's unusual, your own idea about notes and photos turning into a report automatically, and the honest constraint that gloves and poles don't mix with typing.

Here's what I'd suggest: let me build you a playbook that gives you a read on where you stand with AI right now, a few practical use-cases matched to your actual work and Maximo, each with a before and after and a sense of how much effort they'd take to try, some clear next steps, and one small thing you could experiment with today, like testing voice notes on a couple of quick jobs. Sound good?

[[READY_TO_BUILD]]

## Ground truth (reconciled against the transcript)
```json
{
  "named_systems": [
    "Maximo",
    "maintenance system"
  ],
  "workstreams": [
    {
      "name": "inspection reporting",
      "keywords": [
        "report",
        "write-up",
        "paperwork"
      ]
    }
  ],
  "hesitations_voiced": [
    "the actual fieldwork, I don't see AI coming into that much - it's hands-on, you need to be there looking at the equipment yourself",
    "when you're in the middle of a job it's just easier to jot it down quick than mess about with the phone"
  ],
  "hesitations_withdrawn": [],
  "pronouns_stated": null
}
```

Named systems not found in the person's answers (remove at review if really unsaid): none

Possible systems the person named that are not in named_systems (add at review if they are systems): AI

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
