import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Briefcase, CalendarDays, FileSearch, Radar, Sparkles, TrendingUp } from 'lucide-react'
import { get } from '../services/api'
import type { DashboardSummary } from '../types'
import {
  Alert,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  LoadingBlock,
  PageHeader,
  StatCard,
} from '../components/ui'

interface TrendPoint {
  date: string
  label: string
  jobs_discovered: number
  applications_created: number
}

const PIE_COLORS = ['rgb(34 197 94)', 'rgb(96 165 250)', 'rgb(251 191 36)', 'rgb(248 113 113)']

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (fromDate) params.set('from_date', fromDate)
      if (toDate) params.set('to_date', toDate)
      const [summaryData, trendData] = await Promise.all([
        get<DashboardSummary>(`/dashboard/summary?${params.toString()}`),
        get<{ series: TrendPoint[] }>('/dashboard/trend?days=14'),
      ])
      setSummary(summaryData)
      setTrend(trendData.series || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [fromDate, toDate])

  useEffect(() => {
    load()
  }, [load])

  const clearDates = () => {
    setFromDate('')
    setToDate('')
  }

  if (loading && !summary) return <LoadingBlock label="Loading dashboard" />

  const cards = summary
    ? [
        { label: 'Jobs discovered', value: summary.total_jobs, icon: Radar },
        { label: 'Matching jobs', value: summary.matching_jobs, icon: Sparkles, hint: 'score > 0' },
        { label: 'Applications prepared', value: summary.prepared, icon: FileSearch },
        { label: 'Applications submitted', value: summary.submitted, icon: Briefcase },
        { label: 'Interviews', value: summary.interviews, icon: TrendingUp },
        { label: 'Offers', value: summary.offers, icon: Sparkles },
      ]
    : []

  const statusData = summary
    ? [
        { name: 'Submitted', value: summary.submitted },
        { name: 'Interviews', value: summary.interviews },
        { name: 'Offers', value: summary.offers },
        { name: 'Rejected', value: summary.rejected },
      ].filter((item) => item.value > 0)
    : []

  const hasTrendData = trend.some((p) => p.jobs_discovered > 0 || p.applications_created > 0)
  const totalInRange = trend.reduce(
    (sum, p) => sum + p.jobs_discovered + p.applications_created,
    0,
  )

  return (
    <div className="space-y-5">
      <PageHeader title="Overview" description="Pipeline health at a glance." />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

      <Card>
        <CardHeader
          title="Date range"
          description="Filters the pipeline totals below. Leave blank for all time."
          actions={
            <>
              <Button size="sm" onClick={load} loading={loading}>
                Apply
              </Button>
              {(fromDate || toDate) && (
                <Button size="sm" variant="ghost" onClick={clearDates}>
                  Clear
                </Button>
              )}
            </>
          }
        />
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
          <Field label="From">
            <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </Field>
          <Field label="To">
            <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </Field>
        </div>
      </Card>

      {summary && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
              hint={'hint' in card ? card.hint : undefined}
              icon={<card.icon size={14} />}
            />
          ))}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Card className="p-4 transition-all duration-200 hover:border-line-strong hover:shadow-md">
            <div className="text-xs font-medium tracking-wide text-fg-muted">
              Total applications
            </div>
            <div className="tabular mt-1.5 text-2xl font-semibold tracking-tight text-fg">
              {summary.applications}
            </div>
          </Card>
          <Card className="p-4 transition-all duration-200 hover:border-line-strong hover:shadow-md">
            <div className="text-xs font-medium tracking-wide text-fg-muted">Response rate</div>
            <div className="tabular mt-1.5 text-2xl font-semibold tracking-tight text-fg">
              {summary.response_rate}%
            </div>
          </Card>
          <Card className="p-4 transition-all duration-200 hover:border-line-strong hover:shadow-md">
            <div className="text-xs font-medium tracking-wide text-fg-muted">
              Upcoming follow-ups
            </div>
            <div className="tabular mt-1.5 text-2xl font-semibold tracking-tight text-fg">
              {summary.upcoming_follow_ups}
            </div>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Activity (last 14 days)"
            description={totalInRange > 0 ? 'Real counts from your database.' : 'No activity recorded yet.'}
          />
          <div className="p-4">
            {hasTrendData ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={trend} margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
                  <defs>
                    <linearGradient id="gradJobs" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgb(34 197 94)" />
                      <stop offset="100%" stopColor="rgb(34 197 94 / 0.35)" />
                    </linearGradient>
                    <linearGradient id="gradApps" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgb(96 165 250)" />
                      <stop offset="100%" stopColor="rgb(96 165 250 / 0.35)" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--line))" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: 'rgb(var(--fg-subtle))', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                    dy={4}
                  />
                  <YAxis
                    tick={{ fill: 'rgb(var(--fg-subtle))', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                    width={44}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgb(var(--fg-subtle) / 0.09)' }}
                    contentStyle={{
                      background: 'rgb(var(--surface-overlay))',
                      border: '1px solid rgb(var(--line))',
                      borderRadius: 10,
                      color: 'rgb(var(--fg))',
                      fontSize: 12,
                      boxShadow: 'var(--shadow-md)',
                    }}
                    labelStyle={{ color: 'rgb(var(--fg))', fontWeight: 600 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} iconType="circle" />
                  <Bar
                    dataKey="jobs_discovered"
                    name="Jobs discovered"
                    fill="url(#gradJobs)"
                    radius={[5, 5, 0, 0]}
                    maxBarSize={22}
                  />
                  <Bar
                    dataKey="applications_created"
                    name="Applications"
                    fill="url(#gradApps)"
                    radius={[5, 5, 0, 0]}
                    maxBarSize={22}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                icon={<CalendarDays size={24} />}
                title="No activity in this window"
                description="Discover jobs or create an application and the chart will populate."
              />
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Application status" description="Where your applications currently sit." />
          <div className="p-4">
            {statusData.length === 0 ? (
              <EmptyState
                icon={<Briefcase size={24} />}
                title="No applications yet"
                description="Prepare your first application from the Apply page."
              />
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <defs>
                    {PIE_COLORS.map((c, i) => (
                      <linearGradient key={i} id={`pieGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stopColor={c} stopOpacity={1} />
                        <stop offset="100%" stopColor={c} stopOpacity={0.55} />
                      </linearGradient>
                    ))}
                  </defs>
                  <Pie
                    data={statusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={52}
                    outerRadius={86}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {statusData.map((entry, index) => (
                      <Cell
                        key={entry.name}
                        fill={`url(#pieGrad${index % PIE_COLORS.length})`}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'rgb(var(--surface-overlay))',
                      border: '1px solid rgb(var(--line))',
                      borderRadius: 10,
                      color: 'rgb(var(--fg))',
                      fontSize: 12,
                      boxShadow: 'var(--shadow-md)',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}