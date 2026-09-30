import { useEffect } from 'react'

/**
 * Warns before the browser discards unsaved work: while `dirty` is true, closing
 * the tab, reloading, or navigating to another site shows the browser's own
 * "Leave site?" prompt.
 *
 * Deliberately NOT react-router's `useBlocker`: that hook requires a data router
 * (`createBrowserRouter`), and this app mounts `<BrowserRouter>` (App.tsx), where
 * calling it throws. In-app route changes (the admin sidebar, a back link) are
 * therefore not intercepted — the data-router migration that would allow it was
 * dropped from the fix programme (2026-09-25).
 */
export function useUnsavedGuard(dirty: boolean): void {
  useEffect(() => {
    if (!dirty) return
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      // Modern browsers only need preventDefault; returnValue keeps older ones
      // (and some embedded webviews) showing the prompt. The message itself is
      // not customisable — every browser shows its own wording.
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [dirty])
}
