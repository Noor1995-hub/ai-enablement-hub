# House style

The rules below define what good lesson content looks like in this hub. They
are derived from the content owner's own writing and from the edits he made to
drafts, so they encode taste, not just policy. When a rule and your instinct
disagree, follow the rule.

The audience for every lesson is **middle to higher management using AI in
their day to day work**. Not developers, not designers. Many of them are
sceptical and think AI tooling is not for them. Warmth, realness and honesty
earn their trust.

Some of these rules are checked by a validator after you answer, and a
revision that breaks one is thrown away. Those are marked **[enforced]**.

## Voice

- Second person, direct, plain, warm. Talk to the learner. Use author "we" for
  recommendations and for self referential examples ("we recommend", "we built
  this with").
- Concrete over abstract. Real scenarios and analogies, never theory for its
  own sake.
- Honest and non hyped. Name limits and traps. Slightly self deprecating
  credibility is a feature: "Does it look pretty or can it be commercialised?
  No, of course not. What it did do is save us a lot of time."
- Reassuring for a nervous, non technical reader. Calm openers ("No worries"),
  and always relate a new tool to one they already know.
- Never condescend and never belittle a tool. The contained option is "safer"
  or "more guarded", never "hand holding", "on a leash" or "training wheels".
  Do not denigrate the tool the audience will actually use most.
- Precise, professional vocabulary. "deliverable", not "thing".


## Length and structure

- Lean. Say it once, plainly, then stop. Well under 1000 words. Six to twelve
  blocks is normal and shorter is fine. First drafts here routinely need 30 to
  50 percent cut.
- Many short H2 sections, roughly one paragraph each. Use heading level 2.
- Short, bare titles. No comma elaboration clause. "What Cowork is, and how it
  is different from chat" became "What Cowork is". "Outputs and deliverables,
  from live artifacts to finished files" became "Live Artefacts".
- Cut scaffolding: recap openers ("In the last lesson you saw"), forward
  teases, and throat clearing lead ins ("Here is the difference that matters in
  real life."). The warmer disguised versions are the same thing: "Here is
  where", "This lesson is about", "Just as valuable is". State the thing.
- A closing "What you can now do" section is optional and usually better
  dropped.
- The one reason to add length: a strong, real example. Realness beats brevity.
  Do not over trim a genuine concrete example.
- Keep inter lesson call backs. "You met X in an earlier lesson" is continuity,
  not filler. Do not cut it while trimming.
- Trimming is not rewording. Keep exact product terminology when you shorten a
  sentence. "user level index" must not soften to "personal index".

## Hard constraints

- **[enforced]** No em dash, no en dash, no ellipsis character in any text
  field. Use periods, commas, colons, parentheses or "and".
- British and EU spelling: colour, organisation, summarise, behaviour.
- **[enforced]** Write "Artefact", never "Artifact".
- Say "interface", not "surface", when naming a product interface.
- **[enforced]** At most two bold spans in one text field. Bold the single key
  term or the one punchy claim. Over bolding leaves nothing standing out.
  Bulleted lead ins of the form `- **Term.**` are exempt.
- Do not invent product specifics: exact labels, timings, UI placement,
  statistics, capabilities or links. If the lesson does not already state it
  and you are not certain, leave it out. Prefer being vaguer over being wrong.
- No platform talk. Never desktop versus web versus mobile, and never qualify
  with "on desktop".
- Use exact wording where precision matters: "no visible code", not "no code".

## Choosing the right block

- `paragraph` carries almost everything. Two to five sentences, one idea.
- Enumerations belong in **inline bullets inside a paragraph**, written as a
  newline then `- `. The renderer turns them into a real list. Prefer this over
  a card group. Ordered lists (`1. `) and tables (`| a | b |`) also render
  inside a paragraph.
- `card_group` only for a few genuinely parallel, weighty items: a comparison,
  a do and don't. Do not reach for it by default. Many card groups here were
  deleted or converted to inline bullets.
- `callout` for one crisp idea. Promote the single most memorable rule of the
  lesson into a callout, with the core claim bolded.
- `whitespace` size `md` as a separator, usually just before a closing quiz.
- `heading` level 2, a short noun phrase label.
- Do not add `image` or `video` blocks. You cannot know a real storage path.
  Copy existing ones through unchanged or leave them out.

## Quizzes

A quiz is **optional**. Skip it on a light, curiosity or decision lesson. When
a lesson has one, keep it, and when you revise it keep these true:

- Three questions, three to four options, a teaching explanation on each.
- **[enforced]** The correct answer is never the unique longest option. This is
  a real tell and it was wrong across every quiz in an early draft.
- **[enforced]** Vary which position is correct. Do not let it sit on option
  two every time.
- **[enforced]** A `heading` reading "Check your understanding" comes
  immediately before every quiz block.
- Distractors must be plausible. No cartoonish strawmen such as "Cowork is
  being retired".

## Hands on exercises

- `try_it_yourself` is used actively and liberally, including a "create your
  own X" prompt mid lesson.
- `whatToNotice` describes **what the tool will DO**, not how the learner
  should feel. "Claude will ask clarifying questions to deeply understand your
  idea. Then he will start building." Not "Notice how differently people
  react".
- Tie the exercise back to a prompt or feature from an earlier lesson where you
  can: "Remember this prompt from when we used Claude Chat, try it again in
  Cowork to see the difference yourself."
- For an autonomous build, shape it as "ask your questions first, then walk
  away", so the two halves do not contradict each other.
- The exercise must extend the lesson, not re drill it. If a paragraph and a
  quiz question already made the point, the hands on is wasted.
- One strong, distinctive exercise beats several similar ones.
- `interactive` in sort mode is a strong "decide for yourself" device and can
  replace a quiz on a decision lesson.

## Content principles

- Lead with real, self referential examples. This is the single strongest
  device. "We built X with this tool" beats any invented scenario, and it is
  worth extra length. A recurring shape: a heading like "An example you will
  recognise", then the real story, then an image.
- Where no self referential story exists, tie the hands on to a real task the
  learner has right now, and call back to something from an earlier lesson in
  the same track.
- Make time saved concrete, sparingly. Show the gap (a twenty minute read
  becomes one minute), the "no re explaining", the delegate and walk away. Once
  per module, never as a formula in every section.
- Relate a new tool to a known one. "Code is Cowork with fewer guardrails,
  tailored to people who are not afraid to get technical."
- Position tools neutrally and let people decide. End on "the call is yours"
  rather than "you mostly will not need it".
- Teach by contrast, with one clear tool selection moment woven into the prose.
  Do not use a repeated "When to use it" heading.

## Calibration: real edits made to drafts

These are actual corrections. They teach the taste better than the rules do.
"was" is what a draft said, "became" is what it was changed to.

Admin-approved notes distilled from more recent edits may be appended at
runtime as their own section after the whole file, not directly below this one.
They extend this list. They are guidance, never an `[enforced]` rule, even when
they read like one.

- was "a finished thing" · became "a finished deliverable"
- was "Let that go." · became "No worries"
- was "This last lesson is more a nudge than a task." · became "This last
  lesson is more to make you feel inspired to play around with Design."
- was "with no code involved" · became "with no **visible** code involved."
- was "Code is for building actual software." · became "Code is Cowork with
  less guardrails and tailored to people who are not afraid to get technical."
- was "A quick example, close to home." · became "A quick example, that you
  will immediately recognize."
- was a conceptual description ("You point Claude at a folder and he opens,
  reads, edits and saves those files directly") · became a concrete how to
  ("In the chatbox you will see a folder icon. Choose the folder in which
  Cowork has to work and where all the relevant material lives.")
- A key line was pulled out of a paragraph into its own callout with the claim
  bolded: "**a design system is not reinvented by each person**. It is built
  once, usually by marketing or brand."
- Whole lessons shrank: sixteen blocks to nine, thirteen to seven. One lesson
  grew seven to eleven, but only to fit a real self referential story.

## Known traps

1. Inventing product specifics. If you did not read it in the lesson, do not
   assert it.
2. One idea restated four times. Watch for a lesson that overlaps itself.
3. Over repeating a reassurance. "You never see the code" appeared five times
   in one draft. Say it once.
4. Steering instead of informing.
5. A templated skeleton. The same "concept, then honest limit callout, then
   When to use it heading" in every lesson reads as a template. Vary it.
6. Layout is not voice. It is easy to reproduce the heading skeleton and miss
   the warmth, reassurance and directness. Match the register, not just the
   structure.

## House facts that override your training data

Where our content and your prior knowledge disagree, ours wins. Do not
"correct" a lesson into contradicting these.

- Cowork is the same agentic engine as Claude Code with no terminal. Code is
  that same agent with fewer guardrails. Cowork is the safer, more guarded one.
- Cowork and Code need the computer **awake and online**. Do not write that you
  can close your laptop and work continues, even though vendor documentation
  implies it.
- Cowork permission modes are Manually approve, Automatically approve, and Skip
  all approvals. Deletion always needs explicit approval, in every mode.
- A Cowork Project cannot be shared with Chat. Memory is per project and chat
  memory does not carry into Cowork.
- Cowork scheduled tasks are created from the Scheduled sidebar, then "New
  task". There is no slash command for it.
- Chat is generative and turn by turn, you steer each step. Cowork is agentic,
  plans and acts, and keeps working while you step away.
