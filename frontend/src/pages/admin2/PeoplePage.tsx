import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LevelBadge, formatDate } from '../admin/adminHelpers'
import BulkInviteModal from '../admin/BulkInviteModal'
import type { AdminUserEnriched } from '../../types/domain'
import {
  useAdminUsers,
  useBulkAssignUsers,
  useCompanies,
  useLearning,
  useSendReminder,
  useSetRole,
  useTracks,
} from './api'
import InviteModal from './InviteModal'
import { BulkBar, Card, Chip, EmptyState, ErrorState, Modal, ProgressBar, Spinner, Table, Toolbar } from './kit'
import type { ChipTone, TableColumn } from './kit'
import { useScope } from './useScope'

const PAGE_SIZE = 50
type StatusFilter = 'active' | 'invited' | 'attention' | undefined

const STATUS_PILLS: { value: StatusFilter; label: string }[] = [
  { value: undefined, label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'invited', label: 'Invited' },
  { value: 'attention', label: 'Needs attention' },
]

const ROLE_LABEL: Record<string, string> = { admin: 'Admin', 'user+': 'User+', user: 'User' }

/** People screen (spec §3.2, `/admin/people`). Server-driven search + status
 * pills + pager per the contract — `useAdminUsers` threads {q,status,page}
 * through its cache key AND (since the Task 11 reconciliation) `fetchAdminUsers`
 * forwards q/status/limit/offset to the backend and reads the server-computed
 * `total`, so search/filter/pagination are fully functional, not client-side.
 * Prototype: docs/design-prototypes/admin-redesign option-b.html `people()`
 * + common.js `peopleTableHTML()` / `wirePeopleTable()`. */
