import type { HeadingBlock as HeadingBlockType } from '../../../types/contentBlocks'

export default function HeadingBlock({ block }: { block: HeadingBlockType }) {
  const Tag = `h${block.level ?? 2}` as 'h1' | 'h2' | 'h3'

  const sizes: Record<number, number> = { 1: 28, 2: 22, 3: 18 }
  const fontSize = sizes[block.level] ?? 22

  return (
    <Tag style={{
      fontFamily: 'var(--dlw-font-body)',
      fontWeight: 700,
      fontSize,
      letterSpacing: block.level === 3 ? undefined : '-0.01em',
      color: '#101820',
      lineHeight: 1.25,
      margin: '0 0 12px',
    }}>
      {block.text}
    </Tag>
  )
}
