import { useCallback, useEffect, useRef, useState } from 'react'
import { FileText, Trash2, Upload } from 'lucide-react'
import { del, get } from '../services/api'
import type { Resume } from '../types'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  Skeleton,
} from '../components/ui'

export default function Resumes() {
  const [items, setItems] = useState<Resume[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<Resume | null>(null)
  const [deleting, setDeleting] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await get<Resume[]>('/resumes/'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load resumes')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)

    if (!file) {
      setError('Choose a file to upload.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File is larger than 10MB.')
      return
    }

    const form = new FormData()
    form.append('title', title.trim() || file.name)
    form.append('file', file)

    setUploading(true)
    try {
      const res = await fetch('/api/resumes/', { method: 'POST', body: form })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail || `Upload failed (HTTP ${res.status})`)
      }
      setTitle('')
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
      setSuccess('Resume uploaded.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    setError(null)
    try {
      await del(`/resumes/${pendingDelete.id}`)
      setSuccess(`Deleted "${pendingDelete.title}".`)
      setPendingDelete(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Resume Studio"
        description="Store the resumes you want to send with applications."
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}
      {success && <Alert tone="success" onDismiss={() => setSuccess(null)}>{success}</Alert>}

      <Card>
        <CardHeader title="Upload a resume" description="Accepted formats: PDF, DOCX. Max 10MB." />
        <form onSubmit={handleUpload} className="space-y-3 p-4">
          <Field label="Resume title" hint="Defaults to the filename if left blank.">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Frontend Resume"
            />
          </Field>
          <Field label="File">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-fg-muted file:mr-3 file:rounded-md file:border file:border-line file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-fg hover:file:bg-surface-sunken"
            />
          </Field>
          {file && (
            <p className="text-xs text-fg-subtle">
              Selected: {file.name} ({(file.size / 1024).toFixed(0)} KB)
            </p>
          )}
          <Button type="submit" variant="primary" loading={uploading} icon={<Upload size={14} />}>
            Upload resume
          </Button>
        </form>
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="space-y-3 p-4">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </Card>
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<FileText size={26} />}
          title="No resumes yet"
          description="Upload your first resume above to start building applications."
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((resume) => (
            <Card key={resume.id} className="flex flex-col gap-3 p-4">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold text-fg">{resume.title}</h3>
                <p className="mt-0.5 truncate text-xs text-fg-subtle">
                  {resume.original_filename}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge tone="info">{(resume.file_type || '').toUpperCase()}</Badge>
                {resume.is_default && <Badge tone="accent">Default</Badge>}
                {resume.created_at && (
                  <Badge tone="neutral">{new Date(resume.created_at).toLocaleDateString()}</Badge>
                )}
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="self-start text-danger hover:bg-danger-soft"
                icon={<Trash2 size={13} />}
                onClick={() => setPendingDelete(resume)}
              >
                Delete
              </Button>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Delete resume"
        footer={
          <>
            <Button size="sm" onClick={() => setPendingDelete(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button size="sm" variant="danger" loading={deleting} onClick={confirmDelete}>
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-fg-muted">
          Permanently delete <strong className="text-fg">{pendingDelete?.title}</strong>? This cannot be
          undone.
        </p>
      </Modal>
    </div>
  )
}