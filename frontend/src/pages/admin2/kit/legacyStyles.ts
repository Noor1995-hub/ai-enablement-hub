/* Shared constants and styles for admin sub-components.
 * Nav/panel/project-list-and-detail styles that only the old routed admin
 * shell (removed at the admin-panel cutover) used were pruned along with
 * it — admin2's AdminShell + `adm-` CSS classes (styles/admin.css) own all
 * of that now. What remains here backs the still-reused pieces:
 * SurveyResults, BulkInviteModal, EmailTemplatesCard, InterviewCard
 * and legacyHelpers.tsx's badge components. */
import type { CSSProperties } from 'react'
import type { ComponentKey } from '../../../lib/constants'
import { levelByCode, type AssignableLevel, type LevelDef } from '../../../lib/levels'

export const COMPONENT_KEYS: ComponentKey[] = ['assessment', 'learning', 'interview']
export const COMPONENT_LABELS: Record<ComponentKey, string> = {
  assessment: 'Assessment',
  learning: 'Learning path',
  interview: 'Interview',
}

export const RUNG_LABELS = ['Not yet', 'Partial', 'Has it', 'Advanced'] as const
export const RUNG_COLORS = ['#F5F5F5', '#EEF2FF', '#FFF8EC', '#EDFAF4'] as const
export const RUNG_TEXT   = ['#8A8A8A', '#4B5CC4', '#B45309', '#1D7A52'] as const

export type ScoreLevel = AssignableLevel
export type UsageBand = 'dormant' | 'occasional' | 'regular' | 'embedded'

interface BadgeStyle {
  bg: string
  text: string
  label: string
}

// Badge bg/text are the admin status palette (same scheme as BAND_STYLE and
// RUNG_COLORS below); the display names come from the canonical level table.
// Keyed on every LEVELS code, not just ScoreLevel/AssignableLevel: the scoring
// engine only ever assigns the first three, but effective_maturity can still
// come back 'multiplier' (survey_service bumps integrator-and-above scorers
// straight to it for multiplier-gated tracks) — a badge lookup keyed on the
// narrower type silently rendered nothing for those users.
const levelName = (code: LevelDef['code']): string => levelByCode(code)!.name

export const LEVEL_STYLE: Record<LevelDef['code'], BadgeStyle> = {
  explore:      { bg: '#F5F5F5',  text: '#8A8A8A',  label: levelName('explore') },
  practitioner: { bg: '#FFF8EC',  text: '#B45309',  label: levelName('practitioner') },
  integrator:   { bg: '#EDFAF4',  text: '#1D7A52',  label: levelName('integrator') },
  multiplier:   { bg: '#EEF2FF',  text: '#4B5CC4',  label: levelName('multiplier') },
}

export const BAND_STYLE: Record<UsageBand, BadgeStyle> = {
  dormant:    { bg: '#F5F5F5', text: '#8A8A8A',  label: 'Dormant' },
  occasional: { bg: '#F5F5F5', text: '#8A8A8A',  label: 'Occasional' },
  regular:    { bg: '#FFF8EC', text: '#B45309',  label: 'Regular' },
  embedded:   { bg: '#EDFAF4', text: '#1D7A52',  label: 'Embedded' },
}

export const s = {
  /* forms */
  label:      { fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 12, letterSpacing: '0.04em', color: '#3C3C3C', marginBottom: 7 },
  input:      {
    padding: '11px 14px', fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14,
    color: '#101820', border: '1px solid #E2E2E2', borderRadius: 4, outline: 'none',
    transition: 'border-color 180ms', boxSizing: 'border-box', width: '100%',
  },
  formActions: { display: 'flex', alignItems: 'center', gap: 14, marginTop: 18 },
  submitBtn:   {
    padding: '11px 24px', fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 14,
    color: '#fff', background: '#C42828', border: 'none', borderRadius: 999,
    cursor: 'pointer', transition: 'background 180ms', whiteSpace: 'nowrap',
  },
  submitBtnDisabled: { background: '#E2E2E2', color: '#999', cursor: 'not-allowed' },
  formMsg:     { fontSize: 13, lineHeight: 1.5 },
  formMsgOk:   { color: '#1D7A52' },
  formMsgErr:  { color: '#C42828' },

  /* table */
  tableCard:   { background: '#fff', border: '1px solid #E2E2E2', borderRadius: 12, overflow: 'hidden' },
  tableHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #F0EFED' },
  tableTitle:  { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 16, color: '#101820', margin: 0 },
  table:       { width: '100%', borderCollapse: 'collapse' },
  th: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8A8A8A',
    textAlign: 'left', padding: '12px 24px', borderBottom: '1px solid #F0EFED', background: '#FAFAF9',
  },
  td:     { padding: '14px 24px', fontSize: 14, color: '#3C3C3C', fontWeight: 300, borderBottom: '1px solid #F5F5F5', verticalAlign: 'middle' },

  badge: { display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, padding: '3px 10px', borderRadius: 999 },
  badgeActive:  { background: '#EDFAF4', color: '#1D7A52' },
  badgeInvited: { background: '#FFF8EC', color: '#B45309' },

  deleteBtn: {
    background: 'none', border: '1px solid #E2E2E2', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12,
    color: '#B6B6B6', padding: '5px 12px', borderRadius: 999, transition: 'border-color 180ms, color 180ms',
  },
  deleteBtnConfirm: {
    background: '#FFF0EF', border: '1px solid #FBCFCC', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12,
    color: '#C42828', padding: '5px 12px', borderRadius: 999,
  },

  /* user detail panel */
  // panelClose is still used by BulkInviteModal.tsx's modal header — kept
  // even though the old inline-detail component (its original consumer) is gone.
  panelClose: {
    background: 'none', border: 'none', cursor: 'pointer', fontSize: 20,
    color: '#B6B6B6', padding: 0, lineHeight: 1, marginTop: 2,
  },
  panelSectionTitle: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8A8A8A', marginBottom: 10,
  },

  /* survey */
  surveyQLabel:   { fontSize: 11, fontWeight: 600, color: '#8A8A8A', marginBottom: 5, fontFamily: 'var(--dlw-font-ui)', letterSpacing: '0.04em', textTransform: 'uppercase' },
  surveyQText:    { fontSize: 13, color: '#3C3C3C', lineHeight: 1.6, background: '#FAFAF9', padding: '10px 12px', borderRadius: 6, border: '1px solid #F0EFED' },
} satisfies Record<string, CSSProperties>
