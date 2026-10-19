import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  ChevronRight,
  Clock,
  Play,
  Square,
} from 'lucide-react'
import { get, post } from '../services/api'
import { useAppStore } from '../store/useAppStore'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Toggle,
  relativeTime,
} from '../components/ui'
import { MatchScore } from '../components/ui/data-display'
import { DetailDrawer } from '../components/ui/DetailDrawer'
import type { AutoApplySettings, AutoApplyAttempt, QueuedApproval, AutoApplyStats } from '../types'

type AttemptStatus =
  | 'not_started'
  | 'in_progress'
  | 'awaiting_approval'
  | 'submitted_confirmed'
  | 'submitted_unconfirmed'
  | 'failed'
  | 'manual_required'

const STATUS_TONES: Record<AttemptStatus, 'neutral' | 'accent' | 'warn' | 'danger'> = {
  not_started: 'neutral',
  in_progress: 'accent',
  awaiting_approval: 'warn',
  submitted_confirmed: 'accent',
  submitted_unconfirmed: 'warn',
  failed: 'danger',
  manual_required: 'warn',
}

const STEP_LABELS: Record<string, string> = {
  discovered: 'Discovered',
  matched: 'Matched',
  prepared: 'Prepared',
  form_filled: 'Form filled',
  submitted: 'Submitted',
  result: 'Result',
}

