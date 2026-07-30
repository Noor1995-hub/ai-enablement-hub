import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { LevelBadge, formatDate } from '../admin/adminHelpers'
import SurveyResults from '../admin/SurveyResults'
import { LEVELS, levelByCode } from '../../lib/levels'
import type { AdminSurvey, AdminUserEnriched } from '../../types/domain'
import InterviewCard from './InterviewCard'
import {
  useAdminUsers,
  useDeleteUser,
  useResetLink,
  useSendReminder,
  useSetMaturity,
  useSetRole,
  useSurvey,
  useTracks,
} from './api'
import type { SetMaturityInput, SetRoleInput } from './api'
import { Card, Chip, ConfirmButton, EmptyState, ErrorState, ProgressBar, Spinner } from './kit'
import type { ChipTone } from './kit'
import { useScope } from './useScope'

// The three assignable pins — same subset the old panel's inline participant
// detail used (the scoring engine never produces 'multiplier', which gates
// nothing, so it isn't offered as an override here).
const PIN_LEVELS = LEVELS.filter(l => l.code !== 'multiplier')

/** User detail screen (spec §3.3, `/admin/people/:userId`) — the full-width
 * page PeoplePage's rows link to, replacing the old panel's inline
 * participant detail component (since removed at cutover). Ports that
 * component's maturity-pin select verbatim (same value/options/onChange
 * semantics) and the old project detail view's `roleBadgeColor`/reset-link
 * conventions onto the admin2 kit + `adm-` classes, same restyle-only
 * pattern Task 15 used for `LevelBadge`/`formatDate`. Prototype:
 * docs/design-prototypes/admin-redesign option-b.html `userDetail()`. */
