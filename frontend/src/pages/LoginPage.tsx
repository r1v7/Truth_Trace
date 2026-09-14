import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'

export function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(false)
    try {
      await login(email, password)
      navigate('/cases')
    } catch {
      setError(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-16 max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="mb-1 text-xl font-semibold">{t('app.name')}</h1>
      <p className="mb-6 text-sm text-slate-500">{t('app.tagline')}</p>

      <label className="mb-1 block text-sm font-medium">{t('login.email')}</label>
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="mb-4 w-full rounded border border-slate-300 px-3 py-2"
      />

      <label className="mb-1 block text-sm font-medium">{t('login.password')}</label>
      <input
        type="password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="mb-4 w-full rounded border border-slate-300 px-3 py-2"
      />

      {error && <p className="mb-3 text-sm text-red-600">{t('login.error')}</p>}

      <button
        type="submit"
        disabled={busy}
        className="w-full rounded bg-slate-900 py-2 text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {busy ? t('common.loading') : t('login.submit')}
      </button>
    </form>
  )
}
