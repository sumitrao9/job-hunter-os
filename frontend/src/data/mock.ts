/**
 * Demo dataset for surfaces the backend does not serve yet.
 *
 * Anything defined here is clearly synthetic. Pages that have a real API
 * (jobs, applications, resumes, settings) read from the backend and fall back
 * to these values only when a request fails, so demo data never masks a real
 * outage without saying so.
 */

export type ApplicationStage =
  | 'discovered'
  | 'shortlisted'
  | 'preparing'
  | 'awaiting_approval'
  | 'submitted'
  | 'assessment'
  | 'interview'
  | 'offer'
  | 'rejected'

export const APPLICATION_STAGES: ApplicationStage[] = [
  'discovered',
  'shortlisted',
  'preparing',
  'awaiting_approval',
  'submitted',
  'assessment',
  'interview',
  'offer',
  'rejected',
]

export const STAGE_LABELS: Record<ApplicationStage, string> = {
  discovered: 'Discovered',
  shortlisted: 'Shortlisted',
  preparing: 'Preparing',
  awaiting_approval: 'Awaiting Approval',
  submitted: 'Submitted',
  assessment: 'Assessment',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
}

/** Tone per stage so badges stay consistent everywhere. */
export const STAGE_TONES: Record<ApplicationStage, 'neutral' | 'info' | 'accent' | 'warn' | 'danger'> =
  {
    discovered: 'neutral',
    shortlisted: 'info',
    preparing: 'info',
    awaiting_approval: 'warn',
    submitted: 'accent',
    assessment: 'warn',
    interview: 'accent',
    offer: 'accent',
    rejected: 'danger',
  }

export type AgentStatus = 'idle' | 'running' | 'error' | 'disabled'

export interface AgentDefinition {
  id: string
  name: string
  purpose: string
  description: string
  icon: 'radar' | 'target' | 'file' | 'pen' | 'send' | 'mail' | 'bell' | 'copy'
  status: AgentStatus
  enabled: boolean
  lastRun: string | null
  lastDurationMs: number | null
  runsToday: number
  inputs: string[]
  outputs: string[]
  config: { label: string; value: string }[]
}

