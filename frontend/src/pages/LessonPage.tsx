import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { client, errorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import { parseMdxToBlocks } from '../lib/mdxParser'
import { blocksToMdx } from '../lib/blocksToMdx'
import { classifyLessonLoadError, type LessonLoadError } from '../lib/lessonLoadError'
import { useUnsavedGuard } from '../lib/useUnsavedGuard'
import LessonView from '../components/lesson/LessonView'
import LessonEditor, { type EditedLesson } from '../components/lesson/LessonEditor'
import LessonFeedback from '../components/LessonFeedback'
import type { ContentBlock } from '../types/contentBlocks'
import type { LessonDetail, ModuleLessonItem } from '../types/domain'

export default function LessonPage() {
  const { lessonId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate     = useNavigate()
  const { user }     = useAuth()

  // Derived before the state block: the initial editMode depends on it. AppRoutes
  // gates on `loading` before rendering any page, so `user` is already resolved here.
  const isAdmin = user?.role === 'admin'

  const [lesson, setLesson]   = useState<LessonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  // Why the load produced no lesson — 404 vs 403 vs "the request itself
  // failed" need different copy (see the render guards below).
  const [loadError, setLoadError] = useState<LessonLoadError | null>(null)
  const [reloadKey, setReloadKey]   = useState(0)
  // Admin-only: the editor pane used to render for anyone who put ?edit=true in
  // the URL. Writes were always 403'd server-side, so this was cosmetic — but it
  // showed learners an editing surface that isn't theirs (review 2.9).
  const [editMode, setEditMode]   = useState(isAdmin && searchParams.get('edit') === 'true')
  const [mdxMode, setMdxMode]     = useState(false)
  const [mdxText, setMdxText]     = useState('')
  // What the pane was seeded with on opening (blocksToMdx of the lesson), so an
  // untouched pane does not count as unsaved work.
  const [mdxSeed, setMdxSeed]     = useState('')
  const [mdxSaving, setMdxSaving] = useState(false)
  const [mdxError, setMdxError]   = useState<string | null>(null)
  const [quizDone, setQuizDone]           = useState(false)
  const [answers, setAnswers]             = useState<Record<string, string>>({})
  const [completing, setCompleting]       = useState(false)
  const [markError, setMarkError]         = useState<string | null>(null)
  const [moduleLessons, setModuleLessons] = useState<ModuleLessonItem[]>([])
  const [completedIds, setCompletedIds]   = useState<Set<string>>(new Set())
  const [nextLessonId, setNextLessonId]   = useState<string | null>(null)

  // The lesson content scrolls inside this <main>, and the page never remounts
  // between lessons — reset it (and the window) to the top on every lesson change.
  const contentRef = useRef<HTMLElement>(null)

  const completed = lessonId ? completedIds.has(lessonId) : false

  // content_blocks crosses the JSONB boundary as unknown[]; this is the one
  // cast to the hand-written union (design-frontend §2). Memoized so the
  // identity is stable — mdxBlocks below depends on it, and a fresh array
  // every render would defeat that memo.
  const blocks = useMemo(
    () => (lesson?.content_blocks ?? []) as ContentBlock[],
    [lesson?.content_blocks],
  )
  const hasQuiz = blocks.some(b => b.type === 'quiz')

  // The MDX parser is a full multi-pass regex scan over the whole document
  // (lib/mdxParser.ts). Without this memo it re-ran on every render — i.e. on
  // every keystroke in the MDX pane.
  const mdxBlocks = useMemo(
    () => (mdxText.trim() ? parseMdxToBlocks(mdxText) : blocks),
    [mdxText, blocks],
  )

  // The MDX pane is an editor too: pasted or edited MDX is lost on reload until
  // "Save as blocks". Above the early returns below — hooks can't be conditional.
  useUnsavedGuard(mdxMode && mdxText.trim() !== '' && mdxText !== mdxSeed)

  const userId = user?.id
  const moduleId = lesson?.module_id

  // One aggregate call replaces the old lesson + module + answers + prefetch
  // chain: next_lesson_id already resolves the cross-module hop server-side.
  useEffect(() => {
    if (!lessonId) return
    const lid = lessonId
    let cancelled = false
    // Deliberate deviation from the old page: reset per-lesson UI state on
    // navigation. The component never remounts between lessons, so the old
    // page leaked quizDone/completing from the previous lesson — a quiz in
    // the next lesson was silently ungated.
    setQuizDone(false)
    setCompleting(false)
    setMarkError(null)
    // The MDX pane holds the previous lesson's text: left open, "Save as
    // blocks" would PATCH it into this lesson, and the unsaved guard would
    // compare against a stale seed. Close it on every lesson change.
    setMdxMode(false)
    setMdxText('')
    setMdxSeed('')
    // Start each lesson at the top (fresh open and lesson→lesson navigation).
    contentRef.current?.scrollTo(0, 0)
    window.scrollTo(0, 0)
    async function load() {
      // client.GET can REJECT rather than resolve: openapi-fetch has no
      // onError middleware here, so a fetch that never gets a response at all
      // (offline, a dropped connection mid-deploy) throws instead of coming
      // back as some sentinel status. Without this try/catch that rejection
      // was unhandled and `loading` never went back to false — the page (and
      // a failed "Try again") got stuck on "Loading…" forever.
      try {
        const { data, error, response } = await client.GET('/api/lessons/{lesson_id}', {
          params: { path: { lesson_id: lid } },
        })
        if (cancelled) return
        if (!data) {
          setLesson(null)
          // 404 = doesn't exist (or isn't the caller's); 403 = exists but
          // access denied — show the server's own message. Anything else
          // (500, 502, a malformed id, …) is a failure to load, and telling
          // the learner the lesson "doesn't exist" would be both wrong and
          // unactionable.
          setLoadError(classifyLessonLoadError(response.status, error))
          setLoading(false)
          return
        }
        setLoadError(null)
        setLesson(data)
        setAnswers((data.my_answers as Record<string, string> | null) ?? {})
        setNextLessonId(data.next_lesson_id)
        setLoading(false)
      } catch {
        if (cancelled) return
        setLesson(null)
        setLoadError({ kind: 'failed' })
        setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [lessonId, reloadKey])

  // Sidebar: the caller's ASSIGNED lessons in the current module + per-lesson
  // completion. completedIds stays unfiltered so the current lesson's own
  // completed state is right even if it was unassigned after completion.
  useEffect(() => {
    if (!userId || !moduleId) return
    const mid = moduleId
    let cancelled = false
    async function load() {
      const { data } = await client.GET('/api/modules/{module_id}/lessons', {
        params: { path: { module_id: mid } },
      })
      if (cancelled || !data) return
      setModuleLessons(data.lessons.filter(l => l.assigned))
      setCompletedIds(new Set(data.lessons.filter(l => l.completed).map(l => l.id)))
    }
    load()
    return () => { cancelled = true }
  }, [userId, moduleId])

  function handleAnswerChange(blockId: string, text: string) {
    setAnswers(a => ({ ...a, [blockId]: text }))
  }

  // Stable identity is load-bearing: QuizBlock's completion effect depends on
  // onComplete. With an inline arrow, the still-mounted previous quiz (results,
  // all-correct) refires on the render right after navigation and undoes the
  // per-lesson quizDone reset above.
  const onQuizComplete = useCallback(() => setQuizDone(true), [])

  const backUrl = '/learning'

  async function markCompleteAndAdvance() {
    if (!user || !lessonId || completed) return
    setCompleting(true)
    setMarkError(null)

    const { error } = await client.PUT('/api/lessons/{lesson_id}/progress', {
      params: { path: { lesson_id: lessonId } },
      body: { answers },
    })
    if (error) {
      setMarkError('Could not save your progress. Please try again.')
      setCompleting(false)
      return
    }
    setCompletedIds(s => new Set([...s, lessonId]))
    setCompleting(false)

    navigate(nextLessonId ? `/learning/lesson/${nextLessonId}` : backUrl)
  }

  /* ── admin edit + MDX modes ── */

  // Stable identity is load-bearing here too: LessonEditor's live-preview
  // effect depends on onLiveChange. An inline arrow would refire the effect on
  // every render (each firing calls setLesson with a fresh object) — an
  // infinite loop. The old app passed the bare setLesson for the same reason.
  const handleEditorLiveChange = useCallback((updated: EditedLesson) => {
    setLesson(l => (l ? { ...l, title: updated.title, content_blocks: updated.content_blocks } : l))
  }, [])

  function handleEditorSave(updated: EditedLesson) {
    setLesson(l => (l ? { ...l, title: updated.title, content_blocks: updated.content_blocks } : l))
    setEditMode(false)
  }

  async function saveMdx() {
    if (!lesson) return
    const newBlocks = parseMdxToBlocks(mdxText)
    setMdxSaving(true)
    setMdxError(null)
    const { data, error } = await client.PATCH('/api/admin/lessons/{lesson_id}', {
      params: { path: { lesson_id: lesson.id } },
      body: { content_blocks: newBlocks },
    })
    setMdxSaving(false)
    if (error || !data) { setMdxError(errorMessage(error, 'Failed to save.')); return }
    // Use the backend's stamped content_blocks, not the locally parsed ones:
    // the write strips ephemeral SAS urls, so the parsed blocks would render
    // media as placeholders until a reload. The response is re-stamped.
    setLesson(l => (l ? { ...l, content_blocks: data.content_blocks } : l))
    setMdxMode(false)
    setMdxText('')
    setEditMode(true)
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 15, color: '#8A8A8A' }}>Loading…</p>
      </div>
    )
  }

  if (!lesson) {
    // null (never loaded) and 'not-found' both render the same "doesn't
    // exist" copy — loadError is only ever null here on the very first
    // render, before the load effect has run once.
    const isFailedLoad = loadError?.kind === 'failed'
    const message =
      loadError?.kind === 'forbidden' ? loadError.message
      : isFailedLoad ? "We couldn't load this lesson."
      : 'Lesson not found.'
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 16, color: '#101820' }}>
          {message}
        </p>
        {isFailedLoad && (
          <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0 }}>
            Something went wrong on our side. Please try again.
          </p>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          {isFailedLoad && (
            <button
              onClick={() => { setLoading(true); setReloadKey(k => k + 1) }}
              style={{ background: '#C42828', border: 'none', borderRadius: 999, padding: '9px 20px', cursor: 'pointer', fontSize: 14, color: '#fff', fontWeight: 700, fontFamily: 'var(--dlw-font-body)' }}
            >
              Try again
            </button>
          )}
          <button onClick={() => navigate('/learning')} style={{ background: 'none', border: '1px solid #E2E2E2', borderRadius: 999, padding: '9px 20px', cursor: 'pointer', fontSize: 14, color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)' }}>
            ← Back to learning path
          </button>
        </div>
      </div>
    )
  }

  const activeMode = editMode ? 'edit' : mdxMode ? 'mdx' : 'view'

  return (
    <div style={{
      // Edit/MDX modes pin the page to the viewport so preview and editor scroll
      // independently. inset:0 (not height:100vh) — vh units disagree with the
      // baked-in :root zoom across Chromium versions, zero offsets never do.
      ...(activeMode === 'view'
        ? { minHeight: '100vh' }
        : { position: 'fixed' as const, inset: 0, overflow: 'hidden' }),
      background: '#fff', fontFamily: 'var(--dlw-font-body)', display: 'flex', flexDirection: 'column',
    }}>

      <AppNav
        backTo={backUrl}
        backLabel="← Learning path"
        rightExtra={isAdmin && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button"
              onClick={() => {
                if (!mdxMode) { const seed = blocksToMdx(blocks); setMdxText(seed); setMdxSeed(seed) }
                setMdxMode(m => !m); setEditMode(false)
              }}
              style={{ padding: '7px 18px', borderRadius: 999, background: activeMode === 'mdx' ? '#F5F3FF' : '#fff', border: activeMode === 'mdx' ? '1.5px solid #7C3AED' : '1.5px solid #E2E2E2', color: activeMode === 'mdx' ? '#5B21B6' : '#3C3C3C', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
            >
              MDX
            </button>
            <button type="button"
              onClick={() => { setEditMode(m => !m); setMdxMode(false) }}
              style={{ padding: '7px 18px', borderRadius: 999, background: activeMode === 'edit' ? '#3BC9BC' : '#fff', border: activeMode === 'edit' ? '2px solid #3BC9BC' : '1.5px solid #E2E2E2', color: activeMode === 'edit' ? '#fff' : '#3C3C3C', fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}
            >
              {activeMode === 'edit' ? '✓ Editing' : 'Edit content'}
            </button>
          </div>
        )}
      />

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {activeMode === 'edit' ? (
          /* Edit mode: live preview left + block editor right */
          <>
            <div style={{ flex: 1, overflowY: 'auto', borderRight: '1px solid #E2E2E2', background: '#fff' }}>
              <div style={{ maxWidth: 760, margin: '0 auto', padding: '48px 40px' }}>
                <p style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#EF463C', margin: '0 0 14px' }}>
                  {lesson.module.title}
                </p>
                <h1 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 38, lineHeight: 1.15, letterSpacing: '-0.015em', color: '#101820', margin: '0 0 32px' }}>
                  {lesson.title}
                </h1>
                <LessonView blocks={blocks} />
              </div>
            </div>
            <div style={{ width: 480, flexShrink: 0, display: 'flex', flexDirection: 'column', background: '#fff' }}>
              <LessonEditor
                lesson={{ id: lesson.id, title: lesson.title, content_blocks: blocks }}
                onSave={handleEditorSave}
                onLiveChange={handleEditorLiveChange}
              />
            </div>
          </>

        ) : activeMode === 'mdx' ? (
          /* MDX import mode: rendered preview left + MDX textarea right */
          <>
            <div style={{ flex: 1, overflowY: 'auto', borderRight: '1px solid #E2E2E2', background: '#fff' }}>
              <div style={{ maxWidth: 760, margin: '0 auto', padding: '48px 40px' }}>
                <p style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#EF463C', margin: '0 0 14px' }}>
                  {lesson.module.title}
                </p>
                <h1 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 38, lineHeight: 1.15, letterSpacing: '-0.015em', color: '#101820', margin: '0 0 32px' }}>
                  {lesson.title}
                </h1>
                {mdxBlocks.length > 0
                  ? <LessonView blocks={mdxBlocks} />
                  : <p style={{ fontWeight: 300, fontSize: 14, color: '#B0A090', fontStyle: 'italic' }}>Paste MDX on the right to preview it here.</p>
                }
              </div>
            </div>
            <div style={{ width: 480, flexShrink: 0, display: 'flex', flexDirection: 'column', background: '#fff' }}>
              {/* MDX panel toolbar */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '12px 20px', borderBottom: '1px solid #E2E2E2', flexShrink: 0,
              }}>
                <span style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 14, color: '#8A8A8A' }}>
                  {mdxText.trim() ? `${mdxBlocks.length} block${mdxBlocks.length !== 1 ? 's' : ''} parsed` : 'Paste MDX below'}
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => setMdxText('')}
                    disabled={!mdxText.trim()}
                    style={{
                      padding: '7px 14px', borderRadius: 999,
                      background: '#fff', border: '1px solid #E2E2E2',
                      color: mdxText.trim() ? '#3C3C3C' : '#C0C0C0',
                      fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
                      cursor: mdxText.trim() ? 'pointer' : 'default',
                    }}
                  >
                    Clear
                  </button>
                  <button
                    onClick={saveMdx}
                    disabled={!mdxText.trim() || mdxSaving}
                    style={{
                      padding: '7px 20px', borderRadius: 999,
                      background: mdxText.trim() ? '#3BC9BC' : '#E2E2E2',
                      border: 'none',
                      color: mdxText.trim() ? '#fff' : '#8A8A8A',
                      fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13,
                      cursor: mdxText.trim() ? 'pointer' : 'default',
                    }}
                  >
                    {mdxSaving ? 'Saving…' : 'Save as blocks'}
                  </button>
                </div>
              </div>

              {mdxError && (
                <div style={{ padding: '10px 20px', background: '#FEF2F2', color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontSize: 13, flexShrink: 0 }}>
                  {mdxError}
                </div>
              )}

              <textarea
                value={mdxText}
                onChange={e => setMdxText(e.target.value)}
                placeholder={`# Lesson heading\n\nParagraph text here.\n\n> Callout box text\n\n<Cards data='[{"title":"Example","body":"Description"}]' />\n\n<Quiz data='[{"q":"Question?","options":["A","B"],"correct":0}]' />`}
                spellCheck={false}
                style={{
                  flex: 1, resize: 'none', border: 'none', outline: 'none',
                  padding: '20px', fontFamily: 'monospace', fontSize: 13,
                  lineHeight: 1.6, color: '#3C3C3C', background: '#FAFAFA',
                  overflowY: 'auto',
                }}
              />
            </div>
          </>

        ) : (
          /* Learner view: sidebar + content */
          <>
            {/* Module sidebar */}
            <aside style={{
              width: 240, flexShrink: 0,
              borderRight: '1px solid #E2E2E2',
              background: '#fff',
              display: 'flex', flexDirection: 'column',
              overflowY: 'auto',
            }}>
              <div style={{ padding: '24px 20px 16px', borderBottom: '1px solid #F0EFED' }}>
                <p style={{ margin: 0, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.14em', color: '#8A8A8A' }}>
                  Module
                </p>
                <p style={{ margin: '4px 0 0', fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 13, color: '#101820', lineHeight: 1.3 }}>
                  {lesson.module.title}
                </p>
              </div>
              <nav style={{ flex: 1, padding: '8px 0' }}>
                {moduleLessons.map((l, i) => {
                  const isCurrent = l.id === lessonId
                  const isDone    = completedIds.has(l.id)
                  return (
                    <button
                      key={l.id}
                      onClick={() => !isCurrent && navigate(`/learning/lesson/${l.id}`)}
                      className={isCurrent ? undefined : 'menu-item-hover'}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10,
                        width: '100%', textAlign: 'left',
                        padding: '10px 16px 10px 20px',
                        background: isCurrent ? 'var(--dlw-red-tint)' : 'none',
                        border: 'none',
                        borderLeft: `3px solid ${isCurrent ? '#EF463C' : 'transparent'}`,
                        cursor: isCurrent ? 'default' : 'pointer',
                        fontFamily: 'var(--dlw-font-body)',
                      }}
                    >
                      <span style={{
                        width: 20, height: 20, borderRadius: '50%', flexShrink: 0, marginTop: 1,
                        background: isDone ? '#EF463C' : isCurrent ? '#101820' : '#E2E2E2',
                        color: (isDone || isCurrent) ? '#fff' : '#8A8A8A',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 9, fontWeight: 700,
                      }}>
                        {isDone ? '✓' : i + 1}
                      </span>
                      <span style={{
                        fontSize: 13, lineHeight: 1.4,
                        fontWeight: isCurrent ? 600 : 400,
                        color: isDone ? '#8A8A8A' : isCurrent ? '#101820' : '#3C3C3C',
                      }}>
                        {l.title}
                      </span>
                    </button>
                  )
                })}
              </nav>
            </aside>

            {/* Lesson content */}
            <main ref={contentRef} style={{ flex: 1, overflowY: 'auto', padding: '44px 40px 90px' }}>
              <div style={{ maxWidth: 720, margin: '0 auto' }}>

                <p style={{ fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#EF463C', margin: '0 0 14px' }}>
                  {lesson.module.title}
                </p>
                <h1 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 38, lineHeight: 1.15, letterSpacing: '-0.015em', color: '#101820', margin: '0 0 32px' }}>
                  {lesson.title}
                </h1>

                <LessonView blocks={blocks} onQuizComplete={onQuizComplete} answers={answers} onAnswerChange={handleAnswerChange} />

                {!hasQuiz || quizDone ? (
                  <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid #F0EFED' }}>
                    <button
                      onClick={markCompleteAndAdvance}
                      disabled={completed || completing}
                      className={completed ? undefined : 'lesson-cta'}
                      style={{
                        padding: '11px 18px', borderRadius: 8,
                        background: completed ? '#EDFAF4' : '#C42828',
                        border: 'none',
                        color: completed ? '#1D7A52' : '#fff',
                        fontFamily: 'var(--dlw-font-body)', fontWeight: 800, fontSize: 14,
                        cursor: completed ? 'default' : 'pointer',
                        transition: 'background 0.2s, color 0.2s',
                      }}
                    >
                      {completed ? '✓ Completed' : completing ? 'Saving…' : 'Mark as complete →'}
                    </button>
                    {markError && (
                      <p style={{ marginTop: 10, fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 13, color: '#C42828' }}>
                        {markError}
                      </p>
                    )}
                  </div>
                ) : (
                  <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid #F0EFED' }}>
                    <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A' }}>
                      Complete the quiz above to continue.
                    </p>
                  </div>
                )}
              </div>
            </main>
            <LessonFeedback lessonId={lesson.id} lessonTitle={lesson.title} />
          </>
        )}
      </div>
    </div>
  )
}
