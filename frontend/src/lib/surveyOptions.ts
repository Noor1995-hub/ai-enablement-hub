// ── Competency option arrays (used by Assessment.tsx) ────────────────────────
// `as const` so the code unions below can be derived; those unions feed the
// SurveyResponse typing at the API boundary (design-frontend.md §3).

export const C1_OPTIONS = [
  { code: 'MISSING', label: "Honestly, I'm not sure how it works." },
  { code: 'PARTIAL', label: 'It understands my question and gives back the correct information it has stored.' },
  { code: 'HAVE',    label: "It predicts likely wording from patterns in its training, so it's often useful but can be wrong." },
  { code: 'ADV_D',   label: "It completes text from patterns rather than looking anything up or reasoning it out, so what it produces reflects what's statistically likely, not what's true or grounded." },
  { code: 'ADV_E',   label: "I can predict where it will fail. I know which task types produce plausible but wrong outputs, and I use this to decide when AI is and isn't the right tool." },
] as const
export const C2_OPTIONS = [
  { code: 'MISSING', label: "I haven't really thought about where it could help me." },
  { code: 'PARTIAL', label: "I can see it's useful generally, but haven't pinned down where it fits my work." },
  { code: 'HAVE',    label: "I've identified specific recurring tasks of mine where it genuinely helps, and use them." },
  { code: 'ADV_D',   label: "I spot the less obvious uses, where AI can help in ways most people wouldn't think to try." },
  { code: 'ADV_E',   label: "I actively redesign workflows around AI's capabilities, not just applying it to existing tasks but restructuring how work gets done to make the most of what it can do." },
] as const
export const C3_OPTIONS = [
  { code: 'MISSING', label: "Give up and decide it can't do that." },
  { code: 'PARTIAL', label: 'Try again, maybe reword it slightly.' },
  { code: 'HAVE',    label: 'Add context or examples, or break it into steps, and iterate until it works.' },
  { code: 'ADV_D',   label: "I work out why it went wrong, whether it was too vague, missing context, or too big an ask, and fix that specific thing." },
  { code: 'ADV_E',   label: "I work systematically using structured approaches like chain of thought, role framing, or reusable prompt templates, and I help others get better results, not just solve my own problems." },
] as const
export const C4_OPTIONS = [
  { code: 'MISSING', label: "Use it pretty much as is, it reads well." },
  { code: 'PARTIAL', label: 'Skim for anything that jumps out as wrong, then use it.' },
  { code: 'HAVE',    label: "Check the key figures and whether the picture looks balanced, using what I already know, before using it." },
  { code: 'ADV_D',   label: "Verify the claims against an independent source, and look for slants or gaps that aren't obvious from the text." },
  { code: 'ADV_E',   label: "I've built verification into my process. I know which claim types need what evidence and apply systematic checks rather than treating each output as a standalone review." },
] as const
export const C5_OPTIONS = [
  { code: 'PUBLIC_PASTE',   label: 'Put internal documents or client/customer info into a public tool (free ChatGPT, Gemini, etc.)' },
  { code: 'APPROVED_PASTE', label: 'Put internal documents or client information into a company approved tool' },
  { code: 'UNSURE',         label: "Wasn't sure whether a tool was approved for that kind of data" },
  { code: 'KEPT_OUT',       label: 'Mostly kept work information out of public tools' },
  { code: 'NO_USE',         label: "Haven't really used AI for work" },
] as const
export const C6_OPTIONS = [
  { code: 'MISSING', label: 'A clear, confident answer with a source is reliable.' },
  { code: 'PARTIAL', label: "It can be wrong sometimes, but a source it gives makes it trustworthy." },
  { code: 'HAVE',    label: "It can be confidently wrong and can even invent sources that look real, so neither confidence nor a citation is proof." },
  { code: 'ADV_D',   label: "The confident and well sourced answers are the ones I'm least likely to question, so I scrutinise those hardest." },
  { code: 'ADV_E',   label: "I calibrate scrutiny by domain and task type. I know where AI is most unreliable and apply proportionate verification rather than blanket suspicion, and I help others develop the same judgement." },
] as const

