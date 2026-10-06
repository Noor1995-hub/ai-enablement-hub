import { useState } from 'react'
import { Link } from 'react-router-dom'
import { filterMedia, formatBytes, isUnused, mediaSummary, type MediaFile, type MediaFilter } from '../../lib/mediaLibrary'
import { useDeleteMedia, useMediaLibrary } from './api'
import { Card, Chip, ConfirmButton, EmptyState, ErrorState, Spinner, Table, formatDate } from './kit'
import type { TableColumn } from './kit'

const USAGE_PILLS: { value: MediaFilter['usage']; label: string }[] = [
  { value: 'all', label: 'All files' },
  { value: 'unused', label: 'Unused' },
]
const KIND_PILLS: { value: MediaFilter['kind']; label: string }[] = [
  { value: 'all', label: 'Images & videos' },
  { value: 'image', label: 'Images' },
  { value: 'video', label: 'Videos' },
]

/** Admin → Media (B6, spec 2026-10-06): every uploaded file, where it is used,
 * and a two-step delete for unused ones. Power admins only. */
export default function MediaPage() {
  const library = useMediaLibrary()
  const remove = useDeleteMedia()
  const [filter, setFilter] = useState<MediaFilter>({ usage: 'all', kind: 'all' })

  if (library.isLoading) return <div className="adm-loading"><Spinner /></div>
  if (library.error || !library.data) {
    return (
      <ErrorState
        message={library.error?.message.includes('Not Found') ? "Media storage isn't configured." : library.error?.message ?? 'Failed to load the media library.'}
        onRetry={() => void library.refetch()}
      />
    )
  }

  const files = library.data.files
  const columns: TableColumn<MediaFile>[] = [
    {
      key: 'preview',
      header: '',
      width: '64px',
      render: f =>
        f.preview_url ? <img src={f.preview_url} alt="" width={48} height={48} style={{ objectFit: 'cover', borderRadius: 6 }} /> : <Chip>▶ video</Chip>,
    },
    { key: 'name', header: 'File', render: f => <span className="adm-subtext">{f.path.split('/')[1]}</span> },
    { key: 'kind', header: 'Type', render: f => (f.kind === 'image' ? 'Image' : 'Video') },
    { key: 'size', header: 'Size', render: f => formatBytes(f.size_bytes) },
    { key: 'uploaded', header: 'Uploaded', render: f => formatDate(f.uploaded_at) },
    {
      key: 'used',
      header: 'Used in',
      render: f =>
        isUnused(f) ? (
          <Chip tone="warn">Not used anywhere</Chip>
        ) : (
          <span>
            {f.used_in.map((use, i) => (
              <span key={use.lesson_id}>
                {i > 0 && ', '}
                <Link to={`/learning/lesson/${use.lesson_id}?edit=true`}>{use.lesson_title}</Link>
              </span>
            ))}
            {f.proposals > 0 && <span className="adm-subtext"> +{f.proposals} AI proposal{f.proposals === 1 ? '' : 's'}</span>}
          </span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: f =>
        isUnused(f) ? (
          <ConfirmButton
            label="Delete"
            confirmLabel="Yes, delete"
            busy={remove.isPending && remove.variables === f.path}
            onConfirm={() => remove.mutate(f.path)}
          />
        ) : null,
    },
  ]

  return (
    <div>
      <div className="adm-page-head">
        <div>
          <h1 className="adm-page-title">Media</h1>
          <p className="adm-page-sub">{mediaSummary(files)}</p>
        </div>
      </div>

      {remove.error && <p className="adm-form-msg adm-form-msg-err" role="alert">{remove.error.message}</p>}

      <div className="adm-pills">
        {USAGE_PILLS.map(p => (
          <button key={p.value} type="button" className={filter.usage === p.value ? 'adm-pill active' : 'adm-pill'} onClick={() => setFilter(f => ({ ...f, usage: p.value }))}>
            {p.label}
          </button>
        ))}
        {KIND_PILLS.map(p => (
          <button key={p.value} type="button" className={filter.kind === p.value ? 'adm-pill active' : 'adm-pill'} onClick={() => setFilter(f => ({ ...f, kind: p.value }))}>
            {p.label}
          </button>
        ))}
      </div>

      <Card>
        <div className="adm-table-wrap">
          <Table
            columns={columns}
            rows={filterMedia(files, filter)}
            rowKey={f => f.path}
            empty={<EmptyState title="No files" hint="Nothing matches this filter." />}
          />
        </div>
      </Card>
    </div>
  )
}
