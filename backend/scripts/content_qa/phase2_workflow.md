# Phase 2 editorial Workflow — reference

This is the `Workflow`-tool script for the per-module editorial pass. Run it via the `Workflow`
tool with `args` = a list of `{ path, track }` for each `per_module/*.json` file (paths are
ASCII, so they round-trip safely; module titles contain em-dashes and are derived from the file
by the report builder, not trusted from agent echo). Each agent echoes back `module_path`
exactly so results join to files reliably regardless of order or dropped modules.

```javascript
export const meta = {
  name: 'admin-content-qa-editorial',
  description: 'Per-module editorial review (copy/layout + quiz) of the 9 admin-assigned tracks',
  phases: [{ title: 'Review', detail: 'one agent per module' }],
}

const STANDARD = `
House authoring standard (apply strictly):
- British/EU spelling: colour, organisation, summarise, behaviour, Artefact (not Artifact); "interface" not "surface" for chat/tools. NOTE: "Artifacts" is also Anthropic's real product name for the Claude feature - when the text names that product, the American spelling is correct; do NOT flag product-name uses.
- No em dash, en dash or ellipsis in any text field.
- whitespace is size 'md', used as a separator just before a closing quiz.
- A heading "Check your understanding" immediately precedes each quiz.
- Quiz is OPTIONAL per lesson (skip on light/curiosity/decision lessons). When used: 3 questions, 3-4 options, a teaching explanation each; vary which position is correct; distractors must be plausible. A 'sort' interactive can REPLACE a quiz on a decision lesson.
- The answer-length bug (correct answer being the longest option) is ALREADY FIXED - do NOT report it.
`

const SCHEMA = {
  type: 'object',
  required: ['module_path', 'copy_layout', 'quiz'],
  properties: {
    module_path: { type: 'string' },
    copy_layout: {
      type: 'array',
      items: {
        type: 'object',
        required: ['lesson_title', 'issue_type', 'quote', 'suggestion'],
        properties: {
          lesson_title: { type: 'string' },
          issue_type: { type: 'string', enum: ['typo', 'en-gb', 'layout', 'spacing', 'opener-weight', 'other'] },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          quote: { type: 'string' },
          suggestion: { type: 'string' },
          triage_bucket: { type: 'string', enum: ['wording', 'structural', 'factual', 'dedup'] },
        },
      },
    },
    quiz: {
      type: 'array',
      items: {
        type: 'object',
        required: ['lesson_title', 'verdict', 'rationale'],
        properties: {
          lesson_title: { type: 'string' },
          verdict: { type: 'string', enum: ['keep', 'trim-questions', 'convert-to-interactive', 'fix-quality', 'drop', 'no-quiz-ok'] },
          rationale: { type: 'string' },
          suggested_question_count: { type: 'integer' },
          suggested_interactive_mode: { type: 'string', enum: ['predict', 'sort', 'spot_the_flaw', 'none'] },
          variety_note: { type: 'string' },
          quality_flags: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

const modules = args  // [{ path, track }]
log(`Reviewing ${modules.length} modules`)

const results = await parallel(modules.map(m => () =>
  agent(
    `You are reviewing one module of an AI-enablement learning hub against the house standard.\n` +
    STANDARD +
    `\nRead the module file at this exact path: ${m.path}\n` +
    `Track: ${m.track}. Echo the file path back verbatim as "module_path" in your output.\n` +
    `The file contains the module's lessons, each with content_blocks and a "deterministic" ` +
    `object holding already-found mechanical issues (punctuation, americanisms, quiz-conformance). ` +
    `Do NOT re-report anything already in "deterministic" - add only what judgement surfaces.\n\n` +
    `Return TWO arrays:\n` +
    `1. copy_layout[]: residual typos, subtle British-English the grep missed, layout oddities ` +
    `(skipped heading levels, empty blocks, an opener card/callout that should be a lighter kicker), ` +
    `spacing oddities beyond the mechanical check. Each with an EXACT quote from the lesson.\n` +
    `2. quiz[]: one entry per quiz in the module (verdict "no-quiz-ok" for a lesson that ` +
    `correctly has no quiz but where that's worth noting). Judge: is the quiz value-adding (tests ` +
    `the lesson's real thesis, not filler)? Could 3 questions be fewer? Should it become a ` +
    `predict/sort/spot_the_flaw for variety - considering the WHOLE module so the mix stays varied, ` +
    `not all one type? Are distractors plausible? Set verdict + rationale + (where relevant) ` +
    `suggested_question_count, suggested_interactive_mode, variety_note, quality_flags.`,
    { schema: SCHEMA, agentType: 'general-purpose', label: m.track + ': ' + m.path.split(/[\\/]/).pop(), phase: 'Review' }
  )
))

return results.filter(Boolean)
```
