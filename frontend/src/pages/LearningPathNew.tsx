// Learning-path redesign (2026-07-08), parked at /learning/new while the live
// /learning page stays untouched. Runs on REAL data: GET /api/learning/graph
// (assigned tracks/modules/prerequisites + lesson counts) and GET /api/survey/me
// (assessed score_level for the header). Module CTA navigates via
// GET /api/modules/{id}/lessons → next_lesson_id, same contract as ModulePopup.
//
// Design decisions (2026-07-08):
// - White page, red caps eyebrow + bold title header (second mockup's style).
// - Overall bar = one continuous 4-color fill with level checkpoint dots;
//   levels below the assessed level count as complete (Practitioner = 25%).
// - Below it, a solid bar for progress within the current level.
// - Core trunk gets no special treatment ("can be skipped"): the general
//   track renders as a normal row; locking still follows real prerequisites.
// - Tracks are collapsible lanes; the expanded lane draws the track's real
//   prerequisite DAG left-to-right (same rank algorithm as the live page).

import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { client } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import Spinner from '../components/Spinner'
import { LEVELS, LEVEL_GRADIENT } from '../lib/levels'
import { getRectZoomFactor } from '../lib/uiZoom'
import type { ModuleNode, TrackNode } from '../types/domain'

/* ── Lane geometry ── */
const NODE = 56            // node diameter
const RANK_X0 = 96         // x of the first rank's centre
const RANK_DX = 178        // x distance between ranks
const BRANCH_DY = 118      // y distance between parallel modules in a rank
const LANE_MIN_H = 170
const POPOVER_W = 330

const FALLBACK_TRACK_COLOR = '#C42828'

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

function lighten(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16)
  const r = Math.min(255, (n >> 16) + amt)
  const g = Math.min(255, ((n >> 8) & 255) + amt)
  const b = Math.min(255, (n & 255) + amt)
  return `rgb(${r},${g},${b})`
}

