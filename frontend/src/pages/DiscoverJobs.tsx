import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Bookmark,
  LayoutGrid,
  RefreshCw,
  Rows3,
  Search,
  SlidersHorizontal,
  Sparkles,
  Target,
  X,
} from 'lucide-react'
import { get, patch, post } from '../services/api'
import type { Job } from '../types'
import { useAppStore } from '../store/useAppStore'
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  SkeletonCards,
  cx,
  snippet,
} from '../components/ui'
import { DetailDrawer } from '../components/ui/DetailDrawer'
import { CompanyMark, MatchScore } from '../components/ui/data-display'
import { JobCard, JobTable } from '../components/jobs/JobCard'

interface SourceConfig {
  kind: string
  url: string
  company?: string
  name?: string
}

const SOURCE_LABELS: Record<string, string> = {
  greenhouse: 'Greenhouse',
  lever: 'Lever',
  ashby: 'Ashby',
  rss: 'RSS',
  json: 'JSON',
}

type ViewMode = 'cards' | 'table'

export default function DiscoverJobs() {
  const [searchParams] = useSearchParams()
  const pushToast = useAppStore((s) => s.pushToast)
  const navigate = useNavigate()

  const [items, setItems] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const [companyFilter, setCompanyFilter] = useState('')
  const [companies, setCompanies] = useState<string[]>([])
  const [sort, setSort] = useState<'recent' | 'match' | 'salary' | 'company' | 'title'>('recent')
  const [minScore, setMinScore] = useState('')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [savedOnly, setSavedOnly] = useState(false)
  const [view, setView] = useState<ViewMode>('cards')
  const [limit, setLimit] = useState(24)
  const [filtersOpen, setFiltersOpen] = useState(false)

  const [selected, setSelected] = useState<Job | null>(null)
  const [scoringId, setScoringId] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [bulkScoring, setBulkScoring] = useState(false)

  const [sources, setSources] = useState<SourceConfig[]>([])
  const [selectedSources, setSelectedSources] = useState<Record<string, boolean>>({})
  const [discovering, setDiscovering] = useState(false)

  const queryString = useCallback(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (companyFilter) params.set('company', companyFilter)
    if (minScore) params.set('min_score', minScore)
    if (remoteOnly) params.set('remote', 'true')
    if (savedOnly) params.set('saved', 'true')
    params.set('sort', sort)
    params.set('limit', String(limit))
    return params.toString()
  }, [search, companyFilter, minScore, remoteOnly, savedOnly, sort, limit])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = queryString()
      const [rows, countData] = await Promise.all([
        get<Job[]>(`/jobs/?${qs}`),
        get<{ total: number }>(`/jobs/count?${qs}`),
      ])
      setItems(rows)
      setTotal(countData.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }, [queryString])

  useEffect(() => {
    const timer = setTimeout(load, search || companyFilter ? 300 : 0)
    return () => clearTimeout(timer)
  }, [load, search, companyFilter])

  useEffect(() => {
    setLimit(24)
  }, [search, companyFilter, minScore, remoteOnly, savedOnly, sort])

  useEffect(() => {
    get<string[]>('/jobs/companies').then(setCompanies).catch(() => setCompanies([]))
    fetch('/api/discovery/sources')
      .then((res) => res.json())
      .then((data: { sources: SourceConfig[] }) => {
        setSources(data.sources || [])
        setSelectedSources(Object.fromEntries((data.sources || []).map((s) => [s.url, true])))
      })
      .catch(() => setSources([]))
  }, [])

  const hasFilters = !!(search.trim() || companyFilter || minScore || remoteOnly || savedOnly)

  const handleScore = async (jobId: string) => {
    setScoringId(jobId)
    try {
      await post(`/matching/score/${jobId}`)
      await load()
      pushToast({ title: 'Job scored', tone: 'accent' })
    } catch (err) {
      pushToast({
        title: 'Scoring failed',
        body: err instanceof Error ? err.message : undefined,
        tone: 'danger',
      })
    } finally {
      setScoringId(null)
    }
  }

  const handleSave = async (jobId: string, saved: boolean) => {
    setSavingId(jobId)
    setItems((prev) => prev.map((j) => (j.id === jobId ? { ...j, is_saved: saved } : j)))
    setSelected((prev) => (prev && prev.id === jobId ? { ...prev, is_saved: saved } : prev))
    try {
      await patch(`/jobs/${jobId}`, { is_saved: saved })
      pushToast({ title: saved ? 'Job saved' : 'Job removed from saved', tone: 'accent' })
      if (savedOnly && !saved) load()
    } catch {
      setItems((prev) => prev.map((j) => (j.id === jobId ? { ...j, is_saved: !saved } : j)))
      pushToast({ title: 'Could not update this job', tone: 'danger' })
    } finally {
      setSavingId(null)
    }
  }

  const handleSaveFromTable = (job: Job, saved: boolean) => handleSave(job.id, saved)

  /** Sends the user to the preparation flow; nothing is ever submitted for them. */
  const handleApply = (jobId: string) => {
    navigate(`/apply?job=${encodeURIComponent(jobId)}`)
  }

  const handleDiscover = async () => {
    const chosen = sources.filter((s) => selectedSources[s.url])
    if (chosen.length === 0) {
      pushToast({ title: 'Select at least one source', tone: 'warn' })
      return
    }
    setDiscovering(true)
    try {
      const result = await post<{ imported: number; duplicates: number }>('/discovery/run', {
        sources: chosen,
      })
      await load()
      pushToast({
        title: `Imported ${result.imported} new job${result.imported === 1 ? '' : 's'}`,
        body: `${result.duplicates} duplicates skipped.`,
        tone: 'accent',
      })
    } catch (err) {
      pushToast({
        title: 'Discovery failed',
        body: err instanceof Error ? err.message : undefined,
        tone: 'danger',
      })
    } finally {
      setDiscovering(false)
    }
  }

  const handleScoreAll = async () => {
    if (items.length === 0) return
    setBulkScoring(true)
    try {
      const result = await post<{ scored: number }>('/discovery/score', {
        job_ids: items.map((j) => j.id),
        limit: 500,
      })
      await load()
      pushToast({ title: `Scored ${result.scored} jobs`, tone: 'accent' })
    } catch (err) {
      pushToast({
        title: 'Scoring failed',
        body: err instanceof Error ? err.message : undefined,
        tone: 'danger',
      })
    } finally {
      setBulkScoring(false)
    }
  }

  const activeFilterCount =
    (minScore ? 1 : 0) + (remoteOnly ? 1 : 0) + (savedOnly ? 1 : 0) + (companyFilter ? 1 : 0)

  return (
    <div className="space-y-4">
      <PageHeader
        title="Discover Jobs"
        description="Search live job boards, then score roles against your profile."
        actions={
          <>
            <Button size="sm" icon={<RefreshCw size={14} />} onClick={load} loading={loading}>
              Refresh
            </Button>
            <Button
              size="sm"
              variant="primary"
              icon={<Target size={14} />}
              loading={bulkScoring}
              onClick={handleScoreAll}
            >
              Score all shown
            </Button>
          </>
        }
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <Card className="p-4">
        <div className="flex flex-col gap-2 lg:flex-row">
          <div className="relative flex-1">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search title, company, location, skills or description..."
              className="pl-9"
              aria-label="Search jobs"
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
            <Button
              size="md"
              icon={<SlidersHorizontal size={14} />}
              onClick={() => setFiltersOpen((v) => !v)}
              className={cx(filtersOpen && 'border-accent text-accent')}
            >
              Filters
              {activeFilterCount > 0 && (
                <span className="ml-1 rounded-full bg-accent px-1.5 text-2xs text-accent-fg">
                  {activeFilterCount}
                </span>
              )}
            </Button>
            <Select
              value={sort}
              onChange={(e) => setSort(e.target.value as typeof sort)}
              className="w-44"
              aria-label="Sort jobs"
            >
              <option value="recent">Newest first</option>
              <option value="match">Best match</option>
              <option value="salary">Highest salary</option>
              <option value="company">Company A–Z</option>
              <option value="title">Title A–Z</option>
            </Select>
            <div className="hidden items-center rounded-lg border border-line p-0.5 sm:flex">
              {(['cards', 'table'] as ViewMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setView(mode)}
                  aria-pressed={view === mode}
                  aria-label={`${mode} view`}
                  className={cx(
                    'rounded-md p-1.5 transition-colors',
                    view === mode ? 'bg-surface-sunken text-fg' : 'text-fg-subtle hover:text-fg',
                  )}
                >
                  {mode === 'cards' ? <LayoutGrid size={14} /> : <Rows3 size={14} />}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filtersOpen && (
          <div className="mt-4 grid grid-cols-1 gap-3 border-t border-line pt-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Company">
              <Select value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)}>
                <option value="">All companies</option>
                {companies.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Minimum match">
              <Select value={minScore} onChange={(e) => setMinScore(e.target.value)}>
                <option value="">Any</option>
                <option value="70">70%+</option>
                <option value="50">50%+</option>
                <option value="25">25%+</option>
                <option value="1">Scored only</option>
              </Select>
            </Field>
            <Field label="Work mode">
              <Select
                value={remoteOnly ? 'remote' : 'any'}
                onChange={(e) => setRemoteOnly(e.target.value === 'remote')}
              >
                <option value="any">Any</option>
                <option value="remote">Remote only</option>
              </Select>
            </Field>
            <Field label="Saved">
              <Select
                value={savedOnly ? 'saved' : 'all'}
                onChange={(e) => setSavedOnly(e.target.value === 'saved')}
              >
                <option value="all">All jobs</option>
                <option value="saved">Saved only</option>
              </Select>
            </Field>
            {hasFilters && (
              <div className="sm:col-span-2 lg:col-span-4">
                <Button
                  size="sm"
                  variant="ghost"
                  icon={<X size={12} />}
                  onClick={() => {
                    setSearch('')
                    setCompanyFilter('')
                    setMinScore('')
                    setRemoteOnly(false)
                    setSavedOnly(false)
                  }}
                >
                  Clear all filters
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>

      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-fg-muted">Sources</span>
            {sources.map((source) => {
              const active = !!selectedSources[source.url]
              return (
                <button
                  key={source.url}
                  onClick={() => setSelectedSources((p) => ({ ...p, [source.url]: !p[source.url] }))}
                  aria-pressed={active}
                  className={cx(
                    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-2xs font-medium transition-colors',
                    active
                      ? 'border-accent bg-accent-soft text-accent'
                      : 'border-line bg-surface text-fg-muted hover:border-line-strong hover:text-fg',
                  )}
                >
                  {source.company || source.name}
                  <span className="opacity-60">{SOURCE_LABELS[source.kind] ?? source.kind}</span>
                </button>
              )
            })}
          </div>
          <Button size="sm" variant="primary" loading={discovering} onClick={handleDiscover}>
            Discover jobs
          </Button>
        </div>
      </Card>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-fg-muted">
          {loading ? 'Loading…' : `Showing ${items.length} of ${total} jobs`}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSavedOnly((v) => !v)}
            aria-pressed={savedOnly}
            className={cx(
              'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
              savedOnly
                ? 'border-accent bg-accent-soft text-accent'
                : 'border-line bg-surface text-fg-muted hover:border-line-strong hover:text-fg',
            )}
          >
            <Bookmark size={12} fill={savedOnly ? 'currentColor' : 'none'} />
            Saved only
          </button>
          <button
            onClick={() => setRemoteOnly((v) => !v)}
            aria-pressed={remoteOnly}
            className={cx(
              'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
              remoteOnly
                ? 'border-accent bg-accent-soft text-accent'
                : 'border-line bg-surface text-fg-muted hover:border-line-strong hover:text-fg',
            )}
          >
            Remote only
          </button>
        </div>
      </div>

      {loading ? (
        <SkeletonCards count={6} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Search size={26} />}
          title={hasFilters ? 'No jobs match your filters' : 'No jobs yet'}
          description={
            hasFilters
              ? 'Try widening your filters or clearing the search.'
              : 'Click "Discover jobs" to pull live roles from the selected boards.'
          }
          action={
            hasFilters ? (
              <Button
                size="sm"
                onClick={() => {
                  setSearch('')
                  setCompanyFilter('')
                  setMinScore('')
                  setRemoteOnly(false)
                  setSavedOnly(false)
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Button size="sm" variant="primary" onClick={handleDiscover} loading={discovering}>
                Discover jobs
              </Button>
            )
          }
        />
      ) : view === 'cards' ? (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {items.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                scoring={scoringId === job.id || savingId === job.id}
                onScore={handleScore}
                onSave={handleSave}
                onApply={handleApply}
                onOpen={() => setSelected(job)}
              />
            ))}
          </div>
          {total > items.length && (
            <div className="flex justify-center pt-2">
              <Button loading={loading} onClick={() => setLimit((n) => n + 24)}>
                Load more ({total - items.length} remaining)
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          <JobTable jobs={items} onOpen={setSelected} onSave={handleSaveFromTable} />
          {total > items.length && (
            <div className="flex justify-center pt-2">
              <Button loading={loading} onClick={() => setLimit((n) => n + 24)}>
                Load more ({total - items.length} remaining)
              </Button>
            </div>
          )}
        </>
      )}

      <DetailDrawer
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.title ?? ''}
        subtitle={selected?.company ?? ''}
        width="lg"
        footer={
          <>
            {selected?.url && (
              <a
                href={selected.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-8 items-center rounded-lg border border-line px-3 text-xs text-fg-muted transition-colors hover:text-fg"
              >
                Original posting
              </a>
            )}
            <Button
              size="sm"
              icon={<Sparkles size={13} />}
              loading={scoringId === selected?.id}
              onClick={() => selected && handleScore(selected.id)}
            >
              Score
            </Button>
            <Button size="sm" onClick={() => selected && handleSave(selected.id, !selected.is_saved)}>
              {selected?.is_saved ? 'Unsave' : 'Save job'}
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={() => selected && handleApply(selected.id)}
            >
              Prepare application
            </Button>
          </>
        }
      >
        {selected && (
          <div className="space-y-5">
            <div className="flex items-start gap-3">
              <CompanyMark name={selected.company} size={44} />
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-fg">{selected.title}</h3>
                <p className="mt-0.5 text-xs text-fg-muted">{selected.company}</p>
              </div>
              <MatchScore score={selected.match_score} size={46} />
            </div>

            <div className="flex flex-wrap gap-1.5">
              {selected.source && <Badge tone="neutral">{selected.source}</Badge>}
              {selected.remote && <Badge tone="accent">Remote</Badge>}
              {selected.location && <Badge tone="neutral">{selected.location}</Badge>}
            </div>

            {selected.match_score != null && (
              <section>
                <h4 className="mb-2 text-xs font-semibold text-fg">Why this scored {selected.match_score}%</h4>
                {Array.isArray(selected.match_evidence) && selected.match_evidence.length > 0 ? (
                  <ul className="space-y-1">
                    {selected.match_evidence.map((item, i) => (
                      <li key={i} className="flex gap-2 text-xs leading-relaxed text-fg-muted">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-fg-subtle">
                    No explanation recorded yet. Run a score to generate one.
                  </p>
                )}
              </section>
            )}

            <section>
              <h4 className="mb-2 text-xs font-semibold text-fg">Job description</h4>
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-fg-muted">
                {snippet(selected.description, 4000) || 'No description available.'}
              </p>
            </section>

            <div className="rounded-lg border border-warn/20 bg-warn-soft p-3">
              <p className="text-xs leading-relaxed text-warn">
                <strong className="font-medium">Human-in-the-loop:</strong> NS prepares
                applications for your review. Nothing is ever submitted on your behalf.
              </p>
            </div>
          </div>
        )}
      </DetailDrawer>
    </div>
  )
}