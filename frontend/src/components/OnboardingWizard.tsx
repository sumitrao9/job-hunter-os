import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { get, post } from '../services/api'
import type { Profile } from '../types'
import {
  Alert,
  Button,
  Card,
  Field,
  Input,
  LoadingBlock,
  ProgressBar,
  Textarea,
  cx,
} from '../components/ui'

const emptyProfile: Profile = {
  full_name: '',
  email: '',
  phone: '',
  location: '',
  preferred_locations: [],
  skills: [],
  desired_roles: [],
  min_salary: undefined,
  preferred_salary: undefined,
  remote_preference: '',
  experience_level: '',
  notice_period: '',
  preferred_industries: [],
  search_keywords: [],
  search_exclusions: [],
}

const STEPS = ['Basics', 'Preferences', 'Skills']

const toList = (value: string) =>
  value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

export default function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<Profile>(emptyProfile)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const check = useCallback(async () => {
    setLoading(true)
    try {
      const status = await get<{ completed: boolean }>('/onboarding/status')
      if (status.completed) onComplete()
    } catch {
      // A missing onboarding record means setup has not started yet.
    } finally {
      setLoading(false)
    }
  }, [onComplete])

  useEffect(() => {
    void check()
  }, [check])

  const update = <K extends keyof Profile>(field: K, value: Profile[K]) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  const stepValid = () => {
    if (step === 0) {
      return !!(form.full_name?.trim() && form.email?.trim() && form.location?.trim())
    }
    if (step === 1) return !!form.desired_roles?.length
    return !!form.skills?.length
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!stepValid()) {
      setError('Fill in the required fields before continuing.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await post('/profile/', form)
      onComplete()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
      setSaving(false)
    }
  }

  const next = () => {
    if (!stepValid()) {
      setError('Fill in the required fields before continuing.')
      return
    }
    setError(null)
    setStep((s) => Math.min(s + 1, STEPS.length - 1))
  }

  const back = () => {
    setError(null)
    setStep((s) => Math.max(s - 1, 0))
  }

  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center bg-surface">
        <LoadingBlock label="Preparing setup" />
      </div>
    )
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-surface px-4 py-10">
      <div className="w-full max-w-lg">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-sm font-bold text-accent-fg">
            JH
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-fg">Welcome to NS</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Three quick steps. Your profile drives match scoring and every application.
          </p>
        </div>

        <Card>
          <div className="border-b border-line px-4 py-3">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="font-medium text-fg">
                Step {step + 1} of {STEPS.length}: {STEPS[step]}
              </span>
              <span className="text-fg-subtle">{Math.round(((step + 1) / STEPS.length) * 100)}%</span>
            </div>
            <ProgressBar value={((step + 1) / STEPS.length) * 100} />
            <div className="mt-2 flex justify-between">
              {STEPS.map((label, i) => (
                <span
                  key={label}
                  className={cx(
                    'text-[11px]',
                    i <= step ? 'text-accent' : 'text-fg-subtle',
                  )}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 p-4">
            {step === 0 && (
              <>
                <Field label="Full name" required>
                  <Input
                    value={form.full_name || ''}
                    onChange={(e) => update('full_name', e.target.value)}
                    placeholder="Your name"
                    autoFocus
                  />
                </Field>
                <Field label="Email" required>
                  <Input
                    type="email"
                    value={form.email || ''}
                    onChange={(e) => update('email', e.target.value)}
                    placeholder="you@example.com"
                  />
                </Field>
                <Field label="Phone">
                  <Input
                    value={form.phone || ''}
                    onChange={(e) => update('phone', e.target.value)}
                  />
                </Field>
                <Field label="Location" required hint="City and country, e.g. Bengaluru, India">
                  <Input
                    value={form.location || ''}
                    onChange={(e) => update('location', e.target.value)}
                    placeholder="City, Country"
                  />
                </Field>
              </>
            )}

            {step === 1 && (
              <>
                <Field label="Desired roles" required hint="Comma separated job titles.">
                  <Input
                    value={(form.desired_roles || []).join(', ')}
                    onChange={(e) => update('desired_roles', toList(e.target.value))}
                    placeholder="Frontend Developer, React Engineer"
                    autoFocus
                  />
                </Field>
                <Field label="Remote preference" hint="remote, hybrid, or onsite">
                  <Input
                    value={form.remote_preference || ''}
                    onChange={(e) => update('remote_preference', e.target.value)}
                    placeholder="remote"
                  />
                </Field>
                <Field label="Experience level" hint="junior, mid, or senior">
                  <Input
                    value={form.experience_level || ''}
                    onChange={(e) => update('experience_level', e.target.value)}
                    placeholder="mid"
                  />
                </Field>
                <Field label="Minimum salary" hint="Optional. Used to filter out low-paying roles.">
                  <Input
                    type="number"
                    value={form.min_salary ?? ''}
                    onChange={(e) =>
                      update('min_salary', e.target.value ? Number(e.target.value) : undefined)
                    }
                  />
                </Field>
              </>
            )}

            {step === 2 && (
              <>
                <Field label="Skills" required hint="Comma separated.">
                  <Textarea
                    rows={4}
                    value={(form.skills || []).join(', ')}
                    onChange={(e) => update('skills', toList(e.target.value))}
                    placeholder="React, TypeScript, Node.js, Python"
                    autoFocus
                  />
                </Field>
                <Field label="Search keywords" hint="Extra terms used to rank jobs.">
                  <Input
                    value={(form.search_keywords || []).join(', ')}
                    onChange={(e) => update('search_keywords', toList(e.target.value))}
                    placeholder="remote, contract, startup"
                  />
                </Field>
              </>
            )}

            {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}

            <div className="flex items-center justify-between pt-1">
              <Button
                type="button"
                variant="ghost"
                onClick={back}
                disabled={step === 0}
                icon={<ArrowLeft size={14} />}
              >
                Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button type="button" variant="primary" onClick={next} icon={<ArrowRight size={14} />}>
                  Next
                </Button>
              ) : (
                <Button
                  type="submit"
                  variant="primary"
                  loading={saving}
                  icon={<Check size={14} />}
                >
                  Finish setup
                </Button>
              )}
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}