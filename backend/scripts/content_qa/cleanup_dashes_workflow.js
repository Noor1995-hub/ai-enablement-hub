export const meta = {
  name: 'admin-content-qa-cleanup-dashes',
  description: 'Rewrite residual banned punctuation inside quiz blocks (structure-preserving)',
  phases: [{ title: 'Cleanup', detail: 'one agent for all residual quiz blocks' }],
}

const SCHEMA = {
  type: 'object',
  required: ['blocks'],
  properties: {
    blocks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['block_id', 'questions'],
        properties: {
          block_id: { type: 'string' },
          questions: {
            type: 'array',
            items: {
              type: 'object',
              required: ['id', 'q', 'options', 'correct', 'explanation'],
              properties: {
                id: { type: 'string' },
                q: { type: 'string' },
                options: { type: 'array', items: { type: 'string' } },
                correct: { type: 'integer' },
                explanation: { type: 'string' },
              },
            },
          },
        },
      },
    },
  },
}

const path = (typeof args === 'string' ? JSON.parse(args) : args).path

const result = await agent(
  `Read the JSON file at: ${path}\n` +
  `It is a list of quiz blocks (each item has lesson_title and a "block" with id + questions).\n\n` +
  `For EACH block, return a corrected version that removes every banned character and fixes ` +
  `spelling, WITHOUT changing anything else:\n` +
  `- Replace every em dash (—) and en dash (–) and ellipsis (… or "...") with plain ` +
  `punctuation (period, comma, colon, parentheses, or "and") so the sentence reads naturally. ` +
  `Do NOT touch arrow characters like →.\n` +
  `- Change generic "artifact"/"artifacts" to "artefact"/"artefacts" (these are ordinary prose ` +
  `here, NOT the Claude product feature).\n` +
  `- Fix any other American spelling to British (behaviour, organise, etc.).\n\n` +
  `STRICT: preserve each block's id (as block_id), each question's id, the SAME number of ` +
  `questions, the SAME options in the SAME order, and the SAME "correct" index. Only the text ` +
  `wording changes. Return the corrected questions for every block in the file.`,
  { schema: SCHEMA, agentType: 'general-purpose', label: 'cleanup-residual-quiz-dashes', phase: 'Cleanup' }
)

return result
