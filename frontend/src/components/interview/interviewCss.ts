/** The interview page's look (redesign D, from direction A): a warm-grey page with a white
 *  sheet, large Mulish type, and the red dot from the delaware logo as the step and bullet
 *  marker. What inline styles can't express lives here: pseudo-elements, keyframes, media
 *  queries. Rendered once by pages/Interview.tsx. Prefix `iv-`, the page's existing idiom. */
export const INTERVIEW_CSS = `
.iv-sheet { width: min(860px, 100%); box-sizing: border-box; overflow-wrap: anywhere; margin: 28px auto 48px; background: #fff; border-radius: 20px; padding: 40px 64px 48px; box-shadow: 0 1px 0 rgba(16, 24, 32, .04), 0 28px 56px -36px rgba(16, 24, 32, .30); }
.iv-sheet-wide { width: min(1000px, 100%); padding-top: 48px; }
.iv-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: var(--dlw-dot-red); flex: none; }
.iv-h1 { font-family: var(--dlw-font-body); font-weight: 800; font-size: 44px; line-height: 1.08; letter-spacing: -0.022em; color: var(--dlw-black); margin: 0 0 22px; max-width: 24ch; }
.iv-lead { font-size: 19px; line-height: 1.55; font-weight: 400; color: var(--dlw-black); margin: 0 0 30px; max-width: 60ch; }
.iv-lead strong { font-weight: 800; }
.iv-top { display: flex; justify-content: flex-end; margin: -8px 0 6px; }
.iv-steps { list-style: none; margin: 0 0 28px; padding: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; position: relative; }
.iv-steps::before { content: ""; position: absolute; left: 6px; right: calc(33.333% - 22px); top: 5px; height: 2px; background: var(--dlw-border); }
.iv-steps li { position: relative; display: flex; flex-direction: column; gap: 6px; padding-top: 26px; }
.iv-steps .iv-dot { position: absolute; top: 0; left: 0; }
.iv-steps strong { font-weight: 800; font-size: 17px; color: var(--dlw-black); }
.iv-steps span:last-child { font-size: 15px; line-height: 1.5; color: var(--dlw-text); font-weight: 400; max-width: 28ch; }
.iv-start { display: flex; align-items: center; gap: 22px; flex-wrap: wrap; padding-top: 24px; border-top: 1px solid var(--dlw-border); }
.iv-privacy { margin: 0; font-size: 13px; line-height: 1.5; color: #6B6B6B; max-width: 46ch; font-weight: 400; }
.iv-track { position: relative; height: 12px; margin: 4px 0 34px; }
.iv-track::before { content: ""; position: absolute; left: 0; right: 0; top: 5px; height: 2px; background: var(--dlw-border); }
@keyframes iv-run { 0% { left: 0 } 50% { left: calc(100% - 12px) } 100% { left: 0 } }
.iv-run { position: absolute; top: 0; left: 0; animation: iv-run 2.4s var(--dlw-ease) infinite; }
@media (prefers-reduced-motion: reduce) { .iv-run { animation: none; } }
.iv-small { font-family: var(--dlw-font-ui); font-weight: 600; font-size: 13px; color: #6B6B6B; margin: 0 0 10px; }
.iv-parts { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.iv-parts li { display: flex; align-items: center; gap: 12px; font-size: 15.5px; font-weight: 400; color: var(--dlw-black); }
.iv-parts .iv-dot { width: 8px; height: 8px; background: var(--dlw-border); }
.iv-pb-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px 24px; flex-wrap: wrap; margin-bottom: 26px; }
.iv-pb-head .iv-h1 { font-size: 36px; margin: 0; max-width: none; }
.iv-pb-head p { margin: 0; font-size: 14.5px; color: #6B6B6B; font-weight: 400; }

/* Chat (Task 4) */
.iv-chat { background: #fff; border-radius: 20px; box-shadow: 0 1px 0 rgba(16, 24, 32, .04), 0 28px 56px -36px rgba(16, 24, 32, .30); }
.iv-chat-head { display: flex; gap: 12px; align-items: flex-start; padding: 18px 28px 16px; border-bottom: 1px solid var(--dlw-border); }
.iv-mark { width: 22px; height: 22px; flex: none; margin-top: 1px; color: #6B6B6B; }
.iv-who { margin: 0 0 2px; font-weight: 800; font-size: 15px; color: var(--dlw-black); line-height: 1.3; }
.iv-msg-ai { overflow-wrap: anywhere; align-self: flex-start; max-width: 64ch; color: var(--dlw-black); font-size: 16px; font-weight: 400; padding-left: 18px; }
.iv-msg-ai::before { content: ""; position: absolute; left: 0; top: .62em; width: 7px; height: 7px; border-radius: 50%; background: var(--dlw-dot-red); }
.iv-msg-me { overflow-wrap: anywhere; align-self: flex-end; max-width: 72%; background: var(--dlw-warm-grey); color: var(--dlw-black); font-size: 16px; font-weight: 400; padding: 11px 16px; border-radius: 16px 16px 4px 16px; }

@media (max-width: 900px) {
  .iv-sheet { padding: 32px 24px 36px; margin: 16px auto 28px; }
  .iv-h1 { font-size: 32px; }
  .iv-lead { font-size: 17px; }
  .iv-steps { grid-template-columns: 1fr; gap: 18px; }
  .iv-steps::before { left: 5px; right: auto; top: 6px; bottom: 6px; width: 2px; height: auto; }
  .iv-steps li { padding: 0 0 0 28px; }
  .iv-chat-head { padding-left: 18px; padding-right: 18px; }
}
`
