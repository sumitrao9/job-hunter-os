import { useState } from 'react'
import { AlertCircle, CheckCircle2, Plug, Settings2 } from 'lucide-react'
import type { WorkflowDefinition } from '../data/mock'
import { useAppStore } from '../store/useAppStore'
import { get } from '../services/api'
import {
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  Modal,
  PageHeader,
  cx,
  relativeTime,
} from '../components/ui'
import { DemoTag } from '../components/ui/data-display'
import { WorkflowCard } from '../components/agents/AgentCard'

export default function Automation() {
  const workflows = useAppStore((s) => s.workflows)
  const toggleWorkflow = useAppStore((s) => s.toggleWorkflow)
  const runWorkflow = useAppStore((s) => s.runWorkflow)
  const pushToast = useAppStore((s) => s.pushToast)

  const [configuring, setConfiguring] = useState<WorkflowDefinition | null>(null)
  const [n8nUrl, setN8nUrl] = useState('http://localhost:5678')
  const [n8nState, setN8nState] = useState<'unknown' | 'checking' | 'ok' | 'error'>('unknown')
  const [n8nError, setN8nError] = useState<string | null>(null)

  const testN8n = async () => {
    setN8nState('checking')
    setN8nError(null)
    try {
      const result = await get<{ ok: boolean; error?: string }>('/settings/test/n8n')
      if (result.ok) {
        setN8nState('ok')
        pushToast({ title: 'n8n is reachable', tone: 'accent' })
      } else {
        setN8nState('error')
        setN8nError(result.error ?? 'Connection failed')
        pushToast({
          title: 'n8n is not reachable',
          body: result.error ?? 'Connection failed',
          tone: 'danger',
        })
      }
    } catch (err) {
      setN8nState('error')
      setN8nError(err instanceof Error ? err.message : 'Probe failed')
      pushToast({ title: 'n8n probe failed', tone: 'danger' })
    }
  }

  const enabled = workflows.filter((w) => w.enabled).length

  return (
    <div className="space-y-5">
      <PageHeader
        title="Automation"
        description="Scheduled workflows that keep your search moving without manual runs."
        actions={<DemoTag />}
      />

      <Card>
        <CardHeader
          title="n8n connection"
          description="External workflow runner used for longer automations."
          actions={
            <Button
              size="sm"
              variant={n8nState === 'ok' ? 'secondary' : 'primary'}
              loading={n8nState === 'checking'}
              onClick={testN8n}
            >
              Test connection
            </Button>
          }
        />
        <div className="space-y-3 p-4">
          <Field label="n8n base URL" hint="Where your n8n instance is listening.">
            <div className="flex gap-2">
              <Input
                value={n8nUrl}
                onChange={(e) => setN8nUrl(e.target.value)}
                placeholder="http://localhost:5678"
                className="font-mono text-xs"
              />
              <Button size="md" onClick={() => pushToast({ title: 'n8n URL saved', tone: 'accent' })}>
                Save
              </Button>
            </div>
          </Field>

          <div
            className={cx(
              'flex items-center gap-2 rounded-lg px-3 py-2 text-xs ring-1 ring-inset',
              n8nState === 'ok'
                ? 'bg-accent-soft text-accent ring-accent/20'
                : n8nState === 'error'
                  ? 'bg-danger-soft text-danger ring-danger/20'
                  : 'bg-surface-sunken text-fg-muted ring-line',
            )}
          >
            {n8nState === 'ok' ? (
              <CheckCircle2 size={14} className="shrink-0" />
            ) : n8nState === 'error' ? (
              <AlertCircle size={14} className="shrink-0" />
            ) : (
              <Plug size={14} className="shrink-0" />
            )}
            <span>
              {n8nState === 'ok' && 'Connected — n8n responded successfully.'}
              {n8nState === 'error' && `Not reachable: ${n8nError ?? 'connection failed'}`}
              {n8nState === 'checking' && 'Checking connection…'}
              {n8nState === 'unknown' && 'Connection status not checked yet.'}
            </span>
          </div>
        </div>
      </Card>

      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-fg">
          Workflows
          <span className="ml-2 text-xs font-normal text-fg-muted">
            {enabled} of {workflows.length} enabled
          </span>
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {workflows.map((workflow) => (
          <WorkflowCard
            key={workflow.id}
            workflow={workflow}
            onRun={() => runWorkflow(workflow.id)}
            onToggle={() => toggleWorkflow(workflow.id)}
            onConfigure={() => setConfiguring(workflow)}
          />
        ))}
      </div>

      <Modal
        open={!!configuring}
        onClose={() => setConfiguring(null)}
        title={configuring?.name ?? ''}
        footer={
          <Button size="sm" onClick={() => setConfiguring(null)}>
            Close
          </Button>
        }
      >
        {configuring && (
          <div className="space-y-4">
            <p className="text-xs leading-relaxed text-fg-muted">{configuring.description}</p>

            <dl className="space-y-1.5">
              {[
                { label: 'Schedule', value: configuring.schedule },
                { label: 'Last run', value: configuring.lastRun ? relativeTime(configuring.lastRun) : 'Never' },
                { label: 'Next run', value: configuring.nextRun ? relativeTime(configuring.nextRun) : 'Not scheduled' },
                {
                  label: 'Last result',
                  value:
                    configuring.lastStatus === 'success'
                      ? 'Success'
                      : configuring.lastStatus === 'error'
                        ? 'Failed'
                        : 'No runs yet',
                },
              ].map((row) => (
                <div
                  key={row.label}
                  className="flex items-center justify-between rounded-md bg-surface-sunken px-2.5 py-1.5"
                >
                  <dt className="text-xs text-fg-muted">{row.label}</dt>
                  <dd className="text-xs font-medium text-fg">{row.value}</dd>
                </div>
              ))}
            </dl>

            {configuring.lastStatus === 'error' && (
              <div className="flex items-start gap-2 rounded-lg bg-danger-soft p-3 ring-1 ring-inset ring-danger/20">
                <AlertCircle size={15} className="mt-0.5 shrink-0 text-danger" />
                <div className="text-xs leading-relaxed text-danger">
                  <p className="font-medium">Last run failed</p>
                  <p className="mt-0.5">
                    The email agent could not reach your mailbox. Add IMAP credentials in Settings
                    and run it again.
                  </p>
                </div>
              </div>
            )}

            <Field label="Trigger" hint="Change when this workflow runs.">
              <Input
                defaultValue={configuring.schedule}
                onChange={() =>
                  pushToast({ title: 'Schedule updated', tone: 'accent' })
                }
              />
            </Field>

            <div className="flex items-center gap-2">
              <Settings2 size={14} className="text-fg-subtle" />
              <span className="text-xs text-fg-muted">
                Advanced options will appear once this workflow is connected to n8n.
              </span>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}