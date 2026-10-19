import { useCallback, useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import { get, post } from '../services/api'
import type { Profile } from '../types'
import {
  Alert,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  PageHeader,
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

function toList(value: string): string[] {
  return value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

export default function Profile() {
  const [form, setForm] = useState<Profile>(emptyProfile)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await get<Profile>('/profile/')
      setForm((prev) => ({ ...prev, ...data }))
    } catch {
      // A missing profile is expected on first run.
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const update = <K extends keyof Profile>(field: K, value: Profile[K]) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setSaving(true)
    try {
      await post('/profile/', form)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const listField = (
    label: string,
    hint: string,
    value: string[] | undefined,
    onChange: (v: string[]) => void,
  ) => (
    <Field label={label} hint={hint}>
      <Input
        value={(value || []).join(', ')}
        onChange={(e) => onChange(toList(e.target.value))}
        placeholder="react, typescript, node"
      />
    </Field>
  )

  return (
    <div className="space-y-5">
      <PageHeader
        title="Profile"
        description="Your profile drives match scoring and every generated application."
      />

      {error && <Alert tone="danger" onDismiss={() => setError(null)}>{error}</Alert>}
      {saved && <Alert tone="success" onDismiss={() => setSaved(false)}>Profile saved.</Alert>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Card>
          <CardHeader title="Basics" />
          <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
            <Field label="Full name">
              <Input value={form.full_name || ''} onChange={(e) => update('full_name', e.target.value)} />
            </Field>
            <Field label="Email">
              <Input
                type="email"
                value={form.email || ''}
                onChange={(e) => update('email', e.target.value)}
              />
            </Field>
            <Field label="Phone">
              <Input value={form.phone || ''} onChange={(e) => update('phone', e.target.value)} />
            </Field>
            <Field label="Location">
              <Input value={form.location || ''} onChange={(e) => update('location', e.target.value)} />
            </Field>
          </div>
        </Card>

        <Card>
          <CardHeader title="Preferences" />
          <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
            <Field label="Minimum salary">
              <Input
                type="number"
                value={form.min_salary ?? ''}
                onChange={(e) =>
                  update('min_salary', e.target.value ? Number(e.target.value) : undefined)
                }
              />
            </Field>
            <Field label="Preferred salary">
              <Input
                type="number"
                value={form.preferred_salary ?? ''}
                onChange={(e) =>
                  update('preferred_salary', e.target.value ? Number(e.target.value) : undefined)
                }
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
            <Field label="Notice period">
              <Input
                value={form.notice_period || ''}
                onChange={(e) => update('notice_period', e.target.value)}
                placeholder="2 weeks"
              />
            </Field>
          </div>
        </Card>

        <Card>
          <CardHeader title="Skills and search" description="Comma separated lists." />
          <div className="grid grid-cols-1 gap-4 p-4">
            {listField('Skills', 'Your technical and professional skills.', form.skills, (v) =>
              update('skills', v),
            )}
            {listField(
              'Desired roles',
              'Job titles you want to be matched with.',
              form.desired_roles,
              (v) => update('desired_roles', v),
            )}
            {listField(
              'Search keywords',
              'Extra terms used to rank jobs.',
              form.search_keywords,
              (v) => update('search_keywords', v),
            )}
            {listField(
              'Exclusions',
              'Terms that disqualify a job from your feed.',
              form.search_exclusions,
              (v) => update('search_exclusions', v),
            )}
          </div>
        </Card>

        <Button type="submit" variant="primary" loading={saving} disabled={loading} icon={<Save size={14} />}>
          Save profile
        </Button>
      </form>
    </div>
  )
}