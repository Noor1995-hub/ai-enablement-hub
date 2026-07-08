/* Shared constants and styles for admin sub-components.
 * Dead nav/avatar/dropdown styles (D3) are not ported — AppNav owns the nav.
 * navBadge/navDivider/navTabs/navTab/navTabActive/navTabInactive stay: they
 * style the Admin-specific tab strip injected into AppNav via leftExtra. */
import type { CSSProperties } from 'react'
import type { ComponentKey } from '../../lib/constants'
import { levelByCode, type AssignableLevel } from '../../lib/levels'

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
const levelName = (code: ScoreLevel): string => levelByCode(code)!.name

export const LEVEL_STYLE: Record<ScoreLevel, BadgeStyle> = {
  explore:      { bg: '#F5F5F5',  text: '#8A8A8A',  label: levelName('explore') },
  practitioner: { bg: '#FFF8EC',  text: '#B45309',  label: levelName('practitioner') },
  integrator:   { bg: '#EDFAF4',  text: '#1D7A52',  label: levelName('integrator') },
}

export const BAND_STYLE: Record<UsageBand, BadgeStyle> = {
  dormant:    { bg: '#F5F5F5', text: '#8A8A8A',  label: 'Dormant' },
  occasional: { bg: '#F5F5F5', text: '#8A8A8A',  label: 'Occasional' },
  regular:    { bg: '#FFF8EC', text: '#B45309',  label: 'Regular' },
  embedded:   { bg: '#EDFAF4', text: '#1D7A52',  label: 'Embedded' },
}

