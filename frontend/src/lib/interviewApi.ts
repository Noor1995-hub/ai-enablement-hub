// Learner-facing interview endpoints (AI Interviewer feature), typed through the
// generated client: all three paths are in src/api/schema.d.ts.
import { client, errorMessage } from '../api/client'
import type { InterviewState, PlaybookShared } from '../types/domain'

export async function getInterviewState(): Promise<InterviewState> {
  const { data, error } = await client.GET('/api/interview/me')
  if (!data) throw new Error(errorMessage(error, 'Failed to load your interview.'))
  return data
}

export async function buildPlaybook(): Promise<PlaybookShared> {
  const { data, error } = await client.POST('/api/interview/playbook')
  if (!data) throw new Error(errorMessage(error, 'Could not build your playbook.'))
  return data.playbook
}

export async function openInterview(): Promise<{ conversation_id: string; greeting: string }> {
  const { data, error } = await client.POST('/api/interview/opener')
  if (!data) throw new Error(errorMessage(error, 'Could not start the interview.'))
  return data
}
