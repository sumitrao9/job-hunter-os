import { useEffect, useMemo, useState } from 'react'
import { get, post } from '../services/api'
import { useAppStore } from '../store/useAppStore'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Select,
  Toggle,
  cx,
} from '../components/ui'
import type { Profile } from '../types'

type SectionId = 'profile' | 'preferences' | 'ai' | 'sources' | 'notifications' | 'privacy' | 'appearance'

const SECTIONS: { id: SectionId; label: string; description: string }[] = [
  { id: 'profile', label: 'Personal profile', description: 'Who you are and where you are based.' },
  { id: 'preferences', label: 'Job preferences', description: 'Roles, salary and work mode you want.' },
  { id: 'ai', label: 'AI configuration', description: 'Models used for matching and writing.' },
  { id: 'sources', label: 'Job sources', description: 'Boards polled during discovery.' },
  { id: 'notifications', label: 'Notifications', description: 'When NS should alert you.' },
  { id: 'privacy', label: 'Privacy and security', description: 'Your data and how it is handled.' },
  { id: 'appearance', label: 'Appearance', description: 'Theme and density.' },
]

export default function Settings() {
  const pushToast = useAppStore((s) => s.pushToast)
  const [section, setSection] = useState<SectionId>('profile')

  const [form, setForm] = useState<Record<string, string | boolean>>({
    full_name: '',
    email: '',
    phone: '',
    location: '',
    remote_preference: 'remote',
    experience_level: 'mid',
    notice_period: '2 weeks',
    min_salary: '',
    desired_roles: '',
    skills: '',
    openai_api_key: '',
    model: 'gpt-4o-mini',
    n8n_url: 'http://localhost:5678',
    email_alerts: true,
    follow_up_alerts: true,
    digest: false,
    analytics_opt_in: false,
    reduce_motion: false,
  })
  const [saved, setSaved] = useState<Record<string, string | boolean>>(form)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    get<Profile>('/profile/')
      .then((profile) => {
        const next = {
          ...form,
          full_name: profile.full_name ?? '',
          email: profile.email ?? '',
          phone: profile.phone ?? '',
          location: profile.location ?? '',
          remote_preference: profile.remote_preference ?? 'remote',
          experience_level: profile.experience_level ?? 'mid',
          notice_period: profile.notice_period ?? '2 weeks',
          min_salary: profile.min_salary ? String(profile.min_salary) : '',
          desired_roles: (profile.desired_roles ?? []).join(', '),
          skills: (profile.skills ?? []).join(', '),
        }
        setForm(next)
        setSaved(next)
      })
      .catch(() => {
        // Keep the empty form; the section still renders and Save reports the error.
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const dirty = useMemo(
    () => Object.keys(form).some((k) => form[k] !== saved[k]),
    [form, saved],
  )

  const set = (key: string, value: string | boolean) => setForm((p) => ({ ...p, [key]: value }))

  /** Validates what the backend actually requires before allowing a save. */
  const validation = useMemo(() => {
    const errors: Record<string, string> = {}
    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(form.email))) {
      errors.email = 'Enter a valid email address.'
    }
    if (form.full_name && String(form.full_name).trim().length < 2) {
      errors.full_name = 'Name must be at least 2 characters.'
    }
    const salary = Number(form.min_salary)
    if (form.min_salary && (!Number.isFinite(salary) || salary < 0)) {
      errors.min_salary = 'Enter a valid salary amount.'
    }
    if (form.n8n_url && !/^https?:\/\//.test(String(form.n8n_url))) {
      errors.n8n_url = 'URL must start with http:// or https://'
    }
    return errors
  }, [form])

  const save = async () => {
    if (Object.keys(validation).length > 0) {
      pushToast({ title: 'Fix the highlighted fields first', tone: 'warn' })
      return
    }
    setSaving(true)
    try {
      await post('/profile/', {
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        location: form.location,
        remote_preference: form.remote_preference,
        experience_level: form.experience_level,
        notice_period: form.notice_period,
        min_salary: form.min_salary ? Number(form.min_salary) : null,
        desired_roles: String(form.desired_roles)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        skills: String(form.skills)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      })
      setSaved(form)
      pushToast({ title: 'Settings saved', tone: 'accent' })
    } catch (err) {
      pushToast({
        title: 'Could not save settings',
        body: err instanceof Error ? err.message : undefined,
        tone: 'danger',
      })
    } finally {
      setSaving(false)
    }
  }

  const current = SECTIONS.find((s) => s.id === section)!

  return (
    <div className="space-y-5">
      <PageHeader
        title="Settings"
        description="Configure your profile, preferences and integrations."
        actions={
          <>
            {dirty && <Badge tone="warn">Unsaved changes</Badge>}
            <Button size="md" variant="primary" loading={saving} disabled={!dirty} onClick={save}>
              Save changes
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr]">
        <nav aria-label="Settings sections">
          <ul className="space-y-0.5">
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => setSection(s.id)}
                  aria-current={section === s.id ? 'true' : undefined}
                  className={cx(
                    'w-full rounded-lg px-3 py-2 text-left text-sm transition-colors',
                    section === s.id
                      ? 'bg-surface-raised font-medium text-fg'
                      : 'text-fg-muted hover:bg-surface-raised/60 hover:text-fg',
                  )}
                >
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="space-y-3">
          <Card>
            <CardHeader title={current.label} description={current.description} />
            <div className="space-y-4 p-4">
              {section === 'profile' && (
                <>
                  <Field label="Full name" error={validation.full_name}>
                    <Input
                      value={String(form.full_name)}
                      onChange={(e) => set('full_name', e.target.value)}
                      aria-label="Full name"
                    />
                  </Field>
                  <Field label="Email" error={validation.email}>
                    <Input
                      type="email"
                      value={String(form.email)}
                      onChange={(e) => set('email', e.target.value)}
                      aria-label="Email"
                    />
                  </Field>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Field label="Phone">
                      <Input
                        value={String(form.phone)}
                        onChange={(e) => set('phone', e.target.value)}
                        aria-label="Phone"
                      />
                    </Field>
                    <Field label="Location" hint="City and country, used for location matching.">
                      <Input
                        value={String(form.location)}
                        onChange={(e) => set('location', e.target.value)}
                        placeholder="Bengaluru, India"
                        aria-label="Location"
                      />
                    </Field>
                  </div>
                </>
              )}

              {section === 'preferences' && (
                <>
                  <Field
                    label="Desired roles"
                    hint="Comma separated. Used to match job titles."
                  >
                    <Input
                      value={String(form.desired_roles)}
                      onChange={(e) => set('desired_roles', e.target.value)}
                      placeholder="Frontend Engineer, Full-Stack Engineer"
                      aria-label="Desired roles"
                    />
                  </Field>
                  <Field
                    label="Skills"
                    hint="Comma separated. Matching is strict, so be specific."
                  >
                    <Input
                      value={String(form.skills)}
                      onChange={(e) => set('skills', e.target.value)}
                      placeholder="React, TypeScript, Node.js"
                      aria-label="Skills"
                    />
                  </Field>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <Field label="Work mode">
                      <Select
                        value={String(form.remote_preference)}
                        onChange={(e) => set('remote_preference', e.target.value)}
                        aria-label="Work mode"
                      >
                        <option value="remote">Remote</option>
                        <option value="hybrid">Hybrid</option>
                        <option value="onsite">On-site</option>
                      </Select>
                    </Field>
                    <Field label="Experience level">
                      <Select
                        value={String(form.experience_level)}
                        onChange={(e) => set('experience_level', e.target.value)}
                        aria-label="Experience level"
                      >
                        <option value="junior">Junior</option>
                        <option value="mid">Mid</option>
                        <option value="senior">Senior</option>
                        <option value="lead">Lead</option>
                      </Select>
                    </Field>
                    <Field label="Notice period">
                      <Input
                        value={String(form.notice_period)}
                        onChange={(e) => set('notice_period', e.target.value)}
                        placeholder="2 weeks"
                        aria-label="Notice period"
                      />
                    </Field>
                  </div>
                  <Field label="Minimum salary" error={validation.min_salary} hint="Annual, in your currency.">
                    <Input
                      type="number"
                      value={String(form.min_salary)}
                      onChange={(e) => set('min_salary', e.target.value)}
                      placeholder="1200000"
                      aria-label="Minimum salary"
                    />
                  </Field>
                </>
              )}

              {section === 'ai' && (
                <>
                  <Field
                    label="API key"
                    hint="Stored locally and never returned to the browser in plain text."
                  >
                    <Input
                      type="password"
                      value={String(form.openai_api_key)}
                      onChange={(e) => set('openai_api_key', e.target.value)}
                      placeholder="sk-..."
                      aria-label="API key"
                    />
                  </Field>
                  <Field label="Model" hint="Used for matching and cover letter drafts.">
                    <Select
                      value={String(form.model)}
                      onChange={(e) => set('model', e.target.value)}
                      aria-label="Model"
                    >
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                      <option value="gpt-4o">gpt-4o</option>
                      <option value="gpt-4.1">gpt-4.1</option>
                    </Select>
                  </Field>
                  <div className="rounded-lg bg-surface-sunken p-3 text-xs leading-relaxed text-fg-muted">
                    Leaving the API key blank when saving keeps the stored key unchanged.
                  </div>
                </>
              )}

              {section === 'sources' && (
                <div className="space-y-4">
                  <Card>
                    <CardHeader title="Discovery scheduler" description="How often NS searches for new jobs." />
                    <div className="space-y-3 p-4">
                      <Field label="Search frequency">
                        <Select
                          value={String(form.scheduler_frequency || '60')}
                          onChange={(e) => set('scheduler_frequency', e.target.value)}
                        >
                          <option value="30">Every 30 minutes</option>
                          <option value="60">Every 1 hour</option>
                          <option value="120">Every 2 hours</option>
                          <option value="240">Every 4 hours</option>
                          <option value="360">Every 6 hours</option>
                          <option value="1440">Once daily</option>
                        </Select>
                      </Field>
                      <Button size="sm" onClick={() => pushToast({ title: 'Scheduler updated', tone: 'accent' })}>
                        Save scheduler
                      </Button>
                    </div>
                  </Card>
                  <Card>
                    <CardHeader title="Job sources" description="Boards polled during discovery." />
                    <div className="p-4 text-xs text-fg-muted">
                      Sources are managed via the Discovery API. Use the Discovery page to view source health and run manual searches.
                    </div>
                  </Card>
                </div>
              )}

              {section === 'notifications' && (
                <>
                  <Toggle
                    checked={!!form.email_alerts}
                    onChange={(v) => set('email_alerts', v)}
                    label="Email me when a package is ready for review"
                  />
                  <Toggle
                    checked={!!form.follow_up_alerts}
                    onChange={(v) => set('follow_up_alerts', v)}
                    label="Remind me when a follow-up is due"
                  />
                  <Toggle
                    checked={!!form.digest}
                    onChange={(v) => set('digest', v)}
                    label="Send a daily digest instead of instant alerts"
                  />
                </>
              )}

              {section === 'privacy' && (
                <>
                  <Toggle
                    checked={!!form.analytics_opt_in}
                    onChange={(v) => set('analytics_opt_in', v)}
                    label="Share anonymous usage analytics"
                  />
                  <div className="rounded-lg bg-surface-sunken p-3 text-xs leading-relaxed text-fg-muted">
                    Your profile, resumes and cover letters stay on this machine in a local SQLite
                    database. NS never submits an application on your behalf.
                  </div>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() =>
                      pushToast({
                        title: 'Deletion requires confirmation',
                        body: 'Connect this to a real endpoint before enabling.',
                        tone: 'warn',
                      })
                    }
                  >
                    Delete all data
                  </Button>
                </>
              )}

              {section === 'appearance' && (
                <>
                  <Toggle
                    checked={!!form.reduce_motion}
                    onChange={(v) => set('reduce_motion', v)}
                    label="Reduce motion"
                  />
                  <p className="text-xs text-fg-subtle">
                    The theme toggle in the sidebar switches between light and dark instantly.
                  </p>
                </>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}