export const FREQ_OPTIONS = [
  { code: 'NEVER',     label: 'Never' },
  { code: 'MONTHLY',   label: 'A few times a month' },
  { code: 'WEEKLY',    label: 'Most weeks' },
  { code: 'DAILY',     label: 'Most days' },
  { code: 'INTENSIVE', label: 'Every day' },
] as const
export const BREADTH_OPTIONS = [
  { code: 'NONE',    label: 'None of my work' },
  { code: 'FEW',     label: 'One or two tasks' },
  { code: 'SEVERAL', label: 'Several areas' },
  { code: 'MOST',    label: 'Across most of my work' },
  { code: 'ALL',     label: 'Across all of my work' },
] as const
export const TOOLS_OPTIONS = [
  { code: 'CHATGPT',  label: 'ChatGPT' },
  { code: 'COPILOT',  label: 'Microsoft Copilot' },
  { code: 'CLAUDE',   label: 'Claude' },
  { code: 'GEMINI',   label: 'Gemini' },
  { code: 'OTHER',    label: 'Other (incl. tools built into software you use)' },
  { code: 'NONE_YET', label: 'None yet' },
] as const
export const ATTITUDE_OPTIONS = [
  { code: 1, label: "I'd rather not",  sub: "I don't see the point or have real concerns" },
  { code: 2, label: 'Cautious',        sub: "I'll engage but have reservations" },
  { code: 3, label: 'Neutral',         sub: 'Curious, no strong feelings' },
  { code: 4, label: 'Positive',        sub: 'I see clear ways it helps' },
  { code: 5, label: 'Eager',           sub: "I've wanted to do more for a while" },
] as const
export const READINESS_OPTIONS = [
  { code: 1, label: 'Keep as is',      sub: "I'd rather keep working the way I do" },
  { code: 2, label: 'Small tweaks',   sub: "I'm open to small adjustments" },
  { code: 3, label: 'Open to change', sub: "I'm willing to make significant changes" },
  { code: 4, label: 'Full rethink',   sub: "I'd rethink how I work from the ground up" },
  { code: 5, label: 'Already there',  sub: "I've actively reshaped how I work around AI" },
] as const
export const BARRIERS_OPTIONS = [
  { code: 'NO_ACCESS',        label: 'No access to AI tools' },
  { code: 'NO_TIME',          label: 'No time to learn it' },
  { code: 'DONT_TRUST',       label: "Don't trust the outputs" },
  { code: 'NOT_SURE_ALLOWED', label: "Not sure it's allowed" },
  { code: 'POLICY_RESTRICTS', label: 'Company policy restricts it' },
  { code: 'DONT_SEE',         label: "Don't see where it'd help" },
  { code: 'NOTHING',          label: 'Nothing, I use it freely' },
] as const
export const SETUP_OPTIONS = [
  { code: 'WORKSPACE',      label: 'A saved workspace or Project with custom instructions for a recurring context' },
  { code: 'REUSABLE_INSTR', label: 'A reusable instruction set, Skill, agent or saved prompt template for repeated tasks' },
  { code: 'CONNECTION',     label: 'A connection linking an AI tool to another app (email, files, spreadsheets)' },
  { code: 'MULTI_STEP',     label: 'A multi-step workflow that chains several steps or tools together' },
  { code: 'DOCUMENTED',     label: 'A workflow documented well enough that someone else could run it' },
  { code: 'NONE',           label: 'None of these yet' },
] as const

// ── Derived code unions ───────────────────────────────────────────────────────

export type C1Code = (typeof C1_OPTIONS)[number]['code']
export type C2Code = (typeof C2_OPTIONS)[number]['code']
export type C3Code = (typeof C3_OPTIONS)[number]['code']
export type C4Code = (typeof C4_OPTIONS)[number]['code']
export type C5Code = (typeof C5_OPTIONS)[number]['code']
export type C6Code = (typeof C6_OPTIONS)[number]['code']
export type FreqCode = (typeof FREQ_OPTIONS)[number]['code']
export type BreadthCode = (typeof BREADTH_OPTIONS)[number]['code']
export type ToolsCode = (typeof TOOLS_OPTIONS)[number]['code']
export type AttitudeCode = (typeof ATTITUDE_OPTIONS)[number]['code']
export type ReadinessCode = (typeof READINESS_OPTIONS)[number]['code']
export type BarriersCode = (typeof BARRIERS_OPTIONS)[number]['code']
export type SetupCode = (typeof SETUP_OPTIONS)[number]['code']

// ── Object-form labels (used by Admin.tsx for display lookups) ────────────────

function toLabelMap<C extends string | number>(
  opts: readonly { code: C; label: string }[],
): Record<C, string> {
  return Object.fromEntries(opts.map((o) => [o.code, o.label])) as Record<C, string>
}

export const FREQ_LABELS = toLabelMap(FREQ_OPTIONS)
export const BREADTH_LABELS = toLabelMap(BREADTH_OPTIONS)
export const ATTITUDE_LABELS = toLabelMap(ATTITUDE_OPTIONS)
export const READINESS_LABELS = toLabelMap(READINESS_OPTIONS)

// ── Full competency Q&A definitions (used by Admin.tsx SurveyResults) ────────

// key/field are literal unions so SurveyResults can index the typed
// AdminSurveyOut row (c1_rung…c6_rung, c1_code…c6_code/c5_codes) without casts.
export interface CompetencyQA {
  key: 'c1' | 'c2' | 'c3' | 'c4' | 'c5' | 'c6'
  field: 'c1_code' | 'c2_code' | 'c3_code' | 'c4_code' | 'c5_codes' | 'c6_code'
  label: string
  question: string
  options: Record<string, string>
  multi?: boolean
}

export const COMPETENCY_QA: CompetencyQA[] = [
  {
    key: 'c1', field: 'c1_code', label: 'Understanding',
    question: "When a tool like ChatGPT gives you an answer, which is closest to how you'd describe what it's actually doing?",
    options: toLabelMap(C1_OPTIONS),
  },
  {
    key: 'c2', field: 'c2_code', label: 'Use case spotting',
    question: 'Thinking about your everyday work, how far have you got with AI?',
    options: toLabelMap(C2_OPTIONS),
  },
  {
    key: 'c3', field: 'c3_code', label: 'Prompting',
    question: 'When an AI tool gives you a poor or unhelpful answer, what do you usually do?',
    options: toLabelMap(C3_OPTIONS),
  },
  {
    key: 'c4', field: 'c4_code', label: 'Critical evaluation',
    question: 'You ask an AI tool to draft a market summary for a client. It comes back confident, polished, with specific figures and a competitor comparison. What do you actually do with it?',
    options: toLabelMap(C4_OPTIONS),
  },
  {
    key: 'c5', field: 'c5_codes', label: 'Responsible use', multi: true,
    question: 'In the past month or so, which of these have you done with an AI tool?',
    options: toLabelMap(C5_OPTIONS),
  },
  {
    key: 'c6', field: 'c6_code', label: 'Trust calibration',
    question: 'Thinking about how AI assistants actually work, which is closest to your view?',
    options: toLabelMap(C6_OPTIONS),
  },
]