export default function AutoApply() {
  const pushToast = useAppStore((s) => s.pushToast)

  const [settings, setSettings] = useState<AutoApplySettings | null>(null)
  const [active, setActive] = useState<AutoApplyAttempt | null>(null)
  const [history, setHistory] = useState<AutoApplyAttempt[]>([])
  const [approvals, setApprovals] = useState<QueuedApproval[]>([])
  const [stats, setStats] = useState<AutoApplyStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<AutoApplyAttempt | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [settingsData, statusPayload, historyData, queueData, statsData] = await Promise.all([
        get<AutoApplySettings>('/auto-apply/settings'),
        get<{ enabled: boolean; emergency_stop: boolean; mode: string; active_attempt: AutoApplyAttempt | null }>('/auto-apply/status'),
        get<AutoApplyAttempt[]>('/auto-apply/history'),
        get<QueuedApproval[]>('/auto-apply/queue'),
        get<AutoApplyStats>('/auto-apply/stats'),
      ])
      setSettings(settingsData)
      setActive(statusPayload.active_attempt)
      setHistory(historyData)
      setApprovals(queueData)
      setStats(statsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load auto-apply state.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [load])

  const handleToggleEnabled = async (enabled: boolean) => {
    setSaving(true)
    try {
      await post('/auto-apply/settings', { enabled })
      await load()
      pushToast({
        title: enabled ? 'Auto-apply enabled' : 'Auto-apply disabled',
        tone: 'accent',
      })
    } catch {
      pushToast({ title: 'Could not update settings', tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  const handleEmergencyStop = async () => {
    setSaving(true)
    try {
      await post('/auto-apply/stop', {})
      await load()
      pushToast({ title: 'Emergency stop activated', tone: 'danger' })
    } catch {
      pushToast({ title: 'Could not activate emergency stop', tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  const handleStart = async () => {
    setSaving(true)
    try {
      const result = await post<{ ok: boolean; message: string; attempt_id: string }>('/auto-apply/start')
      await load()
      pushToast({ title: result.message, tone: 'accent' })
    } catch (err) {
      pushToast({
        title: 'Could not start auto-apply',
        body: err instanceof Error ? err.message : undefined,
        tone: 'danger',
      })
    } finally {
      setSaving(false)
    }
  }

  const handleApprove = async (approvalId: string, decision: 'approved' | 'rejected') => {
    try {
      await post(`/auto-apply/approvals/${approvalId}/process`, { decision })
      await load()
      pushToast({
        title: decision === 'approved' ? 'Application approved' : 'Application rejected',
        tone: decision === 'approved' ? 'accent' : 'warn',
      })
    } catch {
      pushToast({ title: 'Could not record decision', tone: 'danger' })
    }
  }

  const handleSubmit = async (approvalId: string) => {
    setSaving(true)
    try {
      await post(`/auto-apply/approvals/${approvalId}/submit`, { dry_run: false })
      await load()
      pushToast({
        title: 'Submission started',
        body: 'Playwright browser will fill and submit the application form.',
        tone: 'accent',
      })
    } catch (err) {
      pushToast({
        title: 'Submission failed',
        body: err instanceof Error ? err.message : 'Unknown error',
        tone: 'danger',
      })
    } finally {
      setSaving(false)
    }
  }

  const canStart = settings?.enabled && !settings.emergency_stop && !active
  const isRunning = !!active && active.status === 'in_progress'

  if (loading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Auto Apply" description="Automated job application engine." />
        <Card className="h-40 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Auto Apply"
        description="Automated job application engine. Human approval is required before any submission."
        actions={
          settings?.emergency_stop ? (
            <Badge tone="danger">Emergency stop active</Badge>
          ) : isRunning ? (
            <Button size="sm" variant="danger" icon={<Square size={14} />} onClick={handleEmergencyStop} loading={saving}>
              Emergency stop
            </Button>
          ) : (
            <Button size="sm" variant="primary" icon={<Play size={14} />} onClick={handleStart} loading={saving} disabled={!canStart}>
              Start
            </Button>
          )
        }
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Configuration" description="Control how the engine runs." />
          <div className="space-y-4 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-fg">Enable auto-apply</p>
                <p className="text-xs text-fg-muted">
                  {settings?.enabled ? 'Engine is active.' : 'Engine is inactive.'}
                </p>
              </div>
              <Toggle
                checked={!!settings?.enabled}
                onChange={(v) => handleToggleEnabled(v)}
                label="Enable auto-apply"
              />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-fg">Emergency stop</p>
                <p className="text-xs text-fg-muted">Immediately prevents new automated applications.</p>
              </div>
              <Button
                size="sm"
                variant={settings?.emergency_stop ? 'secondary' : 'danger'}
                onClick={handleEmergencyStop}
                loading={saving}
              >
                {settings?.emergency_stop ? 'Clear stop' : 'Activate stop'}
              </Button>
            </div>
            <Field label="Mode">
              <Select
                value={settings?.mode || 'manual'}
                onChange={async (e) => {
                  setSaving(true)
                  try { await post('/auto-apply/settings', { mode: e.target.value }); await load() } finally { setSaving(false) }
                }}
                disabled={saving}
              >
                <option value="manual">Manual — prepare only, user submits</option>
                <option value="approval">Approval required — prepare, review, then submit</option>
                <option value="autonomous">Autonomous — submit automatically where permitted</option>
              </Select>
            </Field>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Minimum match score" hint="Jobs below this score are skipped.">
                <Input
                  type="number"
                  value={String(settings?.min_match_score ?? 50)}
                  onChange={async (e) => {
                    setSaving(true)
                    try { await post('/auto-apply/settings', { min_match_score: Number(e.target.value) }); await load() } finally { setSaving(false) }
                  }}
                  disabled={saving}
                />
              </Field>
              <Field label="Max applications per day">
                <Input
                  type="number"
                  value={String(settings?.max_per_day ?? 5)}
                  onChange={async (e) => {
                    setSaving(true)
                    try { await post('/auto-apply/settings', { max_per_day: Number(e.target.value) }); await load() } finally { setSaving(false) }
                  }}
                  disabled={saving}
                />
              </Field>
            </div>
            <Toggle
              checked={!!settings?.generate_cover_letter}
              onChange={async (v) => {
                setSaving(true)
                try { await post('/auto-apply/settings', { generate_cover_letter: v }); await load() } finally { setSaving(false) }
              }}
              label="Generate cover letter for each application"
            />
          </div>
        </Card>

        <Card>
          <CardHeader title="Status" description="Current execution state." />
          <div className="space-y-3 p-4">
            <div>
              <p className="text-xs text-fg-muted">Engine state</p>
              <p className="text-sm font-semibold text-fg">
                {settings?.emergency_stop ? 'Emergency stop' : isRunning ? 'Running' : settings?.enabled ? 'Ready' : 'Disabled'}
              </p>
            </div>
            <div>
              <p className="text-xs text-fg-muted">Mode</p>
              <p className="text-sm font-medium text-fg">{settings?.mode || 'manual'}</p>
            </div>
            <div>
              <p className="text-xs text-fg-muted">Active attempt</p>
              {active ? (
                <div className="space-y-1">
                  <p className="text-sm font-medium text-fg">{active.job_id || 'Initializing...'}</p>
                  <Badge tone={STATUS_TONES[active.status as AttemptStatus] || 'neutral'}>{active.status}</Badge>
                  {active.step && <p className="text-xs text-fg-muted">Step: {STEP_LABELS[active.step] || active.step}</p>}
                </div>
              ) : (
                <p className="text-xs text-fg-muted">No active execution.</p>
              )}
            </div>
            <div>
              <p className="text-xs text-fg-muted">Pending approvals</p>
              <p className="text-sm font-semibold text-fg">{stats?.pending_approvals ?? approvals.length}</p>
            </div>
          </div>
        </Card>
      </div>

      {approvals.length > 0 && (
        <Card>
           <CardHeader
             title="Approval queue"
             description="Ready-to-submit applications. Click Submit to auto-fill the form and confirm the final submission yourself."
           />
          <div className="divide-y divide-line">
            {approvals.map((approval) => (
              <div key={approval.approval_id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-fg">
                    {approval.job_title || 'Untitled position'}
                  </p>
                  <p className="text-xs text-fg-muted">
                    {approval.company || 'Unknown company'} · Match: {approval.match_score !== undefined ? `${approval.match_score}%` : '—'}
                  </p>
                </div>
                 <div className="flex items-center gap-2">
                   <Button
                     size="sm"
                     variant="primary"
                     icon={<Play size={14} />}
                     onClick={() => handleSubmit(approval.approval_id)}
                     disabled={saving}
                   >
                     Submit
                   </Button>
                   <Button
                     size="sm"
                     variant="ghost"
                     onClick={() => handleApprove(approval.approval_id, 'rejected')}
                     disabled={saving}
                   >
                     Skip
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <CardHeader
          title="Execution history"
          description="Recent auto-apply attempts and their outcomes."
        />
        {history.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={<Clock size={22} />}
              title="No executions yet"
              description="Enable auto-apply and start the engine to see attempts here."
            />
          </div>
        ) : (
          <div className="divide-y divide-line">
            {history.slice(0, 20).map((attempt) => (
              <button
                key={attempt.id}
                onClick={() => setSelected(attempt)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-sunken/60"
              >
                <MatchScore score={undefined} size={28} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-fg">
                    {attempt.job_id ? `Job ${attempt.job_id.slice(0, 8)}` : 'Unknown job'}
                  </p>
                  <p className="text-xs text-fg-muted">
                    {relativeTime(attempt.started_at)} · {STEP_LABELS[attempt.step || ''] || attempt.step || 'Not started'}
                  </p>
                </div>
                <Badge tone={STATUS_TONES[attempt.status as AttemptStatus] || 'neutral'}>
                  {attempt.status.replace(/_/g, ' ')}
                </Badge>
                <ChevronRight size={14} className="shrink-0 text-fg-subtle" />
              </button>
            ))}
          </div>
        )}
      </Card>

      <DetailDrawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={`Attempt ${selected?.id.slice(0, 8)}`}
        subtitle={selected?.job_id || ''}
        footer={<Button size="sm" onClick={() => setSelected(null)}>Close</Button>}
      >
        {selected && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-fg-muted">Status</p>
                <Badge tone={STATUS_TONES[selected.status as AttemptStatus] || 'neutral'}>
                  {selected.status.replace(/_/g, ' ')}
                </Badge>
              </div>
              <div>
                <p className="text-xs text-fg-muted">Step</p>
                <p className="text-sm font-medium text-fg">{STEP_LABELS[selected.step || ''] || selected.step || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-fg-muted">Started</p>
                <p className="text-sm text-fg">{relativeTime(selected.started_at)}</p>
              </div>
              <div>
                <p className="text-xs text-fg-muted">Finished</p>
                <p className="text-sm text-fg">{selected.finished_at ? relativeTime(selected.finished_at) : '—'}</p>
              </div>
            </div>
            {selected.error && (
              <div className="flex items-start gap-2 rounded-lg bg-danger-soft p-3 ring-1 ring-inset ring-danger/20">
                <AlertCircle size={15} className="mt-0.5 shrink-0 text-danger" />
                <p className="text-xs leading-relaxed text-danger">{selected.error}</p>
              </div>
            )}
          </div>
        )}
      </DetailDrawer>
    </div>
  )
}
