import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  KanbanSquare,
  LayoutGrid,
  Search,
  Rows3,
  X,
} from 'lucide-react'
import { get, patch } from '../services/api'
import type { Application } from '../types'
import {
  APPLICATION_STAGES,
  STAGE_LABELS,
  type ApplicationStage,
} from '../data/mock'
import { useAppStore } from '../store/useAppStore'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  PageHeader,
  Select,
  cx,
  relativeTime,
} from '../components/ui'
import { DetailDrawer } from '../components/ui/DetailDrawer'
import { CompanyMark, MatchScore, StatusBadge } from '../components/ui/data-display'
import { ApplicationCard, KanbanColumn } from '../components/applications/ApplicationCard'

export default function Applications() {
  const pushToast = useAppStore((s) => s.pushToast)
  const setStage = useAppStore((s) => s.setStage)

  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [view, setView] = useState<'board' | 'table'>('board')
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState<ApplicationStage | ''>('')
  const [dragOver, setDragOver] = useState<ApplicationStage | null>(null)
  const [selected, setSelected] = useState<Application | null>(null)
  const [selection, setSelection] = useState<Set<string>>(new Set())

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setApplications(await get<Application[]>('/applications/'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load applications')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return applications.filter((app) => {
      if (stageFilter && app.status !== stageFilter) return false
      if (!term) return true
      return (
        (app.company ?? '').toLowerCase().includes(term) ||
        (app.job_title ?? '').toLowerCase().includes(term)
      )
    })
  }, [applications, search, stageFilter])

  const byStage = useMemo(() => {
    const map = new Map<ApplicationStage, Application[]>()
    for (const stage of APPLICATION_STAGES) map.set(stage, [])
    for (const app of filtered) {
      const stage = (app.status || 'discovered') as ApplicationStage
      if (!map.has(stage)) map.set(stage, [])
      map.get(stage)!.push(app)
    }
    return map
  }, [filtered])

  /** Optimistic stage change with rollback if the API rejects it. */
  const updateStage = useCallback(
    async (app: Application, stage: ApplicationStage) => {
      if ((app.status || 'discovered') === stage) return
      const previous = app.status
      setApplications((prev) =>
        prev.map((a) => (a.id === app.id ? { ...a, status: stage } : a)),
      )
      setStage(app.id, stage)
      setSelected((prev) => (prev && prev.id === app.id ? { ...prev, status: stage } : prev))
      try {
        await patch(`/applications/${app.id}`, { status: stage })
        pushToast({
          title: 'Stage updated',
          body: `${app.company} → ${STAGE_LABELS[stage]}`,
          tone: 'accent',
        })
      } catch {
        setApplications((prev) =>
          prev.map((a) => (a.id === app.id ? { ...a, status: previous } : a)),
        )
        pushToast({ title: 'Could not update the stage', tone: 'danger' })
      }
    },
    [pushToast, setStage],
  )

  const draggingIdRef = useRef<string | null>(null)

  const onDropStage = useCallback(
    (stage: ApplicationStage) => {
      const id = draggingIdRef.current
      setDragOver(null)
      draggingIdRef.current = null
      if (!id) return
      const app = applications.find((a) => a.id === id)
      if (app) updateStage(app, stage)
    },
    [applications, updateStage],
  )

  const toggleSelect = (id: string) => {
    setSelection((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const bulkSetStage = async (stage: ApplicationStage) => {
    const ids = Array.from(selection)
    if (ids.length === 0) return
    for (const id of ids) {
      const app = applications.find((a) => a.id === id)
      if (app) await updateStage(app, stage)
    }
    setSelection(new Set())
  }

  const hasFilters = !!search.trim() || !!stageFilter

  return (
    <div className="space-y-4">
      <PageHeader
        title="Applications"
        description="Track every role from discovery through to offer."
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <Card className="p-4">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search company or role..."
              className="pl-9"
              aria-label="Search applications"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-fg-subtle hover:text-fg"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <Select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value as ApplicationStage | '')}
              className="w-44"
              aria-label="Filter by stage"
            >
              <option value="">All stages</option>
              {APPLICATION_STAGES.map((stage) => (
                <option key={stage} value={stage}>
                  {STAGE_LABELS[stage]}
                </option>
              ))}
            </Select>
            <div className="flex items-center rounded-lg border border-line p-0.5">
              {(
                [
                  { key: 'board' as const, icon: KanbanSquare, label: 'Board view' },
                  { key: 'table' as const, icon: Rows3, label: 'Table view' },
                ]
              ).map((mode) => (
                <button
                  key={mode.key}
                  onClick={() => setView(mode.key)}
                  aria-pressed={view === mode.key}
                  aria-label={mode.label}
                  className={cx(
                    'rounded-md p-1.5 transition-colors',
                    view === mode.key ? 'bg-surface-sunken text-fg' : 'text-fg-subtle hover:text-fg',
                  )}
                >
                  <mode.icon size={14} />
                </button>
              ))}
            </div>
          </div>
        </div>

        {selection.size > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
            <Badge tone="accent">{selection.size} selected</Badge>
            <Select
              value=""
              onChange={(e) => {
                if (e.target.value) bulkSetStage(e.target.value as ApplicationStage)
              }}
              className="h-8 w-44"
              aria-label="Bulk change stage"
            >
              <option value="">Move selected to…</option>
              {APPLICATION_STAGES.map((stage) => (
                <option key={stage} value={stage}>
                  {STAGE_LABELS[stage]}
                </option>
              ))}
            </Select>
            <Button size="sm" variant="ghost" onClick={() => setSelection(new Set())}>
              Clear selection
            </Button>
          </div>
        )}
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {APPLICATION_STAGES.slice(0, 4).map((stage) => (
            <Card key={stage} className="h-40 animate-pulse" />
          ))}
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          icon={<LayoutGrid size={26} />}
          title="No applications yet"
          description="Prepare an application from a job to start tracking it here."
        />
      ) : hasFilters && filtered.length === 0 ? (
        <EmptyState
          icon={<Search size={26} />}
          title="No applications match your filters"
          action={
            <Button
              size="sm"
              onClick={() => {
                setSearch('')
                setStageFilter('')
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : view === 'board' ? (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {APPLICATION_STAGES.map((stage) => {
            const list = byStage.get(stage) ?? []
            if (stageFilter && stage !== stageFilter) return null
            return (
              <KanbanColumn
                key={stage}
                stage={stage}
                label={STAGE_LABELS[stage]}
                count={list.length}
                isOver={dragOver === stage}
                onDropStage={onDropStage}
              >
                {list.length === 0 ? (
                  <p className="px-2 py-6 text-center text-2xs text-fg-subtle">
                    {dragOver === stage ? 'Drop here' : 'Nothing here'}
                  </p>
                ) : (
                  list.map((app) => (
                    <div
                      key={app.id}
                      draggable
                      onDragStart={() => {
                        draggingIdRef.current = app.id
                      }}
                      onDragEnd={() => {
                        draggingIdRef.current = null
                        setDragOver(null)
                      }}
                    >
                      <ApplicationCard
                        application={app}
                        score={app.match_score}
                        onOpen={() => setSelected(app)}
                        selected={selection.has(app.id)}
                        onToggleSelect={() => toggleSelect(app.id)}
                      />
                    </div>
                  ))
                )}
              </KanbanColumn>
            )
          })}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-sunken text-fg-subtle">
              <tr>
                <th className="w-10 px-3 py-2" />
                <th className="px-3 py-2 font-medium">Role</th>
                <th className="px-3 py-2 font-medium">Company</th>
                <th className="px-3 py-2 font-medium">Stage</th>
                <th className="px-3 py-2 font-medium">Match</th>
                <th className="hidden px-3 py-2 font-medium lg:table-cell">Follow-up</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((app) => (
                <tr
                  key={app.id}
                  onClick={() => setSelected(app)}
                  className="cursor-pointer border-t border-line bg-surface-raised transition-colors hover:bg-surface-sunken/60"
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selection.has(app.id)}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => toggleSelect(app.id)}
                      aria-label={`Select ${app.job_title}`}
                      className="h-3.5 w-3.5 rounded border-line accent-[rgb(var(--accent))]"
                    />
                  </td>
                  <td className="max-w-[14rem] truncate px-3 py-2 font-medium text-fg">
                    {app.job_title}
                  </td>
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-2">
                      <CompanyMark name={app.company} size={22} />
                      <span className="truncate text-fg-muted">{app.company}</span>
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge stage={(app.status || 'discovered') as ApplicationStage} />
                  </td>
                  <td className="px-3 py-2">
                    <MatchScore score={app.match_score} size={26} />
                  </td>
                  <td className="hidden px-3 py-2 text-fg-muted lg:table-cell">
                    {app.follow_up_date ? relativeTime(app.follow_up_date) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DetailDrawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.job_title ?? ''}
        subtitle={selected?.company ?? ''}
        footer={
          <Button size="sm" onClick={() => setSelected(null)}>
            Close
          </Button>
        }
      >
        {selected && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <CompanyMark name={selected.company} size={40} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-fg">{selected.company}</p>
                <p className="truncate text-xs text-fg-muted">{selected.job_title}</p>
              </div>
              <MatchScore score={selected.match_score} size={42} />
            </div>

            <section>
              <h4 className="mb-2 text-xs font-semibold text-fg">Stage</h4>
              <Select
                value={(selected.status || 'discovered') as ApplicationStage}
                onChange={(e) => updateStage(selected, e.target.value as ApplicationStage)}
                aria-label="Change stage"
              >
                {APPLICATION_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {STAGE_LABELS[stage]}
                  </option>
                ))}
              </Select>
            </section>

            {selected.job_url && (
              <section>
                <h4 className="mb-1.5 text-xs font-semibold text-fg">Job URL</h4>
                <a
                  href={selected.job_url}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all text-xs text-accent hover:underline"
                >
                  {selected.job_url}
                </a>
              </section>
            )}

            {selected.cover_letter && (
              <section>
                <h4 className="mb-1.5 text-xs font-semibold text-fg">Cover letter</h4>
                <pre className="whitespace-pre-wrap rounded-lg bg-surface-sunken p-3 text-xs leading-relaxed text-fg-muted">
                  {selected.cover_letter}
                </pre>
              </section>
            )}

            <section>
              <h4 className="mb-1.5 text-xs font-semibold text-fg">Notes</h4>
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-fg-muted">
                {selected.notes || 'No notes yet.'}
              </p>
            </section>
          </div>
        )}
      </DetailDrawer>
    </div>
  )
}