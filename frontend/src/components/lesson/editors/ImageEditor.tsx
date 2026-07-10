import { useRef, useState } from 'react'
import type { ImageBlock } from '../../../types/contentBlocks'
import { UploadError, uploadMedia } from '../../../api/upload'

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

const ACCEPT = 'image/png,image/jpeg,image/webp,image/gif'

function friendlyError(err: unknown): string {
  if (err instanceof UploadError) {
    if (err.status === 413) return 'That image is too large. Images must be under 10 MB.'
    if (err.status === 415) return "That file type isn't supported. Use PNG, JPEG, WebP or GIF."
    return err.message
  }
  return 'Upload failed. Please try again.'
}

interface ImageEditorProps {
  block: ImageBlock
  onChange: (b: ImageBlock) => void
}

export default function ImageEditor({ block, onChange }: ImageEditorProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const width = block.width ?? 100

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

      {/* Preview / upload trigger */}
      <div>
        <label style={labelStyle}>Image</label>
        {block.url ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <img
              src={block.url}
              alt={block.alt}
              style={{ display: 'block', width: '100%', maxHeight: 220, objectFit: 'contain', borderRadius: 8, border: '1px solid #E2E2E2', background: '#FAFAFA' }}
            />
            <button type="button" style={buttonStyle} disabled={uploading} onClick={() => fileRef.current?.click()}>
              {uploading ? 'Uploading…' : 'Replace image'}
            </button>
          </div>
        ) : (
          <button type="button" style={buttonStyle} disabled={uploading} onClick={() => fileRef.current?.click()}>
            {uploading ? 'Uploading…' : 'Choose image…'}
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

      <div>
        <label style={labelStyle}>Alt text (required)</label>
        <input
          style={{ ...inputStyle, borderColor: block.alt.trim() ? '#E2E2E2' : '#FCA5A5' }}
          value={block.alt}
          onChange={e => onChange({ ...block, alt: e.target.value })}
          placeholder="Describe the image for screen readers…"
        />
        {!block.alt.trim() && (
          <p style={{ margin: '4px 0 0', fontFamily: 'var(--dlw-font-body)', fontSize: 12, color: '#C42828' }}>
            Alt text is required for accessibility.
          </p>
        )}
      </div>

      <div>
        <label style={labelStyle}>Caption (optional)</label>
        <input
          style={inputStyle}
          value={block.caption ?? ''}
          onChange={e => onChange({ ...block, caption: e.target.value })}
          placeholder="Shown beneath the image…"
        />
      </div>

      <div>
        <label style={labelStyle}>Width — {width}% of the content column</label>
        <input
          type="range"
          min={25}
          max={100}
          step={5}
          value={width}
          onChange={e => onChange({ ...block, width: Number(e.target.value) })}
          style={{ width: '100%', accentColor: '#3BC9BC' }}
        />
      </div>
    </div>
  )
}
