import { afterEach, beforeEach, vi, type MockInstance } from 'vitest'

/** For tests that make a component throw on purpose, to exercise an error
 * boundary. React 18's dev build re-dispatches each caught render error as an
 * uncaught `error` event on window (jsdom then prints it) and logs it once more
 * through console.error, as does the boundary itself. All of that is expected
 * noise here: cancel the window event and mute console.error for the duration of
 * each test. Returns the console.error spy so a test can still assert on it. */
export function silenceRenderErrors(): () => MockInstance<typeof console.error> {
  let consoleError: MockInstance<typeof console.error>
  const cancel = (event: ErrorEvent) => event.preventDefault()
  beforeEach(() => {
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    window.addEventListener('error', cancel)
  })
  afterEach(() => {
    window.removeEventListener('error', cancel)
    consoleError.mockRestore()
  })
  return () => consoleError
}
