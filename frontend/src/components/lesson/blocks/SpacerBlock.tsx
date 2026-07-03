import type { WhitespaceBlock } from '../../../types/contentBlocks'

const HEIGHTS: Record<'sm' | 'md' | 'lg', number> = { sm: 16, md: 32, lg: 64 }

export default function SpacerBlock({ block }: { block: WhitespaceBlock }) {
  return <div style={{ height: HEIGHTS[block.size ?? 'md'] }} />
}
