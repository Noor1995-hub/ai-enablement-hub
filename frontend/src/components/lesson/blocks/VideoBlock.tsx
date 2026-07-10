import type { CSSProperties } from 'react'
import type { VideoBlock as VideoBlockType } from '../../../types/contentBlocks'
import { normalizeEmbedUrl } from '../../../lib/videoEmbeds'

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

// Neutral box shown when there's nothing playable yet: an unsupported embed
// provider, or a blob whose SAS url hasn't been stamped.
function Placeholder({ label }: { label: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 8, minHeight: 160, padding: '24px',
      background: '#FAFAFA', border: '1px dashed #E2E2E2', borderRadius: 12,
    }}>
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="2" stroke="#C9C9C9" strokeWidth="1.5" />
        <path d="M10 9.5l4 2.5-4 2.5v-5z" fill="#C9C9C9" />
      </svg>
      <span style={{ fontFamily: 'var(--dlw-font-body)', fontWeight: 300, fontSize: 13, color: '#8A8A8A', textAlign: 'center' }}>
        {label}
      </span>
    </div>
  )
}

function EmbedVideo({ url }: { url: string }) {
  // Re-normalize defensively: the stored url is already canonical, but a hostile
  // or hand-edited value must never reach the iframe unchecked.
  const src = normalizeEmbedUrl(url)
  if (!src) return <Placeholder label="This video provider isn't supported." />

  return (
    <div style={{
      position: 'relative', width: '100%', aspectRatio: '16 / 9',
      borderRadius: 12, overflow: 'hidden', background: '#000',
    }}>
      <iframe
        src={src}
        title="Embedded video"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 'none' }}
      />
    </div>
  )
}

function BlobVideo({ url }: { url: string | undefined }) {
  if (!url) return <Placeholder label="Video not available." />
  return (
    <video
      src={url}
      controls
      preload="metadata"
      style={{ display: 'block', width: '100%', height: 'auto', borderRadius: 12, background: '#000' }}
    />
  )
}

export default function VideoBlock({ block }: { block: VideoBlockType }) {
  return (
    <figure style={{ margin: '0 0 24px' }}>
      {block.source === 'embed'
        ? <EmbedVideo url={block.url} />
        : <BlobVideo url={block.url} />}
      {block.caption && <figcaption style={captionStyle}>{block.caption}</figcaption>}
    </figure>
  )
}
