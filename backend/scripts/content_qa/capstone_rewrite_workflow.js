export const meta = {
  name: 'admin-content-qa-capstone-rewrite',
  description: 'Reframe For Developers Capstone stale in-track cross-references to sibling tracks',
  phases: [{ title: 'Rewrite', detail: 'single agent' }],
}

const SCHEMA = {
  type: 'object',
  required: ['text_edits'],
  properties: {
    text_edits: {
      type: 'array',
      items: {
        type: 'object',
        required: ['old_string', 'new_string'],
        properties: {
          old_string: { type: 'string', description: 'exact substring copied verbatim from the lesson' },
          new_string: { type: 'string' },
        },
      },
    },
  },
}

const MAPPING = `
After the 2026-07-20 "For Developers" split, that track holds ONLY this Capstone. The modules it
used to contain moved into sibling tracks the learner takes first:
- GitHub Copilot (the old "Module 1") -> the "Copilot II" track.
- Agentic-engineering habits, spec-driven development, the contributor review model, vibe coding
  (the old "Module 2") -> the "General III" track ("Agentic engineering practices").
- Claude Code (the old "Module 3") -> the "Claude II" track ("Claude Code, in depth").
- Calling the Claude API and model choice / Haiku-Sonnet-Opus (the old "Module 4") -> the
  "Claude II" track ("Building on Claude").
`

const path = (typeof args === 'string' ? JSON.parse(args) : args).path

const result = await agent(
  `Read the module file at: ${path}. It has one lesson: the For Developers Capstone ` +
  `("Guided build: ship something real with Copilot + Claude Code").\n\n` +
  `Its prose refers to "this track", "Module 1/2/3/4", "Spec-driven development earlier in this ` +
  `track", "this track's Module 3", "Module 4's model-choice lesson", "Module 2's contributor ` +
  `model", etc. Those references are now STALE: for a current For Developers learner this track ` +
  `contains only the Capstone, and the referenced material lives in sibling/prerequisite tracks.\n` +
  MAPPING +
  `\nReturn exact-substring text_edits that reword every stale "this track / Module N" reference to ` +
  `name the correct sibling track instead (e.g. "GitHub Copilot in Module 1" -> "GitHub Copilot ` +
  `in the Copilot II track"; "the agentic-engineering habits in Module 2" -> "the ` +
  `agentic-engineering habits from the General III track"). Keep it natural and concise; do not ` +
  `change any other meaning. old_string must be copied verbatim (unique in the lesson) and ` +
  `new_string must use British spelling and no em/en dashes or ellipses.`,
  { schema: SCHEMA, agentType: 'general-purpose', label: 'capstone-crossref-rewrite', phase: 'Rewrite' }
)

return result
