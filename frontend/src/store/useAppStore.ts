import { create } from 'zustand'
import {
  MOCK_AGENTS,
  MOCK_AGENT_LOGS,
  MOCK_NOTIFICATIONS,
  MOCK_WORKFLOWS,
  type AgentDefinition,
  type AgentLogEntry,
  type ApplicationStage,
  type WorkflowDefinition,
} from '../data/mock'

export type ToastTone = 'accent' | 'info' | 'warn' | 'danger'

export interface Toast {
  id: string
  title: string
  body?: string
  tone: ToastTone
  leaving?: boolean
}

export interface NotificationItem {
  id: string
  title: string
  body: string
  at: string
  unread: boolean
  tone: 'accent' | 'danger' | 'warn' | 'info'
}

interface AppState {
  // Layout
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  // Agents and workflows are demo-only surfaces, so they live in the store.
  agents: AgentDefinition[]
  toggleAgent: (id: string) => void
  setAgentStatus: (id: string, status: AgentDefinition['status']) => void
  runAgent: (id: string) => Promise<void>
  agentLogs: AgentLogEntry[]

  workflows: WorkflowDefinition[]
  toggleWorkflow: (id: string) => void
  runWorkflow: (id: string) => Promise<void>

  // Application stage changes. A real backend call is layered on by the page.
  stageOverrides: Record<string, ApplicationStage>
  setStage: (applicationId: string, stage: ApplicationStage) => void

  notifications: NotificationItem[]
  markNotificationsRead: () => void
  unreadCount: () => number

  toasts: Toast[]
  pushToast: (toast: Omit<Toast, 'id'>) => void
  dismissToast: (id: string) => void
}

let toastSeq = 0

/** Short, deterministic delay so "Run now" feels responsive without faking speed. */
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export const useAppStore = create<AppState>((set, get) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  agents: MOCK_AGENTS,
  agentLogs: MOCK_AGENT_LOGS,

  toggleAgent: (id) =>
    set((s) => ({
      agents: s.agents.map((a) =>
        a.id === id
          ? {
              ...a,
              enabled: !a.enabled,
              status: !a.enabled ? 'idle' : 'disabled',
            }
          : a,
      ),
    })),

  setAgentStatus: (id, status) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.id === id ? { ...a, status } : a)),
    })),

  runAgent: async (id) => {
    const agent = get().agents.find((a) => a.id === id)
    if (!agent) return
    if (!agent.enabled) {
      get().pushToast({ title: `${agent.name} is disabled`, tone: 'warn' })
      return
    }

    get().setAgentStatus(id, 'running')
    // The Email agent has no credentials in demo data, so it must fail loudly
    // rather than pretend a run succeeded.
    const willFail = id === 'email'
    await sleep(willFail ? 900 : 1100)

    const now = new Date().toISOString()
    const durationMs = willFail ? 1500 : 1200
    const log: AgentLogEntry = {
      id: `l${Date.now()}`,
      agentId: id,
      level: willFail ? 'error' : 'info',
      message: willFail
        ? 'IMAP connection refused — mailbox not configured'
        : `${agent.name} completed successfully`,
      at: now,
      durationMs,
    }

    set((s) => ({
      agents: s.agents.map((a) =>
        a.id === id
          ? {
              ...a,
              status: willFail ? ('error' as const) : ('idle' as const),
              lastRun: now,
              lastDurationMs: durationMs,
              runsToday: a.runsToday + 1,
            }
          : a,
      ),
      agentLogs: [log, ...s.agentLogs].slice(0, 40),
    }))

    get().pushToast({
      title: willFail ? `${agent.name} failed` : `${agent.name} finished`,
      body: log.message,
      tone: willFail ? 'danger' : 'accent',
    })
  },

  workflows: MOCK_WORKFLOWS,

  toggleWorkflow: (id) =>
    set((s) => ({
      workflows: s.workflows.map((w) => (w.id === id ? { ...w, enabled: !w.enabled } : w)),
    })),

  runWorkflow: async (id) => {
    const workflow = get().workflows.find((w) => w.id === id)
    if (!workflow) return
    if (!workflow.enabled) {
      get().pushToast({ title: `${workflow.name} is disabled`, tone: 'warn' })
      return
    }
    await get().runAgent(workflow.agentId)
  },

  stageOverrides: {},
  setStage: (applicationId, stage) =>
    set((s) => ({ stageOverrides: { ...s.stageOverrides, [applicationId]: stage } })),

  notifications: MOCK_NOTIFICATIONS,
  markNotificationsRead: () =>
    set((s) => ({ notifications: s.notifications.map((n) => ({ ...n, unread: false })) })),
  unreadCount: () => get().notifications.filter((n) => n.unread).length,

  toasts: [],
  pushToast: (toast) => {
    const id = `t${++toastSeq}`
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }))
    // Auto-dismiss, marking as leaving first so the exit animation can run.
    setTimeout(() => {
      set((s) => ({
        toasts: s.toasts.map((t) => (t.id === id ? { ...t, leaving: true } : t)),
      }))
      setTimeout(() => {
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
      }, 220)
    }, 4200)
  },
  dismissToast: (id) => {
    set((s) => ({
      toasts: s.toasts.map((t) => (t.id === id ? { ...t, leaving: true } : t)),
    }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 220)
  },
}))