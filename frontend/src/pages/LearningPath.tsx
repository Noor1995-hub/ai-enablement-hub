import React, { useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { client } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import ModulePanel from '../components/ModulePanel'
import ModulePopup from '../components/ModulePopup'
import AddTrackModal from '../components/AddTrackModal'
import AddModuleModal from '../components/AddModuleModal'
import type { ModuleNode, TrackNode } from '../types/domain'

// Note: `col_offset` never existed in the live DB or in this page's buildGraph
// (design-frontend §3's mention of it is stale); layout is pure rank/branch math.

const R             = 20
const STEP          = 99
const BRANCH_OFFSET = 53
const BLUR_PAD      = 33
const EDGE_COLOR    = '#3BC9BC'
const EDGE_DASH     = '6 5'

interface GraphNode { id: string; title: string; x: number; y: number }
interface GraphEdge { id: string; trackId: string | null; x1: number; y1: number; x2: number; y2: number }
interface TrackGroup {
  track: TrackNode
  nodes: GraphNode[]
  labelX: number
  labelY: number
  centerX: number
  centerY: number
  box: { x: number; y: number; w: number; h: number }
}

function orthogonalPath(x1: number, y1: number, x2: number, y2: number): string {
  if (x1 === x2) return `M ${x1} ${y1} L ${x2} ${y2}`
  const midY = (y1 + y2) / 2
  return `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`
}

function buildGraph(
  tracks: TrackNode[],
  modulesMap: Record<string, ModuleNode[]>,
  prereqMap: Map<string, string[]>,
  canvasWidth: number,
): { edges: GraphEdge[]; groups: Record<string, TrackGroup>; canvasHeight: number } {
  const general = tracks.find(t => t.track_type === 'general')
  const tools   = tracks.filter(t => t.track_type === 'tool')
  if (!general || !canvasWidth) return { edges: [], groups: {}, canvasHeight: 500 }

  const GEN_X     = canvasWidth / 2
  const GEN_Y0    = 70
  const SECTION_W = tools.length > 0 ? canvasWidth / tools.length : canvasWidth

  const edges: GraphEdge[]  = []
  const groups: Record<string, TrackGroup> = {}

  function buildTrackNodes(track: TrackNode, centerX: number, startY: number) {
    const mods   = modulesMap[track.id] ?? []
    const modIds = new Set(mods.map(m => m.id))
    const predsOf = new Map(mods.map(m => [m.id, (prereqMap.get(m.id) ?? []).filter(id => modIds.has(id))]))

    // ASAP rank: a module is placed one row below the latest of its same-track predecessors
    const rank = new Map<string, number>()
    function getRank(id: string): number {
      if (rank.has(id)) return rank.get(id)!
      rank.set(id, 0) // cycle guard — resolved to the real value below
      const preds = predsOf.get(id) ?? []
      const r = preds.length === 0 ? 0 : Math.max(...preds.map(getRank)) + 1
      rank.set(id, r)
      return r
    }
    mods.forEach(m => getRank(m.id))

    const byRank = new Map<number, ModuleNode[]>()
    for (const mod of mods) {
      const r = rank.get(mod.id)!
      if (!byRank.has(r)) byRank.set(r, [])
      byRank.get(r)!.push(mod)
    }
    const ranks = [...byRank.keys()].sort((a, b) => a - b)

    // Resolved left-to-right x per module, filled in row by row so children can
    // center themselves under their already-placed predecessors.
    const xOf = new Map<string, number>()
    const avgParentX = (mod: ModuleNode) => {
      const preds = predsOf.get(mod.id) ?? []
      if (!preds.length) return 0
      return preds.reduce((s, id) => s + (xOf.get(id) ?? 0), 0) / preds.length
    }

    const nodes: GraphNode[] = []
    for (const r of ranks) {
      const rowMods = byRank.get(r)!.slice().sort((a, b) =>
        avgParentX(a) - avgParentX(b) || a.sort_order - b.sort_order || a.title.localeCompare(b.title)
      )
      const y = startY + r * STEP
      const groupCount = rowMods.length
      rowMods.forEach((mod, i) => {
        const x = centerX - ((groupCount - 1) * BRANCH_OFFSET) / 2 + i * BRANCH_OFFSET
        xOf.set(mod.id, x)
        nodes.push({ id: mod.id, title: mod.title ?? '', x, y })
      })
    }

    for (const mod of mods) {
      for (const predId of predsOf.get(mod.id) ?? []) {
        edges.push({
          id: `e-${predId}-${mod.id}`, trackId: track.id,
          x1: xOf.get(predId)!, y1: startY + rank.get(predId)! * STEP,
          x2: xOf.get(mod.id)!, y2: startY + rank.get(mod.id)! * STEP,
        })
      }
    }

    const maxRank   = ranks.length ? Math.max(...ranks) : 0
    const halfWidth = nodes.length ? Math.max(BRANCH_OFFSET, ...nodes.map(n => Math.abs(n.x - centerX))) : BRANCH_OFFSET
    return { nodes, maxY: startY + maxRank * STEP, halfWidth }
  }

  const { nodes: genNodes, maxY: genMaxY, halfWidth: genHalfWidth } = buildTrackNodes(general, GEN_X, GEN_Y0)
  const TOOL_Y0 = genMaxY + 140

  groups[general.id] = {
    track: general, nodes: genNodes,
    labelX: GEN_X, labelY: GEN_Y0 - 38,
    centerX: GEN_X, centerY: GEN_Y0 + (genMaxY - GEN_Y0) / 2,
    box: { x: GEN_X - genHalfWidth - R - BLUR_PAD, y: GEN_Y0 - R - BLUR_PAD, w: (genHalfWidth + R + BLUR_PAD) * 2, h: (genMaxY - GEN_Y0) + (R + BLUR_PAD) * 2 },
  }

  let maxCanvasY = TOOL_Y0
  tools.forEach((track, i) => {
    const cx = SECTION_W * i + SECTION_W / 2
    const { nodes: toolNodes, maxY: toolMaxY, halfWidth: toolHalfWidth } = buildTrackNodes(track, cx, TOOL_Y0)
    maxCanvasY = Math.max(maxCanvasY, toolMaxY)

    groups[track.id] = {
      track, nodes: toolNodes,
      labelX: cx, labelY: TOOL_Y0 - 38,
      centerX: cx, centerY: TOOL_Y0 + (toolMaxY - TOOL_Y0) / 2,
      box: { x: cx - toolHalfWidth - R - BLUR_PAD, y: TOOL_Y0 - R - BLUR_PAD, w: (toolHalfWidth + R + BLUR_PAD) * 2, h: (toolMaxY - TOOL_Y0) + (R + BLUR_PAD) * 2 },
    }

    if (genNodes.length > 0 && toolNodes.length > 0) {
      const lastGen   = genNodes.reduce((a, b) => a.y > b.y ? a : b)
      const firstTool = toolNodes.reduce((a, b) => a.y < b.y ? a : b)
      // cross-track edges belong to neither track — always hidden when zoomed
      edges.push({ id: `cross-${track.id}`, trackId: null, x1: lastGen.x, y1: lastGen.y, x2: firstTool.x, y2: firstTool.y })
    }
  })

  return { edges, groups, canvasHeight: maxCanvasY + R + BLUR_PAD + 48 }
}

interface ActiveModule {
  id: string
  title: string
  total: number
  completed: number
  locked: boolean
  anchorRect: DOMRect
}

export default function LearningPath() {
  const { user } = useAuth()
  const [tracks, setTracks]                 = useState<TrackNode[]>([])
  const [modulesMap, setModulesMap]         = useState<Record<string, ModuleNode[]>>({})
  const [prereqMap, setPrereqMap]           = useState<Map<string, string[]>>(new Map())
  const [selected, setSelected]             = useState<TrackNode | null>(null)
  const [zoomScale, setZoomScale]           = useState(1)
  const [zoomOrigin, setZoomOrigin]         = useState('50% 50%')
  const [canvasWidth, setCanvasWidth]       = useState(0)
  const [isEditMode, setIsEditMode]         = useState(false)
  const [selectedModule, setSelectedModule] = useState<{ id: string; title: string } | null>(null)
  const [activeModule, setActiveModule]     = useState<ActiveModule | null>(null)
  const [lessonCountMap, setLessonCountMap] = useState<Record<string, { total: number; completed: number }>>({})
  const [loadError, setLoadError]           = useState<string | null>(null)
  const [loadKey, setLoadKey]               = useState(0)    // increment to trigger data reload
  const [showAddTrack, setShowAddTrack]     = useState(false)
  const [showAddModule, setShowAddModule]   = useState(false)

  const canvasRef = useRef<HTMLDivElement | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const userId = user?.id

  const reload = useCallback(() => setLoadKey(k => k + 1), [])

  useEffect(() => {
    if (!userId) return
    let cancelled = false
    setLoadError(null)

    async function load() {
      // One aggregate replaces the old 7-query chain. The backend returns ALL
      // tracks/modules with per-caller `assigned` flags — filtering to the
      // assigned subset here mirrors the old client-side joins exactly.
      const { data } = await client.GET('/api/learning/graph')
      if (cancelled) return
      if (!data) { setLoadError('Failed to load your tracks. Please refresh.'); return }

      const assignedTracks = data.tracks
        .filter(t => t.assigned)
        .sort((a, b) => a.sort_order - b.sort_order)
      setTracks(assignedTracks)

      if (assignedTracks.length === 0) return

      const trackIds = new Set(assignedTracks.map(t => t.id))
      const assignedModules = data.modules
        .filter(m => m.assigned && trackIds.has(m.track_id))
        .sort((a, b) => a.sort_order - b.sort_order)

      const map: Record<string, ModuleNode[]> = {}
      for (const mod of assignedModules) {
        if (!map[mod.track_id]) map[mod.track_id] = []
        map[mod.track_id].push(mod)
      }
      setModulesMap(map)

      // Prereq rows keyed on assigned modules only (the old query's .in filter);
      // an unassigned prerequisite therefore stays "not completable" → locked.
      const assignedModuleIds = new Set(assignedModules.map(m => m.id))
      const pMap = new Map<string, string[]>()
      for (const row of data.prerequisites) {
        if (!assignedModuleIds.has(row.module_id)) continue
        if (!pMap.has(row.module_id)) pMap.set(row.module_id, [])
        pMap.get(row.module_id)!.push(row.prerequisite_module_id)
      }
      setPrereqMap(pMap)

      const lcMap: Record<string, { total: number; completed: number }> = {}
      for (const mod of assignedModules) {
        lcMap[mod.id] = { total: mod.lesson_count, completed: mod.completed_lesson_count }
      }
      setLessonCountMap(lcMap)
    }

    load()
    return () => { cancelled = true }
  }, [userId, loadKey])

  useLayoutEffect(() => {
    if (!canvasRef.current) return
    const ro = new ResizeObserver(entries => setCanvasWidth(entries[0].contentRect.width))
    ro.observe(canvasRef.current)
    return () => ro.disconnect()
  }, [])

  const { edges, groups, canvasHeight } = useMemo(
    () => buildGraph(tracks, modulesMap, prereqMap, canvasWidth),
    [tracks, modulesMap, prereqMap, canvasWidth]
  )

  const isAdmin = user?.role === 'admin'

  function isModuleUnlocked(moduleId: string): boolean {
    if (isAdmin) return true
    const preds = prereqMap.get(moduleId)
    if (!preds || preds.length === 0) return true
    return preds.every(predId => {
      const counts = lessonCountMap[predId]
      return !!counts && counts.total > 0 && counts.completed === counts.total
    })
  }

  function handleTrackClick(trackId: string) {
    const group    = groups[trackId]
    const canvasEl = canvasRef.current
    if (!group || !canvasEl) return
    if (selected?.id === trackId) { zoomOut(); return }

    const canvasRect = canvasEl.getBoundingClientRect()
    const groupScreenX = canvasRect.left + group.centerX
    const groupScreenY = canvasRect.top  + group.centerY
    const vpCX      = window.innerWidth / 2
    const topOffset = 160
    const vpTopMin  = 190  // first node won't be placed above this (clears the back button + zoomed radius)

    const groupSpan = group.box.h - BLUR_PAD * 2
    const scale     = Math.max(Math.min((window.innerHeight * 0.55) / groupSpan, 3.2), 3.0)

    // Center the group vertically, but shift down if the topmost node would end up
    // above the viewport (can't scroll to it because scrollTop can't go negative).
    const nodeYs      = group.nodes.map(n => n.y)
    const firstNodeY  = nodeYs.length > 0 ? Math.min(...nodeYs) : group.centerY
    const vpCY_center = topOffset + (window.innerHeight - topOffset) / 2
    const firstOnScreen = vpCY_center - (group.centerY - firstNodeY) * scale
    const vpCY = firstOnScreen < vpTopMin
      ? vpTopMin + (group.centerY - firstNodeY) * scale
      : vpCY_center

    // Compute the transform origin (element-relative) such that scaling alone
    // places the group center exactly at vpCX/vpCY — no x/y translation needed.
    const ox = (vpCX - groupScreenX * scale) / (1 - scale) - canvasRect.left
    const oy = (vpCY - groupScreenY * scale) / (1 - scale) - canvasRect.top

    setZoomOrigin(`${ox}px ${oy}px`)
    setSelected(group.track)
    setZoomScale(scale)
    setActiveModule(null)
  }

  function zoomOut() {
    setSelected(null)
    setZoomScale(1)
    setActiveModule(null)
  }

  const isZoomed = !!selected

  return (
    <div style={{ height: '100vh', background: 'var(--dlw-surface)', fontFamily: 'var(--dlw-font-body)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      <AppNav backTo="/" title="Learning path" />

      {/* Edit mode banner */}
      <AnimatePresence>
        {isEditMode && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            style={{ flexShrink: 0, background: '#F0FAF9', borderBottom: '1px solid #B2EBE6', padding: '9px 24px 9px 40px', display: 'flex', alignItems: 'center', gap: 10, zIndex: 10 }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3BC9BC', flexShrink: 0 }} />
            <span style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, color: '#1D7A52' }}>
              Edit mode — click a module node to manage its lessons
            </span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <button
                type="button"
                onClick={() => setShowAddTrack(true)}
                style={{ padding: '6px 14px', borderRadius: 999, border: '1.5px solid #3BC9BC', background: '#fff', color: '#1D7A52', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap' }}
              >
                + Add Track
              </button>
              <button
                type="button"
                onClick={() => setShowAddModule(true)}
                style={{ padding: '6px 14px', borderRadius: 999, border: 'none', background: '#3BC9BC', color: '#fff', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap' }}
              >
                + Add Module
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content area — scrollable in overview, locked when zoomed so canvas rect is stable */}
      <div ref={scrollRef} style={{ flex: 1, position: 'relative', overflowY: 'auto', overflowX: 'hidden' }}>

        {/* Error state */}
        {loadError && (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#C42828', margin: 0 }}>{loadError}</p>
          </div>
        )}

        {/* Empty state */}
        {!loadError && user && tracks.length === 0 && (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8 }}>
            <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 16, color: '#3C3C3C', margin: 0 }}>No tracks assigned yet</p>
            <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0 }}>Your delaware contact will set up your learning path.</p>
          </div>
        )}

        {/* Welcome text — position:absolute so disappearing never shifts the canvas position */}
        <AnimatePresence>
          {!isZoomed && tracks.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.25 }}
              style={{ position: 'absolute', top: 28, left: 0, right: 0, display: 'flex', justifyContent: 'center', pointerEvents: 'none', zIndex: 5 }}
            >
              <div style={{ width: 'min(960px, 100%)', padding: '0 40px', textAlign: 'left' }}>
                <p style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.16em', color: '#EF463C', margin: '0 0 14px' }}>
                  your learning path
                </p>
                <h1 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 44, lineHeight: 1.12, letterSpacing: '-0.015em', color: '#101820', margin: '0 0 12px' }}>
                  Your path to working with AI.
                </h1>
                <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 17, lineHeight: 1.6, color: '#8A8A8A', margin: 0, maxWidth: '54ch' }}>
                  A set of tracks built around where you are today. Click any track to explore its modules.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Graph — always in DOM so ResizeObserver on canvasRef fires on mount; hidden via display:none when no tracks */}
        <div style={{ width: '100%', display: tracks.length === 0 ? 'none' : 'flex', justifyContent: 'center', paddingTop: 200, paddingBottom: 80 }}>
          <motion.div
            ref={canvasRef}
                animate={{ scale: zoomScale }}
                transition={{ type: 'spring', stiffness: 220, damping: 32 }}
                style={{ position: 'relative', width: '100%', maxWidth: 900, height: canvasHeight || 500, transformOrigin: zoomOrigin }}
              >
                {canvasWidth > 0 && (
                  <>
                    {/* Edges — all dotted teal, 90-degree turns */}
                    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible', pointerEvents: 'none', zIndex: 0 }}>
                      {edges.map(e => (
                        <motion.path key={e.id}
                          d={orthogonalPath(e.x1, e.y1, e.x2, e.y2)}
                          stroke={EDGE_COLOR}
                          strokeWidth={1.5}
                          strokeDasharray={EDGE_DASH}
                          fill="none"
                          animate={{
                            opacity: isZoomed
                              ? (e.trackId === selected?.id ? 0.55 : 0)
                              : 0.5,
                          }}
                          transition={{ duration: 0.3 }}
                        />
                      ))}
                    </svg>

                    {/* Per-track groups */}
                    {Object.values(groups).map(group => {
                      const { track, nodes: groupNodes, box, labelX, labelY } = group
                      const isSelected = selected?.id === track.id
                      const isOther    = isZoomed && !isSelected

                      return (
                        <React.Fragment key={track.id}>

                          {/* Nodes */}
                          <motion.div
                            animate={{
                              filter: isOther ? 'blur(6px)' : 'blur(0px)',
                              opacity: isOther ? 0 : 1,
                            }}
                            transition={{ duration: 0.3 }}
                            style={{ position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, pointerEvents: 'none', zIndex: 1 }}
                          >
                            {groupNodes.map(node => {
                              const locked = !isModuleUnlocked(node.id)
                              return (
                              <div key={node.id} style={{
                                position: 'absolute',
                                left: node.x - R - box.x,
                                top:  node.y - R - box.y,
                                width: R * 2, height: R * 2,
                                borderRadius: '50%',
                                overflow: 'hidden',
                                opacity: locked ? 0.45 : 1,
                              }}>
                                <img src="/module.png" alt="" style={{
                                  position: 'absolute', inset: 0,
                                  width: '100%', height: '100%',
                                  objectFit: 'cover',
                                }} />
                                {node.title && (
                                  <span style={{
                                    position: 'absolute', inset: 0,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontFamily: 'var(--dlw-font-ui)',
                                    fontWeight: 700,
                                    fontSize: 5,
                                    color: '#fff',
                                    textAlign: 'center',
                                    lineHeight: 1.2,
                                    padding: '6px',
                                    wordBreak: 'break-word',
                                  }}>
                                    {node.title}
                                  </span>
                                )}
                                {locked && (
                                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#fff" style={{ position: 'absolute', bottom: 2, right: 2, width: 12, height: 12 }}>
                                    <path fillRule="evenodd" d="M12 1.5a5.25 5.25 0 0 0-5.25 5.25v3a3 3 0 0 0-3 3v6.75a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3v-6.75a3 3 0 0 0-3-3v-3c0-2.9-2.35-5.25-5.25-5.25Zm3.75 8.25v-3a3.75 3.75 0 1 0-7.5 0v3h7.5Z" clipRule="evenodd" />
                                  </svg>
                                )}
                              </div>
                              )
                            })}
                          </motion.div>

                          {/* Track label */}
                          <motion.div
                            animate={{ opacity: isZoomed ? 0 : 1 }}
                            transition={{ duration: 0.2 }}
                            style={{
                              position: 'absolute', left: labelX, top: labelY,
                              transform: 'translateX(-50%)',
                              fontSize: 11, fontWeight: 700, color: track.color ?? undefined,
                              fontFamily: 'var(--dlw-font-ui)', letterSpacing: '0.06em',
                              textTransform: 'uppercase', whiteSpace: 'nowrap',
                              pointerEvents: 'none', zIndex: 3,
                            }}
                          >
                            {track.name}
                          </motion.div>

                          {/* Click target — track zoom (non-edit mode) */}
                          {!isEditMode && (
                            <motion.div
                              animate={{ opacity: isOther ? 0 : 1 }}
                              onClick={() => handleTrackClick(track.id)}
                              whileHover={!isZoomed ? { scale: 1.06 } : {}}
                              transition={{ duration: 0.25 }}
                              style={{
                                position: 'absolute', left: box.x, top: box.y,
                                width: box.w, height: box.h,
                                borderRadius: 14,
                                cursor: isZoomed ? 'default' : 'pointer',
                                zIndex: 4,
                              }}
                            />
                          )}

                          {/* Per-node click targets (zoomed non-edit mode) */}
                          {isZoomed && !isEditMode && groupNodes.map(node => (
                            <div
                              key={`zoom-node-${node.id}`}
                              onClick={e => {
                                e.stopPropagation()
                                const rect = e.currentTarget.getBoundingClientRect()
                                setActiveModule({
                                  id: node.id, title: node.title,
                                  total:     lessonCountMap[node.id]?.total     ?? 0,
                                  completed: lessonCountMap[node.id]?.completed ?? 0,
                                  locked:    !isModuleUnlocked(node.id),
                                  anchorRect: rect,
                                })
                              }}
                              style={{
                                position: 'absolute',
                                left: node.x - R, top: node.y - R,
                                width: R * 2, height: R * 2,
                                borderRadius: '50%',
                                cursor: 'pointer',
                                zIndex: 6,
                              }}
                            />
                          ))}

                          {/* Per-node click targets (edit mode only) */}
                          {isEditMode && groupNodes.map(node => (
                            <motion.div
                              key={`edit-${node.id}`}
                              animate={{ opacity: 1 }}
                              onClick={() => setSelectedModule({ id: node.id, title: node.title })}
                              whileHover={{ scale: 1.15 }}
                              transition={{ duration: 0.15 }}
                              title={`Edit lessons for: ${node.title}`}
                              style={{
                                position: 'absolute',
                                left: node.x - R,
                                top:  node.y - R,
                                width: R * 2, height: R * 2,
                                borderRadius: '50%',
                                cursor: 'pointer',
                                zIndex: 5,
                                border: '2.5px solid #3BC9BC',
                                boxShadow: '0 0 0 3px rgba(59,201,188,0.25)',
                                boxSizing: 'border-box',
                              }}
                            />
                          ))}

                        </React.Fragment>
                      )
                    })}
                  </>
                )}
          </motion.div>
        </div>

      </div>

      {/* Back button — fixed so it stays above graph when scrolling */}
      <AnimatePresence>
        {isZoomed && (
          <motion.div
            initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{ position: 'fixed', top: 76, left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 50, pointerEvents: 'none' }}
          >
            <button
              onClick={zoomOut}
              style={{ pointerEvents: 'auto', background: '#fff', border: '1px solid var(--dlw-border)', borderRadius: 999, padding: '11px 28px', cursor: 'pointer', fontSize: 14, fontWeight: 600, color: 'var(--dlw-text)', fontFamily: 'var(--dlw-font-body)', boxShadow: '0 4px 20px rgba(0,0,0,0.12)' }}
            >
              ← Overview
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Admin edit mode toggle — floating bottom-right */}
      {isAdmin && (
        <button
          onClick={() => { setIsEditMode(m => !m); setSelectedModule(null) }}
          style={{
            position: 'fixed', bottom: 28, right: selectedModule ? 448 : 28,
            padding: '10px 22px', borderRadius: 999,
            background: isEditMode ? '#3BC9BC' : '#fff',
            border: isEditMode ? '2px solid #3BC9BC' : '1.5px solid #E2E2E2',
            color: isEditMode ? '#fff' : '#3C3C3C',
            fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14,
            cursor: 'pointer', zIndex: 200,
            boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
            transition: 'right 0.25s ease',
          }}
        >
          {isEditMode ? '✓ Editing' : 'Edit content'}
        </button>
      )}

      {/* Module panel */}
      {isEditMode && selectedModule && (
        <ModulePanel
          moduleId={selectedModule.id}
          moduleName={selectedModule.title}
          onClose={() => setSelectedModule(null)}
        />
      )}

      {/* Transparent backdrop — closes popup without zooming out */}
      {activeModule && (
        <div
          onClick={() => setActiveModule(null)}
          style={{ position: 'fixed', inset: 0, zIndex: 199 }}
        />
      )}

      {/* Module popup — shown when clicking a node in zoomed non-edit view */}
      <AnimatePresence>
        {activeModule && (
          <ModulePopup
            moduleId={activeModule.id}
            title={activeModule.title}
            total={activeModule.total}
            completed={activeModule.completed}
            locked={activeModule.locked}
            anchorRect={activeModule.anchorRect}
            onClose={() => setActiveModule(null)}
          />
        )}
      </AnimatePresence>

      {/* Add Track modal */}
      {showAddTrack && (
        <AddTrackModal
          onClose={() => setShowAddTrack(false)}
          onAdded={() => { setShowAddTrack(false); reload() }}
        />
      )}

      {/* Add Module modal */}
      {showAddModule && (
        <AddModuleModal
          onClose={() => setShowAddModule(false)}
          onAdded={() => { setShowAddModule(false); reload() }}
        />
      )}
    </div>
  )
}