export default function PeoplePage() {
  const scope = useScope()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const unscoped = scope.projectId === null

  const [q, setQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [status, setStatus] = useState<StatusFilter>(undefined)
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const [inviteOpen, setInviteOpen] = useState(false)
  const [bulkCsvOpen, setBulkCsvOpen] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [roleOpen, setRoleOpen] = useState(false)
  const [bulkMessage, setBulkMessage] = useState<string | null>(null)

  // Debounce the raw search box 300ms before it feeds the query (contract §3.2).
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300)
    return () => clearTimeout(timer)
  }, [q])

  // A filter/scope change invalidates the current page.
  useEffect(() => setPage(1), [debouncedQ, status, scope.projectId])

  // Known kit caveat (Task 13): Table's all-selected checkbox assumes the
  // selection is a subset of the rendered rows. Clear it on every axis that
  // can change which rows are rendered, so stale ids never linger over rows
  // that are no longer there (or feed a bulk action invisibly).
  useEffect(() => setSelected(new Set()), [debouncedQ, status, page, scope.projectId])

  // The above can fire while an Assign/Change-role modal is open (e.g. a
  // browser back/forward navigation changing ?project= without touching the
  // overlay) — close it too, so it never operates on a stale, now-empty
  // selection snapshot.
  useEffect(() => {
    if (selected.size === 0) {
      setAssignOpen(false)
      setRoleOpen(false)
    }
  }, [selected])

  useEffect(() => {
    if (!bulkMessage) return
    const timer = setTimeout(() => setBulkMessage(null), 4000)
    return () => clearTimeout(timer)
  }, [bulkMessage])

  const { data, isLoading, error, refetch } = useAdminUsers({
    project: scope.projectId,
    q: debouncedQ.trim() || undefined,
    status,
    page,
  })

  const { data: companies } = useCompanies()
  const scopedProject = companies
    ?.flatMap(company => company.projects.map(project => ({ ...project, companyName: company.name })))
    .find(project => project.id === scope.projectId)

  const sendReminder = useSendReminder()
  const [reminderBusy, setReminderBusy] = useState(false)

  const columns = useMemo<TableColumn<AdminUserEnriched>[]>(() => {
    const cols: TableColumn<AdminUserEnriched>[] = [
      { key: 'participant', header: 'Participant', render: row => <ParticipantCell row={row} /> },
    ]
    if (unscoped) {
      cols.push({ key: 'project', header: 'Project', render: row => <Chip>{row.company_name ?? '—'}</Chip> })
    }
    cols.push(
      {
        key: 'status',
        header: 'Status',
        render: row => {
          const info = statusInfo(row)
          return <Chip tone={info.tone}>{info.label}</Chip>
        },
      },
      { key: 'maturity', header: 'Maturity', render: row => <MaturityCell row={row} /> },
      {
        key: 'progress',
        header: 'Progress',
        render: row => <ProgressBar completed={row.completed_lesson_count} total={row.assigned_lesson_count} />,
      },
      {
        key: 'last_active',
        header: 'Last active',
        render: row => (row.last_active_at ? <span>{formatDate(row.last_active_at)}</span> : <span className="adm-subtext">—</span>),
      },
      {
        key: 'role',
        header: 'Role',
        render: row => <Chip tone={roleTone(row.role)}>{ROLE_LABEL[row.role] ?? row.role}</Chip>,
      },
    )
    return cols
  }, [unscoped])

  if (isLoading) {
    return (
      <div className="adm-loading">
        <Spinner />
      </div>
    )
  }

  if (error || !data) {
    return <ErrorState message={error?.message ?? 'Failed to load participants.'} onRetry={() => void refetch()} />
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  function handleRowClick(row: AdminUserEnriched) {
    navigate({ pathname: `/admin/people/${row.id}`, search: scope.projectId ? `?project=${scope.projectId}` : '' })
  }

  async function handleSendReminder() {
    const ids = [...selected]
    if (ids.length === 0) return
    setReminderBusy(true)
    setBulkMessage(null)
    const results = await Promise.allSettled(ids.map(id => sendReminder.mutateAsync(id)))
    const failed = results.filter(r => r.status === 'rejected').length
    setReminderBusy(false)
    setBulkMessage(
      failed > 0
        ? `Sent ${ids.length - failed} of ${ids.length} reminders (${failed} failed).`
        : `Sent ${ids.length} reminder${ids.length === 1 ? '' : 's'}.`,
    )
  }

  return (
    <div>
      <div className="adm-page-head">
        <div>
          <h1 className="adm-page-title">People</h1>
          <p className="adm-page-sub">
            {data.total} participant{data.total === 1 ? '' : 's'}
            {unscoped ? ' across all projects' : ' in this project'}
          </p>
        </div>
        <div className="adm-page-actions">
          <button
            type="button"
            className="adm-btn adm-btn-ghost"
            disabled={unscoped}
            title={unscoped ? 'Pick a project to bulk invite' : undefined}
            onClick={() => setBulkCsvOpen(true)}
          >
            Bulk invite (CSV)
          </button>
          <button
            type="button"
            className="adm-btn adm-btn-red"
            disabled={unscoped}
            title={unscoped ? 'Pick a project to invite' : undefined}
            onClick={() => setInviteOpen(true)}
          >
            <PlusIcon /> Invite
          </button>
        </div>
      </div>

      {unscoped && <p className="adm-hint">Pick a project in the scope switcher to invite participants.</p>}

      <Toolbar>
        <span className="adm-search">
          <SearchIcon />
          <input placeholder="Search name or email…" value={q} onChange={e => setQ(e.target.value)} />
        </span>
        <div className="adm-pills">
          {STATUS_PILLS.map(pill => (
            <button
              key={pill.label}
              type="button"
              className={status === pill.value ? 'adm-pill active' : 'adm-pill'}
              onClick={() => setStatus(pill.value)}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </Toolbar>

      {bulkMessage && <p className="adm-form-msg adm-form-msg-ok">{bulkMessage}</p>}

      <Card>
        <div className="adm-table-wrap">
          <Table
            columns={columns}
            rows={data.users}
            rowKey={row => row.id}
            onRowClick={handleRowClick}
            selectable
            selected={selected}
            onSelect={setSelected}
            empty={<EmptyState title="No participants found" hint="Try a different search or filter." />}
          />
        </div>
      </Card>

      <div className="adm-pager">
        <span className="adm-pager-info">
          Page {page} of {totalPages} · {data.total} total
        </span>
        <div className="adm-pager-actions">
          <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            Previous
          </button>
          <button
            type="button"
            className="adm-btn adm-btn-ghost adm-btn-sm"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </button>
        </div>
      </div>

      <BulkBar count={selected.size} onClear={() => setSelected(new Set())}>
        <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" onClick={() => setAssignOpen(true)}>
          <GridIcon /> Assign content
        </button>
        <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" disabled={reminderBusy} onClick={() => void handleSendReminder()}>
          {reminderBusy ? <Spinner size="sm" /> : <MailIcon />} Send reminder
        </button>
        <button type="button" className="adm-btn adm-btn-ghost adm-btn-sm" onClick={() => setRoleOpen(true)}>
          Change role
        </button>
      </BulkBar>

      {assignOpen && (
        <AssignContentModal
          userIds={[...selected]}
          projectId={scope.projectId}
          onClose={() => setAssignOpen(false)}
          onAssigned={() => {
            setAssignOpen(false)
            setSelected(new Set())
          }}
        />
      )}

      {roleOpen && (
        <ChangeRoleModal
          userIds={[...selected]}
          onClose={() => setRoleOpen(false)}
          onDone={() => {
            setRoleOpen(false)
            setSelected(new Set())
          }}
        />
      )}

      {inviteOpen && scope.projectId && (
        <InviteModal
          projectId={scope.projectId}
          projectName={scopedProject ? `${scopedProject.companyName} · ${scopedProject.name}` : 'this project'}
          onClose={() => setInviteOpen(false)}
        />
      )}

      {bulkCsvOpen && scope.projectId && (
        <BulkInviteModal
          projectId={scope.projectId}
          projectName={scopedProject?.name ?? 'this project'}
          onClose={() => setBulkCsvOpen(false)}
          onCommitted={() => {
            void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
          }}
        />
      )}
    </div>
  )
}

function statusInfo(row: AdminUserEnriched): { tone: ChipTone; label: string } {
  if (row.needs_attention) return { tone: 'warn', label: 'Needs attention' }
  if (row.activated) return { tone: 'good', label: 'Active' }
  return { tone: 'default', label: 'Invited' }
}

function roleTone(role: string): ChipTone {
  if (role === 'admin') return 'red'
  if (role === 'user+') return 'info'
  return 'default'
}

function initials(name: string): string {
  return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function ParticipantCell({ row }: { row: AdminUserEnriched }) {
  const name = `${row.first_name} ${row.last_name}`
  return (
    <div className="adm-user-cell">
      <span className="adm-user-avatar">{initials(name)}</span>
      <span>
        <span className="adm-user-name">{name}</span>
        <br />
        <span className="adm-user-email">{row.email}</span>
      </span>
    </div>
  )
}

function MaturityCell({ row }: { row: AdminUserEnriched }) {
  if (!row.effective_maturity) return <span className="adm-subtext">Not assessed</span>
  return (
    <span className="adm-maturity" title={row.maturity_override ? 'Pinned by admin' : undefined}>
      <LevelBadge level={row.effective_maturity} />
      {row.maturity_override && (
        <span className="adm-maturity-pin" aria-label="Pinned by admin">
          📌
        </span>
      )}
    </span>
  )
}

// ── Assign content (BulkBar action) ─────────────────────────────────────────

type AssignKind = 'tracks' | 'modules' | 'lessons'

interface ContentItem {
  id: string
  label: string
}

interface AssignContentModalProps {
  userIds: string[]
  projectId: string | null
  onClose: () => void
  onAssigned: () => void
}

/** One `useBulkAssignUsers()` call per the contract — the admin picks
 * exactly one content kind (tracks OR modules OR lessons), then one or more
 * items of that kind; all selected users get the same content in one
 * `POST /api/admin/assignments/bulk`. */
function AssignContentModal({ userIds, projectId, onClose, onAssigned }: AssignContentModalProps) {
  const tracksQuery = useTracks()
  const learningQuery = useLearning(projectId)
  const bulkAssign = useBulkAssignUsers()
  const [kind, setKind] = useState<AssignKind>('tracks')
  const [picked, setPicked] = useState<Set<string>>(new Set())

  useEffect(() => setPicked(new Set()), [kind])

  const items = useMemo<ContentItem[]>(() => {
    if (kind === 'tracks') {
      return [...(tracksQuery.data ?? [])]
        .sort((a, b) => a.sort_order - b.sort_order)
        .map(track => ({ id: track.id, label: track.name }))
    }
    const tracksById = new Map((tracksQuery.data ?? []).map(track => [track.id, track.name]))
    if (kind === 'modules') {
      return [...(learningQuery.data?.modules ?? [])]
        .sort((a, b) => a.sort_order - b.sort_order)
        .map(module => ({ id: module.id, label: `${tracksById.get(module.track_id) ?? '—'} · ${module.title}` }))
    }
    const modulesById = new Map((learningQuery.data?.modules ?? []).map(module => [module.id, module.title]))
    return [...(learningQuery.data?.lessons ?? [])]
      .sort((a, b) => a.sort_order - b.sort_order)
      .map(lesson => ({ id: lesson.id, label: `${modulesById.get(lesson.module_id) ?? '—'} · ${lesson.title}` }))
  }, [kind, tracksQuery.data, learningQuery.data])

  function toggle(id: string) {
    setPicked(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleAssign() {
    if (picked.size === 0) return
    const ids = [...picked]
    try {
      await bulkAssign.mutateAsync({
        user_ids: userIds,
        assigned: true,
        track_ids: kind === 'tracks' ? ids : undefined,
        module_ids: kind === 'modules' ? ids : undefined,
        lesson_ids: kind === 'lessons' ? ids : undefined,
      })
      onAssigned()
    } catch {
      // surfaced below via bulkAssign.isError/error
    }
  }

  const loading = tracksQuery.isLoading || learningQuery.isLoading

  return (
    <Modal
      title="Assign content"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="adm-btn adm-btn-ghost" disabled={bulkAssign.isPending} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="adm-btn adm-btn-red"
            disabled={bulkAssign.isPending || picked.size === 0}
            onClick={() => void handleAssign()}
          >
            {bulkAssign.isPending && <Spinner size="sm" />}
            Assign to {userIds.length} participant{userIds.length === 1 ? '' : 's'}
          </button>
        </>
      }
    >
      <p className="adm-hint">Choose one content type, then the items to assign.</p>
      <div className="adm-pills">
        <button type="button" className={kind === 'tracks' ? 'adm-pill active' : 'adm-pill'} onClick={() => setKind('tracks')}>
          Tracks
        </button>
        <button type="button" className={kind === 'modules' ? 'adm-pill active' : 'adm-pill'} onClick={() => setKind('modules')}>
          Modules
        </button>
        <button type="button" className={kind === 'lessons' ? 'adm-pill active' : 'adm-pill'} onClick={() => setKind('lessons')}>
          Lessons
        </button>
      </div>

      {loading ? (
        <div className="adm-loading">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <div className="adm-modal-section">
          <EmptyState title="Nothing to assign" hint="No content of this type exists yet." />
        </div>
      ) : (
        <div className="adm-check-list adm-modal-section">
          {items.map(item => (
            <label key={item.id} className="adm-check-row">
              <input type="checkbox" checked={picked.has(item.id)} onChange={() => toggle(item.id)} />
              {item.label}
            </label>
          ))}
        </div>
      )}

      {bulkAssign.isError && (
        <p className="adm-form-msg adm-form-msg-err">
          {bulkAssign.error instanceof Error ? bulkAssign.error.message : 'Failed to assign content.'}
        </p>
      )}
    </Modal>
  )
}

// ── Change role (BulkBar action) ────────────────────────────────────────────

interface ChangeRoleModalProps {
  userIds: string[]
  onClose: () => void
  onDone: () => void
}

/** Client-side fan-out over the existing `PATCH /users/{id}` per user id
 * (spec §4.2 explicitly allows this at our scale — no bulk-role endpoint). */
function ChangeRoleModal({ userIds, onClose, onDone }: ChangeRoleModalProps) {
  const setRole = useSetRole()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function apply(role: 'user' | 'user+' | 'admin') {
    setBusy(true)
    setError(null)
    const results = await Promise.allSettled(userIds.map(userId => setRole.mutateAsync({ userId, role })))
    const failed = results.filter(r => r.status === 'rejected').length
    setBusy(false)
    if (failed > 0) setError(`Failed to update ${failed} of ${userIds.length} participants.`)
    else onDone()
  }

  return (
    <Modal title="Change role" onClose={onClose}>
      <p className="adm-hint">
        Apply a role to {userIds.length} selected participant{userIds.length === 1 ? '' : 's'}.
      </p>
      <div className="adm-pills adm-modal-section">
        <button type="button" className="adm-btn adm-btn-ghost" disabled={busy} onClick={() => void apply('user')}>
          User
        </button>
        <button type="button" className="adm-btn adm-btn-ghost" disabled={busy} onClick={() => void apply('user+')}>
          User+
        </button>
        <button type="button" className="adm-btn adm-btn-ghost" disabled={busy} onClick={() => void apply('admin')}>
          Admin
        </button>
      </div>
      {busy && <p className="adm-hint adm-modal-section">Updating…</p>}
      {error && <p className="adm-form-msg adm-form-msg-err">{error}</p>}
    </Modal>
  )
}

function SearchIcon() {
  return (
    <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx={11} cy={11} r={8} />
      <path d="m21 21-4.35-4.35" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 5v14M5 12h14" />
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

function MailIcon() {
  return (
    <svg width={13} height={13} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x={2} y={4} width={20} height={16} rx={2} />
      <path d="m22 7-10 6L2 7" />
    </svg>
  )
}
