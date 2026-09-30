import { Component, type ErrorInfo, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { claimChunkReload, isChunkLoadError } from '../lib/chunkLoadError'

interface ErrorBoundaryProps {
  children: ReactNode
  /** When this value changes, a caught error is cleared and children re-render.
   * The route-level boundary passes the current pathname, so navigating away
   * from a broken screen recovers without a manual reload. */
  resetKey?: string
  /** Custom fallback. `reset` clears the error and retries the children. */
  fallback?: (reset: () => void) => ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/** The app had no error boundary at all: any render-time throw blanked the whole
 * page with no message and no way back. Lesson content is the realistic source —
 * `content_blocks` crosses a JSONB boundary and now arrives from hand edits AND
 * the AI content-improvement pipeline, so a block of a known type with malformed
 * fields (a quiz whose `options` is null) throws inside its renderer. */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // No client error reporting service is wired up yet, so the console is the
    // record. Keep the component stack — it names the block/page that threw.
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  componentDidUpdate(prev: ErrorBoundaryProps): void {
    if (this.state.error !== null && prev.resetKey !== this.props.resetKey) {
      this.setState({ error: null })
    }
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  /** "Try again" on the full-page message. A lazy chunk that failed to load
   * (typically after a redeploy renamed it) cannot be retried in place, because
   * `React.lazy` caches the rejection; only a full reload recovers. */
  retry = (): void => {
    if (isChunkLoadError(this.state.error) && claimChunkReload()) window.location.reload()
    else this.reset()
  }

  render(): ReactNode {
    if (this.state.error === null) return this.props.children
    if (this.props.fallback) return this.props.fallback(this.reset)

    return (
      <div style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 12, padding: 24,
        fontFamily: 'var(--dlw-font-body)', background: '#fff', textAlign: 'center',
      }}>
        <p style={{ fontWeight: 700, fontSize: 18, color: '#101820', margin: 0 }}>
          Something went wrong on this page.
        </p>
        <p style={{ fontWeight: 300, fontSize: 14, color: '#8A8A8A', margin: 0, maxWidth: '46ch' }}>
          Nothing you did is lost on our side. Try again, or go back to your journey.
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button
            type="button"
            onClick={this.retry}
            style={{ padding: '10px 20px', borderRadius: 999, border: 'none', background: '#C42828', color: '#fff', fontWeight: 700, fontSize: 14, fontFamily: 'var(--dlw-font-body)', cursor: 'pointer' }}
          >
            Try again
          </button>
          <a
            href="/"
            style={{ padding: '10px 20px', borderRadius: 999, border: '1px solid #E2E2E2', background: '#fff', color: '#8A8A8A', fontWeight: 600, fontSize: 14, fontFamily: 'var(--dlw-font-body)', textDecoration: 'none' }}
          >
            Back to start
          </a>
        </div>
      </div>
    )
  }
}

/** The route-level boundary. It must sit inside the router so it can key on the
 * pathname: navigating away from a screen that threw clears the error. */
export function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  return <ErrorBoundary resetKey={pathname}>{children}</ErrorBoundary>
}
