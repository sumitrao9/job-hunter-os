import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bookmark,
  Download,
  FileJson,
  Link2,
  Radar,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Target,
  X,
} from 'lucide-react'
import { get, patch, post } from '../services/api'
import type { Job } from '../types'
import { JobCard } from '../components/jobs/JobCard'
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  SkeletonCards,
  Textarea,
  cx,
} from '../components/ui'

interface SourceConfig {
  kind: string
  url: string
  company?: string
  name?: string
}

interface DiscoveryResult {
  imported: number
  duplicates: number
  jobs?: Job[]
}

const SOURCE_LABELS: Record<string, string> = {
  greenhouse: 'Greenhouse',
  lever: 'Lever',
  ashby: 'Ashby',
  rss: 'RSS',
  json: 'JSON',
}

export default function Jobs() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [companyFilter, setCompanyFilter] = useState('')
  const [companies, setCompanies] = useState<string[]>([])

  const [sources, setSources] = useState<SourceConfig[]>([])
  const [sourcesLoading, setSourcesLoading] = useState(true)
  const [selectedSources, setSelectedSources] = useState<Record<string, boolean>>({})
  const [discovering, setDiscovering] = useState(false)
  const [bulkScoring, setBulkScoring] = useState(false)
  const [scoreMessage, setScoreMessage] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<DiscoveryResult | null>(null)

  const [sort, setSort] = useState<'recent' | 'match' | 'salary' | 'company' | 'title'>('recent')
  const [minScore, setMinScore] = useState('')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [savedOnly, setSavedOnly] = useState(false)
  const [total, setTotal] = useState(0)
  const [limit, setLimit] = useState(24)

  const [importText, setImportText] = useState('')
  const [importing, setImporting] = useState(false)
  const [scoringId, setScoringId] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)

  const searchRef = useRef<HTMLInputElement>(null)

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

  // Search runs server-side so it covers every stored job, not just the first page.
  useEffect(() => {
    const timer = setTimeout(load, search || companyFilter ? 300 : 0)
    return () => clearTimeout(timer)
  }, [load, search, companyFilter])

  // Narrowing filters should always return to the first page of results.
  useEffect(() => {
    setLimit(24)
  }, [search, companyFilter, minScore, remoteOnly, savedOnly, sort])

  // Sources come from the backend so the UI never drifts from what actually works.
  useEffect(() => {
    let cancelled = false
    fetch('/api/discovery/sources')
      .then((res) => res.json())
      .then((data: { sources: SourceConfig[] }) => {
        if (cancelled) return
        setSources(data.sources || [])
        setSelectedSources(Object.fromEntries((data.sources || []).map((s) => [s.url, true])))
      })
      .catch(() => {
        if (!cancelled) setError('Could not load job sources from the server.')
      })
      .finally(() => {
        if (!cancelled) setSourcesLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    get<string[]>('/jobs/companies')
      .then(setCompanies)
      .catch(() => setCompanies([]))
  }, [])

  const filtered = items
  const hasFilters = !!(search.trim() || companyFilter)

  const handleDiscover = async () => {
    const chosen = sources.filter((s) => selectedSources[s.url])
    if (chosen.length === 0) {
      setError('Select at least one job source to discover from.')
      return
    }
    setDiscovering(true)
    setError(null)
    setLastResult(null)
    try {
      const result = await post<DiscoveryResult>('/discovery/run', { sources: chosen })
      setLastResult(result)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Discovery failed')
    } finally {
      setDiscovering(false)
    }
  }

  const handleImport = async () => {
    const urls = importText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    if (urls.length === 0) {
      setError('Paste at least one job link first.')
      return
    }
    setImporting(true)
    setError(null)
    try {
      await post('/jobs/import', { jobs: urls.map((url) => ({ url })) })
      setImportText('')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  const handleScore = async (jobId: string) => {
    setScoringId(jobId)
    setError(null)
    try {
      await post(`/matching/score/${jobId}`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scoring failed')
    } finally {
      setScoringId(null)
    }
  }

  // Scoring one job at a time is impractical once discovery has imported
  // thousands of postings, so the whole visible list can be scored in one call.
  const handleScoreAll = async () => {
    if (!filtered.length) return
    setBulkScoring(true)
    setError(null)
    try {
      const ids = filtered.map((j) => j.id)
      const result = await post<{ scored: number; message: string }>('/discovery/score', {
        job_ids: ids,
        limit: 500,
      })
      await load()
      setScoreMessage(
        `Scored ${result.scored} job${result.scored === 1 ? '' : 's'} against your profile.`,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scoring failed')
    } finally {
      setBulkScoring(false)
    }
  }

  const handleExportCSV = () => window.open('/api/export/jobs.csv', '_blank')

  const handleSave = async (jobId: string, saved: boolean) => {
    setSavingId(jobId)
    setError(null)
    // Optimistic: the bookmark should respond instantly, then reconcile.
    setItems((prev) => prev.map((j) => (j.id === jobId ? { ...j, is_saved: saved } : j)))
    try {
      await patch(`/jobs/${jobId}`, { is_saved: saved })
      if (savedOnly && !saved) await load()
    } catch (err) {
      setItems((prev) => prev.map((j) => (j.id === jobId ? { ...j, is_saved: !saved } : j)))
      setError(err instanceof Error ? err.message : 'Could not update this job')
    } finally {
      setSavingId(null)
    }
  }

  // Send the user straight to Apply with this job already chosen.
  const handlePrepare = (jobId: string) => {
    navigate(`/apply?job=${encodeURIComponent(jobId)}`)
  }

  const handleExportJSON = async () => {
    try {
      const data = await get<{ jobs: Job[] }>('/export/jobs.json')
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'jobs.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    }
  }

  const toggleSource = (url: string) =>
    setSelectedSources((prev) => ({ ...prev, [url]: !prev[url] }))

  const activeCount = Object.values(selectedSources).filter(Boolean).length

  return (
    <div className="space-y-5">
      <PageHeader
        title="Job Discovery"
        description="Pull roles from live public job boards, then score them against your profile."
        actions={
          <>
            <Button size="sm" icon={<Download size={13} />} onClick={handleExportCSV}>
              CSV
            </Button>
            <Button size="sm" icon={<FileJson size={13} />} onClick={handleExportJSON}>
              JSON
            </Button>
          </>
        }
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <Card>
        <CardHeader
          title="Live sources"
          description="Public Greenhouse and Lever boards. No login required."
          actions={
            <Button
              variant="primary"
              size="sm"
              loading={discovering}
              disabled={sourcesLoading || activeCount === 0}
              icon={<Radar size={14} />}
              onClick={handleDiscover}
            >
              {discovering ? 'Discovering' : `Discover jobs (${activeCount})`}
            </Button>
          }
        />
        <div className="p-4">
          {sourcesLoading ? (
            <div className="flex flex-wrap gap-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skeleton h-8 w-28" />
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {sources.map((source) => {
                const active = !!selectedSources[source.url]
                return (
                  <button
                    key={source.url}
                    onClick={() => toggleSource(source.url)}
                    aria-pressed={active}
                    className={cx(
                      'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
                      active
                        ? 'border-accent bg-accent-soft text-accent'
                        : 'border-line bg-surface text-fg-muted hover:border-line-strong hover:text-fg',
                    )}
                  >
                    {source.company || source.name || 'Source'}
                    <span className="opacity-60">{SOURCE_LABELS[source.kind] || source.kind}</span>
                  </button>
                )
              })}
            </div>
          )}

          {lastResult && (
            <div className="mt-4">
              <Alert tone={lastResult.imported > 0 ? 'success' : 'warn'}>
                Imported <strong>{lastResult.imported}</strong> new jobs
                {lastResult.duplicates > 0 && <> · {lastResult.duplicates} duplicates skipped</>}.
              </Alert>
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Add a job link"
          description="Paste one or more URLs to save a specific role."
        />
        <div className="space-y-3 p-4">
          <Field label="Job links" hint="One URL per line">
            <Textarea
              rows={3}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder={'https://company.com/careers/job/123\nhttps://jobs.lever.co/company/abc'}
              className="font-mono text-xs"
            />
          </Field>
          <Button
            variant="primary"
            size="sm"
            loading={importing}
            icon={<Link2 size={14} />}
            onClick={handleImport}
          >
            Import jobs
          </Button>
        </div>
      </Card>

      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle"
          />
          <Input
            ref={searchRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title, company, location, or source..."
            className="pl-9"
            aria-label="Search jobs"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-fg-subtle hover:text-fg"
              aria-label="Clear search"
            >
              <X size={13} />
            </button>
          )}
        </div>
        <div className="sm:w-56">
          <select
            value={companyFilter}
            onChange={(e) => setCompanyFilter(e.target.value)}
            className="h-9 w-full rounded-md border border-line bg-surface px-2.5 text-sm text-fg"
            aria-label="Filter by company"
          >
            <option value="">All companies ({companies.length})</option>
            {companies.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:w-44">
          <Select
            value={sort}
            onChange={(e) => setSort(e.target.value as typeof sort)}
            aria-label="Sort jobs"
          >
            <option value="recent">Newest first</option>
            <option value="match">Best match</option>
            <option value="salary">Highest salary</option>
            <option value="company">Company A–Z</option>
            <option value="title">Title A–Z</option>
          </Select>
        </div>
        <div className="sm:w-40">
          <Select
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            aria-label="Minimum match score"
          >
            <option value="">Any match score</option>
            <option value="70">70%+ match</option>
            <option value="50">50%+ match</option>
            <option value="25">25%+ match</option>
            <option value="1">Scored only</option>
          </Select>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setRemoteOnly((v) => !v)}
          aria-pressed={remoteOnly}
          className={cx(
            'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
            remoteOnly
              ? 'border-accent bg-accent-soft text-accent'
              : 'border-line bg-surface text-fg-muted hover:border-line-strong hover:text-fg',
          )}
        >
          Remote only
        </button>
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
        {(minScore || remoteOnly || savedOnly || sort !== 'recent') && (
          <Button
            size="sm"
            variant="ghost"
            icon={<RefreshCw size={12} />}
            onClick={() => {
              setMinScore('')
              setRemoteOnly(false)
              setSavedOnly(false)
              setSort('recent')
            }}
          >
            Reset filters
          </Button>
        )}
      </div>

      {filtered.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-fg-muted">
              Showing {filtered.length} of {total} job{total === 1 ? '' : 's'}
              {search.trim() && <> matching “{search.trim()}”</>}
              {companyFilter && <> at {companyFilter}</>}
            </p>
            <Button
              size="sm"
              icon={<Target size={14} />}
              loading={bulkScoring}
              onClick={handleScoreAll}
            >
              Score all shown
            </Button>
          </div>
        )}

        {scoreMessage && (
          <div className="mb-3">
            <Alert tone="success">{scoreMessage}</Alert>
          </div>
        )}

        {loading ? (
        <SkeletonCards count={6} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Radar size={26} />}
          title={hasFilters ? 'No jobs match your filters' : 'No jobs yet'}
          description={
            hasFilters
              ? 'Try clearing the search box or company filter.'
              : 'Click "Discover jobs" to pull live roles from the selected boards, or paste a job link above.'
          }
          action={
            hasFilters ? (
              <Button
                size="sm"
                icon={<RefreshCw size={13} />}
                onClick={() => {
                  setSearch('')
                  setCompanyFilter('')
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                icon={<Radar size={14} />}
                loading={discovering}
                onClick={handleDiscover}
              >
                Discover jobs
              </Button>
            )
          }
        />
) : (
          <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                scoring={scoringId === job.id || savingId === job.id}
                onScore={handleScore}
                onSave={handleSave}
                onApply={handlePrepare}
              />
            ))}
          </div>

          {total > filtered.length && (
            <div className="flex justify-center pt-2">
              <Button
                loading={loading}
                icon={<SlidersHorizontal size={14} />}
                onClick={() => setLimit((n) => n + 24)}
              >
                Load more ({total - filtered.length} remaining)
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}