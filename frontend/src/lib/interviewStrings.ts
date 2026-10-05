/** Every learner-facing text on the interview screens and the playbook, in the two languages
 *  a learner can pick on the welcome screen (#83). The Dutch is Flemish with the formal "u",
 *  matching the interviewer itself (backend/prompts/interview.md). House style in both: no em
 *  dash, en dash or ellipsis character. Keep the backend's language list in sync
 *  (backend/src/services/interview_language.py). */

export type InterviewLanguage = 'en' | 'nl'

export const DEFAULT_INTERVIEW_LANGUAGE: InterviewLanguage = 'en'

const INTERVIEW_EN = {
  eyebrow: 'AI Opportunity Interview',
  welcomeHeading: 'Let’s find where AI can actually help you.',
  welcomeBodyBefore:
    "A short conversation about your real, everyday work: the systems you're in, the tasks that eat " +
    "your week, the bits you'd love to hand off. It takes about 15 minutes, and there are no wrong " +
    'answers; the more concrete you are, the better the result. At the end, you get a ',
  welcomeBodyStrong: 'personalised playbook',
  welcomeBodyAfter: ': practical AI use cases and clear next steps, made for you.',
  stepTalkLabel: 'Talk',
  stepTalkText: 'A few questions about your week and the tools you use.',
  stepBuildLabel: 'Build',
  stepBuildText: 'We turn the conversation into your playbook.',
  stepStartLabel: 'Start',
  stepStartText: 'You leave with a first step you can take today.',
  privacyNotice: 'Conversations are stored and may be reviewed by hub admins to improve the hub.',
  startButton: 'Start the interview',
  languagePickerLabel: 'Interview language',
  conversationLabel: 'Conversation',
  interviewerName: 'Your interviewer',
  typing: 'The interviewer is typing',
  typingAnnouncement: 'The interviewer is typing.',
  tryAgain: 'Try again',
  speakerYou: 'You: ',
  speakerInterviewer: 'Interviewer: ',
  answerLabel: 'Type your answer',
  answerPlaceholder: 'Type your answer (Shift+Enter for a new line)',
  answerHelp: 'Press Enter to send, Shift+Enter for a new line.',
  send: 'Send',
  buildButton: 'Build my playbook',
  hintReady: "Your playbook's ready to build whenever you are, or keep chatting to add more.",
  hintCanBuild: 'You can build your playbook now, or keep going for a richer result.',
  hintNoMessages: 'Build my playbook unlocks once the interviewer has enough to go on.',
  hintFirstAnswer: 'Answer in your own words. Build my playbook unlocks once the interviewer has enough to go on.',
  hintKeepGoing: 'Keep going: the more you share, the better your playbook.',
  buildLocked: 'Unlocks once the interviewer has enough to go on.',
  buildWaiting: 'Available once the interviewer finishes replying.',
  openFailed: 'Could not start the interview. Please try again.',
  // In English the page shows the server's own message, which can carry useful detail (a rate
  // limit, say); these are the fallbacks, and the Dutch versions replace it (#83).
  loadFailed: 'Failed to load your interview.',
  buildFailed: 'Could not build your playbook. Please try again.',
  chatFailed: 'Your answer did not get through. Please try again.',
  needsAssessmentHeading: 'Complete your assessment first',
  needsAssessmentText: 'The interview builds on your assessment answers, so it opens once your assessment is done.',
  needsAssessmentButton: 'Go to your assessment',
  buildingHeading: 'Building your playbook',
  buildingText:
    'Turning our conversation into practical use cases and clear next steps. This usually takes a ' +
    'minute or two, so hang tight and keep this tab open. Your playbook will appear here.',
  buildingAnnouncement: 'Building your playbook. This usually takes a minute or two.',
  playbookWillContain: 'Your playbook will contain',
  readyAnnouncement: 'Your playbook is ready.',
  playbookHeading: 'Your AI playbook',
  playbookIntro: 'Built from your interview. You can come back to it any time from the hub.',
  playbookUnavailable: 'Your playbook isn’t available right now. Please refresh.',
}

