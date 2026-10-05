/** The playbook's "Where you are today" text, split for display: a short intro, then bullet
 *  points (lines starting with "- "; a model sometimes writes "•" or "*" instead). The field
 *  stays one string in the API, so a summary written before bullets (one paragraph) simply
 *  comes back as intro only and renders as before. */
export function parseSummary(text: string): { intro: string[]; bullets: string[] } {
  const intro: string[] = []
  const bullets: string[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const bullet = line.match(/^[-•*]\s+(.*)$/)
    if (bullet) bullets.push(bullet[1].trim())
    else intro.push(line)
  }
  return { intro, bullets }
}
