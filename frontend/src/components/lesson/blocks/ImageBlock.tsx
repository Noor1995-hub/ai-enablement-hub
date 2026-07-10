import { useState, type CSSProperties } from 'react'
import { motion } from 'framer-motion'
import type { ImageBlock as ImageBlockType } from '../../../types/contentBlocks'

// width is a % of the content column, clamped 25–100; absent = full width.
function clampWidth(width: number | undefined): number {
  if (typeof width !== 'number' || Number.isNaN(width)) return 100
  return Math.min(100, Math.max(25, Math.round(width)))
}

const captionStyle: CSSProperties = {
  fontFamily: 'var(--dlw-font-body)',
  fontWeight: 300,
  fontSize: 13,
  lineHeight: 1.5,
  color: '#8A8A8A',
  fontStyle: 'italic',
  margin: '8px 0 0',
  textAlign: 'center',
}

// Shown before the SAS url arrives (or when a blob_path exists but hasn't been
// stamped) and when the image fails to load: an icon plus the alt text so the
// author/learner still gets a description of what belongs here.
function Placeholder({ alt }: { alt: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 8, minHeight: 160, padding: '24px',
      background: '#FAFAFA', border: '1px dashed #E2E2E2', borderRadius: 12,
    }}>
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="#C9C9C9" strokeWidth="1.5" />
        <circle cx="8.5" cy="8.5" r="1.5" fill="#C9C9C9" />
        <path d="M21 15l-5-5L5 21" stroke="#C9C9C9" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 13, color: '#8A8A8A', textAlign: 'center' }}>
        {alt || 'Image'}
      </span>
    </div>
  )
}

// Owns its own load/error state so it resets cleanly on a src change (mounted
// with a `key={url}` by the parent) — e.g. when an author re-uploads and the
// live-preview keeps the same block instance.
function LoadableImage({ src, alt }: { src: string; alt: string }) {
  const [loaded, setLoaded] = useState(false)
  const [errored, setErrored] = useState(false)

  if (errored) return <Placeholder alt={alt} />

  return (
    <div style={{
      position: 'relative',
      borderRadius: 12,
      overflow: 'hidden',
      background: loaded ? 'none' : '#F0EFED',
      minHeight: loaded ? undefined : 160,
    }}>
      {!loaded && (
        <motion.div
          aria-hidden="true"
          style={{ position: 'absolute', inset: 0, background: '#E2E2E2' }}
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}
      <img
        src={src}
        alt={alt}
        onLoad={() => setLoaded(true)}
        onError={() => setErrored(true)}
        style={{
          display: 'block', width: '100%', height: 'auto',
          opacity: loaded ? 1 : 0, transition: 'opacity .2s var(--dlw-ease)',
        }}
      />
    </div>
  )
}

export default function ImageBlock({ block }: { block: ImageBlockType }) {
  const width = clampWidth(block.width)

  return (
    <figure style={{ width: `${width}%`, maxWidth: '100%', margin: '0 auto 24px' }}>
      {block.url
        ? <LoadableImage key={block.url} src={block.url} alt={block.alt} />
        : <Placeholder alt={block.alt} />}
      {block.caption && <figcaption style={captionStyle}>{block.caption}</figcaption>}
    </figure>
  )
}
