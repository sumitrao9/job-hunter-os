import type { Application } from '../../types'
import { STAGE_LABELS, type ApplicationStage } from '../../data/mock'
import { relativeTime, Badge, cx } from '../ui'
import { CompanyMark, MatchScore, StatusBadge } from '../ui/data-display'

export function ApplicationCard({
  application,
  score,
  draggable,
  onOpen,
  onDragStart,
  onDragEnd,
  selected,
  onToggleSelect,
}: {
  application: Application
  score?: number | null
  draggable?: boolean
  onOpen: () => void
  onDragStart?: () => void
  onDragEnd?: () => void
  selected?: boolean
  onToggleSelect?: () => void
}) {
  return (
    <article
      draggable={draggable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onOpen}
      className={cx(
        'group cursor-pointer rounded-lg border bg-surface-raised p-3 shadow-xs transition-all duration-150',
        'hover:border-line-strong hover:shadow-sm',
        selected ? 'border-accent ring-1 ring-accent/30' : 'border-line',
      )}
    >
      <div className="flex items-start gap-2.5">
        {onToggleSelect && (
          <input
            type="checkbox"
            checked={!!selected}
            onClick={(e) => e.stopPropagation()}
            onChange={onToggleSelect}
            aria-label={`Select ${application.job_title} at ${application.company}`}
            className="mt-1 h-3.5 w-3.5 shrink-0 rounded border-line accent-[rgb(var(--accent))]"
          />
        )}
        <CompanyMark name={application.company} size={28} />
        <div className="min-w-0 flex-1">
          <h4 className="truncate text-xs font-semibold text-fg" title={application.job_title}>
            {application.job_title || 'Untitled role'}
          </h4>
          <p className="truncate text-xs text-fg-muted">{application.company || 'Unknown'}</p>
        </div>
        <MatchScore score={score} size={30} />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <StatusBadge stage={(application.status || 'discovered') as ApplicationStage} />
        {application.follow_up_date && (
          <Badge tone="warn">
            <span aria-hidden="true">◷</span> {relativeTime(application.follow_up_date)}
          </Badge>
        )}
      </div>

      <p className="mt-2 text-2xs text-fg-subtle">
        {application.status === 'discovered'
          ? `Found ${relativeTime(application.follow_up_date) === '' ? 'recently' : relativeTime(application.follow_up_date)}`
          : `Updated ${relativeTime(application.created_at as unknown as string)}`}
      </p>
    </article>
  )
}

export function KanbanColumn({
  stage,
  label,
  children,
  count,
  onDropStage,
  isOver,
}: {
  stage: ApplicationStage
  label: string
  children: React.ReactNode
  count: number
  onDropStage: (stage: ApplicationStage) => void
  isOver: boolean
}) {
  return (
    <section
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
      }}
      onDrop={(e) => {
        e.preventDefault()
        onDropStage(stage)
      }}
      aria-label={`${label} column, ${count} applications`}
      className={cx(
        'flex w-[260px] shrink-0 flex-col rounded-xl border bg-surface/60 transition-colors',
        isOver ? 'border-accent bg-accent-soft/40' : 'border-line',
      )}
    >
      <header className="flex items-center justify-between gap-2 border-b border-line px-3 py-2.5">
        <h3 className="text-xs font-semibold text-fg">{label}</h3>
        <span className="tabular rounded-full bg-surface-sunken px-1.5 py-0.5 text-2xs text-fg-muted">
          {count}
        </span>
      </header>
      <div className="flex-1 space-y-2 overflow-y-auto p-2">{children}</div>
    </section>
  )
}

export { STAGE_LABELS }