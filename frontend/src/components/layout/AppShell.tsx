import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Compass, FileText, Target } from 'lucide-react'
import { Modal } from '../ui'
import { ToastViewport } from '../ui/Toast'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const ACTIONS = [
  {
    to: '/discover',
    title: 'Discover jobs',
    body: 'Search live job boards and score roles against your profile.',
    icon: Compass,
  },
  {
    to: '/applications',
    title: 'Track an application',
    body: 'Move an application through your pipeline.',
    icon: Target,
  },
  {
    to: '/resumes',
    title: 'Manage resumes',
    body: 'Upload, tailor and compare resume versions.',
    icon: FileText,
  },
]

export function AppShell({ children }: { children: ReactNode }) {
  const [quickAddOpen, setQuickAddOpen] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="flex h-full overflow-hidden bg-canvas">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onQuickAdd={() => setQuickAddOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1400px] px-4 py-5 md:px-6">{children}</div>
        </main>
      </div>

      <Modal
        open={quickAddOpen}
        onClose={() => setQuickAddOpen(false)}
        title="Quick add"
        footer={
          <button
            onClick={() => setQuickAddOpen(false)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs text-fg-muted transition-colors hover:text-fg"
          >
            Close
          </button>
        }
      >
        <div className="space-y-2">
          {ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <button
                key={action.to}
                onClick={() => {
                  setQuickAddOpen(false)
                  navigate(action.to)
                }}
                className="flex w-full items-start gap-3 rounded-lg border border-line p-3 text-left transition-colors hover:border-line-strong hover:bg-surface-sunken"
              >
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-sunken text-accent ring-1 ring-line">
                  <Icon size={15} />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-fg">{action.title}</span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-fg-muted">
                    {action.body}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      </Modal>

      <ToastViewport />
    </div>
  )
}