export const MOCK_AGENTS: AgentDefinition[] = [
  {
    id: 'discovery',
    name: 'Job Discovery Agent',
    purpose: 'Fetches new postings from every configured job board and stores them.',
    description: 'Polls Greenhouse, Lever and Ashby boards, deduplicates by URL and saves new roles.',
    icon: 'radar',
    status: 'idle',
    enabled: true,
    lastRun: '2026-10-02T06:15:00Z',
    lastDurationMs: 4820,
    runsToday: 3,
    inputs: ['Job board URLs', 'Run schedule'],
    outputs: ['New Job records', 'Per-source import report'],
    config: [
      { label: 'Sources', value: '10 boards' },
      { label: 'Schedule', value: 'Every 6 hours' },
      { label: 'Max per run', value: '500' },
    ],
  },
  {
    id: 'matching',
    name: 'Job Matching Agent',
    purpose: 'Scores every new job against your profile and explains the score.',
    description: 'Weighted skill, role, location, remote and salary scoring with written rationale.',
    icon: 'target',
    status: 'idle',
    enabled: true,
    lastRun: '2026-10-02T06:19:00Z',
    lastDurationMs: 1260,
    runsToday: 3,
    inputs: ['Profile', 'Unscored jobs'],
    outputs: ['match_score', 'match_evidence'],
    config: [
      { label: 'Minimum score', value: '25%' },
      { label: 'Auto-score on import', value: 'On' },
    ],
  },
  {
    id: 'resume',
    name: 'Resume Agent',
    purpose: 'Tailors your resume to a specific role and keeps versions.',
    description: 'Reorders and rewrites resume sections so they answer a given job description.',
    icon: 'file',
    status: 'idle',
    enabled: true,
    lastRun: '2026-10-01T18:40:00Z',
    lastDurationMs: 940,
    runsToday: 1,
    inputs: ['Resume versions', 'Target job'],
    outputs: ['Tailored resume', 'ATS feedback'],
    config: [
      { label: 'Model', value: 'gpt-4o-mini' },
      { label: 'Max pages', value: '2' },
    ],
  },
  {
    id: 'cover_letter',
    name: 'Cover Letter Agent',
    purpose: 'Writes a tailored letter using only facts from your profile.',
    description: 'Never invents achievements. Every claim traces back to a field you entered.',
    icon: 'pen',
    status: 'running',
    enabled: true,
    lastRun: '2026-10-02T09:58:00Z',
    lastDurationMs: 2100,
    runsToday: 6,
    inputs: ['Profile', 'Job description'],
    outputs: ['Cover letter text'],
    config: [
      { label: 'Tone', value: 'Professional' },
      { label: 'Max words', value: '260' },
    ],
  },
  {
    id: 'application',
    name: 'Application Assistant',
    purpose: 'Assembles the package and stops before anything is submitted.',
    description: 'Builds the cover letter and form answers, then waits for your review.',
    icon: 'send',
    status: 'idle',
    enabled: true,
    lastRun: '2026-10-02T09:58:30Z',
    lastDurationMs: 540,
    runsToday: 6,
    inputs: ['Prepared package', 'Your confirmation'],
    outputs: ['Application record', 'Pipeline status'],
    config: [
      { label: 'Auto-submit', value: 'Never (human-in-the-loop)' },
    ],
  },
  {
    id: 'email',
    name: 'Email Monitoring Agent',
    purpose: 'Watches your inbox for application updates.',
    description: 'Matches incoming mail to applications and surfaces confirmations and rejections.',
    icon: 'mail',
    status: 'error',
    enabled: true,
    lastRun: '2026-10-02T07:00:00Z',
    lastDurationMs: 15000,
    runsToday: 4,
    inputs: ['IMAP credentials', 'Application company list'],
    outputs: ['Status updates', 'Follow-up reminders'],
    config: [
      { label: 'Mailbox', value: 'Not configured' },
      { label: 'Polling', value: 'Every 30 min' },
    ],
  },
  {
    id: 'follow_up',
    name: 'Follow-up Agent',
    purpose: 'Reminds you when an application goes quiet.',
    description: 'Tracks days since submission and drafts a courteous follow-up message.',
    icon: 'bell',
    status: 'idle',
    enabled: true,
    lastRun: '2026-10-02T08:00:00Z',
    lastDurationMs: 310,
    runsToday: 5,
    inputs: ['Applications past 7 days'],
    outputs: ['Follow-up drafts', 'Due dates'],
    config: [
      { label: 'Wait before nudging', value: '7 days' },
      { label: 'Max nudges', value: '2' },
    ],
  },
  {
    id: 'dedupe',
    name: 'Duplicate Detection Agent',
    purpose: 'Stops the same posting being tracked twice.',
    description: 'Matches on canonical URL first, then a title and company fingerprint.',
    icon: 'copy',
    status: 'idle',
    enabled: false,
    lastRun: '2026-09-28T11:20:00Z',
    lastDurationMs: 760,
    runsToday: 0,
    inputs: ['Incoming jobs', 'Existing jobs'],
    outputs: ['is_duplicate flags'],
    config: [
      { label: 'Match on', value: 'URL + fingerprint' },
    ],
  },
]

export interface AgentLogEntry {
  id: string
  agentId: string
  level: 'info' | 'warn' | 'error'
  message: string
  at: string
  durationMs?: number
}

export const MOCK_AGENT_LOGS: AgentLogEntry[] = [
  { id: 'l1', agentId: 'discovery', level: 'info', message: 'Fetched 10 boards, imported 1 new job', at: '2026-10-02T06:15:00Z', durationMs: 4820 },
  { id: 'l2', agentId: 'discovery', level: 'info', message: 'Fetched 10 boards, 0 new (all duplicates)', at: '2026-09-30T06:15:00Z', durationMs: 4610 },
  { id: 'l3', agentId: 'matching', level: 'info', message: 'Scored 1944 jobs, 118 above threshold', at: '2026-10-02T06:19:00Z', durationMs: 1260 },
  { id: 'l4', agentId: 'email', level: 'error', message: 'IMAP connection refused — mailbox not configured', at: '2026-10-02T07:00:00Z', durationMs: 15000 },
  { id: 'l5', agentId: 'email', level: 'warn', message: 'Retried 3 times before giving up', at: '2026-10-02T07:00:05Z' },
  { id: 'l6', agentId: 'cover_letter', level: 'info', message: 'Generated letter for Manager, Design Engineering', at: '2026-10-02T09:58:00Z', durationMs: 2100 },
  { id: 'l7', agentId: 'follow_up', level: 'info', message: '2 applications due a follow-up today', at: '2026-10-02T08:00:00Z', durationMs: 310 },
  { id: 'l8', agentId: 'discovery', level: 'warn', message: 'Lever returned 404 for cloudflare — board retired', at: '2026-10-01T06:15:00Z' },
]

