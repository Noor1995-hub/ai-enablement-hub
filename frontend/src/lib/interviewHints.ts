/** The hint in the interview chat's toolbar. There is always one, so the toolbar keeps its
 *  height and the chat never shifts; it is also the Build button's description (why it is
 *  greyed out). Before the first answer it explains the greyed-out button. While there is
 *  nothing to answer yet (the opener is loading or failed), it does not ask for an answer.
 *  Copy follows the lesson house style: no em dash, en dash or ellipsis character. */
export function chatToolbarHint(args: {
  modelReady: boolean
  canBuild: boolean
  answerCount: number
  hasMessages: boolean
}): string {
  const { modelReady, canBuild, answerCount, hasMessages } = args
  if (modelReady) return "Your playbook's ready to build whenever you are, or keep chatting to add more."
  if (canBuild) return 'You can build your playbook now, or keep going for a richer result.'
  if (!hasMessages) return 'Build my playbook unlocks once the interviewer has enough to go on.'
  if (answerCount === 0) {
    return 'Answer in your own words. Build my playbook unlocks once the interviewer has enough to go on.'
  }
  return 'Keep going: the more you share, the better your playbook.'
}
