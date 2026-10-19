import {
  Bell,
  Copy,
  FileText,
  Mail,
  Pen,
  Radar,
  Send,
  Target,
  type LucideIcon,
} from 'lucide-react'
import type { AgentDefinition, WorkflowDefinition } from '../../data/mock'
import { relativeTime, Badge, Button, cx } from '../ui'
import type { Tone } from '../ui'

export const AGENT_ICONS: Record<AgentDefinition['icon'], LucideIcon> = {
  radar: Radar,
  target: Target,
  file: FileText,
  pen: Pen,
  send: Send,
  mail: Mail,
  bell: Bell,
  copy: Copy,
}

const STATUS_META: Record<AgentDefinition['status'], { label: string; tone: Tone }> = {
  idle: { label: 'Idle', tone: 'neutral' },
  running: { label: 'Running', tone: 'accent' },
  error: { label: 'Error', tone: 'danger' },
  disabled: { label: 'Disabled', tone: 'neutral' },
}

export function StatusIndicator({ status }: { status: AgentDefinition['status'] }) {
  const meta = STATUS_META[status]
  return (
    <Badge tone={meta.tone}>
      {status === 'running' && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute h-full w-full animate-ping rounded-full bg-accent opacity-70" />
          <span className="relative h-1.5 w-1.5 rounded-full bg-accent" />
        </span>
      )}
      {meta.label}
    </Badge>
  )
}

export function AgentCard({
  agent,
  onConfigure,
  onRun,
  onToggle,
}: {
  agent: AgentDefinition
  onConfigure: () => void
  onRun: () => void
  onToggle: () => void
}) {
  const Icon = AGENT_ICONS[agent.icon]

  return (
    <article
      className={cx(
        'flex flex-col gap-3 rounded-xl border border-line bg-surface-raised p-4 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md',
        !agent.enabled && 'opacity-60',
      )}
    >
      <header className="flex items-start gap-3">
        <span
          className={cx(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
            agent.status === 'error'
              ? 'bg-danger-soft text-danger ring-danger/20'
              : agent.enabled
                ? 'bg-accent-soft text-accent ring-accent/20'
                : 'bg-surface-sunken text-fg-subtle ring-line',
          )}
        >
          <Icon size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-fg">{agent.name}</h3>
          <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-fg-muted">
            {agent.description}
          </p>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-1.5">
        <StatusIndicator status={agent.status} />
        {agent.lastRun && (
          <span className="text-2xs text-fg-subtle">
            Last run {relativeTime(agent.lastRun)}
            {agent.lastDurationMs ? ` · ${(agent.lastDurationMs / 1000).toFixed(1)}s` : ''}
          </span>
        )}
      </div>

      <footer className="mt-auto flex items-center gap-2 border-t border-line/60 pt-3">
        <Button size="sm" onClick={onConfigure}>
          Configure
        </Button>
        <Button
          size="sm"
          variant="primary"
          loading={agent.status === 'running'}
          disabled={!agent.enabled}
          onClick={onRun}
        >
          Run now
        </Button>
        <button
          onClick={onToggle}
          role="switch"
          aria-checked={agent.enabled}
          aria-label={`${agent.enabled ? 'Disable' : 'Enable'} ${agent.name}`}
          className={cx(
            'relative ml-auto h-5 w-9 shrink-0 rounded-full transition-colors duration-200',
            agent.enabled ? 'bg-accent' : 'bg-line-strong',
          )}
        >
          <span
            className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200"
            style={{ transform: agent.enabled ? 'translateX(16px)' : 'none' }}
          />
        </button>
      </footer>
    </article>
  )
}

export function WorkflowCard({
  workflow,
  onRun,
  onToggle,
  onConfigure,
}: {
  workflow: WorkflowDefinition
  onRun: () => void
  onToggle: () => void
  onConfigure: () => void
}) {
  const Icon = AGENT_ICONS[workflow.icon as AgentDefinition['icon']]
  const agentRunning = workflow.agentId ? false : false

  return (
    <article className="flex flex-col gap-3 rounded-xl border border-line bg-surface-raised p-4 shadow-xs transition-all duration-200 hover:border-line-strong hover:shadow-md">
      <header className="flex items-start gap-3">
        <span
          className={cx(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
            workflow.lastStatus === 'error'
              ? 'bg-danger-soft text-danger ring-danger/20'
              : 'bg-surface-sunken text-accent ring-line',
          )}
        >
          <Icon size={17} />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-fg">{workflow.name}</h3>
          <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">{workflow.schedule}</p>
        </div>
        <button
          onClick={onToggle}
          role="switch"
          aria-checked={workflow.enabled}
          aria-label={`${workflow.enabled ? 'Disable' : 'Enable'} ${workflow.name}`}
          className={cx(
            'relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200',
            workflow.enabled ? 'bg-accent' : 'bg-line-strong',
          )}
        >
          <span
            className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200"
            style={{ transform: workflow.enabled ? 'translateX(16px)' : 'none' }}
          />
        </button>
      </header>

      <p className="text-xs leading-relaxed text-fg-muted">{workflow.description}</p>

      <dl className="grid grid-cols-2 gap-2 rounded-lg bg-surface-sunken p-2.5 text-2xs">
        <div>
          <dt className="text-fg-subtle">Last run</dt>
          <dd className="mt-0.5 text-fg-muted">
            {workflow.lastRun ? relativeTime(workflow.lastRun) : 'Never'}
          </dd>
        </div>
        <div>
          <dt className="text-fg-subtle">Next run</dt>
          <dd className="mt-0.5 text-fg-muted">
            {workflow.nextRun ? relativeTime(workflow.nextRun) : 'Not scheduled'}
          </dd>
        </div>
      </dl>

      {workflow.lastStatus === 'error' && (
        <p className="rounded-md bg-danger-soft px-2.5 py-1.5 text-2xs leading-relaxed text-danger">
          Last run failed — mailbox credentials are missing.
        </p>
      )}

      <footer className="mt-auto flex items-center gap-2 border-t border-line/60 pt-3">
        <Button size="sm" loading={agentRunning} disabled={!workflow.enabled} onClick={onRun}>
          Run now
        </Button>
        <Button size="sm" variant="ghost" onClick={onConfigure}>
          Configure
        </Button>
      </footer>
    </article>
  )
}