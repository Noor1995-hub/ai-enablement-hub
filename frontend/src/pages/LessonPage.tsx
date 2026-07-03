import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { client } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import AppNav from '../components/AppNav'
import LessonView from '../components/lesson/LessonView'
import type { ContentBlock } from '../types/contentBlocks'
import type { LessonDetail, ModuleLessonItem } from '../types/domain'

// Admin edit mode (LessonEditor, MDX import) is Batch 6 — this port covers
// VIEW + PROGRESS only.

export default function LessonPage() {
  const { lessonId } = useParams()
  const navigate     = useNavigate()
  const { user }     = useAuth()

  const [lesson, setLesson]   = useState<LessonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [quizDone, setQuizDone]           = useState(false)
  const [answers, setAnswers]             = useState<Record<string, string>>({})
  const [completing, setCompleting]       = useState(false)
  const [markError, setMarkError]         = useState<string | null>(null)
  const [moduleLessons, setModuleLessons] = useState<ModuleLessonItem[]>([])
  const [completedIds, setCompletedIds]   = useState<Set<string>>(new Set())
  const [nextLessonId, setNextLessonId]   = useState<string | null>(null)

  const completed = lessonId ? completedIds.has(lessonId) : false

  // content_blocks crosses the JSONB boundary as unknown[]; this is the one
  // cast to the hand-written union (design-frontend §2).
  const blocks  = (lesson?.content_blocks ?? []) as ContentBlock[]
  const hasQuiz = blocks.some(b => b.type === 'quiz')

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
    async function load() {
      const { data } = await client.GET('/api/lessons/{lesson_id}', {
        params: { path: { lesson_id: lid } },
      })
      if (cancelled) return
      if (!data) { setLesson(null); setLoading(false); return }
      setLesson(data)
      setAnswers((data.my_answers as Record<string, string> | null) ?? {})
      setNextLessonId(data.next_lesson_id)
      setLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [lessonId])

  // Sidebar: all lessons in the current module + per-lesson completion.
  useEffect(() => {
    if (!userId || !moduleId) return
    const mid = moduleId
    let cancelled = false
    async function load() {
      const { data } = await client.GET('/api/modules/{module_id}/lessons', {
        params: { path: { module_id: mid } },
      })
      if (cancelled || !data) return
      setModuleLessons(data.lessons)
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

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F9F9F8' }}>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 15, color: '#8A8A8A' }}>Loading…</p>
      </div>
    )
  }

  if (!lesson) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 16, color: '#101820' }}>Lesson not found.</p>
        <button onClick={() => navigate('/learning')} style={{ background: 'none', border: '1px solid #E2E2E2', borderRadius: 999, padding: '9px 20px', cursor: 'pointer', fontSize: 14, color: '#8A8A8A', fontFamily: 'var(--dlw-font-body)' }}>
          ← Back to learning path
        </button>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F9F9F8', fontFamily: 'var(--dlw-font-body)', display: 'flex', flexDirection: 'column' }}>

      <AppNav
        backTo={backUrl}
        backLabel="← Learning path"
      />

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Learner view: sidebar + content */}
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
              <p style={{ margin: 0, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.14em', color: '#8A8A8A' }}>
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
                    style={{
                      display: 'flex', alignItems: 'flex-start', gap: 10,
                      width: '100%', textAlign: 'left',
                      padding: '10px 16px 10px 20px',
                      background: isCurrent ? '#FEF2F2' : 'none',
                      border: 'none',
                      borderLeft: `3px solid ${isCurrent ? '#C42828' : 'transparent'}`,
                      cursor: isCurrent ? 'default' : 'pointer',
                      fontFamily: 'var(--dlw-font-body)',
                    }}
                  >
                    <span style={{
                      width: 20, height: 20, borderRadius: '50%', flexShrink: 0, marginTop: 1,
                      background: isDone ? '#C42828' : isCurrent ? '#101820' : '#E2E2E2',
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
          <main style={{ flex: 1, overflowY: 'auto', padding: '48px 40px' }}>
            <div style={{ maxWidth: 720, margin: '0 auto' }}>

              <h1 style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 36, color: '#101820', margin: '0 0 36px', lineHeight: 1.15 }}>
                {lesson.title}
              </h1>

              <LessonView blocks={blocks} onQuizComplete={onQuizComplete} answers={answers} onAnswerChange={handleAnswerChange} />

              {!hasQuiz || quizDone ? (
                <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid #E2E2E2' }}>
                  <button
                    onClick={markCompleteAndAdvance}
                    disabled={completed || completing}
                    style={{
                      padding: '12px 32px', borderRadius: 999,
                      background: completed ? '#E8F5E9' : '#C42828',
                      border: completed ? '1.5px solid #A5D6A7' : 'none',
                      color: completed ? '#2E7D32' : '#fff',
                      fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 15,
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
                <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid #E2E2E2' }}>
                  <p style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14, color: '#8A8A8A' }}>
                    Complete the quiz above to continue.
                  </p>
                </div>
              )}
            </div>
          </main>
        </>
      </div>
    </div>
  )
}
