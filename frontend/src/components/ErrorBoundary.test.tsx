import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { silenceRenderErrors } from '../test/silenceRenderErrors'
import ErrorBoundary, { RoutedErrorBoundary } from './ErrorBoundary'

const PAGE_FALLBACK = 'Something went wrong on this page.'

// These tests throw on purpose; the boundary's own console entry is asserted where it matters.
const consoleError = silenceRenderErrors()

function Thrower({ error }: { error: Error }): never {
  throw error
}

describe('ErrorBoundary', () => {
  it('renders its children when nothing throws', () => {
    render(<ErrorBoundary><p>All good</p></ErrorBoundary>)
    expect(screen.getByText('All good')).toBeInTheDocument()
    expect(screen.queryByText(PAGE_FALLBACK)).not.toBeInTheDocument()
  })

  it('shows the default full-page message and logs the error when a child throws', () => {
    const error = new Error('boom')
    render(<ErrorBoundary><Thrower error={error} /></ErrorBoundary>)
    expect(screen.getByText(PAGE_FALLBACK)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to start' })).toHaveAttribute('href', '/')
    expect(consoleError()).toHaveBeenCalledWith('[ErrorBoundary]', error, expect.any(String))
  })

  it('renders a custom fallback, whose reset retries the children', () => {
    let shouldThrow = true
    function Flaky() {
      if (shouldThrow) throw new Error('flaky')
      return <p>Recovered</p>
    }
    render(
      <ErrorBoundary fallback={reset => <button type="button" onClick={reset}>Retry block</button>}>
        <Flaky />
      </ErrorBoundary>,
    )
    shouldThrow = false
    fireEvent.click(screen.getByRole('button', { name: 'Retry block' }))
    expect(screen.getByText('Recovered')).toBeInTheDocument()
  })

  it('clears a caught error when resetKey changes', () => {
    function Harness() {
      const [key, setKey] = useState('a')
      return (
        <>
          <button type="button" onClick={() => setKey('b')}>Change key</button>
          <ErrorBoundary resetKey={key}>
            {key === 'a' ? <Thrower error={new Error('only on a')} /> : <p>Screen b</p>}
          </ErrorBoundary>
        </>
      )
    }
    render(<Harness />)
    expect(screen.getByText(PAGE_FALLBACK)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Change key' }))
    expect(screen.getByText('Screen b')).toBeInTheDocument()
  })

  describe('"Try again"', () => {
    const realLocation = window.location
    let reload: ReturnType<typeof vi.fn>
    beforeEach(() => {
      sessionStorage.clear()
      // jsdom's location.reload is not spy-able in place; swap the whole object.
      reload = vi.fn()
      Object.defineProperty(window, 'location', { configurable: true, value: { ...realLocation, reload } })
    })
    afterEach(() => {
      Object.defineProperty(window, 'location', { configurable: true, value: realLocation })
    })

    it('re-renders the children in place for an ordinary error', () => {
      let shouldThrow = true
      function Flaky() {
        if (shouldThrow) throw new Error('transient')
        return <p>Back again</p>
      }
      render(<ErrorBoundary><Flaky /></ErrorBoundary>)
      shouldThrow = false
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
      expect(screen.getByText('Back again')).toBeInTheDocument()
      expect(reload).not.toHaveBeenCalled()
    })

    it('reloads the whole page for a chunk-load failure (React.lazy caches the rejection)', () => {
      const error = new TypeError('Failed to fetch dynamically imported module: /assets/AdminShell-abc.js')
      render(<ErrorBoundary><Thrower error={error} /></ErrorBoundary>)
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
      expect(reload).toHaveBeenCalledTimes(1)
      // No in-place retry (it would only re-throw); the reload does the recovery.
      expect(screen.getByText(PAGE_FALLBACK)).toBeInTheDocument()
    })

    it('does not reload again right after a reload already failed to help (loop guard)', () => {
      const error = new TypeError('Failed to fetch dynamically imported module: /assets/x.js')
      render(<ErrorBoundary><Thrower error={error} /></ErrorBoundary>)
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
      expect(reload).toHaveBeenCalledTimes(1)
    })
  })
})

describe('RoutedErrorBoundary', () => {
  function BrokenPage(): never {
    throw new Error('this screen is broken')
  }
  function Nav() {
    const navigate = useNavigate()
    return <button type="button" onClick={() => navigate('/fine')}>Go elsewhere</button>
  }

  function renderAt(path: string) {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Nav />
        <RoutedErrorBoundary>
          <Routes>
            <Route path="/broken" element={<BrokenPage />} />
            <Route path="/fine" element={<p>Fine page</p>} />
          </Routes>
        </RoutedErrorBoundary>
      </MemoryRouter>,
    )
  }

  it('shows the fallback for a route that throws; what sits outside it survives', () => {
    renderAt('/broken')
    expect(screen.getByText(PAGE_FALLBACK)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Go elsewhere' })).toBeInTheDocument()
  })

  it('recovers on navigation, because it keys on the pathname', () => {
    renderAt('/broken')
    fireEvent.click(screen.getByRole('button', { name: 'Go elsewhere' }))
    expect(screen.getByText('Fine page')).toBeInTheDocument()
    expect(screen.queryByText(PAGE_FALLBACK)).not.toBeInTheDocument()
  })

  it('is invisible when the route renders normally', () => {
    renderAt('/fine')
    expect(screen.getByText('Fine page')).toBeInTheDocument()
    expect(consoleError()).not.toHaveBeenCalled()
  })
})