export type InterviewStrings = typeof INTERVIEW_EN

const INTERVIEW_NL: InterviewStrings = {
  eyebrow: 'AI-kansengesprek',
  welcomeHeading: 'Laten we ontdekken waar AI u echt kan helpen.',
  welcomeBodyBefore:
    'Een kort gesprek over uw echte, dagelijkse werk: de systemen waarin u werkt, de taken die uw week ' +
    'opslorpen, de dingen die u graag uit handen zou geven. Het duurt ongeveer 15 minuten en er zijn ' +
    'geen foute antwoorden; hoe concreter u bent, hoe beter het resultaat. Op het einde krijgt u een ',
  welcomeBodyStrong: 'persoonlijk playbook',
  welcomeBodyAfter: ': praktische AI-toepassingen en duidelijke volgende stappen.',
  stepTalkLabel: 'Praten',
  stepTalkText: 'Een paar vragen over uw week en de tools die u gebruikt.',
  stepBuildLabel: 'Bouwen',
  stepBuildText: 'We zetten het gesprek om in uw playbook.',
  stepStartLabel: 'Starten',
  stepStartText: 'U vertrekt met een eerste stap die u vandaag al kunt zetten.',
  privacyNotice:
    'Gesprekken worden bewaard en kunnen door de beheerders van de hub worden nagelezen om de hub te verbeteren.',
  startButton: 'Start het gesprek',
  languagePickerLabel: 'Taal van het gesprek',
  conversationLabel: 'Gesprek',
  interviewerName: 'Uw interviewer',
  typing: 'De interviewer is aan het typen',
  typingAnnouncement: 'De interviewer is aan het typen.',
  tryAgain: 'Probeer opnieuw',
  speakerYou: 'U: ',
  speakerInterviewer: 'Interviewer: ',
  answerLabel: 'Typ uw antwoord',
  answerPlaceholder: 'Typ uw antwoord (Shift+Enter voor een nieuwe regel)',
  answerHelp: 'Druk op Enter om te verzenden, Shift+Enter voor een nieuwe regel.',
  send: 'Verzenden',
  buildButton: 'Bouw mijn playbook',
  hintReady: 'Uw playbook is klaar om te bouwen wanneer u wilt, of praat verder om meer toe te voegen.',
  hintCanBuild: 'U kunt uw playbook nu bouwen, of verder praten voor een rijker resultaat.',
  hintNoMessages: 'De knop ‘Bouw mijn playbook’ wordt actief zodra de interviewer genoeg weet.',
  hintFirstAnswer: 'Antwoord in uw eigen woorden. U kunt uw playbook bouwen zodra de interviewer genoeg weet.',
  hintKeepGoing: 'Ga gerust verder: hoe meer u vertelt, hoe beter uw playbook.',
  buildLocked: 'Wordt actief zodra de interviewer genoeg weet.',
  buildWaiting: 'Beschikbaar zodra de interviewer klaar is met antwoorden.',
  openFailed: 'Het gesprek kon niet starten. Probeer het opnieuw.',
  loadFailed: 'Uw gesprek kon niet geladen worden.',
  buildFailed: 'Uw playbook kon niet gebouwd worden. Probeer het opnieuw.',
  chatFailed: 'Uw antwoord is niet doorgekomen. Probeer het opnieuw.',
  needsAssessmentHeading: 'Rond eerst uw assessment af',
  needsAssessmentText: 'Het gesprek vertrekt van uw antwoorden in het assessment, dus het opent zodra u dat hebt afgerond.',
  needsAssessmentButton: 'Naar uw assessment',
  buildingHeading: 'Uw playbook wordt gebouwd',
  buildingText:
    'We zetten ons gesprek om in praktische toepassingen en duidelijke volgende stappen. Dat duurt ' +
    'meestal een minuutje of twee, dus even geduld en laat dit tabblad open. Uw playbook verschijnt hier.',
  buildingAnnouncement: 'Uw playbook wordt gebouwd. Dat duurt meestal een minuutje of twee.',
  playbookWillContain: 'Uw playbook bevat',
  readyAnnouncement: 'Uw playbook is klaar.',
  playbookHeading: 'Uw AI-playbook',
  playbookIntro: 'Gebouwd op basis van uw gesprek. U kunt er altijd naar terugkeren via de hub.',
  playbookUnavailable: 'Uw playbook is nu niet beschikbaar. Vernieuw de pagina.',
}

