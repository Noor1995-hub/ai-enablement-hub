export type ComponentKey = 'assessment' | 'learning' | 'interview'

export const DEFAULT_LOCKED: Record<ComponentKey, boolean> = {
  assessment: false,
  learning: true,
  interview: true,
}
export const DEFAULT_HIDDEN: Record<ComponentKey, boolean> = {
  assessment: false,
  learning: false,
  interview: false,
}