export interface WorkflowDefinition {
  id: string
  name: string
  description: string
  enabled: boolean
  schedule: string
  lastRun: string | null
  nextRun: string | null
  lastStatus: 'success' | 'error' | 'never'
  agentId: string
  icon: 'radar' | 'target' | 'file' | 'pen' | 'bell' | 'mail' | 'send'
}

export const MOCK_WORKFLOWS: WorkflowDefinition[] = [
  {
    id: 'daily_discovery',
    name: 'Daily job discovery',
    description: 'Pull new postings from all connected boards and store anything unseen.',
    enabled: true,
    schedule: 'Every 6 hours',
    lastRun: '2026-10-02T06:15:00Z',
    nextRun: '2026-10-02T12:15:00Z',
    lastStatus: 'success',
    agentId: 'discovery',
    icon: 'radar',
  },
  {
    id: 'ai_matching',
    name: 'AI job matching',
    description: 'Score new jobs against your profile and flag strong matches.',
    enabled: true,
    schedule: 'After discovery',
    lastRun: '2026-10-02T06:19:00Z',
    nextRun: '2026-10-02T12:15:00Z',
    lastStatus: 'success',
    agentId: 'matching',
    icon: 'target',
  },
  {
    id: 'resume_gen',
    name: 'Resume generation',
    description: 'Create a tailored resume version for shortlisted roles.',
    enabled: false,
    schedule: 'Manual only',
    lastRun: '2026-10-01T18:40:00Z',
    nextRun: null,
    lastStatus: 'success',
    agentId: 'resume',
    icon: 'file',
  },
  {
    id: 'prep_package',
    name: 'Application preparation',
    description: 'Build the cover letter and form answers, then pause for approval.',
    enabled: true,
    schedule: 'On demand',
    lastRun: '2026-10-02T09:58:30Z',
    nextRun: null,
    lastStatus: 'success',
    agentId: 'cover_letter',
    icon: 'pen',
  },
  {
    id: 'approval_notify',
    name: 'Approval notifications',
    description: 'Ping you when a package is ready for review before submission.',
    enabled: true,
    schedule: 'Every hour',
    lastRun: '2026-10-02T09:00:00Z',
    nextRun: '2026-10-02T10:00:00Z',
    lastStatus: 'success',
    agentId: 'application',
    icon: 'send',
  },
  {
    id: 'email_monitor',
    name: 'Email monitoring',
    description: 'Detect application confirmations and updates in your inbox.',
    enabled: true,
    schedule: 'Every 30 min',
    lastRun: '2026-10-02T07:00:00Z',
    nextRun: '2026-10-02T07:30:00Z',
    lastStatus: 'error',
    agentId: 'email',
    icon: 'mail',
  },
  {
    id: 'follow_up_reminders',
    name: 'Follow-up reminders',
    description: 'Draft a courteous nudge when an application has gone quiet.',
    enabled: true,
    schedule: 'Daily at 08:00',
    lastRun: '2026-10-02T08:00:00Z',
    nextRun: '2026-10-03T08:00:00Z',
    lastStatus: 'success',
    agentId: 'follow_up',
    icon: 'bell',
  },
]

export const MOCK_NOTIFICATIONS = [
  {
    id: 'n1',
    title: 'Package ready for review',
    body: 'Cover letter prepared for Manager, Design Engineering at Sentry.',
    at: '2026-10-02T09:58:00Z',
    unread: true,
    tone: 'accent' as const,
  },
  {
    id: 'n2',
    title: 'Email agent needs attention',
    body: 'IMAP connection refused. Add mailbox credentials in Settings.',
    at: '2026-10-02T07:00:00Z',
    unread: true,
    tone: 'danger' as const,
  },
  {
    id: 'n3',
    title: '2 follow-ups due today',
    body: 'Stripe and Linear have not replied in over a week.',
    at: '2026-10-02T08:00:00Z',
    unread: false,
    tone: 'warn' as const,
  },
  {
    id: 'n4',
    title: 'Discovery added 1 new job',
    body: 'Airbnb posted a new frontend role.',
    at: '2026-10-02T06:15:00Z',
    unread: false,
    tone: 'info' as const,
  },
]

