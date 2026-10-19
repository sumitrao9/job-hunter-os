import { useState } from 'react'
import {
  Bookmark,
  Briefcase,
  ChevronDown,
  ExternalLink,
  MapPin,
  Sparkles,
  Wallet,
} from 'lucide-react'
import type { Job } from '../../types'
import { Badge, Button, ProgressBar, cx, formatSalary, relativeTime, snippet } from '../ui'
import { CompanyMark, MatchScore } from '../ui/data-display'

export function scoreTone(score?: number | null): 'accent' | 'warn' | 'danger' | 'neutral' {
  if (score == null) return 'neutral'
  if (score >= 70) return 'accent'
  if (score >= 40) return 'warn'
  return 'danger'
}

export function JobCard({
  job,
  scoring,
  onScore,
  onSave,
  onApply,
  onOpen,
}: {
  job: Job
  scoring?: boolean
  onScore?: (id: string) => void
  onSave?: (id: string, saved: boolean) => void
  onApply?: (id: string) => void
  onOpen?: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const saved = !!job.is_saved
  const salary = formatSalary(job.salary_min, job.salary_max)
  const evidence = Array.isArray(job.match_evidence) ? job.match_evidence : []
  const score = job.match_score

  return (
    <article
      className={cx(
        'group relative flex flex-col gap-3 rounded-xl border bg-surface-raised p-4 shadow-xs',
        'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md',
        saved ? 'border-accent/50' : 'border-line hover:border-line-strong',
      )}
    >
      {score != null && score >= 70 && (
        <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent to-transparent opacity-70" />
      )}

      <header className="flex items-start gap-2.5">
        <CompanyMark name={job.company} size={34} />
        <div className="min-w-0 flex-1">
          <h3
            className="truncate text-sm font-semibold text-fg"
            title={job.title}
            onClick={onOpen}
          >
            {job.title || 'Untitled role'}
          </h3>
          <p className="mt-0.5 truncate text-sm text-fg-muted">{job.company || 'Unknown company'}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <MatchScore score={score} size={34} />
          {onSave && (
            <button
              type="button"
              onClick={() => onSave(job.id, !saved)}
              aria-pressed={saved}
              aria-label={saved ? `Unsave ${job.title}` : `Save ${job.title}`}
              className={cx(
                'rounded-md p-1 transition-colors',
                saved
                  ? 'text-accent hover:bg-accent-soft'
                  : 'text-fg-subtle hover:bg-surface-sunken hover:text-fg',
              )}
            >
              <Bookmark size={15} fill={saved ? 'currentColor' : 'none'} />
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-subtle">
        <span className="inline-flex items-center gap-1">
          <MapPin size={11} />
          {job.location || 'Location not set'}
        </span>
        {job.remote && (
          <Badge tone="accent">
            <Briefcase size={10} /> Remote
          </Badge>
        )}
        {salary && (
          <span className="inline-flex items-center gap-1 text-fg-muted">
            <Wallet size={11} />
            {salary}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {job.source && <Badge tone="neutral">{job.source}</Badge>}
        {job.created_at && (
          <span className="text-2xs text-fg-subtle">Posted {relativeTime(job.created_at)}</span>
        )}
      </div>

      {score != null && <ProgressBar value={score} tone={scoreTone(score)} />}

      {evidence.length > 0 && (
        <ul className="space-y-0.5 text-xs leading-relaxed text-fg-muted">
          {evidence.slice(0, expanded ? evidence.length : 2).map((item, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent/70" />
              <span className="min-w-0">{item}</span>
            </li>
          ))}
        </ul>
      )}

      {expanded && job.description && (
        <p className="max-h-40 overflow-y-auto rounded-md bg-surface-sunken p-2.5 text-xs leading-relaxed text-fg-muted">
          {snippet(job.description, 900)}
        </p>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-2 border-t border-line/60 pt-3">
        {onApply && (
          <Button size="sm" variant="primary" onClick={() => onApply(job.id)}>
            Apply
          </Button>
        )}
        {onScore && (
          <Button
            size="sm"
            loading={scoring}
            icon={<Sparkles size={13} />}
            onClick={() => onScore(job.id)}
          >
            {score != null ? 'Rescore' : 'Score'}
          </Button>
        )}
        {onOpen && (
          <Button size="sm" variant="ghost" onClick={onOpen}>
            Details
          </Button>
        )}
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            Posting <ExternalLink size={12} />
          </a>
        )}
        {job.description && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            aria-label={expanded ? 'Hide description' : 'Show description'}
            className="inline-flex items-center gap-1 text-xs text-fg-subtle transition-colors hover:text-fg"
          >
            <ChevronDown size={12} className={cx('transition-transform', expanded && 'rotate-180')} />
          </button>
        )}
      </div>
    </article>
  )
}

/** Dense table alternative to the card grid. */
export function JobTable({
  jobs,
  onOpen,
  onSave,
}: {
  jobs: Job[]
  onOpen: (job: Job) => void
  onSave?: (job: Job, saved: boolean) => void
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface-sunken text-fg-subtle">
          <tr>
            <th className="px-3 py-2 font-medium">Role</th>
            <th className="px-3 py-2 font-medium">Company</th>
            <th className="hidden px-3 py-2 font-medium md:table-cell">Location</th>
            <th className="hidden px-3 py-2 font-medium lg:table-cell">Salary</th>
            <th className="hidden px-3 py-2 font-medium lg:table-cell">Posted</th>
            <th className="px-3 py-2 font-medium">Match</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.id}
              onClick={() => onOpen(job)}
              className="cursor-pointer border-t border-line bg-surface-raised transition-colors hover:bg-surface-sunken/60"
            >
              <td className="max-w-[16rem] truncate px-3 py-2 font-medium text-fg">{job.title}</td>
              <td className="max-w-[10rem] truncate px-3 py-2 text-fg-muted">{job.company}</td>
              <td className="hidden max-w-[9rem] truncate px-3 py-2 text-fg-muted md:table-cell">
                {job.location || '—'}
              </td>
              <td className="hidden px-3 py-2 text-fg-muted lg:table-cell">
                {formatSalary(job.salary_min, job.salary_max) ?? '—'}
              </td>
              <td className="hidden px-3 py-2 text-fg-muted lg:table-cell">
                {job.created_at ? relativeTime(job.created_at) : '—'}
              </td>
              <td className="px-3 py-2">
                <MatchScore score={job.match_score} size={26} />
              </td>
              <td className="px-3 py-2 text-right">
                {onSave && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onSave(job, !job.is_saved)
                    }}
                    aria-label={job.is_saved ? 'Unsave job' : 'Save job'}
                    className={cx(
                      'rounded p-1',
                      job.is_saved ? 'text-accent' : 'text-fg-subtle hover:text-fg',
                    )}
                  >
                    <Bookmark size={14} fill={job.is_saved ? 'currentColor' : 'none'} />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}