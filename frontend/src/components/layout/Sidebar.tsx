import { NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  Bot,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Compass,
  FileText,
  HelpCircle,
  LayoutDashboard,
  Search,
  Send,
  Settings,
  Target,
  UserCog,
  Workflow,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAppStore } from '../../store/useAppStore'
import { cx } from '../ui'
import { get } from '../../services/api'

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  end?: boolean
}

const PRIMARY: NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/discover', label: 'Discover Jobs', icon: Compass },
  { to: '/agents', label: 'AI Agents', icon: Bot },
  { to: '/applications', label: 'Applications', icon: Target },
  { to: '/resumes', label: 'Resume Studio', icon: FileText },
  { to: '/automation', label: 'Automation', icon: Workflow },
  { to: '/analytics', label: 'Analytics', icon: Activity },
]

const SECONDARY: NavItem[] = [
  { to: '/apply', label: 'Prepare Application', icon: Send },
  { to: '/follow-ups', label: 'Follow-ups', icon: CalendarClock },
  { to: '/profile', label: 'Profile', icon: UserCog },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function NavButton({
  item,
  collapsed,
}: {
  item: NavItem
  collapsed: boolean
}) {
  const location = useLocation()
  const active = item.end
    ? location.pathname === item.to
    : location.pathname.startsWith(item.to)
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={collapsed ? item.label : undefined}
      aria-current={active ? 'page' : undefined}
      className={cx(
        'group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors',
        collapsed && 'justify-center px-0',
        active
          ? 'bg-surface-raised font-medium text-fg'
          : 'text-fg-muted hover:bg-surface-raised/60 hover:text-fg',
      )}
    >
      {active && (
        <motion.span
          layoutId="sidebar-active"
          className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r-full bg-accent"
          transition={{ type: 'spring', stiffness: 420, damping: 32 }}
        />
      )}
      <Icon size={16} className={cx('shrink-0', active ? 'text-accent' : '')} />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  )
}

export function Sidebar() {
  const collapsed = useAppStore((s) => s.sidebarCollapsed)
  const toggle = useAppStore((s) => s.toggleSidebar)
  const [profile, setProfile] = useState<{ full_name?: string }>({})

  useEffect(() => {
    get<{ full_name?: string }>('/profile/')
      .then((p) => setProfile(p || {}))
      .catch(() => {})
  }, [])

  const initials = (profile.full_name || 'C')
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <aside
      className={cx(
        'z-30 hidden shrink-0 flex-col border-r border-line bg-surface transition-[width] duration-200 md:flex',
        collapsed ? 'w-[60px]' : 'w-[250px]',
      )}
    >
      <div
        className={cx(
          'flex h-14 items-center border-b border-line px-3',
          collapsed ? 'justify-center' : 'gap-2.5',
        )}
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-fg shadow-glow">
          <Search size={15} strokeWidth={2.5} />
        </span>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight text-fg">
              NS
            </p>
            <p className="truncate text-2xs text-fg-subtle">Application copilot</p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3" aria-label="Main">
        {PRIMARY.map((item) => (
          <NavButton key={item.to} item={item} collapsed={collapsed} />
        ))}

        <div className="!mt-4 border-t border-line pt-3">
          {SECONDARY.map((item) => (
            <NavButton key={item.to} item={item} collapsed={collapsed} />
          ))}
          <NavLink
            to="/help"
            title={collapsed ? 'Help' : undefined}
            className={cx(
              'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-raised/60 hover:text-fg',
              collapsed && 'justify-center px-0',
            )}
          >
            <HelpCircle size={16} className="shrink-0" />
            {!collapsed && <span>Help</span>}
          </NavLink>
        </div>
      </nav>

      <div className="border-t border-line p-2">
        <div
          className={cx(
            'mb-1 flex items-center gap-2.5 rounded-lg p-1.5',
            collapsed && 'justify-center px-0',
          )}
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-2xs font-semibold text-fg ring-1 ring-line">
            {initials}
          </span>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-fg">{profile.full_name || 'Candidate'}</p>
              <p className="truncate text-2xs text-accent">Open to work</p>
            </div>
          )}
        </div>

        <button
          onClick={toggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cx(
            'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-xs text-fg-subtle transition-colors hover:bg-surface-raised/60 hover:text-fg',
            collapsed && 'justify-center px-0',
          )}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}