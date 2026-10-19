import type { ReactNode } from 'react'
import { STAGE_LABELS, STAGE_TONES, type ApplicationStage } from '../../data/mock'
import { Badge, cx, type Tone } from '../ui'

/** Circular match score with a colour that reflects how strong the fit is. */
export function MatchScore({
  score,
  size = 44,
  showLabel = true,
}: {
  score?: number | null
  size?: number
  showLabel?: boolean
}) {
  if (score == null) {
    return (
      <span className="inline-flex items-center justify-center rounded-full border border-dashed border-line text-2xs text-fg-subtle"
        style={{ width: size, height: size }}>
        —
      </span>
    )
  }

  const pct = Math.max(0, Math.min(100, score))
  const tone =
    pct >= 70 ? 'text-accent' : pct >= 40 ? 'text-warn' : 'text-danger'
  const ring =
    pct >= 70 ? 'stroke-accent' : pct >= 40 ? 'stroke-warn' : 'stroke-danger'
  const radius = (size - 6) / 2
  const circumference = 2 * Math.PI * radius

  return (
    <span
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Match score ${pct} percent`}
      title={`Match score ${pct}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={3}
          className="stroke-line"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - pct / 100)}
          className={cx(ring, 'transition-[stroke-dashoffset] duration-500')}
        />
      </svg>
      <span className={cx('absolute text-xs font-semibold tabular', tone)}>
        {Math.round(pct)}
      </span>
      {showLabel && <span className="sr-only">{pct} percent match</span>}
    </span>
  )
}

/** Stage pill used on cards, tables and the kanban board. */
export function StatusBadge({ stage }: { stage: ApplicationStage }) {
  return (
    <Badge tone={STAGE_TONES[stage] as Tone}>{STAGE_LABELS[stage]}</Badge>
  )
}

/**
 * Company mark. Real logos are not available from job boards, so this derives
 * stable initials from the company name rather than shipping broken images.
 */
export function CompanyMark({
  name,
  size = 32,
  tone,
}: {
  name?: string
  size?: number
  tone?: string
}) {
  const label = (name ?? 'Unknown').trim()
  const initials =
    label
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => w[0] ?? '')
      .join('')
      .toUpperCase() || '?'

  // Deterministic hue so a company keeps the same colour across the app.
  let hash = 0
  for (let i = 0; i < label.length; i += 1) hash = (hash * 31 + label.charCodeAt(i)) % 360

  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-lg font-semibold text-white ring-1 ring-inset ring-white/10"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        background: tone ?? `hsl(${hash} 42% 32%)`,
      }}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}

export function MetricCard({
  label,
  value,
  delta,
  icon,
  hint,
  onClick,
}: {
  label: string
  value: ReactNode
  /** Percentage change versus the previous period. Demo data only. */
  delta?: number
  icon?: ReactNode
  hint?: string
  onClick?: () => void
}) {
  const Wrapper = onClick ? 'button' : 'div'
  const positive = (delta ?? 0) >= 0

  return (
    <Wrapper
      {...(onClick ? { onClick, type: 'button' as const } : {})}
      className={cx(
        'group relative overflow-hidden rounded-xl border border-line bg-surface-raised p-4 text-left shadow-xs',
        onClick && 'transition-all duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium tracking-wide text-fg-muted">{label}</span>
        {icon && (
          <span className="text-fg-subtle transition-colors group-hover:text-accent">{icon}</span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="tabular text-2xl font-semibold tracking-tight text-fg">{value}</span>
        {delta != null && (
          <span
            className={cx(
              'tabular text-xs font-medium',
              positive ? 'text-accent' : 'text-danger',
            )}
          >
            {positive ? '+' : ''}
            {delta}%
          </span>
        )}
      </div>
      {hint && <p className="mt-1 text-xs text-fg-subtle">{hint}</p>}
    </Wrapper>
  )
}

/** Small "demo data" marker so synthetic numbers are never mistaken for live ones. */
export function DemoTag({ label = 'Demo data' }: { label?: string }) {
  return (
    <Badge tone="info" className="shrink-0">
      {label}
    </Badge>
  )
}