/* ── Icons ── */
function LockGlyph({ size = 17 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
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

export default function LearningPathNew() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [tracks, setTracks] = useState<TrackNode[]>([])
  const [modulesMap, setModulesMap] = useState<Record<string, ModuleNode[]>>({})
  const [prereqMap, setPrereqMap] = useState<Map<string, string[]>>(new Map())
  const [levelCode, setLevelCode] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [openTrackId, setOpenTrackId] = useState<string | null>(null)
  const [popover, setPopover] = useState<PopoverState | null>(null)
  const [ctaLoading, setCtaLoading] = useState(false)

  const userId = user?.id
  const isAdmin = user?.role === 'admin'

  /* ── Load: graph + assessed level, in parallel ── */
  useEffect(() => {
    if (!userId) return
    let cancelled = false
    setLoadError(null)

    async function load() {
      const [graphRes, surveyRes] = await Promise.all([
        client.GET('/api/learning/graph'),
        client.GET('/api/survey/me'),
      ])
      if (cancelled) return
      if (!graphRes.data) { setLoadError('Failed to load your tracks. Please refresh.'); return }

      // Same filtering semantics as the live /learning page: assigned tracks,
      // assigned modules within them, prereq rows keyed on assigned modules
      // (an unassigned prerequisite stays un-completable → locked).
      const assignedTracks = graphRes.data.tracks
        .filter(t => t.assigned)
        .sort((a, b) => a.sort_order - b.sort_order)

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

      setTracks(assignedTracks)
      setModulesMap(map)
      setPrereqMap(pMap)
      setLevelCode(surveyRes.data?.score_level ?? null)
      setLoaded(true)
    }

    load()
    return () => { cancelled = true }
  }, [userId])

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
  const isUnlocked = (id: string): boolean => {
    if (isAdmin) return true // same bypass as the live page
    const preds = prereqMap.get(id)
    if (!preds || preds.length === 0) return true
    return preds.every(isDone)
  }
  const firstCurrent = (mods: ModuleNode[]): ModuleNode | null =>
    mods.find(m => !isDone(m.id) && isUnlocked(m.id)) ?? null

  /* ── Level + header math ── */
  // Fallback to Explorer when no completed assessment exposes a level yet.
  const levelIdx = Math.max(0, LEVELS.findIndex(l => l.code === levelCode))
  const level = LEVELS[levelIdx]

  const allModules = useMemo(() => Object.values(modulesMap).flat(), [modulesMap])
  const lessonsTotal = allModules.reduce((s, m) => s + m.lesson_count, 0)
  const lessonsDone = allModules.reduce((s, m) => s + Math.min(m.completed_lesson_count, m.lesson_count), 0)
  const levelFraction = lessonsTotal > 0 ? lessonsDone / lessonsTotal : 0
  const modulesDone = allModules.filter(m => isDone(m.id)).length

  // Levels below the assessed one count as complete (design decision).
  const overallPct = Math.round(((levelIdx + levelFraction) / LEVELS.length) * 100)
  const levelPct = Math.round(levelFraction * 100)

  /* ── Default open lane: restore the learner's last choice, else the first
        track with something actionable ── */
  useEffect(() => {
    if (!loaded || tracks.length === 0 || !userId) return
    setOpenTrackId(prev => {
      if (prev !== null) return prev
      const stored = readStoredOpenTrack(userId)
      if (stored === null) return null                                // explicitly collapsed
      if (stored && tracks.some(t => t.id === stored)) return stored  // restore, if still valid
      const active = tracks.find(t => firstCurrent(modulesMap[t.id] ?? []) !== null)
      return (active ?? tracks[0]).id                                 // smart default (unchanged)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, tracks, userId])

  /* ── Expanded-lane layout (real prerequisite DAG, left→right) ── */
  const laneLayout = useMemo((): LaneLayout | null => {
    const mods = openTrackId ? modulesMap[openTrackId] : undefined
    if (!openTrackId || !mods || mods.length === 0) return null
    const track = tracks.find(t => t.id === openTrackId)
    const color = track?.color ?? FALLBACK_TRACK_COLOR
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

    const nodes: LaneNode[] = mods.map(m => {
      const p = pos.get(m.id)!
      return { mod: m, x: p.x, y: p.y, index: ids.indexOf(m.id) + 1 }
    })
    const width = RANK_X0 + (rows.length - 1) * RANK_DX + 130
    return { nodes, edges, height, width }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openTrackId, modulesMap, prereqMap, tracks, isAdmin])

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
  const fullName = user ? `${user.first_name} ${user.last_name}`.trim() : ''

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
        {/* Error state */}
        {loadError && <p style={s.errorText}>{loadError}</p>}

        {/* ── Header — static, stays visible while data loads ── */}
        {!loadError && (
          <>
            <p style={s.eyebrow}>your enablement journey</p>
            <h1 style={s.heading}>Your learning path{firstName ? `, ${firstName}` : ''}.</h1>
            <p style={s.subtitle}>
              Based on your maturity assessment, these tracks are tailored to where
              you are today. Work through them at your own pace — each module
              builds on the last.
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
                <p style={{ ...s.levelName, color: level.color }}>{level.name}</p>
                <p style={{ ...s.levelTagline, color: level.color }}>{level.tagline}</p>
                <p style={{ ...s.smallLabel, marginTop: 22 }}>tailored for</p>
                <p style={s.tailoredName}>{fullName || '—'}</p>
              </div>

              <div style={s.barsCol}>
                {/* Overall journey bar */}
                <div style={s.barHeader}>
                  <span style={s.smallLabel}>overall journey</span>
                  <span style={{ ...s.barValue, color: level.color }}>{overallPct}% of the full path</span>
                </div>
                <div style={s.overallTrack}>
                  {overallPct > 0 && (
                    <div style={{
                      ...s.overallFill,
                      width: `${overallPct}%`,
                      backgroundSize: `${10000 / overallPct}% 100%`,
                    }} />
                  )}
                  {LEVELS.map((l, i) => {
                    const passed = i < levelIdx || (i === levelIdx && levelFraction >= 1)
                    const current = !passed && i === levelIdx
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
                    const reached = i <= levelIdx
                    return (
                      <span key={l.code} style={{
                        ...s.segmentLabel,
                        left: `${12.5 + i * 25}%`,
                        color: reached ? l.color : '#B6B6B6',
                        fontWeight: i === levelIdx ? 800 : 600,
                      }}>
                        {l.name}
                      </span>
                    )
                  })}
                </div>

                {/* Current-level bar */}
                <div style={{ ...s.barHeader, marginTop: 26 }}>
                  <span style={s.smallLabel}>{level.name} progress</span>
                  <span style={{ ...s.barValue, color: level.color }}>
                    {modulesDone} of {allModules.length} modules · {levelPct}%
                  </span>
                </div>
                <div style={s.levelTrack}>
                  <div style={{ ...s.levelFill, width: `${levelPct}%`, background: level.color }} />
                </div>
              </div>
            </div>

            {/* ── Track list ── */}
            <p style={{ ...s.smallLabel, margin: '44px 0 14px' }}>your tracks</p>
            <div style={s.laneList}>
              {tracks.map(track => {
                const mods = modulesMap[track.id] ?? []
                const color = track.color ?? FALLBACK_TRACK_COLOR
                const done = mods.filter(m => isDone(m.id)).length
                const next = firstCurrent(mods)
                const open = openTrackId === track.id
                const subtitle =
                  `${done} of ${mods.length} modules` +
                  (next ? ` · next: ${next.title}`
                    : done === mods.length && mods.length > 0 ? ' · track complete' : ' · locked')

                return (
                  <div key={track.id} style={s.lane}>
                    <button
                      type="button"
                      className="lpn-lane-toggle"
                      onClick={() => {
                        const nextOpen = open ? null : track.id
                        setOpenTrackId(nextOpen)
                        if (userId) writeStoredOpenTrack(userId, nextOpen)
                        setPopover(null)
                      }}
                      style={{ ...s.laneToggle, background: open ? '#FDFCFB' : '#fff' }}
                    >
                      <ProgressRing color={color} frac={mods.length ? done / mods.length : 0} />
                      <div style={s.laneTitleCol}>
                        <span style={s.laneName}>{track.name}</span>
                        <span style={s.laneSubtitle}>{subtitle}</span>
                      </div>
                      <div style={s.laneDots}>
                        {mods.map(m => {
                          const d = isDone(m.id)
                          const u = isUnlocked(m.id)
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
                                    onClick={e => openPopover(mod, e.currentTarget)}
                                    whileHover={{ scale: 1.1 }}
                                    transition={{ duration: 0.16 }}
                                    style={{
                                      ...s.node,
                                      left: x - NODE / 2,
                                      top: y - NODE / 2,
                                      background: bg,
                                      opacity: unlocked ? 1 : 0.55,
                                      boxShadow: current
                                        ? '0 4px 16px rgba(196,40,40,.30)'
                                        : '0 3px 10px rgba(0,0,0,.14)',
                                    }}
                                  >
                                    {current && (
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
          </>
        )}
      </main>

      {/* ── Module popover ── */}
      {popover && <div style={s.backdrop} onClick={() => setPopover(null)} />}
      <AnimatePresence>
        {popover && (() => {
          const { mod, anchor } = popover
          const track = tracks.find(t => t.id === mod.track_id)
          const color = track?.color ?? FALLBACK_TRACK_COLOR
          const unlocked = isUnlocked(mod.id)
          const done = isDone(mod.id)
          const completed = Math.min(mod.completed_lesson_count, mod.lesson_count)
          const pct = mod.lesson_count > 0 ? Math.round((100 * completed) / mod.lesson_count) : 0
          const missing = (prereqMap.get(mod.id) ?? [])
            .filter(p => !isDone(p))
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
                    <div style={s.popDoneRow}>
                      <span style={{ ...s.popDoneBadge, background: color }}><CheckGlyph size={12} /></span>
                      module completed
                    </div>
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
    padding: '26px 30px', display: 'flex', gap: 32, flexWrap: 'wrap',
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
  tailoredName: {
    fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 15, color: '#101820', margin: '5px 0 0',
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
  levelTrack: { position: 'relative', height: 8, borderRadius: 999, background: '#F5F5F5', overflow: 'hidden' },
  levelFill: { position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 999, transition: 'width .4s ease' },

  /* Track lanes */
  laneList: { display: 'flex', flexDirection: 'column', gap: 14 },
  lane: {
    border: '1px solid #E2E2E2', borderRadius: 16, background: '#fff',
    boxShadow: '0 1px 4px rgba(0,0,0,.05)', overflow: 'hidden',
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
    color: '#8A8A8A', textTransform: 'lowercase', letterSpacing: '0.04em',
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
  popDoneRow: {
    display: 'flex', alignItems: 'center', gap: 8,
    fontSize: 13, fontWeight: 800, color: '#3C3C3C',
  },
  popDoneBadge: {
    width: 22, height: 22, borderRadius: '50%',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  },
  popCta: {
    marginTop: 2, padding: '11px 18px', borderRadius: 8, border: 'none',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
  },
  errorText: { fontWeight: 300, fontSize: 14, color: '#C42828', textAlign: 'center', marginTop: 80 },
  emptyWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 60 },
  emptyTitle: { fontWeight: 600, fontSize: 16, color: '#3C3C3C', margin: 0 },
  emptySub: { fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0 },
} satisfies Record<string, CSSProperties>