export const INTERVIEW_STRINGS: Record<InterviewLanguage, InterviewStrings> = {
  en: INTERVIEW_EN,
  nl: INTERVIEW_NL,
}

/** An error as the interview page shows it. In English, the server's own message (it can carry
 *  useful detail, such as a rate limit); in Dutch, the dictionary's, since the server and the
 *  shared chat hook only speak English. */
export function interviewError(
  message: string | null,
  language: InterviewLanguage,
  key: 'loadFailed' | 'openFailed' | 'buildFailed' | 'chatFailed',
): string | null {
  if (message === null) return null
  return language === 'en' ? message : INTERVIEW_STRINGS[language][key]
}

const PLAYBOOK_EN = {
  whereYouAreToday: 'Where you are today',
  useCases: 'Your AI use cases',
  nextMoves: 'Your next moves',
  holdingYouBack: 'What might be holding you back',
  doThisToday: 'Do this today',
  startHere: 'Start here',
  inPractice: 'In practice: ',
  before: 'Before',
  after: 'After',
  impact: 'Impact: ',
  assumptionToCheck: 'Assumption to check: ',
  realConcern: 'The real concern',
  reframe: 'Reframe',
  firstProof: 'First proof',
  difficultyQuickWin: 'Quick win',
  difficultyWorthASession: 'Worth a session',
  difficultyBiggerBuild: 'Bigger build',
  showDetails: 'Show details',
  hideDetails: 'Hide details',
  systems: 'Systems',
  withColleagues: 'Involves colleagues',
  forUseCase: 'For: ',
  timeNeeded: 'Time needed: ',
  useCaseCountOne: 'One use case, picked for you',
  useCaseCountMany: '{n} use cases, ranked for you',
}

export type PlaybookStrings = typeof PLAYBOOK_EN

const PLAYBOOK_NL: PlaybookStrings = {
  whereYouAreToday: 'Waar u vandaag staat',
  useCases: 'Uw AI-toepassingen',
  nextMoves: 'Uw volgende stappen',
  holdingYouBack: 'Wat u misschien tegenhoudt',
  doThisToday: 'Doe dit vandaag',
  startHere: 'Begin hier',
  inPractice: 'In de praktijk: ',
  before: 'Voor',
  after: 'Na',
  impact: 'Impact: ',
  assumptionToCheck: 'Na te gaan: ',
  realConcern: 'De eigenlijke bezorgdheid',
  reframe: 'Een andere kijk',
  firstProof: 'Een eerste bewijs',
  difficultyQuickWin: 'Snelle winst',
  difficultyWorthASession: 'Een sessie waard',
  difficultyBiggerBuild: 'Groter project',
  showDetails: 'Details tonen',
  hideDetails: 'Details verbergen',
  systems: 'Systemen',
  withColleagues: 'Samen met collega’s',
  forUseCase: 'Voor: ',
  timeNeeded: 'Benodigde tijd: ',
  useCaseCountOne: 'Eén toepassing, voor u gekozen',
  useCaseCountMany: '{n} toepassingen, voor u gerangschikt',
}

export const PLAYBOOK_STRINGS: Record<InterviewLanguage, PlaybookStrings> = {
  en: PLAYBOOK_EN,
  nl: PLAYBOOK_NL,
}

/** The use-case count under the playbook's use-case heading, singular for one. */
export function formatUseCaseCount(n: number, t: PlaybookStrings): string {
  return n === 1 ? t.useCaseCountOne : t.useCaseCountMany.replace('{n}', String(n))
}