export default function UserDetailPage() {
  const { userId } = useParams<{ userId: string }>()
  const scope = useScope()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Per the brief: the user row comes from the same useAdminUsers cache
  // PeoplePage populates (or a refetch under this scope) — no dedicated
  // "get one user" endpoint exists yet.
  const usersQuery = useAdminUsers({ project: scope.projectId })
  const surveyQuery = useSurvey(userId ?? null)

  const peopleSearch = scope.projectId ? `?project=${scope.projectId}` : ''

  if (!userId) {
    return <ErrorState message="Missing participant id." />
  }

  if (usersQuery.isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (usersQuery.error || !usersQuery.data) {
    return (
      <ErrorState
        message={usersQuery.error?.message ?? 'Failed to load participants.'}
        onRetry={() => void usersQuery.refetch()}
      />
    )
  }

  const user = usersQuery.data.users.find(u => u.id === userId)

  // Bad/stale URL (deleted user, wrong project scope, typo'd id) — never a
  // blank screen.
  if (!user) {
    return (
      <div>
        <ErrorState message="This participant could not be found." />
        <p className="adm-hint">
          <Link to={{ pathname: '/admin/people', search: peopleSearch }}>← Back to People</Link>
        </p>
      </div>
    )
  }

  const name = `${user.first_name} ${user.last_name}`
  const status = statusInfo(user)
  const assignmentsSearch = user.project_id
    ? `?project=${user.project_id}`
    : scope.projectId
      ? `?project=${scope.projectId}`
      : ''

  function handleDeleted() {
    // The deleted user's survey is no longer reachable — no mutation hook
    // touches this key (reset-link/role/maturity don't affect it), so clear
    // it here rather than leaving a dead cache entry.
    void queryClient.invalidateQueries({ queryKey: ['admin', 'survey', userId] })
    navigate({ pathname: '/admin/people', search: peopleSearch })
  }

  return (
    // Keyed on userId: React Router keeps the same UserDetailPage element
    // mounted across a param-only navigation (people/:userId -> a different
    // :userId), so without this key AccountCard's local state (copied,
    // resetDismissed), its mutation objects, and ConfirmButton's internal
    // "armed" state would all survive a switch to a different user — an
    // armed "Confirm removal" for user A could fire one click later on user
    // B. The key forces the whole subtree to unmount/remount per user.
    <div key={userId}>
      <div className="adm-breadcrumb">
        <Link to={{ pathname: '/admin/people', search: peopleSearch }}>People</Link>
        <span className="adm-breadcrumb-sep">/</span>
        <span className="adm-breadcrumb-here">{name}</span>
      </div>

      <div className="adm-detail-head">
        <span className="adm-avatar-big">{initials(name)}</span>
        <span className="adm-detail-who">
          <h1 className="adm-detail-name">{name}</h1>
          <span className="adm-detail-sub">
            {user.email} · <Chip>{user.company_name ?? '—'}</Chip> <Chip tone={status.tone}>{status.label}</Chip>{' '}
            <span className="adm-subtext">
              {user.last_active_at ? `Last active ${formatDate(user.last_active_at)}` : 'Never active'}
            </span>
          </span>
        </span>
        <Link
          className="adm-btn adm-btn-ghost adm-btn-sm adm-push-right"
          to={{ pathname: '/admin/assignments', search: assignmentsSearch }}
        >
          <GridIcon /> Assignments
        </Link>
      </div>

      <div className="adm-grid-31">
        <Card title="Assessment results" actions={<span className="adm-card-hint">the answers behind the maturity level</span>}>
          {surveyQuery.isLoading ? (
            <div className="adm-loading">
              <Spinner />
            </div>
          ) : surveyQuery.error ? (
            <ErrorState message={surveyQuery.error.message} onRetry={() => void surveyQuery.refetch()} />
          ) : surveyQuery.data ? (
            <SurveyResults survey={surveyQuery.data} />
          ) : (
            <NotAssessed user={user} />
          )}
        </Card>

        <div>
          <AccountCard user={user} survey={surveyQuery.data} onDeleted={handleDeleted} />
          <LearningProgressCard user={user} />
        </div>
      </div>

      <Card title="AI interview">
        <InterviewCard userId={userId} />
      </Card>
    </div>
  )
}

function statusInfo(user: AdminUserEnriched): { tone: ChipTone; label: string } {
  if (user.needs_attention) return { tone: 'warn', label: 'Needs attention' }
  if (user.activated) return { tone: 'good', label: 'Active' }
  return { tone: 'default', label: 'Invited' }
}

function initials(name: string): string {
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function roleClass(role: string): 'admin' | 'user-plus' | 'user' {
  if (role === 'admin') return 'admin'
  if (role === 'user+') return 'user-plus'
  return 'user'
}

// ── Assessment card, not-assessed state ─────────────────────────────────────

/** Mirrors DashboardPage's AttentionRow reminder-feedback convention (same
 * email_status → short text mapping). */
function NotAssessed({ user }: { user: AdminUserEnriched }) {
  const sendReminder = useSendReminder()

  // attention_reason (Task 8 enrichment) already carries the specific reason
  // when the backend has flagged this user; fall back to the two generic
  // cases the brief calls out, derived from `activated`, when it hasn't.
  const why = user.attention_reason ?? (user.activated ? 'Activated but not started.' : 'Invite not redeemed.')

  const status = sendReminder.data?.email_status
  const feedback = sendReminder.isError
    ? 'Failed to send'
    : status === 'sent'
      ? 'Reminder sent'
      : status === 'failed'
        ? 'Failed to send'
        : status === 'disabled'
          ? 'Email not configured'
          : status === 'skipped'
            ? 'Reminder skipped'
            : null

  return (
    <div className="adm-empty">
      <p className="adm-empty-title">No completed assessment yet</p>
      <p className="adm-empty-hint">{why}</p>
      <div className="adm-modal-section">
        {feedback && <p className="adm-form-msg adm-form-msg-ok">{feedback}</p>}
        <button
          type="button"
          className="adm-btn adm-btn-ghost adm-btn-sm"
          disabled={sendReminder.isPending}
          onClick={() => sendReminder.mutate(user.id)}
        >
          {sendReminder.isPending ? <Spinner size="sm" /> : <MailIcon />} Send reminder
        </button>
      </div>
    </div>
  )
}

// ── Account card ─────────────────────────────────────────────────────────────

interface AccountCardProps {
  user: AdminUserEnriched
  survey: AdminSurvey | null | undefined
  onDeleted: () => void
}

function AccountCard({ user, survey, onDeleted }: AccountCardProps) {
  const setRole = useSetRole()
  const setMaturity = useSetMaturity()
  const resetLink = useResetLink()
  const deleteUser = useDeleteUser()

  const [copied, setCopied] = useState(false)
  const [resetDismissed, setResetDismissed] = useState(false)

  function handleGenerateReset(sendEmail: boolean) {
    setResetDismissed(false)
    setCopied(false)
    resetLink.mutate({ userId: user.id, sendEmail })
  }

  function copyResetLink() {
    if (!resetLink.data) return
    void navigator.clipboard.writeText(resetLink.data.link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleDelete() {
    deleteUser.mutate(user.id, { onSuccess: onDeleted })
  }

  return (
    <Card title="Account">
      <div className="adm-acct-row">
        <span className="adm-acct-label">Role</span>
        <select
          className={`adm-select adm-role-select-${roleClass(user.role)}`}
          disabled={setRole.isPending}
          value={user.role}
          onChange={e => setRole.mutate({ userId: user.id, role: e.target.value as SetRoleInput['role'] })}
        >
          <option value="user">User</option>
          <option value="user+">User+</option>
          <option value="admin">Admin</option>
        </select>
        <span className="adm-subtext">user / user+ / admin</span>
      </div>
      {setRole.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {setRole.error instanceof Error ? setRole.error.message : 'Failed to update the role.'}
        </p>
      )}

      {/* Maturity pin — ported verbatim from the old panel's inline
          participant detail component: same value (`maturity_override ?? ''`),
          same two option groups ("From assessment" + PIN_LEVELS), same
          effective-level badge via LevelBadge, same onChange payload
          (`level: value || null`). Only the styling moved from inline
          CSSProperties to adm- classes. */}
      <div className="adm-acct-row">
        <span className="adm-acct-label">Maturity</span>
        {user.effective_maturity ? <LevelBadge level={user.effective_maturity} /> : <span className="adm-subtext">none yet</span>}
        {user.maturity_override && <Chip tone="info">Pinned</Chip>}
        <select
          className="adm-select adm-push-right"
          disabled={setMaturity.isPending}
          value={user.maturity_override ?? ''}
          onChange={e =>
            setMaturity.mutate({ userId: user.id, level: (e.target.value || null) as SetMaturityInput['level'] })
          }
        >
          <option value="">
            From assessment{survey?.score_level ? ` (${levelByCode(survey.score_level)?.name ?? survey.score_level})` : ''}
          </option>
          {PIN_LEVELS.map(l => (
            <option key={l.code} value={l.code}>
              Pin to {l.name}
            </option>
          ))}
        </select>
      </div>
      {setMaturity.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {setMaturity.error instanceof Error ? setMaturity.error.message : 'Failed to update the maturity level.'}
        </p>
      )}

      {/* Two actions over one endpoint, mirroring InviteModal's send/link-only
          split: the spinner tracks `resetLink.variables` so it lands on the
          button that was actually clicked, not on both. */}
      <div className="adm-acct-row">
        <span className="adm-acct-label">Password</span>
        <button
          type="button"
          className="adm-btn adm-btn-ghost adm-btn-sm"
          disabled={resetLink.isPending}
          onClick={() => handleGenerateReset(true)}
        >
          {resetLink.isPending && resetLink.variables?.sendEmail ? <Spinner size="sm" /> : <MailIcon />} Send
          reset link
        </button>
        <button
          type="button"
          className="adm-btn adm-btn-ghost adm-btn-sm"
          disabled={resetLink.isPending}
          onClick={() => handleGenerateReset(false)}
        >
          {resetLink.isPending && resetLink.variables?.sendEmail === false && <Spinner size="sm" />} Create
          reset link
        </button>
      </div>
      {resetLink.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {resetLink.error instanceof Error ? resetLink.error.message : 'Failed to generate a reset link.'}
        </p>
      )}

      {/* Reset-link result — same emailed/failed/plain copy + copyable
          fallback as the old panel's reset-link entry (since removed),
          reusing the adm-link-box family InviteModal already established. */}
      {resetLink.data && !resetDismissed && (
        <div className="adm-link-box">
          <p className="adm-link-box-label">
            {resetLink.data.email_status === 'sent'
              ? 'Password reset link — emailed to the participant (fallback below)'
              : resetLink.data.email_status === 'failed'
                ? 'Email failed — send this link to the participant'
                : 'Password reset link — send this to the participant'}
          </p>
          {/* Issuing a reset token revokes the user's prior unused ones, so any
              link handed out earlier (emailed or copied) is now dead. True of
              both actions, hence unconditional. */}
          <p className="adm-hint">
            This replaces any earlier reset link for this participant — older links stop working.
          </p>
          <div className="adm-link-row">
            <input className="adm-link-input" readOnly value={resetLink.data.link} onFocus={e => e.target.select()} />
            <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" onClick={copyResetLink}>
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button type="button" className="adm-btn adm-btn-subtle adm-btn-sm" onClick={() => setResetDismissed(true)}>
              Dismiss
            </button>
          </div>
        </div>
      )}

      <div className="adm-acct-row">
        <span className="adm-acct-label">Danger</span>
        <ConfirmButton
          label="Remove participant"
          confirmLabel="Confirm removal"
          busy={deleteUser.isPending}
          onConfirm={handleDelete}
        />
      </div>
      {deleteUser.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {deleteUser.error instanceof Error ? deleteUser.error.message : 'Failed to remove this participant.'}
        </p>
      )}
    </Card>
  )
}

