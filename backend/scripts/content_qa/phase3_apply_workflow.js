export const meta = {
  name: 'admin-content-qa-apply-edits',
  description: 'Generate exact copy edits + corrected quiz blocks for the 9 admin tracks',
  phases: [{ title: 'Generate edits', detail: 'one agent per module' }],
}

const RULES = `
House standard:
- British/EU spelling: colour, organisation, summarise, behaviour, Artefact, licence (noun), sceptical, per cent (two words), towards, -ise not -ize. BUT "Artifacts"/"Artifact" is Anthropic's real Claude product-feature name: KEEP the American spelling wherever the text names that product; only change to "artefact" in generic non-product prose.
- NO em dash, en dash, or ellipsis in any text field. Rewrite each into plain punctuation (period, comma, colon, parentheses, or "and"), preserving meaning. Three-dot "..." is also banned; rewrite it away.
- "interface" not "surface" for Chat/Cowork/Code/Design tools.
- Fix plain typos: doubled words, "it's" vs "its", missing full stops at end of a text block, double spaces, obvious misspellings, wrong articles.
`

const SCHEMA = {
  type: 'object',
  required: ['module_path', 'text_edits', 'quiz_edits'],
  properties: {
    module_path: { type: 'string' },
    text_edits: {
      type: 'array',
      description: 'Exact substring replacements in NON-QUIZ text fields only.',
      items: {
        type: 'object',
        required: ['lesson_id', 'old_string', 'new_string', 'category'],
        properties: {
          lesson_id: { type: 'string' },
          old_string: { type: 'string', description: 'EXACT substring copied verbatim from a block text field, minimal but unique within the lesson' },
          new_string: { type: 'string' },
          category: { type: 'string', enum: ['em-dash', 'en-dash', 'ellipsis', 'typo', 'en-gb', 'surface', 'artifact'] },
        },
      },
    },
    quiz_edits: {
      type: 'array',
      description: 'Corrected quiz blocks for quizzes whose review verdict is fix-quality or trim-questions ONLY. Do NOT convert to interactive and do NOT drop.',
      items: {
        type: 'object',
        required: ['lesson_id', 'block_id', 'questions', 'change_summary'],
        properties: {
          lesson_id: { type: 'string' },
          block_id: { type: 'string', description: 'the id of the existing quiz block' },
          questions: {
            type: 'array',
            items: {
              type: 'object',
              required: ['q', 'options', 'correct', 'explanation'],
              properties: {
                id: { type: 'string' },
                q: { type: 'string' },
                options: { type: 'array', items: { type: 'string' } },
                correct: { type: 'integer' },
                explanation: { type: 'string' },
              },
            },
          },
          change_summary: { type: 'string', description: 'what changed and why, for the human changelog' },
        },
      },
    },
  },
}

const modules = typeof args === 'string' ? JSON.parse(args) : args
log(`Generating edits for ${modules.length} modules`)

const results = await parallel(modules.map(m => () =>
  agent(
    `You produce precise, safe edits for one module of an AI-enablement learning hub.\n` +
    RULES +
    `\nRead the module file at this exact path: ${m.path}\n` +
    `Echo the path back verbatim as "module_path".\n` +
    `Each lesson has content_blocks (CURRENT live text), a "deterministic" object (already-found ` +
    `em-dashes/americanisms), "quiz_verdicts" (the review's per-quiz judgement) and ` +
    `"editorial_copy_notes" (typos/layout the review found).\n\n` +
    `Produce TWO arrays:\n\n` +
    `text_edits[]: one exact substring replacement per issue in NON-QUIZ text fields ` +
    `(paragraph/heading/callout/kicker/card body+title/interactive/try_it_yourself/image ` +
    `alt+caption). Cover EVERY em dash, en dash and ellipsis (there are known ones in ` +
    `"deterministic"), plus typos and non-British spellings. old_string MUST be copied ` +
    `verbatim from the current text (include enough surrounding words to be unique within the ` +
    `lesson) and new_string must preserve meaning and introduce no banned punctuation. Do NOT ` +
    `emit edits for text inside quiz blocks (handle those in quiz_edits). For artifact/artifacts, ` +
    `only emit an edit where it is NOT the Claude product name.\n\n` +
    `quiz_edits[]: ONLY for quizzes whose quiz_verdicts verdict is "fix-quality" or ` +
    `"trim-questions". Return the full corrected questions array for that quiz block (use the ` +
    `existing block_id). Apply ONLY: shuffle option order so the correct answer is NOT always the ` +
    `same position across the quiz (update the "correct" index to match the new order); trim ` +
    `untaught or duplicate questions the verdict names; fix implausible distractors the verdict ` +
    `names; fix any typo/spelling inside the quiz. Keep 3 questions where possible (2 if a trim ` +
    `leaves 2). Preserve each question's "id" if present. Do NOT convert the quiz to another block ` +
    `type and do NOT drop a quiz entirely. Give a change_summary for each. If a quiz's verdict is ` +
    `keep/convert-to-interactive/drop/no-quiz-ok, do NOT touch it.`,
    { schema: SCHEMA, agentType: 'general-purpose', label: m.track + ': ' + m.path.split(/[\\/]/).pop(), phase: 'Generate edits' }
  )
))

return results.filter(Boolean)
