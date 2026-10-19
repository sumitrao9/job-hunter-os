import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, ArrowRight, Play, Terminal } from 'lucide-react'
import { type AgentDefinition } from '../data/mock'
import { useAppStore } from '../store/useAppStore'
import { Badge, Button, Card, CardHeader, EmptyState, PageHeader, relativeTime, cx } from '../components/ui'
import type { Tone } from '../components/ui'
import { DemoTag } from '../components/ui/data-display'
import { AGENT_ICONS, AgentCard, StatusIndicator } from '../components/agents/AgentCard'
import { Modal } from '../components/ui'

/** Ordered pipeline, used for the connection overview. */
const PIPELINE = ['discovery', 'matching', 'resume', 'cover_letter', 'application', 'follow_up']

export default function Agents() {
  const agents = useAppStore((s) => s.agents)
  const logs = useAppStore((s) => s.agentLogs)
  const runAgent = useAppStore((s) => s.runAgent)
  const toggleAgent = useAppStore((s) => s.toggleAgent)

  const [configuring, setConfiguring] = useState<AgentDefinition | null>(null)

  const stats = useMemo(() => {
    const enabled = agents.filter((a) => a.enabled).length
    const running = agents.filter((a) => a.status === 'running').length
    const errors = agents.filter((a) => a.status === 'error').length
    const runsToday = agents.reduce((sum, a) => sum + a.runsToday, 0)
    return { enabled, running, errors, runsToday }
  }, [agents])

  const pipelineAgents = useMemo(
    () => PIPELINE.map((id) => agents.find((a) => a.id === id)).filter(Boolean) as AgentDefinition[],
    [agents],
  )

  const recentLogs = logs.slice(0, 8)

  return (
    <div className="space-y-5">
      <PageHeader
        title="AI Agents"
        description="Each agent owns one step of the job search and can be run or tuned independently."
        actions={<DemoTag />}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { label: 'Enabled', value: `${stats.enabled}/${agents.length}`, tone: 'text-fg' },
          { label: 'Running now', value: stats.running, tone: 'text-accent' },
          { label: 'Needs attention', value: stats.errors, tone: stats.errors ? 'text-danger' : 'text-fg' },
          { label: 'Runs today', value: stats.runsToday, tone: 'text-fg' },
        ].map((s) => (
          <Card key={s.label} className="p-4">
            <p className="text-xs text-fg-muted">{s.label}</p>
            <p className={cx('tabular mt-1.5 text-2xl font-semibold tracking-tight', s.tone)}>
              {s.value}
            </p>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader
          title="Workflow overview"
          description="How a new job travels through the system."
        />
        <div className="overflow-x-auto p-4">
          <ol className="flex min-w-max items-center gap-2">
            {pipelineAgents.map((agent, index) => {
              const Icon = AGENT_ICONS[agent.icon]
              return (
                <li key={agent.id} className="flex items-center gap-2">
                  <motion.div
                    whileHover={{ y: -2 }}
                    className={cx(
                      'flex w-[168px] flex-col gap-2 rounded-xl border p-3 transition-colors',
                      agent.status === 'error'
                        ? 'border-danger/30 bg-danger-soft/40'
                        : agent.enabled
                          ? 'border-line bg-surface-raised hover:border-line-strong'
                          : 'border-line bg-surface-sunken/60 opacity-60',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-sunken text-accent ring-1 ring-line">
                        <Icon size={14} />
                      </span>
                      <span className="min-w-0 truncate text-xs font-medium text-fg">
                        {agent.name.replace(' Agent', '')}
                      </span>
                    </div>
                    <StatusIndicator status={agent.status} />
                  </motion.div>
                  {index < pipelineAgents.length - 1 && (
                    <ArrowRight size={14} className="shrink-0 text-fg-subtle" aria-hidden="true" />
                  )}
                </li>
              )
            })}
          </ol>
        </div>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-fg">All agents</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onConfigure={() => setConfiguring(agent)}
              onRun={() => runAgent(agent.id)}
              onToggle={() => toggleAgent(agent.id)}
            />
          ))}
        </div>
      </div>

      <Card>
        <CardHeader
          title="Execution log"
          description="Most recent agent activity across the system."
          actions={<DemoTag />}
        />
        {recentLogs.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={<Terminal size={22} />}
              title="No runs recorded"
              description="Run an agent to see its output here."
            />
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {recentLogs.map((log) => {
              const agent = agents.find((a) => a.id === log.agentId)
              return (
                <li key={log.id} className="flex items-start gap-3 px-4 py-2.5">
                  <span
                    className={cx(
                      'mt-1 h-1.5 w-1.5 shrink-0 rounded-full',
                      log.level === 'error'
                        ? 'bg-danger'
                        : log.level === 'warn'
                          ? 'bg-warn'
                          : 'bg-accent',
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-fg">
                      {agent?.name ?? log.agentId}
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">{log.message}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-2xs text-fg-subtle">{relativeTime(log.at)}</p>
                    {log.durationMs && (
                      <p className="text-2xs text-fg-subtle">{(log.durationMs / 1000).toFixed(1)}s</p>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      <Modal
        open={!!configuring}
        onClose={() => setConfiguring(null)}
        title={configuring?.name ?? ''}
        footer={
          <>
            <Button size="sm" onClick={() => setConfiguring(null)}>
              Close
            </Button>
            <Button
              size="sm"
              variant="primary"
              icon={<Play size={13} />}
              loading={configuring?.status === 'running'}
              disabled={!configuring?.enabled}
              onClick={() => configuring && runAgent(configuring.id)}
            >
              Test agent
            </Button>
          </>
        }
      >
        {configuring && (
          <div className="space-y-4">
            <p className="text-xs leading-relaxed text-fg-muted">{configuring.purpose}</p>

            <section>
              <h4 className="mb-2 text-xs font-semibold text-fg">Configuration</h4>
              <dl className="space-y-1.5">
                {configuring.config.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between rounded-md bg-surface-sunken px-2.5 py-1.5"
                  >
                    <dt className="text-xs text-fg-muted">{item.label}</dt>
                    <dd className="text-xs font-medium text-fg">{item.value}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <h4 className="mb-1.5 text-xs font-semibold text-fg">Inputs</h4>
                <ul className="space-y-1">
                  {configuring.inputs.map((item) => (
                    <li key={item} className="text-xs text-fg-muted">
                      · {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="mb-1.5 text-xs font-semibold text-fg">Outputs</h4>
                <ul className="space-y-1">
                  {configuring.outputs.map((item) => (
                    <li key={item} className="text-xs text-fg-muted">
                      · {item}
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            <section>
              <h4 className="mb-1.5 text-xs font-semibold text-fg">Status</h4>
              <div className="flex flex-wrap items-center gap-2">
                <StatusIndicator status={configuring.status} />
                <Badge tone={configuring.enabled ? 'accent' : ('neutral' as Tone)}>
                  {configuring.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                <span className="text-2xs text-fg-subtle">
                  {configuring.runsToday} runs today
                </span>
              </div>
            </section>

            {configuring.status === 'error' && (
              <div className="flex items-start gap-2 rounded-lg bg-danger-soft p-3 ring-1 ring-inset ring-danger/20">
                <AlertCircle size={15} className="mt-0.5 shrink-0 text-danger" />
                <p className="text-xs leading-relaxed text-danger">
                  Last run failed. The mailbox is not configured — add credentials in Settings, then
                  run the agent again.
                </p>
              </div>
            )}

            <section>
              <h4 className="mb-1.5 text-xs font-semibold text-fg">Recent runs</h4>
              {logs.filter((l) => l.agentId === configuring.id).length === 0 ? (
                <p className="text-xs text-fg-subtle">No runs recorded yet.</p>
              ) : (
                <ul className="space-y-1">
                  {logs
                    .filter((l) => l.agentId === configuring.id)
                    .slice(0, 4)
                    .map((log) => (
                      <li key={log.id} className="flex items-center gap-2 text-xs">
                        <span
                          className={cx(
                            'h-1.5 w-1.5 shrink-0 rounded-full',
                            log.level === 'error' ? 'bg-danger' : 'bg-accent',
                          )}
                        />
                        <span className="min-w-0 flex-1 truncate text-fg-muted">{log.message}</span>
                        <span className="shrink-0 text-fg-subtle">{relativeTime(log.at)}</span>
                      </li>
                    ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </Modal>
    </div>
  )
}