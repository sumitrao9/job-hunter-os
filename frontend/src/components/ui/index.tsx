import {
  forwardRef,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'
import { AlertCircle, CheckCircle2, Info, Loader2, TriangleAlert } from 'lucide-react'

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-b from-accent to-accent-hover text-accent-fg border-white/10 hover:from-accent-hover hover:to-accent-hover active:translate-y-px shadow-xs hover:shadow-glow',
  secondary:
    'bg-surface-raised text-fg border-line hover:bg-surface-sunken hover:border-line-strong active:translate-y-px shadow-xs hover:shadow-sm',
  ghost:
    'bg-transparent text-fg-muted border-transparent hover:bg-surface-sunken hover:text-fg',
  danger:
    'bg-danger text-white border-transparent hover:brightness-110 active:translate-y-px shadow-xs',
}

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-2.5 text-xs gap-1.5 rounded-md',
  md: 'h-9 px-3.5 text-sm gap-2 rounded-lg',
  lg: 'h-11 px-5 text-sm gap-2 rounded-lg',
}

const ICON_SIZES: Record<ButtonSize, number> = { sm: 13, md: 15, lg: 16 }

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', loading, icon, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cx(
        'relative inline-flex select-none items-center justify-center whitespace-nowrap border font-medium',
        'transition-all duration-150',
        'disabled:pointer-events-none disabled:opacity-50',
        BUTTON_VARIANTS[variant],
        BUTTON_SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 size={ICON_SIZES[size]} className="animate-spin" />
      ) : (
        icon
      )}
      {children}
    </button>
  )
})

export function Card({
  children,
  className,
  as: Tag = 'div',
  interactive,
  ...rest
}: {
  children?: ReactNode
  className?: string
  as?: 'div' | 'section' | 'article'
  interactive?: boolean
} & Omit<HTMLAttributes<HTMLElement>, 'children'>) {
  return (
    <Tag
      className={cx(
        'rounded-xl border border-line bg-surface-raised shadow-xs',
        interactive &&
          'ring-gradient cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  )
}

export function CardHeader({
  title,
  description,
  actions,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="hairline-top flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-3.5">
      <div className="min-w-0">
        <h2 className="text-[0.8125rem] font-semibold tracking-tight text-fg">{title}</h2>
        {description && <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[1.375rem] font-semibold tracking-tight text-fg">{title}</h1>
        {description && (
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-fg-muted">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

const FIELD_BASE =
  'w-full rounded-lg border border-line bg-surface-sunken text-sm text-fg shadow-xs ' +
  'transition-all duration-150 placeholder:text-fg-subtle ' +
  'hover:border-line-strong focus:border-accent focus:bg-surface focus:outline-none ' +
  'focus:ring-4 focus:ring-accent/12 disabled:opacity-60'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cx(FIELD_BASE, 'h-9 px-3', className)} {...rest} />
  },
)

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...rest }, ref) {
  return (
    <textarea ref={ref} className={cx(FIELD_BASE, 'resize-y px-3 py-2.5', className)} {...rest} />
  )
})

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...rest }, ref) {
    return (
      <select
        ref={ref}
        className={cx(
          FIELD_BASE,
          'h-9 cursor-pointer appearance-none bg-[length:16px] bg-[right_0.6rem_center] bg-no-repeat pr-8',
          className,
        )}
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2.5' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
        }}
        {...rest}
      >
        {children}
      </select>
    )
  },
)

export function Field({
  label,
  hint,
  children,
  className,
  required,
  error,
}: {
  label: string
  hint?: string
  children: ReactNode
  className?: string
  required?: boolean
  error?: string
}) {
  return (
    <label className={cx('block space-y-1.5', className)}>
      <span className="text-xs font-medium tracking-wide text-fg-muted">
        {label}
        {required && <span className="ml-0.5 text-danger">*</span>}
      </span>
      {children}
      {error ? (
        <span className="block text-xs text-danger">{error}</span>
      ) : (
        hint && <span className="block text-xs leading-relaxed text-fg-subtle">{hint}</span>
      )}
    </label>
  )
}

export type Tone = 'neutral' | 'accent' | 'info' | 'warn' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-sunken text-fg-muted ring-line',
  accent: 'bg-accent-soft text-accent ring-accent/20',
  info: 'bg-info-soft text-info ring-info/20',
  warn: 'bg-warn-soft text-warn ring-warn/20',
  danger: 'bg-danger-soft text-danger ring-danger/20',
}

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode
  tone?: Tone
  className?: string
}) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-2xs font-medium ring-1 ring-inset',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function Dot({ tone = 'accent' }: { tone?: Tone }) {
  return (
    <span className="relative flex h-1.5 w-1.5">
      <span
        className={cx(
          'absolute inline-flex h-full w-full rounded-full opacity-70',
          tone === 'accent'
            ? 'bg-accent'
            : tone === 'danger'
              ? 'bg-danger'
              : tone === 'warn'
                ? 'bg-warn'
                : 'bg-info',
        )}
      />
      <span
        className={cx(
          'relative inline-flex h-1.5 w-1.5 rounded-full',
          tone === 'accent'
            ? 'bg-accent'
            : tone === 'danger'
              ? 'bg-danger'
              : tone === 'warn'
                ? 'bg-warn'
                : 'bg-info',
        )}
      />
    </span>
  )
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 size={16} className={cx('animate-spin text-fg-muted', className)} />
}

export function LoadingBlock({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20">
      <span className="relative flex h-8 w-8 items-center justify-center">
        <span className="absolute h-8 w-8 rounded-full bg-accent/20 animate-pulse-ring" />
        <Spinner className="text-accent" />
      </span>
      <p className="text-sm text-fg-muted">{label}…</p>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('skeleton', className)} />
}