/** 14 days of activity for the overview line chart. */
export const MOCK_ACTIVITY = [
  { date: '2026-09-19', label: '19 Sep', discovered: 42, applied: 3, interviews: 0 },
  { date: '2026-09-20', label: '20 Sep', discovered: 55, applied: 5, interviews: 1 },
  { date: '2026-09-21', label: '21 Sep', discovered: 28, applied: 2, interviews: 0 },
  { date: '2026-09-22', label: '22 Sep', discovered: 61, applied: 4, interviews: 1 },
  { date: '2026-09-23', label: '23 Sep', discovered: 74, applied: 6, interviews: 2 },
  { date: '2026-09-24', label: '24 Sep', discovered: 38, applied: 3, interviews: 0 },
  { date: '2026-09-25', label: '25 Sep', discovered: 19, applied: 1, interviews: 0 },
  { date: '2026-09-26', label: '26 Sep', discovered: 47, applied: 4, interviews: 1 },
  { date: '2026-09-27', label: '27 Sep', discovered: 66, applied: 5, interviews: 0 },
  { date: '2026-09-28', label: '28 Sep', discovered: 81, applied: 7, interviews: 2 },
  { date: '2026-09-29', label: '29 Sep', discovered: 52, applied: 4, interviews: 1 },
  { date: '2026-09-30', label: '30 Sep', discovered: 39, applied: 3, interviews: 0 },
  { date: '2026-10-01', label: '1 Oct', discovered: 44, applied: 5, interviews: 1 },
  { date: '2026-10-02', label: '2 Oct', discovered: 58, applied: 6, interviews: 2 },
]

export const MOCK_SOURCES = [
  { name: 'Greenhouse', count: 1247, color: 'rgb(34 197 94)' },
  { name: 'Ashby', count: 293, color: 'rgb(96 165 250)' },
  { name: 'Lever', count: 400, color: 'rgb(234 179 8)' },
  { name: 'Manual', count: 4, color: 'rgb(156 163 175)' },
]

/** Resume variants used by Resume Studio when the API has nothing stored. */
export const MOCK_RESUMES = [
  {
    id: 'r1',
    title: 'Frontend Engineer — Master',
    updatedAt: '2026-09-28T10:00:00Z',
    pages: 2,
    atsScore: 94,
    isDefault: true,
    keywords: 41,
  },
  {
    id: 'r2',
    title: 'Full-Stack Engineer',
    updatedAt: '2026-09-14T10:00:00Z',
    pages: 2,
    atsScore: 89,
    isDefault: false,
    keywords: 33,
  },
  {
    id: 'r3',
    title: 'React Specialist',
    updatedAt: '2026-08-30T10:00:00Z',
    pages: 1,
    atsScore: 91,
    isDefault: false,
    keywords: 27,
  },
]

export const MOCK_RESUME_BODY = {
  summary:
    'Frontend Engineer with 6+ years building accessible, high-traffic product interfaces in React and TypeScript. Comfortable owning a feature from design review through production monitoring, and mentoring engineers through code review.',
  skills: [
    'React',
    'TypeScript',
    'Node.js',
    'GraphQL',
    'Next.js',
    'Tailwind CSS',
    'Jest',
    'Playwright',
    'AWS',
    'Docker',
  ],
  experience: [
    {
      title: 'Senior Frontend Engineer',
      company: 'Northwind Labs',
      period: '2023 — Present',
      bullets: [
        'Led the migration of a 40-screen dashboard to React and TypeScript, cutting interaction latency by 38%.',
        'Built the design-system package adopted by four product teams.',
        'Introduced visual regression testing, dropping UI regressions 26% over two quarters.',
      ],
    },
    {
      title: 'Frontend Engineer',
      company: 'Kite Systems',
      period: '2020 — 2023',
      bullets: [
        'Shipped the checkout redesign that lifted conversion 11%.',
        'Reduced bundle size 42% through route-level code splitting.',
      ],
    },
  ],
}