import { DEFAULT_INTERVIEW_LANGUAGE, INTERVIEW_STRINGS, type InterviewLanguage } from './interviewStrings'

/** The hint in the interview chat's toolbar. There is always one, so the toolbar keeps its
 *  height and the chat never shifts; it is also the Build button's description (why it is
 *  greyed out). Before the first answer it explains the greyed-out button. While there is
 *  nothing to answer yet (the opener is loading or failed), it does not ask for an answer.
 *  In the interview's language (#83); copy follows the lesson house style: no em dash, en
 *  dash or ellipsis character. */
export function chatToolbarHint(
  args: {
    modelReady: boolean
    canBuild: boolean
    answerCount: number
    hasMessages: boolean
  },
  language: InterviewLanguage = DEFAULT_INTERVIEW_LANGUAGE,
): string {
  const { modelReady, canBuild, answerCount, hasMessages } = args
  const t = INTERVIEW_STRINGS[language]
  if (modelReady) return t.hintReady
  if (canBuild) return t.hintCanBuild
  if (!hasMessages) return t.hintNoMessages
  if (answerCount === 0) return t.hintFirstAnswer
  return t.hintKeepGoing
}
