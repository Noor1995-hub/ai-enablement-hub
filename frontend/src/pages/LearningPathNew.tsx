// Learning-path redesign (promoted to /learning 2026-07-08). Runs on REAL data:
// ONE GET /api/learning/graph aggregate carries assigned tracks/modules/
// prerequisites, lesson counts, per-track maturity locks (unlocked_by_maturity +
// required_level) and the caller's effective maturity_level (page header). Module
// CTA navigates via GET /api/modules/{id}/lessons → next_lesson_id, same contract
// as ModulePopup.
//
// Maturity gating (2026-07-08): each track has a required_level; a track the
// caller's effective maturity doesn't reach renders as a locked, non-expandable
// lane ("Unlocks at {Level}"). Maturity gates whole tracks; prerequisites still
// gate modules WITHIN an unlocked track. Admins bypass both. Completing a level's
// modules advances maturity server-side, so returning here unlocks the next
// track automatically (the self-propelling ladder).
//
// Design decisions (2026-07-08):
// - White page, red caps eyebrow + bold title header (second mockup's style).
// - Overall bar = one continuous 4-color fill with level checkpoint dots;
//   levels below the assessed level count as complete (Practitioner = 25%).
// - Core trunk gets no special treatment ("can be skipped"): the general
//   track renders as a normal row; locking still follows real prerequisites.
// - Tracks are collapsible lanes; the expanded lane draws the track's real
//   prerequisite DAG left-to-right (same rank algorithm as the live page).
//
// Level group headers (2026-07-14): the lane list is grouped under per-level
// section headers — a journey-bar-style checkpoint dot (border always in the
// level color so the color↔level mapping survives the locked state), level
// name + tagline, and that level's own progress bar/counts. The old top-panel
// "{level} progress" bar moved into these headers; the panel keeps the level
// card + overall journey bar. Levels passed via assessment show ACTUAL module
// progress (the dot carries "passed", the bar agrees with the lanes). Spec:
// docs/superpowers/specs/2026-07-14-learning-path-level-headers-design.md

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { client } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import Spinner from '../components/Spinner'
import ModulePanel from '../components/ModulePanel'
import AddTrackModal from '../components/AddTrackModal'
import AddModuleModal from '../components/AddModuleModal'
import { LEVELS, LEVEL_GRADIENT, levelByCode, INTRODUCTION_LEVEL } from '../lib/levels'
import { resolveTrackColor, FALLBACK_TRACK_COLOR } from '../lib/trackColors'
import { getRectZoomFactor } from '../lib/uiZoom'
import type { ModuleNode, TrackNode } from '../types/domain'

/* ── Lane geometry ── */
const NODE = 56            // node diameter
const RANK_X0 = 96         // x of the first rank's centre
const RANK_DX = 178        // x distance between ranks
const BRANCH_DY = 118      // y distance between parallel modules in a rank
const LANE_MIN_H = 170
const POPOVER_W = 330

/* ── Persisted open lane (per user; multiple people share a browser) ── */
const OPEN_TRACK_KEY = (userId: string) => `hub.learning.openTrack.${userId}`

// undefined = no stored preference; null = explicitly collapsed; string = track id
function readStoredOpenTrack(userId: string): string | null | undefined {
  try {
    const raw = localStorage.getItem(OPEN_TRACK_KEY(userId))
    if (raw === null) return undefined
    return raw === '' ? null : raw
  } catch { return undefined }
}

function writeStoredOpenTrack(userId: string, value: string | null): void {
  try { localStorage.setItem(OPEN_TRACK_KEY(userId), value ?? '') } catch { /* ignore */ }
}

// The synthetic group code for Introduction tracks (they are NOT a maturity
// level, so they must not group with their required_level='explore' peers).
const INTRO_GROUP = 'introduction'
function groupCode(track: TrackNode): string {
  return track.is_introduction ? INTRO_GROUP : track.required_level
}

// Maturity-ladder rank of a track. Introduction sorts before every level.
function trackRank(track: TrackNode): number {
  if (track.is_introduction) return -1
  const i = LEVELS.findIndex(l => l.code === track.required_level)
  return i === -1 ? LEVELS.length : i
}

/* ── Un-assessed display state ──
   A learner with no completed survey and no admin maturity_override gets
   maturity_level: null from the graph. `levelIdx` deliberately clamps that to
   Explorer (0) because it also drives layout maths and the below-level review
   rule in isUnlocked — so every LEVEL-DERIVED DISPLAY value has to be
   suppressed explicitly instead of being read off levelIdx. Without that, the
   page tells an un-placed learner they are Explorer while padlocking Explorer
   content ("Unlocks at Explorer"). Spec:
   docs/superpowers/specs/2026-08-04-unassessed-path-signpost-design.md */
const NOT_ASSESSED_NAME = 'Not assessed yet'
const NOT_ASSESSED_TAGLINE = 'The assessment sets your level'
const NOT_ASSESSED_PROGRESS = 'not started yet'
const NOT_ASSESSED_SUBTITLE =
  'Your maturity assessment decides which tracks open up and how far along the ' +
  'path you start. Take it first. It takes about 10 minutes.'
/** Unchanged copy, moved from JSX to a constant so the two variants sit side by
    side. JSX was collapsing its whitespace, so it is written pre-collapsed here
    and renders character-for-character as it does today. */
const ASSESSED_SUBTITLE =
  'Based on your maturity assessment, these tracks are tailored to where you ' +
  'are today. Work through them at your own pace each module builds on the last.'
/** Locked-lane subtitle while the learner has no level at all. Wins over
    "Unlocks at {Level}", which wrong-foots someone who was never placed. */
const LOCKED_UNTIL_ASSESSED = 'Take the assessment to unlock'
/** Locked-lane accent while un-assessed: no level colour has been earned. */
const NEUTRAL_LOCK_COLOR = '#8A8A8A'

/** Overall-journey checkpoint state for level `i`. Un-assessed learners have
    nothing passed and nothing current — the bar reads empty, not "Explorer". */
function checkpointState(
  i: number,
  levelIdx: number,
  levelFraction: number,
  notAssessed: boolean,
): { passed: boolean; current: boolean } {
  if (notAssessed) return { passed: false, current: false }
  const passed = i < levelIdx || (i === levelIdx && levelFraction >= 1)
  return { passed, current: !passed && i === levelIdx }
}

/** Level-group header state (dot fill, tick, weight).
    - Introduction keys off its own completion; it is not a maturity level and
      is unaffected by whether the learner has been assessed.
    - Maturity groups go fully inert when un-assessed: no group may read as
      "current" or "passed" when the learner has no level at all. */