export const s = {
  page: { minHeight: '100vh', background: '#F5F5F5', display: 'flex', flexDirection: 'column' },

  navDivider:{ width: 1, height: 20, background: '#E2E2E2' },
  navBadge:  {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.12em', textTransform: 'uppercase',
    background: '#FBF1F0', color: '#C42828', padding: '3px 10px', borderRadius: 999,
  },
  navTabs:   { display: 'flex', gap: 4 },
  navTab:    {
    padding: '6px 14px', fontFamily: 'var(--dlw-font-body)', fontWeight: 600,
    fontSize: 13, border: 'none', borderRadius: 6, cursor: 'pointer',
    transition: 'background 150ms, color 150ms',
  },
  navTabActive:   { background: '#101820', color: '#fff' },
  navTabInactive: { background: 'none', color: '#8A8A8A' },

  main:    { flex: 1, width: 'min(1400px, 100%)', margin: '0 auto', padding: '44px 48px 60px' },

  pageTitle: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 28, color: '#101820', margin: '0 0 4px' },
  pageSubtitle: { fontSize: 15, fontWeight: 300, color: '#8A8A8A', margin: '0 0 32px' },

  errorBanner: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 20, padding: '11px 14px',
    background: '#FFF0EF', border: '1px solid #FBCFCC', borderRadius: 6, fontSize: 13, color: '#C42828',
  },
  errorBannerClose: { background: 'none', border: 'none', cursor: 'pointer', color: '#C42828', fontSize: 18, lineHeight: 1, padding: 0 },

  /* cards */
  card: {
    background: '#fff', border: '1px solid #E2E2E2', borderRadius: 12,
    padding: '28px 28px 24px', marginBottom: 28,
  },
  cardTitle: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 16, color: '#101820', margin: '0 0 20px' },

  /* forms */
  formRow:    { display: 'flex', gap: 14, flexWrap: 'wrap' },
  fieldWrap:  { display: 'flex', flexDirection: 'column', flex: 1, minWidth: 160 },
  label:      { fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 12, letterSpacing: '0.04em', color: '#3C3C3C', marginBottom: 7 },
  input:      {
    padding: '11px 14px', fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14,
    color: '#101820', border: '1px solid #E2E2E2', borderRadius: 4, outline: 'none',
    transition: 'border-color 180ms', boxSizing: 'border-box', width: '100%',
  },
  inputFocus: { borderColor: '#EF463C' },
  select:     {
    padding: '11px 14px', fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 14,
    color: '#101820', border: '1px solid #E2E2E2', borderRadius: 4, outline: 'none',
    background: '#fff', cursor: 'pointer', boxSizing: 'border-box', width: '100%',
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

  linkBox:      { marginTop: 16, padding: '14px 16px', background: '#EDFAF4', border: '1px solid #A7E3C8', borderRadius: 8 },
  linkBoxLabel: { fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#1D7A52', marginBottom: 8 },
  linkRow:      { display: 'flex', gap: 8, alignItems: 'center' },
  linkInput:    {
    flex: 1, padding: '8px 12px', fontSize: 12, fontFamily: 'var(--dlw-font-body)',
    fontWeight: 300, color: '#101820', background: '#fff',
    border: '1px solid #A7E3C8', borderRadius: 4, outline: 'none',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  copyBtn: {
    padding: '8px 14px', fontFamily: 'var(--dlw-font-body)', fontWeight: 700,
    fontSize: 12, color: '#1D7A52', background: '#fff',
    border: '1px solid #A7E3C8', borderRadius: 4, cursor: 'pointer',
    whiteSpace: 'nowrap', transition: 'background 150ms',
  },

  /* table */
  tableCard:   { background: '#fff', border: '1px solid #E2E2E2', borderRadius: 12, overflow: 'hidden' },
  tableHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #F0EFED' },
  tableTitle:  { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 16, color: '#101820', margin: 0 },
  userCount:   { fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 12, color: '#8A8A8A' },
  table:       { width: '100%', borderCollapse: 'collapse' },
  th: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8A8A8A',
    textAlign: 'left', padding: '12px 24px', borderBottom: '1px solid #F0EFED', background: '#FAFAF9',
  },
  td:     { padding: '14px 24px', fontSize: 14, color: '#3C3C3C', fontWeight: 300, borderBottom: '1px solid #F5F5F5', verticalAlign: 'middle' },
  tdName: { fontWeight: 600, color: '#101820' },
  emptyRow: { textAlign: 'center', padding: '48px 24px', fontSize: 14, color: '#B6B6B6', fontWeight: 300 },

  badge: { display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, padding: '3px 10px', borderRadius: 999 },
  badgeActive:  { background: '#EDFAF4', color: '#1D7A52' },
  badgeInvited: { background: '#FFF8EC', color: '#B45309' },

  resendBtn: {
    background: 'none', border: '1px solid #E2E2E2', cursor: 'pointer',
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 12,
    color: '#8A8A8A', padding: '5px 12px', borderRadius: 999, transition: 'border-color 180ms, color 180ms',
  },
  actionCell: { display: 'flex', gap: 8, alignItems: 'center' },
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

  /* component toggles */
  toggleOpen:    { padding: '4px 12px', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.04em', borderRadius: 999, cursor: 'pointer', border: '1px solid #A7E3C8', background: '#EDFAF4', color: '#1D7A52', transition: 'opacity 150ms' },
  toggleLocked:  { padding: '4px 12px', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.04em', borderRadius: 999, cursor: 'pointer', border: '1px solid #FBCFCC', background: '#FFF0EF', color: '#C42828', transition: 'opacity 150ms' },
  toggleVisible: { padding: '4px 12px', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.04em', borderRadius: 999, cursor: 'pointer', border: '1px solid #A7E3C8', background: '#EDFAF4', color: '#1D7A52', transition: 'opacity 150ms' },
  toggleHidden:  { padding: '4px 12px', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.04em', borderRadius: 999, cursor: 'pointer', border: '1px solid #E2E2E2', background: '#F5F5F5', color: '#B6B6B6', transition: 'opacity 150ms' },
  toggleBusy:    { opacity: 0.45, cursor: 'not-allowed' },

  /* track/module assignment */
  toggleAssigned:   { padding: '4px 12px', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.04em', borderRadius: 999, cursor: 'pointer', border: '1px solid #A7E3C8', background: '#EDFAF4', color: '#1D7A52', transition: 'opacity 150ms' },
  toggleUnassigned: { padding: '4px 12px', fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.04em', borderRadius: 999, cursor: 'pointer', border: '1px solid #E2E2E2', background: 'none', color: '#C4C4C4', transition: 'opacity 150ms' },
  moduleList:        { padding: '0 24px 16px', display: 'flex', flexDirection: 'column', gap: 8 },
  moduleItem:        { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: '#FAFAF9', borderRadius: 6, border: '1px solid #F0EFED' },
  moduleTitle:       { fontSize: 13, fontWeight: 400, color: '#3C3C3C' },

  /* project list */
  companyBlock:  { marginBottom: 28 },
  companyLabel:  { fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8A8A8A', marginBottom: 10 },
  projectGrid:   { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 },
  projectCard:   {
    background: '#fff', border: '1px solid #E2E2E2', borderRadius: 10,
    padding: '18px 20px', cursor: 'pointer', transition: 'border-color 150ms, box-shadow 150ms',
  },
  projectCardName: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 14, color: '#101820', marginBottom: 4 },
  projectCardMeta: { fontSize: 12, fontWeight: 300, color: '#8A8A8A' },

  /* project view */
  projectViewHeader: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 },
  backLink: {
    background: 'none', border: 'none', cursor: 'pointer', padding: 0,
    fontFamily: 'var(--dlw-font-body)', fontWeight: 600, fontSize: 13, color: '#8A8A8A',
  },
  projectViewTitle: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 22, color: '#101820', margin: 0 },
  projectViewCo:    { fontSize: 13, fontWeight: 300, color: '#8A8A8A', marginLeft: 4 },

  /* user detail panel */
  panelOverlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,.18)', zIndex: 50,
    display: 'flex', justifyContent: 'flex-end',
  },
  panel: {
    // height:100% (not 100vh): the :root CSS zoom of 1.25 multiplies vh units,
    // so 100vh renders ~125% of the screen and the last tracks fall below the
    // fold, unreachable. The overlay is fixed/inset:0 and sized correctly, so
    // filling it keeps the panel exactly one viewport tall and scrollable.
    width: 560, maxWidth: '95vw', height: '100%', background: '#fff',
    borderLeft: '1px solid #E2E2E2', overflowY: 'auto', display: 'flex', flexDirection: 'column',
  },
  panelHeader: {
    padding: '24px 28px 20px', borderBottom: '1px solid #F0EFED',
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    position: 'sticky', top: 0, background: '#fff', zIndex: 1,
  },
  panelClose: {
    background: 'none', border: 'none', cursor: 'pointer', fontSize: 20,
    color: '#B6B6B6', padding: 0, lineHeight: 1, marginTop: 2,
  },
  panelName: { fontFamily: 'var(--dlw-font-body)', fontWeight: 700, fontSize: 18, color: '#101820', marginBottom: 4 },
  panelMeta: { fontSize: 13, fontWeight: 300, color: '#8A8A8A' },
  panelBody: { padding: '24px 28px', flex: 1 },
  panelSection: { marginBottom: 32 },
  panelSectionTitle: {
    fontFamily: 'var(--dlw-font-ui)', fontWeight: 600, fontSize: 11,
    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8A8A8A', marginBottom: 14,
  },

  /* survey */
  surveyQRow:     { marginBottom: 14 },
  surveyQLabel:   { fontSize: 11, fontWeight: 600, color: '#8A8A8A', marginBottom: 5, fontFamily: 'var(--dlw-font-ui)', letterSpacing: '0.04em', textTransform: 'uppercase' },
  surveyQText:    { fontSize: 13, color: '#3C3C3C', lineHeight: 1.6, background: '#FAFAF9', padding: '10px 12px', borderRadius: 6, border: '1px solid #F0EFED' },
  noSurvey:       { fontSize: 13, color: '#B6B6B6', fontWeight: 300, padding: '20px 0' },
} satisfies Record<string, CSSProperties>
