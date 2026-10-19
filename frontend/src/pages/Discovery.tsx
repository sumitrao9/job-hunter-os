import { useEffect, useMemo, useState } from 'react'
import { Play, Globe } from 'lucide-react'
import { get, post } from '../services/api'
import { useAppStore } from '../store/useAppStore'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Toggle,
  relativeTime,
} from '../components/ui'
import { MetricCard } from '../components/ui/data-display'

type SourceStatus = {
  id: string
  source_name: string
  adapter: string
  enabled: boolean
  health_status: string
  last_run?: string
  jobs_found: number
  new_jobs: number
  duplicates: number
  schedule: string
}

type SchedulerStatus = {
  enabled: boolean
  frequency_minutes: number
  last_run?: string
  next_run?: string
  running: boolean
  total_runs: number
}

export default function Discovery() {
  const pushToast = useAppStore((s) => s.pushToast)
  const [sources, setSources] = useState<SourceStatus[]>([])
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = useMemo(() => async () => {
    setLoading(true)
    try {
      const [sourcesData, schedulerData] = await Promise.all([
        get<SourceStatus[]>('/discovery/v2/sources'),
        get<SchedulerStatus>('/discovery/v2/scheduler'),
      ])
      setSources(sourcesData)
      setScheduler(schedulerData)
    } catch {
      pushToast({ title: 'Could not load discovery status', tone: 'danger' })
    } finally {
      setLoading(false)
    }
  }, [pushToast])

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [load])

  const handleRun = async () => {
    setRunning(true)
    try {
      const result = await post<{ total_found: number; imported: number; duplicates: number }>('/discovery/v2/run', {})
      pushToast({
        title: 'Discovery completed',
        body: `Found ${result.total_found} jobs, ${result.imported} new, ${result.duplicates} duplicates`,
        tone: 'accent',
      })
      await load()
    } catch {
      pushToast({ title: 'Discovery run failed', tone: 'danger' })
    } finally {
      setRunning(false)
    }
  }

  const healthColor = (status: string) => {
    switch (status) {
      case 'HEALTHY': return 'accent'
      case 'DEGRADED': return 'warn'
      case 'BLOCKED': return 'danger'
      case 'RATE_LIMITED': return 'warn'
      case 'AUTH_REQUIRED': return 'warn'
      case 'UNAVAILABLE': return 'danger'
      default: return 'neutral'
    }
  }

  const enabledSources = sources.filter(s => s.enabled).length
  const healthySources = sources.filter(s => s.health_status === 'HEALTHY').length
  const totalNew = sources.reduce((sum, s) => sum + s.new_jobs, 0)
  const totalDuplicates = sources.reduce((sum, s) => sum + s.duplicates, 0)

  if (loading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Discovery" description="Multi-source job search engine." />
        <Card className="h-40 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Discovery"
        description="Multi-source job search engine with aggressive deduplication."
        actions={
          <Button
            size="sm"
            variant="primary"
            icon={<Play size={14} />}
            loading={running}
            onClick={handleRun}
          >
            Search now
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Registered sources" value={sources.length} />
        <MetricCard label="Active sources" value={enabledSources} />
        <MetricCard label="Healthy" value={healthySources} />
        <MetricCard label="New jobs (total)" value={totalNew} />
      </div>

      <Card>
        <CardHeader title="Scheduler" description="Automatic discovery schedule." />
        <div className="flex items-center justify-between p-4">
          <div>
            <p className="text-sm font-medium text-fg">
              {scheduler?.enabled ? 'Active' : 'Paused'}
            </p>
            <p className="text-xs text-fg-muted">
              {scheduler?.enabled
                ? `Every ${scheduler.frequency_minutes}m`
                : 'Automatic search is disabled'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {scheduler?.last_run && (
              <span className="text-xs text-fg-muted">
                Last: {relativeTime(scheduler.last_run)}
              </span>
            )}
            <Badge tone={scheduler?.running ? 'accent' : 'neutral'}>
              {scheduler?.running ? 'Running' : 'Idle'}
            </Badge>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Sources"
          description={`${sources.length} registered · ${enabledSources} enabled · ${totalDuplicates} duplicates removed`}
        />
        {sources.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={<Globe size={22} />}
              title="No sources configured"
              description="Add job sources to start discovering jobs."
            />
          </div>
        ) : (
          <div className="divide-y divide-line">
            {sources.map((source) => (
              <div key={source.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-fg">{source.source_name}</p>
                  <p className="text-xs text-fg-muted">
                    {source.adapter} · {source.schedule} · Found: {source.jobs_found} · New: {source.new_jobs}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={healthColor(source.health_status)}>
                    {source.health_status.replace(/_/g, ' ')}
                  </Badge>
                  <Toggle
                    checked={source.enabled}
                    onChange={async (v) => {
                       await post(`/discovery/v2/sources/${source.id}`, { enabled: v })
                      pushToast({ title: v ? 'Source enabled' : 'Source disabled', tone: 'accent' })
                      await load()
                    }}
                    label=""
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
