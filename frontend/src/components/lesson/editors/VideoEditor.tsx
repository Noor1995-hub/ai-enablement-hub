import { useRef, useState } from 'react'
import type { VideoBlock } from '../../../types/contentBlocks'
import { UploadError, uploadMedia } from '../../../api/upload'
import { normalizeEmbedUrl } from '../../../lib/videoEmbeds'

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--dlw-font-ui)',
  fontWeight: 600,
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#8A8A8A',
  marginBottom: 4,
  display: 'block',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  border: '1px solid #E2E2E2',
  borderRadius: 6,
  fontFamily: 'var(--dlw-font-body)',
  fontSize: 13,
  color: '#101820',
  outline: 'none',
  boxSizing: 'border-box',
}

const buttonStyle: React.CSSProperties = {
  padding: '7px 14px', borderRadius: 6, border: '1px solid #E2E2E2',
  background: '#fff', fontFamily: 'var(--dlw-font-body)', fontWeight: 600,
  fontSize: 13, color: '#3C3C3C', cursor: 'pointer',
}

const ACCEPT = 'video/mp4,video/webm'

function friendlyError(err: unknown): string {
  if (err instanceof UploadError) {
    if (err.status === 413) return 'That video is too large. Videos must be under 300 MB.'
    if (err.status === 415) return "That file type isn't supported. Use MP4 or WebM."
    return err.message
  }
  return 'Upload failed. Please try again.'
}

type EmbedVideo = Extract<VideoBlock, { source: 'embed' }>
type BlobVideo = Extract<VideoBlock, { source: 'blob' }>

// Segmented Embed/Upload switch — the InteractiveEditor mode-switch pattern,
// but preserving id + caption so toggling source keeps the author's caption.
function SourceToggle({ block, onChange }: VideoEditorProps) {
  function select(source: VideoBlock['source']) {
    if (source === block.source) return
    if (source === 'embed') {
      onChange({ id: block.id, type: 'video', source: 'embed', url: '', caption: block.caption })
    } else {
      onChange({ id: block.id, type: 'video', source: 'blob', blob_path: '', caption: block.caption })
    }
  }

  return (
    <div>
      <span style={labelStyle}>Source</span>
      <div style={{ display: 'flex', gap: 6 }}>
        {(['embed', 'blob'] as const).map(source => {
          const active = block.source === source
          return (
            <button key={source} type="button" onClick={() => select(source)} style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: '1.5px solid',
              borderColor: active ? '#3BC9BC' : '#E2E2E2',
              background: active ? '#F0FAF9' : '#fff',
              color: active ? '#1D7A52' : '#8A8A8A',
              fontFamily: 'var(--dlw-font-ui)',
              fontWeight: 700,
              fontSize: 13,
              cursor: 'pointer',
            }}>
              {source === 'embed' ? 'Embed (YouTube / Vimeo / Stream)' : 'Upload'}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function EmbedFields({ block, onChange }: { block: EmbedVideo; onChange: (b: VideoBlock) => void }) {
  // Store the canonical embed url when the paste normalizes; otherwise keep the
  // raw text so the "unsupported" hint has something to explain.
  const normalized = block.url.trim() ? normalizeEmbedUrl(block.url) : null

  return (
    <div>
      <label style={labelStyle}>Video URL or embed code</label>
      <textarea
        style={{ ...inputStyle, resize: 'vertical', fontFamily: 'var(--dlw-font-mono, monospace)' }}
        rows={2}
        value={block.url}
        onChange={e => {
          const v = e.target.value
          onChange({ ...block, url: normalizeEmbedUrl(v) ?? v })
        }}
        placeholder="Paste a YouTube / Vimeo link, a SharePoint Stream embed link, or an <iframe> snippet…"
      />
      {block.url.trim() && (
        normalized ? (
          <p style={{ margin: '6px 0 0', fontFamily: 'var(--dlw-font-body)', fontSize: 12, color: '#1D7A52', wordBreak: 'break-all' }}>
            ✓ Embed ready: {normalized}
          </p>
        ) : (
          <p style={{ margin: '6px 0 0', fontFamily: 'var(--dlw-font-body)', fontSize: 12, color: '#B45309' }}>
            Unsupported provider. Use YouTube, Vimeo, or a SharePoint / Stream embed link.
          </p>
        )
      )}
    </div>
  )
}

function UploadFields({ block, onChange }: { block: BlobVideo; onChange: (b: VideoBlock) => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File | undefined) {
    if (!file) return
    setError(null)
    setUploading(true)
    setProgress(0)
    try {
      const media = await uploadMedia(file, setProgress)
      onChange({ ...block, blob_path: media.blob_path, url: media.url })
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPT}
        style={{ display: 'none' }}
        onChange={e => { void handleFile(e.target.files?.[0]); e.target.value = '' }}
      />

      <div>
        <label style={labelStyle}>Video file (MP4 or WebM, up to 300 MB)</label>
        {block.url ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <video src={block.url} controls preload="metadata" style={{ display: 'block', width: '100%', maxHeight: 220, borderRadius: 8, border: '1px solid #E2E2E2', background: '#000' }} />
            <button type="button" style={buttonStyle} disabled={uploading} onClick={() => fileRef.current?.click()}>
              {uploading ? 'Uploading…' : 'Replace video'}
            </button>
          </div>
        ) : (
          <button type="button" style={buttonStyle} disabled={uploading} onClick={() => fileRef.current?.click()}>
            {uploading ? 'Uploading…' : 'Choose video…'}
          </button>
        )}
      </div>

      {uploading && (
        <div style={{ height: 6, borderRadius: 999, background: '#E2E2E2', overflow: 'hidden' }}>
          <div style={{ width: `${progress}%`, height: '100%', background: '#3BC9BC', transition: 'width .15s var(--dlw-ease)' }} />
        </div>
      )}

      {error && (
        <div style={{ padding: '8px 12px', background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 6, color: '#C42828', fontFamily: 'var(--dlw-font-body)', fontSize: 13 }}>
          {error}
        </div>
      )}
    </div>
  )
}

interface VideoEditorProps {
  block: VideoBlock
  onChange: (b: VideoBlock) => void
}

export default function VideoEditor({ block, onChange }: VideoEditorProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <SourceToggle block={block} onChange={onChange} />

      {block.source === 'embed'
        ? <EmbedFields block={block} onChange={onChange} />
        : <UploadFields block={block} onChange={onChange} />}

      <div>
        <label style={labelStyle}>Caption (optional)</label>
        <input
          style={inputStyle}
          value={block.caption ?? ''}
          onChange={e => onChange({ ...block, caption: e.target.value })}
          placeholder="Shown beneath the video…"
        />
      </div>
    </div>
  )
}
