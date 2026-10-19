import { useCallback, useEffect, useState } from 'react'
import { ClipboardCopy, FileText } from 'lucide-react'
import { get, post } from '../services/api'
import type { Application, Job } from '../types'
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  LoadingBlock,
  PageHeader,
  Select,
  Textarea,
} from '../components/ui'

export default function CoverLetter() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedJobId, setSelectedJobId] = useState('')
  const [selectedAppId, setSelectedAppId] = useState('')
  const [letter, setLetter] = useState('')
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [jobData, appData] = await Promise.all([
        get<Job[]>('/jobs/'),
        get<Application[]>('/applications/'),
      ])
      setJobs(jobData)
      setApplications(appData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs and applications')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleGenerate = async () => {
    if (!selectedJobId && !selectedAppId) {
      setError('Select a job or an application first.')
      return
    }
    setWorking(true)
    setError(null)
    try {
      const payload: { job_id?: string; application_id?: string } = {}
      if (selectedJobId) payload.job_id = selectedJobId
      else payload.application_id = selectedAppId
      const data = await post<{ cover_letter: string }>('/cover-letter/generate', payload)
      setLetter(data.cover_letter)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate cover letter')
    } finally {
      setWorking(false)
    }
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(letter)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Clipboard unavailable. Select the text and copy manually.')
    }
  }

  if (loading) return <LoadingBlock label="Loading" />

  return (
    <div className="space-y-5">
      <PageHeader
        title="Cover Letter"
        description="Generate a tailored draft you can edit before sending."
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <Card>
        <CardHeader title="Target" description="Pick a job or an existing application." />
        <div className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2">
          <Field label="Job">
            <Select
              value={selectedJobId}
              disabled={!!selectedAppId}
              onChange={(e) => {
                setSelectedJobId(e.target.value)
                setSelectedAppId('')
              }}
            >
              <option value="">Choose a job...</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title || 'Untitled'} — {job.company || 'Unknown'}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Application">
            <Select
              value={selectedAppId}
              disabled={!!selectedJobId}
              onChange={(e) => {
                setSelectedAppId(e.target.value)
                setSelectedJobId('')
              }}
            >
              <option value="">Choose an application...</option>
              {applications.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.job_title || 'Untitled'} — {app.company || 'Unknown'}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="border-t border-line px-4 py-3">
          <Button
            variant="primary"
            loading={working}
            disabled={!selectedJobId && !selectedAppId}
            icon={<FileText size={14} />}
            onClick={handleGenerate}
          >
            Generate cover letter
          </Button>
        </div>
      </Card>

      {letter ? (
        <Card>
          <CardHeader
            title="Draft"
            description="Editable. Review before sending."
            actions={
              <Button size="sm" icon={<ClipboardCopy size={13} />} onClick={copy}>
                {copied ? 'Copied' : 'Copy'}
              </Button>
            }
          />
          <div className="p-4">
            <Textarea
              rows={16}
              value={letter}
              onChange={(e) => setLetter(e.target.value)}
              className="font-mono text-xs leading-relaxed"
              aria-label="Cover letter draft"
            />
          </div>
        </Card>
      ) : (
        !loading && (
          <EmptyState
            icon={<FileText size={26} />}
            title="No draft yet"
            description="Select a target above and generate a tailored cover letter."
          />
        )
      )}
    </div>
  )
}