export function SkeletonCards({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="space-y-3.5 p-5">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-3 w-2/3" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-7 w-20" />
            <Skeleton className="h-7 w-16" />
          </div>
        </Card>
      ))}
    </div>
  )
}

const ALERT_TONES = {
  danger: {
    box: 'bg-danger-soft text-danger ring-danger/20',
    icon: <AlertCircle size={15} />,
  },
  warn: { box: 'bg-warn-soft text-warn ring-warn/20', icon: <TriangleAlert size={15} /> },
  info: { box: 'bg-info-soft text-info ring-info/20', icon: <Info size={15} /> },
  success: {
    box: 'bg-accent-soft text-accent ring-accent/20',
    icon: <CheckCircle2 size={15} />,
  },
} as const

export function Alert({
  tone = 'info',
  children,
  onDismiss,
}: {
  tone?: keyof typeof ALERT_TONES
  children: ReactNode
  onDismiss?: () => void
}) {
  const t = ALERT_TONES[tone]
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cx(
        'flex animate-fade-in items-start gap-2.5 rounded-lg px-3.5 py-2.5 text-sm ring-1 ring-inset',
        t.box,
      )}
    >
      <span className="mt-0.5 shrink-0">{t.icon}</span>
      <div className="min-w-0 flex-1 leading-relaxed">{children}</div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="-mr-1 shrink-0 rounded px-1 opacity-60 transition-opacity hover:opacity-100"
          aria-label="Dismiss"
        >
          ×
        </button>
      )}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-xl border border-dashed border-line px-6 py-16 text-center">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-24 opacity-[0.07]"
        style={{
          background:
            'radial-gradient(20rem 8rem at 50% 0%, rgb(var(--accent) / 0.9), transparent 70%)',
        }}
      />
      {icon && (
        <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-surface-sunken text-fg-subtle ring-1 ring-inset ring-line">
          {icon}
        </div>
      )}
      <div className="relative">
        <p className="text-sm font-medium text-fg">{title}</p>
        {description && (
          <p className="mx-auto mt-1 max-w-md text-sm leading-relaxed text-fg-muted">
            {description}
          </p>
        )}
      </div>
      {action && <div className="relative pt-1.5">{action}</div>}
    </div>
  )
}

export function StatCard({
  label,
  value,
  hint,
  tone = 'neutral',
  icon,
}: {
  label: string
  value: ReactNode
  hint?: string
  tone?: Tone
  icon?: ReactNode
}) {
  return (
    <Card className="group relative overflow-hidden p-4 transition-all duration-200 hover:border-line-strong hover:shadow-md">
      <div
        className="pointer-events-none absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-[0.18]"
        style={{ background: 'rgb(var(--accent))' }}
      />
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium tracking-wide text-fg-muted">{label}</span>
        {hint ? (
          <Badge tone={tone}>{hint}</Badge>
        ) : icon ? (
          <span className="text-fg-subtle">{icon}</span>
        ) : null}
      </div>
      <div className="tabular mt-2 text-2xl font-semibold tracking-tight text-fg">{value}</div>
    </Card>
  )
}

const BAR_TONES: Record<Tone, string> = {
  neutral: 'bg-fg-subtle',
  accent: 'bg-gradient-to-r from-accent to-accent-hover',
  info: 'bg-gradient-to-r from-info to-info/70',
  warn: 'bg-gradient-to-r from-warn to-warn/70',
  danger: 'bg-gradient-to-r from-danger to-danger/70',
}

export function ProgressBar({ value, tone = 'accent' }: { value: number; tone?: Tone }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken ring-1 ring-inset ring-line/60">
      <div
        className={cx('h-full rounded-full transition-[width] duration-500 ease-out', BAR_TONES[tone])}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-lg animate-scale-in overflow-hidden rounded-xl border border-line bg-surface-overlay shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="hairline-top flex items-center justify-between border-b border-line px-5 py-3.5">
          <h3 className="text-sm font-semibold tracking-tight text-fg">{title}</h3>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close dialog">
            ×
          </Button>
        </div>
        <div className="max-h-[70vh] overflow-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-line bg-surface-sunken/50 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void | Promise<void>
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2.5 text-sm text-fg-muted transition-colors hover:text-fg"
    >
      <span
        className={cx(
          'relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200',
          checked ? 'bg-accent' : 'bg-line-strong',
        )}
      >
        <span
          className={cx(
            'absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200',
          )}
          style={{ transform: checked ? 'translateX(16px)' : 'none' }}
        />
      </span>
      {label}
    </button>
  )
}

/** Formats a salary range for display, or null when it is unknown. */
export function formatSalary(min?: number | null, max?: number | null): string | null {
  const fmt = (n: number) =>
    n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`
  if (min && max && min !== max) return `${fmt(min)}–${fmt(max)}`
  if (max) return `up to ${fmt(max)}`
  if (min) return `from ${fmt(min)}`
  return null
}

/** Relative time such as "3d ago", used for posting and activity dates. */
export function relativeTime(iso?: string | null): string {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const seconds = Math.floor((Date.now() - then) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}mo ago`
  return `${Math.floor(months / 12)}y ago`
}

/** Trims a posting body down to a readable number of characters on a word boundary. */
export function snippet(text?: string | null, max = 220): string {
  if (!text) return ''
  const clean = text.replace(/\s+/g, ' ').trim()
  if (clean.length <= max) return clean
  return `${clean.slice(0, clean.lastIndexOf(' ', max))}…`
}