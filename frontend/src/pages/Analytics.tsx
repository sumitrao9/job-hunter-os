import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Download, Timer, TrendingUp } from 'lucide-react'
import { APPLICATION_STAGES, MOCK_ACTIVITY, MOCK_SOURCES, STAGE_LABELS } from '../data/mock'
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Select,
} from '../components/ui'
import { DemoTag, MetricCard } from '../components/ui/data-display'

const TOOLTIP = {
  background: 'rgb(var(--surface-overlay))',
  border: '1px solid rgb(var(--line))',
  borderRadius: 10,
  color: 'rgb(var(--fg))',
  fontSize: 12,
  boxShadow: 'var(--shadow-md)',
}

const RANGES = ['7 days', '30 days', '90 days'] as const

/** Match distribution buckets, used for the histogram. */
const MATCH_BUCKETS = [
  { label: '0–20', value: 1844 },
  { label: '21–40', value: 0 },
  { label: '41–60', value: 101 },
  { label: '61–80', value: 7 },
  { label: '81–100', value: 0 },
]

const STAGE_FUNNEL = APPLICATION_STAGES.filter((s) =>
  ['discovered', 'shortlisted', 'submitted', 'assessment', 'interview', 'offer'].includes(s),
).map((stage, i) => ({ name: STAGE_LABELS[stage], value: [120, 42, 14, 8, 5, 1][i] }))

export default function Analytics() {
  const [range, setRange] = useState<(typeof RANGES)[number]>('30 days')

  const slice = useMemo(() => {
    const days = range === '7 days' ? 7 : range === '30 days' ? 14 : 14
    return MOCK_ACTIVITY.slice(-days)
  }, [range])

  const exportCsv = () => {
    const header = 'date,discovered,applied,interviews'
    const rows = slice.map((d) => `${d.date},${d.discovered},${d.applied},${d.interviews}`)
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ns-analytics-${range.replace(' ', '-')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const headline = [
    { label: 'Response rate', value: '18%', delta: 4, icon: <TrendingUp size={15} /> },
    { label: 'Interview conversion', value: '36%', delta: 2, icon: <TrendingUp size={15} /> },
    { label: 'Avg response time', value: '6.2 days', delta: -12, icon: <Timer size={15} /> },
    { label: 'Offers', value: 1, delta: 0, icon: <TrendingUp size={15} /> },
  ]

  return (
    <div className="space-y-5">
      <PageHeader
        title="Analytics"
        description="How your search is performing over time."
        actions={
          <>
            <Select
              value={range}
              onChange={(e) => setRange(e.target.value as (typeof RANGES)[number])}
              className="w-36"
              aria-label="Date range"
            >
              {RANGES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
            <Button size="md" icon={<Download size={14} />} onClick={exportCsv}>
              Export CSV
            </Button>
          </>
        }
      />

      <div className="flex items-center gap-2">
        <DemoTag label="Demo data" />
        <span className="text-xs text-fg-muted">
          These figures are illustrative and not drawn from your real applications.
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {headline.map((m) => (
          <MetricCard key={m.label} label={m.label} value={m.value} delta={m.delta} icon={m.icon} />
        ))}
      </div>

      <Card>
        <CardHeader title="Applications over time" description={`Last ${slice.length} days`} />
        <div className="p-4">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={slice} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--line))" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: 'rgb(var(--fg-subtle))', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                dy={4}
              />
              <YAxis
                tick={{ fill: 'rgb(var(--fg-subtle))', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
                width={46}
              />
              <Tooltip contentStyle={TOOLTIP} labelStyle={{ color: 'rgb(var(--fg))', fontWeight: 600 }} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} iconType="circle" />
              <Line
                type="monotone"
                dataKey="applied"
                name="Applications"
                stroke="rgb(34 197 94)"
                strokeWidth={2}
                dot={{ r: 2.5 }}
              />
              <Line
                type="monotone"
                dataKey="interviews"
                name="Interviews"
                stroke="rgb(234 179 8)"
                strokeWidth={2}
                dot={{ r: 2.5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <Card>
          <CardHeader title="Applications by source" />
          <div className="p-4">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Tooltip contentStyle={TOOLTIP} />
                <Pie
                  data={MOCK_SOURCES}
                  dataKey="count"
                  nameKey="name"
                  innerRadius={48}
                  outerRadius={80}
                  paddingAngle={3}
                  strokeWidth={0}
                >
                  {MOCK_SOURCES.map((s) => (
                    <Cell key={s.name} fill={s.color} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader title="Match score distribution" description="How jobs score against your profile." />
          <div className="p-4">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={MATCH_BUCKETS} margin={{ left: -18, right: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--line))" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'rgb(var(--fg-subtle))', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: 'rgb(var(--fg-subtle))', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={52}
                />
                <Tooltip contentStyle={TOOLTIP} cursor={{ fill: 'rgb(var(--fg-subtle) / 0.08)' }} />
                <Bar dataKey="value" name="Jobs" fill="rgb(34 197 94)" radius={[4, 4, 0, 0]} maxBarSize={34} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader title="Pipeline funnel" description="Where applications drop off." />
          <div className="space-y-2 p-4">
            {STAGE_FUNNEL.map((stage, i) => {
              const max = STAGE_FUNNEL[0].value || 1
              const pct = Math.round((stage.value / max) * 100)
              return (
                <div key={stage.name}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-fg-muted">{stage.name}</span>
                    <span className="tabular text-fg">{stage.value}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                    <div
                      className="h-full rounded-full transition-[width] duration-500"
                      style={{
                        width: `${pct}%`,
                        background: `hsl(${142 - i * 8} 60% ${45 - i * 2}%)`,
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {slice.length === 0 && (
        <EmptyState title="No data in this range" description="Widen the date range to see activity." />
      )}
    </div>
  )
}