// ── Learning progress card ───────────────────────────────────────────────────

/** Real per-track LESSON completion, from the admin enrichment's
 * `track_progress` map (`user.track_progress[trackId] = { assigned,
 * completed }` — lessons assigned to this user in that track vs. how many of
 * those they've completed). Only tracks with ≥1 assigned lesson get a map
 * entry; a track can be assigned to the user with zero assigned lessons
 * (e.g. assigned before any lesson under it was), in which case the entry is
 * absent and the row falls back to a muted "No lessons assigned" instead of
 * a misleading 0/0 bar. */
function LearningProgressCard({ user }: { user: AdminUserEnriched }) {
  const tracksQuery = useTracks()

  const assignedTracks = [...(tracksQuery.data ?? [])]
    .filter(track => user.assigned_track_ids.includes(track.id))
    .sort((a, b) => a.sort_order - b.sort_order)

  return (
    <Card title="Learning progress" actions={<span className="adm-card-hint">lesson completion</span>}>
      {tracksQuery.isLoading ? (
        <div className="adm-loading">
          <Spinner />
        </div>
      ) : tracksQuery.error ? (
        <ErrorState
          message={tracksQuery.error instanceof Error ? tracksQuery.error.message : 'Failed to load learning progress.'}
          onRetry={() => void tracksQuery.refetch()}
        />
      ) : assignedTracks.length === 0 ? (
        <EmptyState title="No tracks assigned" />
      ) : (
        assignedTracks.map(track => {
          const progress = user.track_progress[track.id]
          return (
            <div key={track.id} className="adm-track-progress-row">
              <span className="adm-track-progress-name">{track.name}</span>
              <span className="adm-track-progress-meta">
                {progress ? (
                  <>
                    <ProgressBar completed={progress.completed} total={progress.assigned} />
                    <span className="adm-subtext">
                      {progress.completed} of {progress.assigned} lessons completed
                    </span>
                  </>
                ) : (
                  <span className="adm-subtext">No lessons assigned</span>
                )}
              </span>
            </div>
          )
        })
      )}
    </Card>
  )
}

function MailIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={2} y={4} width={20} height={16} rx={2} />
      <path d="m22 7-10 6L2 7" />
    </svg>
  )
}

function GridIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={3} y={3} width={7} height={7} rx={1} />
      <rect x={14} y={3} width={7} height={7} rx={1} />
      <rect x={14} y={14} width={7} height={7} rx={1} />
      <rect x={3} y={14} width={7} height={7} rx={1} />
    </svg>
  )
}
