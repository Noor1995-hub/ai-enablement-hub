import { useLocation } from 'react-router-dom'

/** Temporary per-section stub so the new admin shell is walkable end-to-end
 * before each real page lands (Phase B/C swap these out one task at a time).
 * Shows the resolved path so a manual nav-item-by-nav-item walk can confirm
 * routing + scope persistence without guessing which section rendered. */
export default function Placeholder() {
  const { pathname, search } = useLocation()
  return (
    <div>
      <h1>Coming soon</h1>
      <p>{pathname}{search}</p>
    </div>
  )
}
