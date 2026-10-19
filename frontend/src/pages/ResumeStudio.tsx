import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Plus,
  Sparkles,
  Upload,
} from 'lucide-react'
import { MOCK_RESUME_BODY, MOCK_RESUMES } from '../data/mock'
import { useAppStore } from '../store/useAppStore'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  PageHeader,
  ProgressBar,
  cx,
  relativeTime,
} from '../components/ui'
import { DemoTag } from '../components/ui/data-display'
import { get } from '../services/api'

export interface Profile {
  full_name?: string
  email?: string
  phone?: string
  location?: string
}

const TIPS = [
  { label: 'Single column layout', ok: true },
  { label: 'Standard section headings', ok: true },
  { label: 'No tables or columns', ok: true },
  { label: 'Standard bullet characters', ok: true },
  { label: 'Contact info in header', ok: true },
  { label: 'Contains graphics or charts', ok: false },
]

export default function ResumeStudio() {
  const pushToast = useAppStore((s) => s.pushToast)
  const [activeId, setActiveId] = useState(MOCK_RESUMES[0].id)
  const [dragging, setDragging] = useState(false)
  const [profile, setProfile] = useState<Profile>({})

  useEffect(() => {
    get<Profile>('/profile/')
      .then((p) => setProfile(p || {}))
      .catch(() => {})
  }, [])

  const active = MOCK_RESUMES.find((r) => r.id === activeId) ?? MOCK_RESUMES[0]

  const displayName = profile.full_name || 'Candidate'
  const displayLocation = profile.location || ''
  const displayEmail = profile.email || ''
  const displayPhone = profile.phone || ''

  const simulateUpload = (name: string) => {
    pushToast({
      title: 'Resume uploaded',
      body: `${name} is queued for parsing. Connect the API to persist it.`,
      tone: 'accent',
    })
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Resume Studio"
        description="Manage versions, tailor to a role, and keep every version ATS-readable."
        actions={<DemoTag />}
      />

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-1">
          <Card
            className={cx(
              'border-dashed p-5 text-center transition-colors',
              dragging ? 'border-accent bg-accent-soft/40' : 'border-line',
            )}
          >
            <div
              onDragOver={(e: React.DragEvent) => {
                e.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e: React.DragEvent) => {
                e.preventDefault()
                setDragging(false)
                const file = e.dataTransfer.files?.[0]
                if (file) simulateUpload(file.name)
              }}
            >
            <span className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-surface-sunken text-accent ring-1 ring-line">
              <Upload size={18} />
            </span>
            <p className="text-sm font-medium text-fg">Drop a resume here</p>
            <p className="mt-1 text-xs text-fg-muted">PDF or DOCX, up to 10MB</p>
            <Button
              size="sm"
              className="mt-3"
              icon={<Plus size={13} />}
              onClick={() => simulateUpload('resume.pdf')}
            >
              Choose file
            </Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Your resumes" description={`${MOCK_RESUMES.length} versions`} />
            <ul className="divide-y divide-line">
              {MOCK_RESUMES.map((resume) => (
                <li key={resume.id}>
                  <button
                    onClick={() => setActiveId(resume.id)}
                    aria-current={activeId === resume.id ? 'true' : undefined}
                    className={cx(
                      'flex w-full items-start gap-2.5 px-4 py-3 text-left transition-colors',
                      activeId === resume.id ? 'bg-surface-sunken' : 'hover:bg-surface-sunken/60',
                    )}
                  >
                    <FileText
                      size={15}
                      className={cx('mt-0.5 shrink-0', activeId === resume.id ? 'text-accent' : 'text-fg-subtle')}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-medium text-fg">{resume.title}</span>
                      <span className="mt-0.5 block text-2xs text-fg-subtle">
                        {resume.pages} pages · updated {relativeTime(resume.updatedAt)}
                      </span>
                    </span>
                    {resume.isDefault && <Badge tone="accent">Default</Badge>}
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <div className="space-y-3 lg:col-span-2">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Card className="p-4">
              <p className="text-xs text-fg-muted">ATS score</p>
              <p className="tabular mt-1.5 text-2xl font-semibold text-accent">{active.atsScore}%</p>
              <ProgressBar value={active.atsScore} tone="accent" />
            </Card>
            <Card className="p-4">
              <p className="text-xs text-fg-muted">Pages</p>
              <p className="tabular mt-1.5 text-2xl font-semibold text-fg">{active.pages}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs text-fg-muted">Keywords</p>
              <p className="tabular mt-1.5 text-2xl font-semibold text-fg">{active.keywords}</p>
            </Card>
          </div>

          <Card>
            <CardHeader
              title={active.title}
              description="Document preview"
              actions={
                <>
                  <Button size="sm" icon={<Download size={13} />}>
                    PDF
                  </Button>
                  <Button size="sm" icon={<Download size={13} />}>
                    DOCX
                  </Button>
                </>
              }
            />
            <div className="bg-surface-sunken p-4">
              <article className="mx-auto max-w-2xl rounded-lg border border-line bg-surface-raised p-6 shadow-xs">
                <header className="border-b border-line pb-4">
                  <h2 className="text-lg font-semibold text-fg">{displayName}</h2>
                  <p className="mt-0.5 text-xs text-fg-muted">
                    {[displayLocation, displayEmail, displayPhone].filter(Boolean).join(' · ') || 'Complete your profile to see contact details here.'}
                  </p>
                </header>

                <section className="mt-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                    Summary
                  </h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-fg-muted">
                    {MOCK_RESUME_BODY.summary}
                  </p>
                </section>

                <section className="mt-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                    Skills
                  </h3>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {MOCK_RESUME_BODY.skills.map((skill) => (
                      <Badge key={skill} tone="neutral">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </section>

                <section className="mt-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-fg-subtle">
                    Experience
                  </h3>
                  <div className="mt-2 space-y-3">
                    {MOCK_RESUME_BODY.experience.map((role) => (
                      <div key={role.title}>
                        <div className="flex items-baseline justify-between gap-2">
                          <p className="text-xs font-semibold text-fg">{role.title}</p>
                          <p className="shrink-0 text-2xs text-fg-subtle">{role.period}</p>
                        </div>
                        <p className="text-xs text-fg-muted">{role.company}</p>
                        <ul className="mt-1 space-y-0.5">
                          {role.bullets.map((bullet) => (
                            <li key={bullet} className="text-xs leading-relaxed text-fg-muted">
                              · {bullet}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </section>
              </article>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Card>
              <CardHeader title="ATS formatting" description="Automated readability checks." />
              <ul className="divide-y divide-line">
                {TIPS.map((tip) => (
                  <li key={tip.label} className="flex items-center gap-2 px-4 py-2">
                    {tip.ok ? (
                      <CheckCircle2 size={14} className="shrink-0 text-accent" />
                    ) : (
                      <AlertTriangle size={14} className="shrink-0 text-warn" />
                    )}
                    <span className="text-xs text-fg-muted">{tip.label}</span>
                  </li>
                ))}
              </ul>
            </Card>

            <Card>
              <CardHeader
                title="Tailoring suggestions"
                description="Changes that would strengthen this version."
              />
              <ul className="divide-y divide-line">
                {[
                  'Add a GraphQL bullet — it appears in 4 of your target roles.',
                  'Lead the summary with your years of React experience.',
                  'Move the AWS line under a dedicated "Infrastructure" heading.',
                ].map((tip) => (
                  <li key={tip} className="flex items-start gap-2 px-4 py-2">
                    <Sparkles size={13} className="mt-0.5 shrink-0 text-accent" />
                    <span className="text-xs leading-relaxed text-fg-muted">{tip}</span>
                  </li>
                ))}
              </ul>
              <div className="border-t border-line p-3">
                <Button size="sm" variant="primary" icon={<Sparkles size={13} />} className="w-full">
                  Tailor to selected job
                </Button>
              </div>
            </Card>
          </div>

          <div className="flex items-start gap-2 rounded-lg bg-warn-soft p-3 ring-1 ring-inset ring-warn/20">
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-warn" />
            <p className="text-xs leading-relaxed text-warn">
              <strong className="font-medium">Verify before sending.</strong> Generated content is
              drafted from your profile and must be reviewed for accuracy before you submit it.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}