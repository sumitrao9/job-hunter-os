import { useCallback, useEffect, useState } from 'react'
import { Bell, CalendarClock } from 'lucide-react'
import { get } from '../services/api'
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  LoadingBlock,
  PageHeader,
} from '../components/ui'

interface FollowUp {
  id: string
  company: string
  job_title: string
  follow_up_date: string | null
  status: string
}

function daysUntil(date: string | null): number | null {
  if (!date) return null
  const target = new Date(`${date}T00:00:00`)
  if (Number.isNaN(target.getTime())) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((target.getTime() - today.getTime()) / 86400000)
}

function dueTone(days: number | null): 'danger' | 'warn' | 'info' | 'neutral' {
  if (days === null) return 'neutral'
  if (days < 0) return 'danger'
  if (days <= 3) return 'warn'
  return 'info'
}

function dueLabel(days: number | null): string {
  if (days === null) return 'No date'
  if (days < 0) return `${Math.abs(days)}d overdue`
  if (days === 0) return 'Due today'
  if (days === 1) return 'Due tomorrow'
  return `in ${days}d`
}

export default function FollowUps() {
  const [items, setItems] = useState<FollowUp[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setItems(await get<FollowUp[]>('/follow-ups/'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load follow-ups')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-5">
      <PageHeader
        title="Follow-ups"
        description="Upcoming follow-up dates from your active applications."
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      {loading ? (
        <LoadingBlock label="Loading follow-ups" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Bell size={26} />}
          title="No upcoming follow-ups"
          description="Set a follow-up date on an application and it will appear here."
        />
      ) : (
        <div className="space-y-2">
          {items.map((item) => {
            const days = daysUntil(item.follow_up_date)
            return (
              <Card key={item.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-fg">
                    {item.job_title || 'Untitled role'}
                  </h3>
                  <p className="mt-0.5 truncate text-sm text-fg-muted">{item.company}</p>
                  <p className="mt-1 flex items-center gap-1 text-xs text-fg-subtle">
                    <CalendarClock size={12} />
                    {item.follow_up_date || 'No follow-up date set'}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge tone="neutral" className="capitalize">
                    {item.status}
                  </Badge>
                  <Badge tone={dueTone(days)}>{dueLabel(days)}</Badge>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}