import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Bell, Check, ChevronRight, Moon, Plus, Search, Sun } from 'lucide-react'
import { useAppStore } from '../../store/useAppStore'
import { useTheme } from '../../hooks/useTheme'
import { relativeTime, cx } from '../ui'

const TITLES: Record<string, { title: string; crumb: string }> = {
  '/': { title: 'Overview', crumb: 'Dashboard' },
  '/discover': { title: 'Discover Jobs', crumb: 'Pipeline' },
  '/jobs': { title: 'Job Discovery', crumb: 'Pipeline' },
  '/agents': { title: 'AI Agents', crumb: 'Control center' },
  '/applications': { title: 'Applications', crumb: 'Pipeline' },
  '/resumes': { title: 'Resume Studio', crumb: 'Documents' },
  '/automation': { title: 'Automation', crumb: 'Workflows' },
  '/analytics': { title: 'Analytics', crumb: 'Insights' },
  '/settings': { title: 'Settings', crumb: 'Configure' },
  '/help': { title: 'Help', crumb: 'Support' },
}

export function Topbar({ onQuickAdd }: { onQuickAdd: () => void }) {
  const location = useLocation()
  const meta = TITLES[location.pathname] ?? { title: 'NS', crumb: 'Workspace' }
  const { theme, toggle } = useTheme()

  const notifications = useAppStore((s) => s.notifications)
  const markRead = useAppStore((s) => s.markNotificationsRead)
  const unread = notifications.filter((n) => n.unread).length

  const [notifOpen, setNotifOpen] = useState(false)
  const notifRef = useRef<HTMLDivElement>(null)

  const [query, setQuery] = useState('')

  // "/" focuses search from anywhere, the convention users expect here.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const typing =
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable
      if (e.key === '/' && !typing) {
        e.preventDefault()
        document.getElementById('global-search')?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    if (!notifOpen) return
    const onClick = (e: MouseEvent) => {
      if (!notifRef.current?.contains(e.target as Node)) setNotifOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [notifOpen])

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur-md">
      <div className="min-w-0 shrink-0">
        <div className="flex items-center gap-1.5 text-2xs text-fg-subtle">
          <span>{meta.crumb}</span>
          <ChevronRight size={11} />
        </div>
        <h1 className="truncate text-sm font-semibold tracking-tight text-fg">{meta.title}</h1>
      </div>

      <div className="relative ml-auto w-full max-w-sm">
        <Search
          size={14}
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-subtle"
        />
        <input
          id="global-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && query.trim()) {
              window.location.href = `/discover?q=${encodeURIComponent(query.trim())}`
            }
          }}
          placeholder="Search jobs, companies, skills..."
          aria-label="Global search"
          className="h-8 w-full rounded-lg border border-line bg-surface-raised pl-8 pr-9 text-xs text-fg shadow-xs transition-colors placeholder:text-fg-subtle hover:border-line-strong focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/12"
        />
        {!query && (
          <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-line bg-surface-sunken px-1.5 py-0.5 font-mono text-[10px] text-fg-subtle">
            /
          </kbd>
        )}
      </div>

      <button
        onClick={toggle}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-raised hover:text-fg"
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>

      <div className="relative shrink-0" ref={notifRef}>
        <button
          onClick={() => {
            setNotifOpen((v) => !v)
            if (!notifOpen && unread > 0) markRead()
          }}
          aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
          aria-expanded={notifOpen}
          className="relative flex h-8 w-8 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-raised hover:text-fg"
        >
          <Bell size={16} />
          {unread > 0 && (
            <span className="absolute right-1 top-1 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-accent px-1 text-[9px] font-semibold text-accent-fg">
              {unread}
            </span>
          )}
        </button>

        <AnimatePresence>
          {notifOpen && (
            <motion.div
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.14 }}
              className="absolute right-0 top-10 z-40 w-80 overflow-hidden rounded-xl border border-line bg-surface-overlay shadow-lg"
            >
              <div className="flex items-center justify-between border-b border-line px-3.5 py-2.5">
                <span className="text-xs font-semibold text-fg">Notifications</span>
                {unread === 0 && (
                  <span className="inline-flex items-center gap-1 text-2xs text-fg-subtle">
                    <Check size={11} /> All read
                  </span>
                )}
              </div>
              <ul className="max-h-80 overflow-y-auto">
                {notifications.map((n) => (
                  <li
                    key={n.id}
                    className="border-b border-line/60 px-3.5 py-2.5 last:border-0 hover:bg-surface-raised/60"
                  >
                    <div className="flex items-start gap-2">
                      {!n.unread && (
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-fg-subtle" />
                      )}
                      <div className={cx('min-w-0', !n.unread && 'pl-3.5')}>
                        <p className="text-xs font-medium text-fg">{n.title}</p>
                        <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">{n.body}</p>
                        <p className="mt-1 text-2xs text-fg-subtle">{relativeTime(n.at)}</p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button
        onClick={onQuickAdd}
        className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg bg-accent px-2.5 text-xs font-medium text-accent-fg shadow-xs transition-colors hover:bg-accent-hover"
      >
        <Plus size={14} />
        <span className="hidden sm:inline">Quick add</span>
      </button>

      <Link
        to="/settings"
        aria-label="Open profile"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-2xs font-semibold text-fg ring-1 ring-line transition-colors hover:ring-line-strong"
      >
        SY
      </Link>
    </header>
  )
}