function groupHeaderState(args: {
  isIntroGroup: boolean
  introComplete: boolean
  groupIdx: number
  levelIdx: number
  fraction: number
  modulesTotal: number
  notAssessed: boolean
}): { isCurrent: boolean; contentComplete: boolean; showOpenDot: boolean } {
  const { isIntroGroup, introComplete, groupIdx, levelIdx, fraction, modulesTotal, notAssessed } = args
  if (isIntroGroup) {
    return {
      isCurrent: !introComplete,
      contentComplete: introComplete,
      showOpenDot: !introComplete && groupIdx <= levelIdx,
    }
  }
  if (notAssessed) {
    return { isCurrent: false, contentComplete: false, showOpenDot: false }
  }
  // `passed` stays local: it only ever fed isCurrent, never the JSX.
  const passed =
    groupIdx !== -1 && (groupIdx < levelIdx || (groupIdx === levelIdx && fraction >= 1))
  const contentComplete = groupIdx !== -1 && modulesTotal > 0 && fraction >= 1
  return {
    isCurrent: !passed && groupIdx === levelIdx,
    contentComplete,
    showOpenDot: !contentComplete && groupIdx <= levelIdx,
  }
}

function lighten(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.min(255, (n >> 16) + amt)
  const g = Math.min(255, ((n >> 8) & 255) + amt)
  const b = Math.min(255, (n & 255) + amt)
  return `rgb(${r},${g},${b})`
}

/* ── Icons ── */
function LockGlyph({ size = 17, stroke = '#fff' }: { size?: number; stroke?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={stroke} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="9" rx="2.5" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  )
}
function CheckGlyph({ size = 20, stroke = '#fff' }: { size?: number; stroke?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" fill="none"
      stroke={stroke} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3.5 9.5l3.5 3.5 7.5-8" />
    </svg>
  )
}

/* ── Per-track progress ring (row header) ── */
function ProgressRing({ color, frac }: { color: string; frac: number }) {
  const circ = 2 * Math.PI * 18
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" style={{ flexShrink: 0 }}>
      <circle cx="22" cy="22" r="18" fill="none" stroke="#EFEDEA" strokeWidth="5" />
      <circle cx="22" cy="22" r="18" fill="none" stroke={color} strokeWidth="5"
        strokeLinecap="round" strokeDasharray={`${(circ * frac).toFixed(1)} ${circ.toFixed(1)}`}
        transform="rotate(-90 22 22)" />
      <circle cx="22" cy="22" r="6" fill={color} />
    </svg>
  )
}

interface LaneNode { mod: ModuleNode; x: number; y: number; index: number }
interface LaneEdge { id: string; d: string; stroke: string; dash: string }
interface LaneLayout { nodes: LaneNode[]; edges: LaneEdge[]; height: number; width: number }

interface PopoverState { mod: ModuleNode; anchor: DOMRect }

/* ── Per-level content aggregate (drives the group headers + overall bar) ── */
interface LevelStats { modulesTotal: number; modulesDone: number; lessonsTotal: number; lessonsDone: number }
const EMPTY_LEVEL_STATS: LevelStats = { modulesTotal: 0, modulesDone: 0, lessonsTotal: 0, lessonsDone: 0 }
const lessonFraction = (st: LevelStats): number =>
  st.lessonsTotal > 0 ? st.lessonsDone / st.lessonsTotal : 0

