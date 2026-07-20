export const meta = {
  name: 'admin-content-qa-convert-quizzes',
  description: 'Author sort / spot_the_flaw interactive blocks to replace flagged quizzes',
  phases: [{ title: 'Author', detail: 'one agent per lesson to convert' }],
}

const SCHEMA = {
  type: 'object',
  required: ['lesson_title', 'quiz_block_id', 'new_block'],
  properties: {
    lesson_title: { type: 'string' },
    quiz_block_id: { type: 'string', description: 'id of the existing quiz block being replaced' },
    new_block: {
      type: 'object',
      description: 'the interactive block that replaces the quiz',
      required: ['type', 'mode', 'prompt'],
      properties: {
        type: { type: 'string', enum: ['interactive'] },
        mode: { type: 'string', enum: ['sort', 'spot_the_flaw'] },
        prompt: { type: 'string' },
        // sort
        buckets: { type: 'array', items: { type: 'object', required: ['id', 'label'], properties: { id: { type: 'string' }, label: { type: 'string' } } } },
        items: { type: 'array', items: { type: 'object', required: ['id', 'text', 'bucketId', 'reason'], properties: { id: { type: 'string' }, text: { type: 'string' }, bucketId: { type: 'string' }, reason: { type: 'string' } } } },
        // spot_the_flaw
        example: { type: 'string' },
        candidates: { type: 'array', items: { type: 'object', required: ['id', 'text', 'isFlaw', 'reason'], properties: { id: { type: 'string' }, text: { type: 'string' }, isFlaw: { type: 'boolean' }, reason: { type: 'string' } } } },
      },
    },
  },
}

const RULES = `
Block contracts (match EXACTLY):
- sort: { type:"interactive", mode:"sort", prompt, buckets:[{id,label}], items:[{id,text,bucketId,reason}] }. 3-4 buckets, 5-8 items; every item.bucketId must equal one bucket.id; each item.reason is a one-line why. Give ids like "b1","b2" for buckets and "i1".."i6" for items.
- spot_the_flaw: { type:"interactive", mode:"spot_the_flaw", prompt, example, candidates:[{id,text,isFlaw,reason}] }. "example" is a realistic AI output or scenario shown to the learner; 3-5 candidates, at least one isFlaw:true and at least one isFlaw:false; each reason explains why it is or isn't a flaw. Ids "c1".."c5".
House style: British/EU spelling; NO em dash, en dash or ellipsis; keep it grounded in THIS lesson's own running example, not a generic one.
`

const items = (typeof args === 'string' ? JSON.parse(args) : args)
log(`Authoring ${items.length} interactive conversions`)

const results = await parallel(items.map(m => () =>
  agent(
    `You convert one lesson's closing quiz into a "${m.mode}" interactive block, using the ` +
    `lesson's OWN content and examples.\n` + RULES +
    `\nRead the module file at: ${m.path}\nFind the lesson titled exactly: "${m.lesson_title}".\n` +
    `Study its content_blocks and its existing quiz. Author a ${m.mode} interactive that tests ` +
    `the same understanding the quiz did, but more actively, reusing the lesson's concrete ` +
    `examples and the decision/comparison structure the lesson already sets up (e.g. its ` +
    `"when to use / when not to" cards). Return the existing quiz block's id as quiz_block_id and ` +
    `the new interactive block as new_block. Echo lesson_title exactly.`,
    { schema: SCHEMA, agentType: 'general-purpose', label: `${m.mode}: ${m.lesson_title.slice(0, 40)}`, phase: 'Author' }
  )
))

return results.filter(Boolean)
