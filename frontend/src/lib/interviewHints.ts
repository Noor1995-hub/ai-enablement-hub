/** The hint in the interview chat's toolbar. There is always one, so the toolbar keeps its
 *  height and the chat never shifts. Before the first answer it explains why the Build
 *  button is still greyed out: the interviewer opens the conversation itself, so the
 *  learner only has to answer its question. */
export function chatToolbarHint(args: {
  modelReady: boolean
  canBuild: boolean
  answerCount: number
}): string {
  const { modelReady, canBuild, answerCount } = args
  if (modelReady) return "Your playbook's ready to build whenever you are — or keep chatting to add more."
  if (canBuild) return 'You can build your playbook now, or keep going for a richer result.'
  if (answerCount === 0) {
    return 'Answer in your own words. Build my playbook unlocks once the interviewer has enough to go on.'
  }
  return 'Keep going — the more you share, the better your playbook.'
}