export default function LearningPathNew() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [tracks, setTracks] = useState<TrackNode[]>([])
  const [modulesMap, setModulesMap] = useState<Record<string, ModuleNode[]>>({})
  const [prereqMap, setPrereqMap] = useState<Map<string, string[]>>(new Map())
  // module_id → maturity-level rank of its track (over the FULL graph, so an
  // unassigned lower-level predecessor is still recognised). Drives predSatisfied.
  const [moduleLevelRank, setModuleLevelRank] = useState<Map<string, number>>(new Map())
  const [levelCode, setLevelCode] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [openTrackId, setOpenTrackId] = useState<string | null>(null)
  const [popover, setPopover] = useState<PopoverState | null>(null)
  const [ctaLoading, setCtaLoading] = useState(false)

  // Admin edit mode (ported from the live /learning page, tailored to lanes):
  // toggle → per-node click opens ModulePanel; banner adds tracks/modules.
  const [isEditMode, setIsEditMode] = useState(false)
  const [editingModule, setEditingModule] = useState<{ id: string; title: string } | null>(null)
  const [showAddTrack, setShowAddTrack] = useState(false)
  const [showAddModule, setShowAddModule] = useState(false)
  const [loadKey, setLoadKey] = useState(0) // bump to re-fetch the graph after an edit

  const userId = user?.id
  const isAdmin = user?.role === 'admin'
  // 'user+' rides the same learning-path lock bypass as admins (prerequisites,
  // Introduction gate, maturity gating) but has NO admin powers — edit mode and
  // the add-track/module controls stay gated on isAdmin below. See the
  // 2026-07-22 user-plus-role spec.
  const canBypassLocks = isAdmin || user?.role === 'user+'
  const reload = () => setLoadKey(k => k + 1)

  /* ── Load: one graph aggregate (maturity level + locks come with it) ── */
  useEffect(() => {
    if (!userId) return
    let cancelled = false
    setLoadError(null)

    async function load() {
      const graphRes = await client.GET('/api/learning/graph')
      if (cancelled) return
      if (!graphRes.data) { setLoadError('Failed to load your tracks. Please refresh.'); return }

      // Same filtering semantics as the live /learning page: assigned tracks,
      // assigned modules within them, prereq rows keyed on assigned modules
      // (an unassigned prerequisite stays un-completable → locked). Ordered by
      // the maturity ladder [rank(required_level), sort_order] so General I →
      // General II → tool tracks read top-to-bottom.
      const assignedTracks = graphRes.data.tracks
        .filter(t => t.assigned)
        .sort((a, b) => trackRank(a) - trackRank(b) || a.sort_order - b.sort_order)

      const trackIds = new Set(assignedTracks.map(t => t.id))
      const assignedModules = graphRes.data.modules
        .filter(m => m.assigned && trackIds.has(m.track_id))
        .sort((a, b) => a.sort_order - b.sort_order)

      const map: Record<string, ModuleNode[]> = {}
      for (const mod of assignedModules) {
        ;(map[mod.track_id] ??= []).push(mod)
      }

      const assignedIds = new Set(assignedModules.map(m => m.id))
      const pMap = new Map<string, string[]>()
      for (const row of graphRes.data.prerequisites) {
        if (!assignedIds.has(row.module_id)) continue
        if (!pMap.has(row.module_id)) pMap.set(row.module_id, [])
        pMap.get(row.module_id)!.push(row.prerequisite_module_id)
      }

      // Maturity-level rank of EVERY module (by its track's required_level, over
      // the FULL unfiltered graph so an unassigned lower-level predecessor is
      // still recognised). Lets predSatisfied treat a prerequisite that points
      // into an already-maturity-cleared lower level as satisfied.
      const trackRankById = new Map<string, number>()
      for (const t of graphRes.data.tracks) {
        const r = LEVELS.findIndex(l => l.code === t.required_level)
        if (r !== -1) trackRankById.set(t.id, r)
      }
      const modRank = new Map<string, number>()
      for (const m of graphRes.data.modules) {
        const r = trackRankById.get(m.track_id)
        if (r !== undefined) modRank.set(m.id, r)
      }

      setTracks(assignedTracks)
      setModulesMap(map)
      setPrereqMap(pMap)
      setModuleLevelRank(modRank)
      // Effective maturity (override- and progression-aware) — no separate
      // /api/survey/me call; the graph carries the header level now.
      setLevelCode(graphRes.data.maturity_level ?? null)
      setLoaded(true)
    }

    load()
    return () => { cancelled = true }
    // loadKey re-runs the fetch after an edit. Returning from a lesson remounts
    // this page (React Router swaps /learning ↔ /learning/lesson/:id), so the
    // graph reloads and unlocked_by_maturity is recomputed server-side — the
    // next track unlocks itself with no client logic (the self-propelling
    // ladder). `loaded` stays true across loadKey so the graph never flashes
    // back to the spinner.
  }, [userId, loadKey])

  /* ── Progress lookups ── */
  const moduleById = useMemo(() => {
    const m = new Map<string, ModuleNode>()
    for (const mods of Object.values(modulesMap)) for (const mod of mods) m.set(mod.id, mod)
    return m
  }, [modulesMap])

  const isDone = (id: string): boolean => {
    const mod = moduleById.get(id)
    return !!mod && mod.lesson_count > 0 && mod.completed_lesson_count >= mod.lesson_count
  }

  // Introduction gate: the pre-Explorer track(s) must be finished before any
  // other track unlocks. Lesson-based (matches the group bar) with the guard
  // that an EMPTY Introduction (no lessons yet) leaves the gate OPEN, so
  // shipping the empty track changes nothing until content is published.
  const introComplete = useMemo(() => {
    const introMods = tracks
      .filter(t => t.is_introduction)
      .flatMap(t => modulesMap[t.id] ?? [])
    const total = introMods.reduce((n, m) => n + m.lesson_count, 0)
    const done = introMods.reduce(
      (n, m) => n + Math.min(m.completed_lesson_count, m.lesson_count),
      0,
    )
    return total === 0 || done >= total
  }, [tracks, modulesMap])

  // A prerequisite is satisfied either by completion, OR — when it points into a
  // strictly-lower maturity level than the dependent module's track — by the
  // learner's maturity alone. isUnlocked only reaches the prereq check for a
  // maturity-unlocked module, so its effective level already covers every
  // lower-level track; re-gating on those cross-track (general → tool) edges
  // would block a pinned/skip-ahead learner on general modules the ladder never
  // required them to walk. Same-track and same-level prerequisites still gate.
  const predSatisfied = (predId: string, dependentId: string): boolean => {
    const myRank = moduleLevelRank.get(dependentId)
    const pRank = moduleLevelRank.get(predId)
    if (myRank !== undefined && pRank !== undefined && pRank < myRank) return true
    return isDone(predId)
  }
  const isUnlocked = (id: string): boolean => {
    if (canBypassLocks) return true // admin + user+ bypass, same as the live page
    const mod = moduleById.get(id)
    if (mod?.unlocked_by_maturity === false) return false
    // Introduction gate: modules OUTSIDE the Introduction track stay locked
    // until the Introduction is complete.
    if (mod && !mod.is_introduction && !introComplete) return false
    // Below-level tracks are already "mastered": a module whose track sits at a
    // maturity level strictly below the learner's effective level is fully
    // unlocked — the whole prerequisite path is bypassed so the learner can
    // freely review it (levels below the assessed level count as complete, the
    // same model the overall bar uses). Current-level and higher tracks still
    // gate: higher levels never reach here (unlocked_by_maturity === false
    // above), and same-level prerequisites fall through to predSatisfied below.
    const rank = moduleLevelRank.get(id)
    if (rank !== undefined && rank < levelIdx) return true
    const preds = prereqMap.get(id)
    if (!preds || preds.length === 0) return true
    return preds.every(p => predSatisfied(p, id))
  }
  const firstCurrent = (mods: ModuleNode[]): ModuleNode | null =>
    mods.find(m => !isDone(m.id) && isUnlocked(m.id)) ?? null

  // Maturity gate: a track (and, by inheritance, its modules/lessons) is locked
  // when the caller's effective maturity is below its required_level. Admins
  // bypass it, same as the prerequisite lock.
  const isTrackLocked = (track: TrackNode): boolean => {
    if (canBypassLocks) return false
    // The Introduction track itself is never gated by its own completion; it is
    // force-unlocked server-side (unlocked_by_maturity true even w/o maturity).
    if (track.is_introduction) return !track.unlocked_by_maturity
    return !track.unlocked_by_maturity || !introComplete
  }

  /* ── Level + header math ── */
  // levelIdx clamps a missing level to Explorer(0) for layout maths and for the
  // below-level review rule in isUnlocked. `notAssessed` is what the DISPLAY
  // branches on, so an un-placed learner is never rendered as an Explorer.
  const resolvedLevelIdx = LEVELS.findIndex(l => l.code === levelCode)
  const levelIdx = Math.max(0, resolvedLevelIdx)
  const level = LEVELS[levelIdx]
  // Gated on `loaded` because levelCode starts null and the page header renders
  // BEFORE the graph arrives: an un-gated flag briefly told every assessed
  // learner to go take the assessment they had already done. Keyed on
  // resolvedLevelIdx rather than `levelCode === null` so a level code outside
  // LEVELS cannot clamp to Explorer(0) and resurface the same bug.
  const notAssessed = loaded && resolvedLevelIdx === -1

  // Progress is aggregated PER maturity level. A module's level is its track's
  // required_level, so each level-group header (and the current-level term of
  // the overall bar) counts only modules in tracks at that level. This mirrors
  // the server's advance_level (it clears one rung over the modules AT that
  // level), so no bar is diluted by other levels' tracks. Header text counts
  // modules; the bar fraction is lesson-based — the same split the old single
  // "{level} progress" bar used.
  const trackLevelById = useMemo(() => {
    const m = new Map<string, string>()
    for (const t of tracks) m.set(t.id, groupCode(t))
    return m
  }, [tracks])
  const levelStats = useMemo(() => {
    const stats = new Map<string, LevelStats>()
    for (const mods of Object.values(modulesMap)) {
      for (const m of mods) {
        const code = trackLevelById.get(m.track_id)
        if (!code) continue
        let st = stats.get(code)
        if (!st) { st = { ...EMPTY_LEVEL_STATS }; stats.set(code, st) }
        st.modulesTotal += 1
        if (m.lesson_count > 0 && m.completed_lesson_count >= m.lesson_count) st.modulesDone += 1
        st.lessonsTotal += m.lesson_count
        st.lessonsDone += Math.min(m.completed_lesson_count, m.lesson_count)
      }
    }
    return stats
  }, [modulesMap, trackLevelById])
  const levelFraction = lessonFraction(levelStats.get(level.code) ?? EMPTY_LEVEL_STATS)

  // Each level below the current one is a whole completed segment (levelIdx); the
  // current level's fraction fills its own segment; locked higher levels are 0.
  const overallPct = Math.round(((levelIdx + levelFraction) / LEVELS.length) * 100)

  // Contiguous runs of equal required_level over the ladder-sorted track list —
  // each run renders as one level group (header + lanes). Unknown levels sort
  // last (trackRank) and keep their raw code as the group key.
  const trackGroups = useMemo(() => {
    const groups: { levelCode: string; tracks: TrackNode[] }[] = []
    for (const t of tracks) {
      const code = groupCode(t)
      const last = groups[groups.length - 1]
      if (last && last.levelCode === code) last.tracks.push(t)
      else groups.push({ levelCode: code, tracks: [t] })
    }
    return groups
  }, [tracks])

  /* ── Default open lane: restore the learner's last choice, else the first
        track with something actionable ── */
  useEffect(() => {
    if (!loaded || tracks.length === 0 || !userId) return
    setOpenTrackId(prev => {
      if (prev !== null) return prev
      const stored = readStoredOpenTrack(userId)
      if (stored === null) return null                                // explicitly collapsed
      const storedTrack = stored ? tracks.find(t => t.id === stored) : undefined
      if (storedTrack) return storedTrack.id  // restore whatever was open (locked tracks are previewable too)
      // Smart default: first unlocked track with something actionable, else the
      // first unlocked track, else the first track (maturity-locked lanes never
      // auto-open — they render inert).
      const openable = tracks.filter(t => !isTrackLocked(t))
      const active = openable.find(t => firstCurrent(modulesMap[t.id] ?? []) !== null)
      return (active ?? openable[0] ?? tracks[0]).id
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, tracks, userId])

  /* ── Expanded-lane layout (real prerequisite DAG, left→right) ── */
  const laneLayout = useMemo((): LaneLayout | null => {
    const mods = openTrackId ? modulesMap[openTrackId] : undefined
    if (!openTrackId || !mods || mods.length === 0) return null
    const track = tracks.find(t => t.id === openTrackId)
    const color = track ? resolveTrackColor(track) : FALLBACK_TRACK_COLOR
    const ids = mods.map(m => m.id)
    const idSet = new Set(ids)

    // ASAP rank: one column right of the latest same-track predecessor
    // (same algorithm as the live page's buildGraph, rotated 90°).
    const rank = new Map<string, number>()
    const getRank = (id: string): number => {
      if (rank.has(id)) return rank.get(id)!
      rank.set(id, 0) // cycle guard
      const preds = (prereqMap.get(id) ?? []).filter(p => idSet.has(p))
      const r = preds.length === 0 ? 0 : Math.max(...preds.map(getRank)) + 1
      rank.set(id, r)
      return r
    }
    ids.forEach(getRank)

    const rows: ModuleNode[][] = []
    for (const mod of mods) {
      const r = rank.get(mod.id)!
      ;(rows[r] ??= []).push(mod)
    }

    const maxBranch = Math.max(1, ...rows.map(r => r.length))
    const height = Math.max(LANE_MIN_H, maxBranch * BRANCH_DY + 64)
    const pos = new Map<string, { x: number; y: number }>()
    rows.forEach((row, r) => {
      row.forEach((mod, j) => {
        pos.set(mod.id, {
          x: RANK_X0 + r * RANK_DX,
          y: Math.round(height / 2 - 14 + (j - (row.length - 1) / 2) * BRANCH_DY),
        })
      })
    })

    const edges: LaneEdge[] = []
    for (const id of ids) {
      for (const p of prereqMap.get(id) ?? []) {
        const a = pos.get(p)
        const b = pos.get(id)
        if (!a || !b) continue
        edges.push({
          id: `${p}-${id}`,
          d: `M ${a.x + NODE / 2} ${a.y} C ${a.x + 90} ${a.y}, ${b.x - 90} ${b.y}, ${b.x - NODE / 2} ${b.y}`,
          stroke: isDone(p) ? color : '#72C4BF',
          dash: isDone(p) ? 'none' : '6 5',
        })
      }
    }

    // Node badges follow the on-screen reading order — left→right by
    // prerequisite rank, then top→bottom within a rank — NOT raw sort_order,
    // which the DAG layout reorders visually. Without this a module gated behind
    // another (e.g. Claude Code, sitting after Cowork) would show a lower number
    // than the module it visually follows. `rows` is already rank-major and, per
    // rank, in sort_order (== top→bottom, matching the y positions above), so a
    // single left-to-right sweep numbers them 1..N in the order they read.
    const badgeByModule = new Map<string, number>()
    let badge = 0
    rows.forEach(row => { for (const mod of row) badgeByModule.set(mod.id, ++badge) })

    const nodes: LaneNode[] = mods.map(m => {
      const p = pos.get(m.id)!
      return { mod: m, x: p.x, y: p.y, index: badgeByModule.get(m.id)! }
    })
    const width = RANK_X0 + (rows.length - 1) * RANK_DX + 130
    return { nodes, edges, height, width }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openTrackId, modulesMap, prereqMap, tracks, isAdmin, canBypassLocks])

  /* ── Popover CTA: server-computed next lesson, same as ModulePopup ── */
  async function startModule(moduleId: string) {
    setCtaLoading(true)
    const { data } = await client.GET('/api/modules/{module_id}/lessons', {
      params: { path: { module_id: moduleId } },
    })
    if (!data) { setCtaLoading(false); return }
    const assignedLessons = data.lessons.filter(l => l.assigned)
    if (assignedLessons.length === 0) { setCtaLoading(false); return }
    navigate(`/learning/lesson/${data.next_lesson_id ?? assignedLessons[0].id}`)
  }

  function openPopover(mod: ModuleNode, target: HTMLElement) {
    setPopover({ mod, anchor: target.getBoundingClientRect() })
  }

  const firstName = user?.first_name ?? ''

  /* ── Render ── */
  return (
    <div style={s.page}>
      <style>{`
        @keyframes lpn-pulse { 0% { transform: scale(1); opacity: .9; } 70%, 100% { transform: scale(1.35); opacity: 0; } }
        .lpn-lane-toggle:hover { background: #F7F6F4 !important; }
        .lpn-cta { transition: background 150ms; }
        .lpn-cta:hover:not(:disabled) { background: #EF463C !important; }
      `}</style>

      <AppNav backTo="/" title="Learning path" />

      <main style={s.main}>
        {/* ── Admin edit-mode banner ── */}
        <AnimatePresence>
          {isAdmin && isEditMode && (
            <motion.div
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              style={s.editBanner}
            >
              <span style={s.editDot} />
              <span style={s.editBannerText}>
                Edit mode — open a track and click a module to manage its lessons.
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error state */}
        {loadError && <p style={s.errorText}>{loadError}</p>}

        {/* ── Header — static, stays visible while data loads ── */}
        {!loadError && (
          <>
            <p style={s.eyebrow}>your enablement journey</p>
            <h1 style={s.heading}>Your learning path{firstName ? `, ${firstName}` : ''}.</h1>
            <p style={s.subtitle}>
              {notAssessed ? NOT_ASSESSED_SUBTITLE : ASSESSED_SUBTITLE}
            </p>
          </>
        )}

        {/* Loading — minHeight ≈ panel + first lanes so the page doesn't jump */}
        {!loadError && !loaded && (
          <div style={{ minHeight: 420, display: 'flex' }}>
            <Spinner />
          </div>
        )}

        {/* Empty state */}
        {!loadError && loaded && tracks.length === 0 && (
          <div style={s.emptyWrap}>
            <p style={s.emptyTitle}>No tracks assigned yet</p>
            <p style={s.emptySub}>Your delaware contact will set up your learning path.</p>
          </div>
        )}

        {!loadError && tracks.length > 0 && (
          <>
            {/* ── Progress panel: level card + the two bars ── */}
            <div style={s.panel}>
              <div style={s.levelCard}>
                <p style={s.smallLabel}>current level</p>
                {notAssessed ? (
                  <>
                    <p style={{ ...s.levelName, color: '#101820', fontSize: 24 }}>
                      {NOT_ASSESSED_NAME}
                    </p>
                    <p style={{ ...s.levelTagline, color: '#8A8A8A' }}>
                      {NOT_ASSESSED_TAGLINE}
                    </p>
                    <button
                      type="button"
                      onClick={() => navigate('/assessment')}
                      style={s.assessCta}
                    >
                      Take the assessment →
                    </button>
                  </>
                ) : (
                  <>
                    <p style={{ ...s.levelName, color: level.color }}>{level.name}</p>
                    <p style={{ ...s.levelTagline, color: level.color }}>{level.tagline}</p>
                  </>
                )}
              </div>

              <div style={s.barsCol}>
                {/* Overall journey bar */}
                <div style={s.barHeader}>
                  <span style={s.smallLabel}>overall journey</span>
                  <span style={{ ...s.barValue, color: notAssessed ? '#8A8A8A' : level.color }}>
                    {notAssessed ? NOT_ASSESSED_PROGRESS : `${overallPct}% of the full path`}
                  </span>
                </div>
                <div style={s.overallTrack}>
                  {!notAssessed && overallPct > 0 && (
                    <div style={{
                      ...s.overallFill,
                      width: `${overallPct}%`,
                      backgroundSize: `${10000 / overallPct}% 100%`,
                    }} />
                  )}
                  {LEVELS.map((l, i) => {
                    const { passed, current } = checkpointState(i, levelIdx, levelFraction, notAssessed)
                    return (
                      <div key={l.code} title={l.name} style={{
                        ...s.checkpoint,
                        left: `${(i + 1) * 25}%`,
                        background: passed ? l.color : '#fff',
                        border: `2px solid ${passed || current ? l.color : '#E2E2E2'}`,
                      }}>
                        {passed && <CheckGlyph size={10} />}
                        {current && <span style={{ width: 6, height: 6, borderRadius: '50%', background: l.color }} />}
                      </div>
                    )
                  })}
                </div>
                <div style={s.segmentLabels}>
                  {LEVELS.map((l, i) => {
                    const reached = !notAssessed && i <= levelIdx
                    return (
                      <span key={l.code} style={{
                        ...s.segmentLabel,
                        left: `${12.5 + i * 25}%`,
                        color: reached ? l.color : '#B6B6B6',
                        fontWeight: !notAssessed && i === levelIdx ? 800 : 600,
                      }}>
                        {l.name}
                      </span>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* ── Track list ── */}
            <div style={s.tracksHeader}>
              <p style={{ ...s.smallLabel, margin: 0 }}>your tracks</p>
              {isAdmin && isEditMode && (
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="button" onClick={() => setShowAddTrack(true)} style={s.editBtnGhost}>
                    + Add track
                  </button>
                  <button type="button" onClick={() => setShowAddModule(true)} style={s.editBtnSolid}>
                    + Add module
                  </button>
                </div>
              )}
            </div>
            <div style={s.laneList}>
              {trackGroups.map((group, gIdx) => {
                // Header state mirrors the overall bar's checkpoints (passed /
                // current / future) — but the dot border keeps the level color
                // even for future levels: the header's job is the color↔level
                // mapping. The bar shows ACTUAL content progress, so a level
                // passed via assessment reads passed-dot + honest 0% (agrees
                // with its lanes, invites revisiting skipped content).
                const isIntroGroup = group.levelCode === INTRO_GROUP
                const groupLevel = isIntroGroup ? INTRODUCTION_LEVEL : levelByCode(group.levelCode)
                const groupIdx = LEVELS.findIndex(l => l.code === group.levelCode) // -1 for intro
                const groupColor = groupLevel?.color ?? FALLBACK_TRACK_COLOR
                const stats = levelStats.get(group.levelCode) ?? EMPTY_LEVEL_STATS
                const groupPct = Math.round(lessonFraction(stats) * 100)
                // The header tick means the level's CONTENT is actually finished.
                // A level the learner is past by maturity but hasn't worked
                // through yet (0% with locked lanes) reads as an open ring + dot,
                // like the Introduction and the current level, rather than a tick
                // that wrongly implies it is done. An un-assessed learner has no
                // level, so no maturity group reads as current or passed.
                const { isCurrent, contentComplete, showOpenDot } = groupHeaderState({
                  isIntroGroup,
                  introComplete,
                  groupIdx,
                  levelIdx,
                  fraction: lessonFraction(stats),
                  modulesTotal: stats.modulesTotal,
                  notAssessed,
                })
                return (
                  <div key={`${group.levelCode}:${gIdx}`} style={{ ...s.laneList, marginTop: gIdx > 0 ? 14 : 0 }}>
                    <div>
                      <div style={s.levelHeaderRow}>
                        <span style={{
                          ...s.levelHeaderDot,
                          borderColor: groupColor,
                          background: contentComplete ? groupColor : '#fff',
                        }}>
                          {contentComplete && <CheckGlyph size={10} />}
                          {showOpenDot && <span style={{ width: 6, height: 6, borderRadius: '50%', background: groupColor }} />}
                        </span>
                        <span style={{ ...s.levelHeaderName, color: groupColor, fontWeight: isCurrent ? 800 : 600 }}>
                          {groupLevel?.name ?? group.levelCode}
                        </span>
                        {groupLevel && <span style={s.levelHeaderTagline}>· {groupLevel.tagline}</span>}
                        {groupLevel && (
                          <span style={{ ...s.barValue, color: groupColor, marginLeft: 'auto' }}>
                            {stats.modulesDone} of {stats.modulesTotal} modules · {groupPct}%
                          </span>
                        )}
                      </div>
                      {groupLevel && (
                        <div style={s.levelHeaderBar}>
                          <div style={{ ...s.levelHeaderBarFill, width: `${groupPct}%`, background: groupColor }} />
                        </div>
                      )}
                    </div>
                    {group.tracks.map(track => {
                      const mods = modulesMap[track.id] ?? []
                      const color = resolveTrackColor(track)
                      const maturityLocked = isTrackLocked(track)
                      const requiredLevel = levelByCode(track.required_level)
                      // Locked specifically because the Introduction isn't done
                      // yet — this message wins over the maturity "Unlocks at" note.
                      const introBlocked =
                        maturityLocked && !track.is_introduction && !introComplete
                      const done = mods.filter(m => isDone(m.id)).length
                      const next = maturityLocked ? null : firstCurrent(mods)
                      const open = openTrackId === track.id
                      // Precedence: the Introduction is the one thing an
                      // un-assessed learner can act on, so it still wins. Once it
                      // is done, the real blocker is the assessment — naming a
                      // level ("Unlocks at Explorer") wrong-foots a learner who
                      // was never placed on the ladder. The group header above the
                      // lane still shows which level it belongs to.
                      const subtitle = introBlocked
                        ? 'Complete the Introduction first'
                        : notAssessed && maturityLocked
                          ? LOCKED_UNTIL_ASSESSED
                          : maturityLocked
                            ? `Unlocks at ${requiredLevel?.name ?? track.required_level}`
                            : `${done} of ${mods.length} modules` +
                              (next ? ` · next: ${next.title}`
                                : done === mods.length && mods.length > 0 ? ' · track complete' : ' · locked')
                      const lockColor = introBlocked
                        ? INTRODUCTION_LEVEL.color
                        : notAssessed && maturityLocked
                          ? NEUTRAL_LOCK_COLOR
                          : (requiredLevel?.color ?? '#8A8A8A')
                      const ringColor = maturityLocked ? '#C4C4C4' : color

                      return (
                        <div key={track.id} style={{ ...s.lane, ...(maturityLocked ? s.laneLocked : {}) }}>
                          <button
                            type="button"
                            className="lpn-lane-toggle"
                            onClick={() => {
                              const nextOpen = open ? null : track.id
                              setOpenTrackId(nextOpen)
                              if (userId) writeStoredOpenTrack(userId, nextOpen)
                              setPopover(null)
                            }}
                            style={{
                              ...s.laneToggle,
                              background: open ? '#FDFCFB' : '#fff',
                              cursor: 'pointer',
                            }}
                          >
                            {maturityLocked
                              ? <div style={s.laneLockCircle}><LockGlyph size={16} stroke="#fff" /></div>
                              : <ProgressRing color={ringColor} frac={mods.length ? done / mods.length : 0} />}
                            <div style={s.laneTitleCol}>
                              <span style={{ ...s.laneName, color: maturityLocked ? '#B6B6B6' : '#3C3C3C' }}>{track.name}</span>
                              <span style={{ ...s.laneSubtitle, ...(maturityLocked ? { color: lockColor, fontWeight: 700 } : {}) }}>{subtitle}</span>
                            </div>
                            <div style={s.laneDots}>
                              {mods.map(m => {
                                const d = !maturityLocked && isDone(m.id)
                                const u = !maturityLocked && isUnlocked(m.id)
                                return <span key={m.id} style={{
                                  ...s.laneDot,
                                  background: d ? color : u ? '#fff' : '#EFEDEA',
                                  border: `1.5px solid ${d || u ? color : '#D6D6D6'}`,
                                }} />
                              })}
                            </div>
                            <motion.span
                              animate={{ rotate: open ? 180 : 0 }}
                              transition={{ duration: 0.2 }}
                              style={s.chevron}
                            >
                              ▾
                            </motion.span>
                          </button>

                          <AnimatePresence initial={false}>
                            {open && laneLayout && (
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: laneLayout.height, opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
                                style={s.laneBody}
                              >
                                <div style={{ position: 'relative', height: laneLayout.height, width: laneLayout.width, minWidth: '100%' }}>
                                  <svg width={laneLayout.width} height={laneLayout.height} style={s.laneSvg}>
                                    {laneLayout.edges.map(e => (
                                      <path key={e.id} d={e.d} fill="none" stroke={e.stroke}
                                        strokeWidth="2.5" strokeDasharray={e.dash} strokeLinecap="round" />
                                    ))}
                                  </svg>
                                  {laneLayout.nodes.map(({ mod, x, y, index }) => {
                                    const done = isDone(mod.id)
                                    const unlocked = isUnlocked(mod.id)
                                    const current = firstCurrent(mods)?.id === mod.id
                                    const bg = !unlocked
                                      ? 'radial-gradient(circle at 32% 30%, #D6D6D6, #ADADAD)'
                                      : `radial-gradient(circle at 32% 30%, ${lighten(color, done ? 35 : 55)}, ${color})`
                                    return (
                                      <div key={mod.id}>
                                        <motion.button
                                          type="button"
                                          onClick={e => isEditMode
                                            ? setEditingModule({ id: mod.id, title: mod.title })
                                            : openPopover(mod, e.currentTarget)}
                                          title={isEditMode ? `Edit lessons for: ${mod.title}` : undefined}
                                          whileHover={{ scale: 1.1 }}
                                          transition={{ duration: 0.16 }}
                                          style={{
                                            ...s.node,
                                            left: x - NODE / 2,
                                            top: y - NODE / 2,
                                            background: bg,
                                            opacity: unlocked ? 1 : 0.55,
                                            boxShadow: isEditMode
                                              ? '0 0 0 3px rgba(59,201,188,.45), 0 3px 10px rgba(0,0,0,.16)'
                                              : current
                                                ? '0 4px 16px rgba(196,40,40,.30)'
                                                : '0 3px 10px rgba(0,0,0,.14)',
                                          }}
                                        >
                                          {current && !isEditMode && (
                                            <span style={{ ...s.pulseRing, border: `2.5px solid ${color}` }} />
                                          )}
                                          {!unlocked ? <LockGlyph />
                                            : done ? <CheckGlyph />
                                            : <span style={s.nodeNumber}>{index}</span>}
                                        </motion.button>
                                        <div style={{ ...s.nodeLabel, left: x - 63, top: y + NODE / 2 + 8 }}>
                                          <span style={{ ...s.nodeTitle, color: unlocked ? '#3C3C3C' : '#B6B6B6' }}>
                                            {mod.title}
                                          </span>
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      )
                    })}
                  </div>
                )
              })}
            </div>
          </>
        )}
      </main>

      {/* ── Module popover ── */}
      {popover && <div style={s.backdrop} onClick={() => setPopover(null)} />}
      <AnimatePresence>
        {popover && (() => {
          const { mod, anchor } = popover
          const track = tracks.find(t => t.id === mod.track_id)
          const color = track ? resolveTrackColor(track) : FALLBACK_TRACK_COLOR
          const unlocked = isUnlocked(mod.id)
          const done = isDone(mod.id)
          const completed = Math.min(mod.completed_lesson_count, mod.lesson_count)
          const pct = mod.lesson_count > 0 ? Math.round((100 * completed) / mod.lesson_count) : 0
          const missing = (prereqMap.get(mod.id) ?? [])
            .filter(p => !predSatisfied(p, mod.id))
            .map(p => moduleById.get(p)?.title)
            .filter((t): t is string => !!t)
          // This popover is position:fixed inside the zoomed root; anchor comes
          // from getBoundingClientRect (zoom-scaled), so convert it + the viewport
          // back into local space (POPOVER_W stays a local unit).
          const z = getRectZoomFactor()
          const aRight = anchor.right / z, aLeft = anchor.left / z, aTop = anchor.top / z
          const vpW = window.innerWidth / z, vpH = window.innerHeight / z
          const x = aRight + 14 + POPOVER_W > vpW
            ? Math.max(10, aLeft - POPOVER_W - 14)
            : aRight + 14
          const y = Math.max(16, Math.min(aTop - 10, vpH - 300))
          return (
            <motion.div
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92 }}
              transition={{ duration: 0.16 }}
              style={{ ...s.popover, left: x, top: y }}
            >
              <div style={s.popTrackRow}>
                <span style={{ ...s.popTrackDot, background: color }} />
                <span style={s.popTrackName}>{track?.name ?? ''}</span>
              </div>
              <p style={s.popTitle}>{mod.title}</p>

              {!unlocked ? (
                <div style={s.popLockedNote}>
                  <span style={{ fontWeight: 800 }}>locked</span>
                  {missing.length > 0
                    ? <> — finish <span style={{ fontWeight: 700, color: '#C42828' }}>{missing.join(', ')}</span> first to unlock this module.</>
                    : <> — complete the required modules first to unlock this one.</>}
                </div>
              ) : (
                <>
                  <div style={s.popLessonsRow}>
                    <span style={{ color: '#8A8A8A' }}>lessons</span>
                    <span style={{ color: '#3C3C3C' }}>{completed} of {mod.lesson_count} complete</span>
                  </div>
                  <div style={s.popBarTrack}>
                    <div style={{ ...s.popBarFill, width: `${pct}%`, background: color }} />
                  </div>
                  {done ? (
                    <button
                      type="button"
                      className="lpn-cta"
                      disabled={ctaLoading}
                      onClick={() => startModule(mod.id)}
                      style={{
                        ...s.popCta,
                        background: '#C42828',
                        color: '#fff',
                        cursor: 'pointer',
                      }}
                    >
                      {ctaLoading ? 'Loading…' : 'Review module →'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="lpn-cta"
                      disabled={ctaLoading || mod.lesson_count === 0}
                      onClick={() => startModule(mod.id)}
                      style={{
                        ...s.popCta,
                        background: mod.lesson_count === 0 ? '#E2E2E2' : '#C42828',
                        color: mod.lesson_count === 0 ? '#8A8A8A' : '#fff',
                        cursor: mod.lesson_count === 0 ? 'default' : 'pointer',
                      }}
                    >
                      {ctaLoading ? 'Loading…' : completed > 0 ? 'Continue module →' : 'Start module →'}
                    </button>
                  )}
                </>
              )}
            </motion.div>
          )
        })()}
      </AnimatePresence>

      {/* ── Admin edit-mode toggle (floating, bottom-right) ── */}
      {isAdmin && (
        <button
          type="button"
          onClick={() => { setIsEditMode(m => !m); setEditingModule(null); setPopover(null) }}
          style={{
            ...s.editToggle,
            right: editingModule ? 448 : 28,
            background: isEditMode ? '#3BC9BC' : '#fff',
            border: isEditMode ? '2px solid #3BC9BC' : '1.5px solid #E2E2E2',
            color: isEditMode ? '#fff' : '#3C3C3C',
          }}
        >
          {isEditMode ? '✓ Editing' : 'Edit content'}
        </button>
      )}

      {/* ── Lesson-management panel (edit mode, per module) ── */}
      {isEditMode && editingModule && (
        <ModulePanel
          moduleId={editingModule.id}
          moduleName={editingModule.title}
          onClose={() => setEditingModule(null)}
          onDeleted={() => { setEditingModule(null); reload() }}
        />
      )}

      {/* ── Add track / module modals ── */}
      {showAddTrack && (
        <AddTrackModal
          onClose={() => setShowAddTrack(false)}
          onAdded={() => { setShowAddTrack(false); reload() }}
        />
      )}
      {showAddModule && (
        <AddModuleModal
          onClose={() => setShowAddModule(false)}
          onAdded={() => { setShowAddModule(false); reload() }}
        />
      )}
    </div>
  )
}

/* ── Styles ── */
const s = {
  page: { minHeight: '100vh', background: '#fff', fontFamily: 'var(--dlw-font-body)', display: 'flex', flexDirection: 'column' },
  main: { flex: 1, width: 'min(1080px, 100%)', margin: '0 auto', padding: '44px 40px 90px' },

  /* Header */
  eyebrow: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase',
    color: '#EF463C', margin: '0 0 14px',
  },
  heading: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 44, lineHeight: 1.12, letterSpacing: '-0.015em',
    color: '#101820', margin: '0 0 12px',
  },
  subtitle: {
    fontSize: 17, lineHeight: 1.6, fontWeight: 300,
    color: '#8A8A8A', margin: '0 0 36px', maxWidth: '54ch',
  },

  /* Progress panel */
  panel: {
    border: '1px solid #E2E2E2', borderRadius: 12,
    padding: '22px 30px', display: 'flex', gap: 32, flexWrap: 'wrap',
    alignItems: 'center',
  },
  levelCard: {
    flexShrink: 0, minWidth: 180, paddingRight: 32,
    borderRight: '1px solid #F0EFED',
  },
  smallLabel: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase',
    color: '#8A8A8A', margin: 0,
  },
  levelName: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 800,
    fontSize: 30, lineHeight: 1.15, margin: '6px 0 2px',
  },
  levelTagline: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600,
    fontSize: 12.5, margin: 0, opacity: 0.85,
  },
  /* Un-assessed CTA in the level card. Same treatment as the module popover's
     popCta so the page keeps one button language. */
  assessCta: {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    marginTop: 14, padding: '9px 15px', border: 'none', borderRadius: 8,
    background: '#C42828', color: '#fff', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-ui)', fontSize: 12.5, fontWeight: 700,
  },
  barsCol: { flex: '1 1 420px', minWidth: 340, paddingTop: 2 },
  barHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 },
  barValue: { fontFamily: 'var(--dlw-font-ui)', fontWeight: 700, fontSize: 13 },
  overallTrack: {
    position: 'relative', height: 10, borderRadius: 999,
    background: '#F5F5F5', border: '1px solid #ECECEC',
  },
  overallFill: {
    position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 999,
    background: LEVEL_GRADIENT,
    backgroundRepeat: 'no-repeat',
    transition: 'width .4s ease',
  },
  checkpoint: {
    position: 'absolute', top: -6, width: 18, height: 18, marginLeft: -9,
    borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,.12)', boxSizing: 'border-box',
  },
  segmentLabels: { position: 'relative', height: 20, marginTop: 12 },
  segmentLabel: {
    position: 'absolute', transform: 'translateX(-50%)', whiteSpace: 'nowrap',
    fontFamily: 'var(--dlw-font-ui)', fontSize: 11.5,
  },
  /* Level group headers (lane list) */
  levelHeaderRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '0 2px' },
  levelHeaderDot: {
    width: 18, height: 18, borderRadius: '50%', boxSizing: 'border-box',
    borderWidth: 2, borderStyle: 'solid', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,.12)',
  },
  levelHeaderName: {
    fontFamily: 'var(--dlw-font-ui)', fontSize: 11.5,
    letterSpacing: '0.14em', textTransform: 'uppercase',
  },
  levelHeaderTagline: { fontFamily: 'var(--dlw-font-ui)', fontSize: 11.5, fontWeight: 600, color: '#8A8A8A' },
  levelHeaderBar: {
    position: 'relative', height: 5, borderRadius: 999,
    background: '#F5F5F5', overflow: 'hidden', marginTop: 8,
  },
  levelHeaderBarFill: {
    position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 999,
    transition: 'width .4s ease',
  },

  /* Track lanes */
  laneList: { display: 'flex', flexDirection: 'column', gap: 14 },
  lane: {
    border: '1px solid #E2E2E2', borderRadius: 16, background: '#fff',
    boxShadow: '0 1px 4px rgba(0,0,0,.05)', overflow: 'hidden',
  },
  laneLocked: { background: '#FBFAF9', borderColor: '#ECEAE7', boxShadow: 'none' },
  laneLockCircle: {
    width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: '#C4C4C4',
  },
  laneToggle: {
    width: '100%', display: 'flex', alignItems: 'center', gap: 16,
    padding: '16px 22px', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', textAlign: 'left',
    transition: 'background 150ms',
  },
  laneTitleCol: { flex: 1, display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 },
  laneName: { fontSize: 16.5, fontWeight: 800, color: '#3C3C3C' },
  laneSubtitle: {
    fontSize: 12.5, fontWeight: 600, color: '#8A8A8A',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  laneDots: { display: 'flex', gap: 6, alignItems: 'center', marginRight: 10, flexShrink: 0 },
  laneDot: { width: 11, height: 11, borderRadius: '50%', boxSizing: 'border-box' },
  chevron: { fontSize: 18, color: '#8A8A8A', display: 'inline-block', flexShrink: 0 },
  laneBody: {
    borderTop: '1px solid #EFEDEA', background: '#FDFCFB',
    overflowX: 'auto', overflowY: 'hidden',
  },
  laneSvg: { position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none' },
  node: {
    position: 'absolute', width: NODE, height: NODE, borderRadius: '50%',
    border: 'none', cursor: 'pointer', padding: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  pulseRing: {
    position: 'absolute', inset: -6, borderRadius: '50%',
    animation: 'lpn-pulse 1.9s ease-out infinite', pointerEvents: 'none',
  },
  nodeNumber: { color: '#fff', fontWeight: 800, fontSize: 15, fontFamily: 'var(--dlw-font-ui)' },
  nodeLabel: { position: 'absolute', width: 126, textAlign: 'center', pointerEvents: 'none' },
  nodeTitle: { fontSize: 11.5, fontWeight: 700, lineHeight: 1.25, fontFamily: 'var(--dlw-font-body)' },

  /* Popover */
  backdrop: { position: 'fixed', inset: 0, zIndex: 199 },
  popover: {
    position: 'fixed', zIndex: 200, width: POPOVER_W,
    background: '#fff', borderRadius: 16, border: '1px solid #E2E2E2',
    boxShadow: '0 14px 40px rgba(0,0,0,.16)', padding: 22,
    display: 'flex', flexDirection: 'column', gap: 12,
    fontFamily: 'var(--dlw-font-body)',
  },
  popTrackRow: { display: 'flex', alignItems: 'center', gap: 8 },
  popTrackDot: { width: 10, height: 10, borderRadius: '50%' },
  popTrackName: {
    fontFamily: 'var(--dlw-font-ui)', fontSize: 11.5, fontWeight: 800,
    color: '#8A8A8A', letterSpacing: '0.04em',
  },
  popTitle: { fontSize: 19, fontWeight: 800, color: '#101820', lineHeight: 1.25, margin: 0 },
  popLockedNote: {
    background: '#F5F5F5', borderRadius: 10, padding: '12px 14px',
    fontSize: 12.5, color: '#3C3C3C', lineHeight: 1.5,
  },
  popLessonsRow: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 12, fontWeight: 700, fontFamily: 'var(--dlw-font-ui)',
  },
  popBarTrack: { height: 8, borderRadius: 999, background: '#F5F5F5', overflow: 'hidden' },
  popBarFill: { height: '100%', borderRadius: 999, transition: 'width .3s ease' },
  popCta: {
    marginTop: 2, padding: '11px 18px', borderRadius: 8, border: 'none',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
  },
  /* Admin edit mode */
  tracksHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    gap: 12, margin: '44px 0 14px', minHeight: 30,
  },
  editBanner: {
    display: 'flex', alignItems: 'center', gap: 10,
    background: '#F0FAF9', border: '1px solid #B2EBE6', borderRadius: 12,
    padding: '11px 16px', marginBottom: 24,
  },
  editDot: { width: 8, height: 8, borderRadius: '50%', background: '#3BC9BC', flexShrink: 0 },
  editBannerText: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, color: '#1D7A52',
  },
  editBtnGhost: {
    padding: '6px 14px', borderRadius: 999, border: '1.5px solid #3BC9BC',
    background: '#fff', color: '#1D7A52', fontFamily: 'var(--dlw-font-body)',
    fontWeight: 600, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  editBtnSolid: {
    padding: '6px 14px', borderRadius: 999, border: 'none',
    background: '#3BC9BC', color: '#fff', fontFamily: 'var(--dlw-font-body)',
    fontWeight: 600, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap',
  },
  editToggle: {
    position: 'fixed', bottom: 28, padding: '10px 22px', borderRadius: 999,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14,
    cursor: 'pointer', zIndex: 200, boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
    transition: 'right 0.25s ease',
  },

  errorText: { fontWeight: 300, fontSize: 14, color: '#C42828', textAlign: 'center', marginTop: 80 },
  emptyWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 60 },
  emptyTitle: { fontWeight: 600, fontSize: 16, color: '#3C3C3C', margin: 0 },
  emptySub: { fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0 },
} satisfies Record<string, CSSProperties>
