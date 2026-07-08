/**
 * The site is rendered at a baked-in CSS `zoom` (see `--dlw-zoom` / `:root` in
 * index.css) so it looks like ~125% browser zoom by default.
 *
 * That breaks any JS that mixes `getBoundingClientRect()` coordinates with
 * hand-computed layout coordinates, because the two live in different spaces:
 * in Chrome/Edge (M128+) and Firefox, CSS `zoom` scales the values returned by
 * getBoundingClientRect/getClientRects; in Safari it historically does NOT.
 *
 * Rather than assume a browser or hardcode the factor, we *measure* it: a probe
 * element of known local width tells us exactly how much rect coordinates are
 * scaled. Divide any rect-derived screen coordinate by this factor to get back
 * into the local (layout) space that absolutely/fixed-positioned elements and
 * transform-origins use. Returns 1 when there is no zoom (or in Safari, where
 * no compensation is needed), so call sites are correct in every case.
 */
export function getRectZoomFactor(): number {
  if (typeof document === 'undefined' || !document.body) return 1
  const probe = document.createElement('div')
  probe.style.cssText =
    'position:absolute;left:0;top:0;width:1000px;height:0;visibility:hidden;pointer-events:none'
  document.body.appendChild(probe)
  const measured = probe.getBoundingClientRect().width
  document.body.removeChild(probe)
  return measured > 0 ? measured / 1000 : 1
}
