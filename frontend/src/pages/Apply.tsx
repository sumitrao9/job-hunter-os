import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ClipboardCopy, ExternalLink, FileText, Info, Send } from 'lucide-react'
import { get, post } from '../services/api'
import type { Application, Job } from '../types'
import {
  Alert,
  Badge,
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

interface PrepareResult {
  cover_letter: string
  form_answers: Record<string, unknown>
  action?: string
  url?: string
  instructions?: string
  application_id?: string
}

export default function Apply() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  // Deep-linked from the Discover job drawer as /apply?job=<id>.
  const [selectedJobId, setSelectedJobId] = useState(() => searchParams.get('job') ?? '')
  const [selectedAppId, setSelectedAppId] = useState('')
  const [prepared, setPrepared] = useState<PrepareResult | null>(null)
  const [markingSubmitted, setMarkingSubmitted] = useState(false)
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null)
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

      // Arriving from a job card's "Prepare" action preselects that job.
      const requested = new URLSearchParams(window.location.search).get('job')
      if (requested && jobData.some((j) => j.id === requested)) {
        setSelectedJobId(requested)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs and applications')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const selectedJob = jobs.find((j) => j.id === selectedJobId)
  const targetUrl = prepared?.url || selectedJob?.url || ''

  const handlePrepare = async () => {
    setWorking(true)
    setError(null)
    setCopied(false)
    setPrepared(null)
    try {
      const payload: { job_id?: string; application_id?: string } = {}
      if (selectedJobId) payload.job_id = selectedJobId
      else if (selectedAppId) payload.application_id = selectedAppId
      else {
        setError('Select a job or an application first.')
        return
      }
      setPrepared(await post<PrepareResult>('/apply/prepare', payload))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to prepare application')
    } finally {
      setWorking(false)
    }
  }

  const copyCoverLetter = async () => {
    if (!prepared) return
    try {
      await navigator.clipboard.writeText(prepared.cover_letter)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Clipboard unavailable. Select the text and copy manually.')
    }
  }

  const answerEntries = prepared ? Object.entries(prepared.form_answers || {}) : []
  const emptyAnswers = answerEntries.filter(
    ([, v]) => v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0),
  )

  // The user submits on the employer's site; this only records what happened.
  const handleMarkSubmitted = async () => {
    const applicationId = prepared?.application_id
    if (!applicationId) return
    setMarkingSubmitted(true)
    setError(null)
    try {
      await post(`/apply/complete/${applicationId}`)
      setSubmittedMessage('Marked as submitted. Your pipeline is up to date.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the application.')
    } finally {
      setMarkingSubmitted(false)
    }
  }

  if (loading) return <LoadingBlock label="Loading" />

  return (
    <div className="space-y-5">
      <PageHeader
        title="Apply"
        description="Generate a tailored application package, then submit it yourself on the employer's site."
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <Card>
        <CardHeader
          title="Choose a target"
          description="Pick a discovered job or an existing application."
        />
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
        <div className="flex flex-wrap items-center gap-3 border-t border-line px-4 py-3">
          <Button
            variant="primary"
            loading={working}
            disabled={!selectedJobId && !selectedAppId}
            icon={<FileText size={14} />}
            onClick={handlePrepare}
          >
            Prepare application
          </Button>
          {!selectedJobId && !selectedAppId && (
            <span className="text-xs text-fg-subtle">Select a target to continue.</span>
          )}
        </div>
      </Card>

      {prepared && (
        <>
          <Alert tone="info">
            {prepared.instructions ||
              'Review the generated content, then open the original posting and submit it yourself.'}
          </Alert>

          <Card>
            <CardHeader
              title="Cover letter"
              description="Generated from your profile and the job description."
              actions={
                <Button size="sm" icon={<ClipboardCopy size={13} />} onClick={copyCoverLetter}>
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              }
            />
            <div className="p-4">
              <Textarea
                readOnly
                rows={14}
                value={prepared.cover_letter}
                className="font-mono text-xs leading-relaxed"
                aria-label="Generated cover letter"
              />
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Form answers"
              description={
                emptyAnswers.length > 0
                  ? `${emptyAnswers.length} field(s) still need your input before submitting.`
                  : 'Pre-filled from your profile.'
              }
              actions={
                emptyAnswers.length > 0 ? (
                  <Badge tone="warn">{emptyAnswers.length} missing</Badge>
                ) : (
                  <Badge tone="accent">Complete</Badge>
                )
              }
            />
            <div className="p-4">
              {answerEntries.length === 0 ? (
                <p className="text-sm text-fg-muted">No form answers generated.</p>
              ) : (
                <dl className="divide-y divide-line">
                  {answerEntries.map(([key, value]) => {
                    const isEmpty =
                      value === null ||
                      value === undefined ||
                      value === '' ||
                      (Array.isArray(value) && value.length === 0)
                    const display = Array.isArray(value)
                      ? value.join(', ')
                      : value === null || value === undefined || value === ''
                        ? '—'
                        : String(value)
                    return (
                      <div key={key} className="flex flex-wrap items-start justify-between gap-3 py-2">
                        <dt className="text-xs font-medium capitalize text-fg-muted">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        <dd
                          className={
                            isEmpty
                              ? 'text-sm italic text-fg-subtle'
                              : 'text-sm text-fg'
                          }
                        >
                          {isEmpty ? 'Needs your input' : display}
                        </dd>
                      </div>
                    )
                  })}
                </dl>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Submit"
              description="NS never submits on your behalf. You review and submit."
            />
            <div className="space-y-3 p-4">
              {targetUrl ? (
                <a
                  href={targetUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
                >
                  Open the original posting <ExternalLink size={13} />
                </a>
              ) : (
                <p className="text-sm text-fg-muted">
                  No application URL available for this target. Open the job from Job Discovery instead.
                </p>
              )}
              <div className="flex items-start gap-2 rounded-md bg-surface-sunken p-3 text-xs text-fg-muted">
                <Info size={14} className="mt-0.5 shrink-0" />
                <p>
                  Paste the cover letter above and fill any missing answers on the employer's site, then
                  submit. Track the outcome in Applications.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" icon={<Send size={13} />} onClick={() => navigate('/applications')}>
                  Go to Applications
                </Button>
                {prepared?.application_id && (
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={markingSubmitted}
                    onClick={handleMarkSubmitted}
                  >
                    Mark as submitted
                  </Button>
                )}
              </div>
              {submittedMessage && (
                <Alert tone="success">{submittedMessage}</Alert>
              )}
            </div>
          </Card>
        </>
      )}

      {!prepared && !loading && jobs.length === 0 && applications.length === 0 && (
        <EmptyState
          icon={<FileText size={26} />}
          title="Nothing to apply to yet"
          description="Discover jobs first, then come back here to prepare an application."
          action={
            <Button variant="primary" size="sm" onClick={() => navigate('/jobs')}>
              Discover jobs
            </Button>
          }
        />
      )}
    </div>
  )
}