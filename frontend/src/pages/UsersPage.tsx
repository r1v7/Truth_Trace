import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { Role, User } from '../api/types'
import { Avatar } from '../components/Mark'
import { Section } from '../components/Section'
import { useAuth } from '../auth'

const ROLES: Role[] = ['investigator', 'supervisor', 'admin']

export function UsersPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const isAdmin = user?.role === 'admin'

  async function load() {
    setError(null)
    try {
      const { data } = await api.get<User[]>('/auth/users')
      setUsers(data)
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      setError(status === 403 ? t('users.forbidden') : t('common.error'))
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    setError(null)
    try {
      await api.post('/auth/users', {
        email: form.get('email'),
        full_name: form.get('full_name'),
        password: form.get('password'),
        role: form.get('role'),
      })
      element.reset()
      setShowForm(false)
      await load()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(typeof detail === 'string' ? detail : t('common.error'))
    }
  }

  return (
    <div className="space-y-6">
      <div className="tt-rise">
        <div className="tt-label mb-2 text-[var(--color-accent)]">{t('users.eyebrow')}</div>
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.02em]">{t('users.title')}</h1>
        <p className="mt-2 mb-0 max-w-3xl text-[var(--color-muted)]">{t('users.blurb')}</p>
      </div>

      <Section
        title={t('users.accounts')}
        aside={isAdmin ? undefined : t('users.readOnly')}
      >
        {isAdmin && (
          <div className="mb-4">
            <button onClick={() => setShowForm((v) => !v)} className="tt-btn tt-btn-primary">
              {t('users.add')}
            </button>
          </div>
        )}

        {showForm && isAdmin && (
          <form onSubmit={create} className="tt-fade mb-5 flex flex-wrap items-end gap-3">
            <label className="block">
              <span className="tt-label mb-2 block">{t('users.name')}</span>
              <input name="full_name" required className="tt-field w-48" />
            </label>
            <label className="block">
              <span className="tt-label mb-2 block">{t('users.email')}</span>
              <input name="email" type="email" required className="tt-field w-64" />
            </label>
            <label className="block">
              <span className="tt-label mb-2 block">{t('users.password')}</span>
              <input
                name="password"
                type="password"
                required
                minLength={10}
                className="tt-field w-48"
              />
            </label>
            <label className="block">
              <span className="tt-label mb-2 block">{t('users.role')}</span>
              <select name="role" defaultValue="investigator" className="tt-field w-44">
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {t(`role.${role}`)}
                  </option>
                ))}
              </select>
            </label>
            <button className="tt-btn tt-btn-primary">{t('common.save')}</button>
          </form>
        )}

        {error && <p className="mb-3 text-[13px] text-[var(--color-danger)]">{error}</p>}

        {users.length > 0 && (
          <ul className="space-y-2">
            {users.map((u) => (
              <li
                key={u.id}
                className="flex flex-wrap items-center gap-3 rounded-xl border border-[var(--color-line)] bg-[var(--color-surface-2)] p-3"
              >
                <Avatar name={u.full_name} tone={u.role === 'admin' ? 'violet' : 'accent'} />
                <div className="min-w-0">
                  <p dir="auto" className="m-0 font-medium">
                    {u.full_name}
                  </p>
                  <p className="tt-mono m-0 text-[11.5px] text-[var(--color-muted)]">{u.email}</p>
                </div>
                <span className="tt-tag ms-auto">{t(`role.${u.role}`)}</span>
                {!u.is_active && (
                  <span className="tt-tag" style={{ color: 'var(--color-warn)' }}>
                    {t('users.inactive')}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title={t('users.whatRolesDo')}>
        <dl className="m-0 grid gap-4 sm:grid-cols-3">
          {ROLES.map((role) => (
            <div key={role}>
              <dt className="tt-label mb-1.5 text-[var(--color-accent)]">{t(`role.${role}`)}</dt>
              <dd className="m-0 text-[13px] leading-relaxed text-[var(--color-muted)]">
                {t(`users.roleHelp.${role}`)}
              </dd>
            </div>
          ))}
        </dl>
      </Section>
    </div>
  )
}
