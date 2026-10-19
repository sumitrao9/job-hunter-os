import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CalendarClock,
  CheckCircle,
  Compass,
  FileText,
  Plus,
  Send,
  Target,
  Users,
  Wrench,
} from 'lucide-react'
import { get } from '../services/api'
import type { Application, Job } from '../types'
import { Button, Card, CardHeader, EmptyState, PageHeader } from '../components/ui'
import type { Tone } from '../components/ui'
import { MetricCard } from '../components/ui/data-display'

interface HealthComponent {
  name: string
  status: string
  message: string
}

interface HealthResponse {
  status: string
  components: HealthComponent[]
  version: string
}

export default function Overview() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [profile, setProfile] = useState<{ full_name?: string; skills?: string[] } | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [jobData, appData, healthData, profileData] = await Promise.allSettled([
        get<Job[]>('/jobs/?limit=20'),
        get<Application[]>('/applications/'),
        get<HealthResponse>('/health/'),
        get<{ full_name?: string; skills?: string[] }>('/profile/'),
      ])

      if (jobData.status === 'fulfilled') setJobs(jobData.value)
      if (appData.status === 'fulfilled') setApplications(appData.value || [])
      if (healthData.status === 'fulfilled') setHealth(healthData.value)
      if (profileData.status === 'fulfilled') setProfile(profileData.value || null)
    } catch {
      // Silently fail — dashboard will show empty states
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // --- WHAT SHOULD I DO TODAY? ---
  const todaysTasks = useMemo(() => {
    const tasks: Array<{
      id: string
      type: 'review' | 'apply' | 'followup' | 'setup' | 'interview'
      title: string
      description: string
      action: string
      actionTo: string
      tone: Tone
    }> = []

    // Applications waiting for approval
    const awaiting = applications.filter((a) => a.status === 'awaiting_approval' || a.status === 'preparing')
    awaiting.slice(0, 5).forEach((app) => {
      tasks.push({
        id: app.id,
        type: 'review',
        title: `Review application for ${app.company || 'company'}`,
        description: app.job_title || '',
        action: 'Review',
        actionTo: `/applications/${app.id}`,
        tone: 'warn',
      })
    })

    // Follow-ups due
    const now = new Date().getTime()
    const dueFollowUps = applications.filter((a) => {
      if (!a.follow_up_date) return false
      const followUpTime = new Date(a.follow_up_date).getTime()
      return followUpTime <= now
    })
    dueFollowUps.slice(0, 3).forEach((app) => {
      tasks.push({
        id: `followup-${app.id}`,
        type: 'followup',
        title: `Send follow-up for ${app.company || 'company'}`,
        description: app.job_title || '',
        action: 'View',
        actionTo: `/applications/${app.id}`,
        tone: 'info',
      })
    })

    // Jobs ready for preparation (strong matches)
    const readyJobs = jobs.filter((j) => (j.match_score ?? 0) >= 25 && j.status === 'shortlisted')
    readyJobs.slice(0, 3).forEach((job) => {
      tasks.push({
        id: `prepare-${job.id}`,
        type: 'apply',
        title: `Prepare application for ${job.company || 'company'}`,
        description: job.title || '',
        action: 'Prepare',
        actionTo: `/apply?job=${job.id}`,
        tone: 'accent',
      })
    })

    // Setup reminders
    if (profile && !profile.skills?.length) {
      tasks.push({
        id: 'setup-skills',
        type: 'setup',
        title: 'Complete your profile',
        description: 'Add your skills and experience',
        action: 'Set up',
        actionTo: '/profile',
        tone: 'warn',
      })
    }

    return tasks
  }, [jobs, applications, profile])

  // --- HEALTH SUMMARY ---
  const healthIssues = useMemo(() => {
    if (!health) return []
    return health.components.filter((c) => c.status !== 'ready')
  }, [health])

  // --- APPLICATION PIPELINE ---
  const pipeline = useMemo(() => {
    const stages = [
      { key: 'discovered', label: 'New', color: 'neutral' as Tone },
      { key: 'shortlisted', label: 'Worth reviewing', color: 'accent' as Tone },
      { key: 'preparing', label: 'Preparing application', color: 'info' as Tone },
      { key: 'awaiting_approval', label: 'Waiting for your review', color: 'warn' as Tone },
      { key: 'submitted_confirmed', label: 'Applied', color: 'success' as Tone },
    ]
    return stages.map((s) => {
      if (['discovered', 'shortlisted'].includes(s.key)) {
        const count = jobs.filter((j) => (j.status || 'discovered') === s.key).length
        return { ...s, count }
      }
      const count = applications.filter((a) => (a.status || 'discovered') === s.key).length
      return { ...s, count }
    })
  }, [jobs, applications])

  const firstName = profile?.full_name?.split(' ')[0] || 'there'

  if (loading && !jobs.length && !applications.length && !health) {
    return (
      <div className="space-y-5">
        <PageHeader title="Loading NS..." description="Getting everything ready for you." />
        <div className="text-center py-12 text-fg-muted">
          <Plus className="mx-auto h-8 w-8 animate-pulse text-accent" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <PageHeader
        title={`Good ${new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, ${firstName}`}
        description={new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}
      />

      {/* Health Alert */}
      {healthIssues.length > 0 && (
        <Card className="border-warn/30 bg-warn-soft/50">
          <CardHeader
            title="Some things need your attention"
            description={healthIssues.map((h) => h.message).join(' ')}
          />
          <div className="px-5 pb-3.5">
            {healthIssues.map((item) => (
              <div key={item.name} className="flex items-start gap-2.5 py-1.5">
                <Wrench size={15} className="mt-0.5 text-warn shrink-0" />
                <div>
                  <p className="text-sm font-medium text-fg">{item.name}</p>
                  <p className="text-xs text-fg-muted">{item.message}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* WHAT SHOULD I DO TODAY? */}
      <Card>
        <CardHeader
          title="What should I do today?"
          description={todaysTasks.length === 0 ? 'Nothing requires your attention right now.' : `${todaysTasks.length} item(s) need your attention`}
        />
        {todaysTasks.length === 0 ? (
          <div className="px-5 pb-5">
            <EmptyState
              icon={<CheckCircle size={24} />}
              title="All caught up!"
              description="You have no pending actions. New jobs and follow-ups will appear here automatically."
            />
            <div className="mt-4 flex justify-center">
              <Link to="/discover">
                <Button icon={<Compass size={16} />} variant="primary">Find new jobs</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-line">
            {todaysTasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between px-5 py-3.5 transition-colors hover:bg-surface-sunken/60">
                <div className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-surface-sunken text-xs">
                    {task.type === 'review' && <Send size={14} />}
                    {task.type === 'apply' && <Target size={14} />}
                    {task.type === 'followup' && <CalendarClock size={14} />}
                    {task.type === 'setup' && <Wrench size={14} />}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-fg">{task.title}</p>
                    <p className="text-xs text-fg-muted">{task.description}</p>
                  </div>
                </div>
                <Link to={task.actionTo}>
                  <Button size="sm" variant={task.tone === 'accent' ? 'primary' : 'secondary'}>
                    {task.action}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Jobs discovered"
          value={jobs.filter((j) => j.status === 'discovered').length}
          icon={<Target size={15} />}
        />
        <MetricCard
          label="Applications submitted"
          value={applications.filter((a) => a.status === 'submitted_confirmed').length}
          icon={<Send size={15} />}
        />
        <MetricCard
          label="Interviews"
          value={applications.filter((a) => a.status === 'interview').length}
          icon={<Users size={15} />}
        />
        <MetricCard
          label="Ready to apply"
          value={jobs.filter((j) => (j.match_score ?? 0) >= 25 && j.status === 'shortlisted').length}
          icon={<FileText size={15} />}
        />
      </div>

      {/* Application Pipeline */}
      <Card>
        <CardHeader title="Your application pipeline" description="Where your applications are at right now." />
        <div className="p-5">
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {pipeline.map((stage, idx) => (
              <div key={stage.key} className="flex items-center gap-2 shrink-0">
                <div className="flex flex-col items-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-sunken text-xs font-medium text-fg">
                    {stage.count}
                  </div>
                  <span className="mt-1 text-xs text-fg-muted">{stage.label}</span>
                </div>
                {idx < pipeline.length - 1 && <div className="w-6 border-t-2 border-line" />}
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader title="Quick actions" description="Common things you can do." />
        <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-3">
          <Link to="/discover">
            <Button className="justify-center" icon={<Compass size={16} />} variant="secondary">Find jobs</Button>
          </Link>
          <Link to="/applications">
            <Button className="justify-center" icon={<Target size={16} />} variant="secondary">My pipeline</Button>
          </Link>
          <Link to="/resumes">
            <Button className="justify-center" icon={<FileText size={16} />} variant="secondary">My resume</Button>
          </Link>
        </div>
      </Card>
    </div>
  )
}
