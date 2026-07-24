interface TileProps {
  label: string
  value: string | number
  alert?: boolean
}

/** Dashboard stat tile — one number + label. `alert` reddens the value; it is
 * always paired with text elsewhere on the screen (e.g. the attention list)
 * so the meaning never rests on color alone.
 * Prototype: docs/design-prototypes/admin-redesign/common.js `tile()` /
 * styles.css `.tile`. */
export function Tile({ label, value, alert = false }: TileProps) {
  return (
    <div className={`adm-tile${alert ? ' adm-tile-alert' : ''}`}>
      <div className="adm-tile-label">{label}</div>
      <div className="adm-tile-value">{value}</div>
    </div>
  )
}
