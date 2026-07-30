// Learner-facing interview endpoints (AI Interviewer feature). Not yet in schema.d.ts —
// see the INTERIM interview types block atop src/types/domain.ts — so this replicates the
// `rawRequest<T>` escape hatch from pages/admin2/api.ts locally rather than casting at each
// call site. After tomorrow's `gen:api`, these swap to typed `client.GET`/`client.POST` calls.
import { client, errorMessage } from '../api/client'
import type { InterviewState, PlaybookShared } from '../types/domain'

interface RawInit {
  params?: { query?: Record<string, string | number | boolean | undefined> }
  body?: unknown
}
interface RawResult<T> {
  data?: T
  error?: unknown
}
type RawMethod = 'GET' | 'PUT' | 'POST' | 'PATCH'
type RawClient = Record<RawMethod, (url: string, init?: RawInit) => Promise<RawResult<unknown>>>

async function rawRequest<T>(method: RawMethod, url: string, init?: RawInit): Promise<RawResult<T>> {
  const raw = client as unknown as RawClient
  return (await raw[method](url, init)) as RawResult<T>
}

export async function getInterviewState(): Promise<InterviewState> {
  const { data, error } = await rawRequest<InterviewState>('GET', '/api/interview/me')
  if (!data) throw new Error(errorMessage(error, 'Failed to load your interview.'))
  return data
}

export async function buildPlaybook(): Promise<PlaybookShared> {
  const { data, error } = await rawRequest<{ playbook: PlaybookShared }>('POST', '/api/interview/playbook')
  if (!data) throw new Error(errorMessage(error, 'Could not build your playbook.'))
  return data.playbook
}

export async function openInterview(): Promise<{ conversation_id: string; greeting: string }> {
  const { data, error } = await rawRequest<{ conversation_id: string; greeting: string }>(
    'POST',
    '/api/interview/opener',
  )
  if (!data) throw new Error(errorMessage(error, 'Could not start the interview.'))
  return data
}
