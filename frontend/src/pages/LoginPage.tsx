import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import { Mark } from '../components/Mark'
import { ThemeToggle } from '../components/ThemeToggle'
import { setLanguage, type Language } from '../i18n'

export function LoginPage() {
  const { t, i18n } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const other: Language = i18n.language === 'ar' ? 'en' : 'ar'

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
    <div className="grid min-h-screen items-stretch [grid-template-columns:repeat(auto-fit,minmax(330px,1fr))]">
      <section className="relative flex min-w-0 flex-col justify-between gap-11 overflow-hidden border-e border-[var(--color-line)] px-12 py-14">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(900px 480px at 8% 12%, rgba(53,224,196,.14), transparent 60%),' +
              'radial-gradient(700px 420px at 90% 88%, rgba(155,140,255,.13), transparent 62%)',
          }}
        />

        <div className="relative flex items-center gap-3">
          <Mark />
          <span className="tt-wordmark text-[12px] font-bold uppercase tracking-[0.3em]">
            {t('app.name')}
          </span>
        </div>

        <div className="tt-rise relative max-w-[480px]">
          <div className="tt-label mb-4 text-[11px] tracking-[0.24em] text-[var(--color-accent)]">
            {t('login.eyebrow')}
          </div>
          <p className="m-0 mb-5 text-[38px] font-semibold leading-[1.12] tracking-[-0.02em]">
            {/* The headline is written as separate lines in both languages; keep them. */}
            {t('login.headlineTop')
              .split('\n')
              .map((line) => (
                <span key={line} className="block">
                  {line}
                </span>
              ))}
            <span className="block text-[var(--color-danger)]">{t('login.headlineAccent')}</span>
          </p>
          <p className="m-0 max-w-[430px] text-[var(--color-muted)]">{t('login.blurb')}</p>
        </div>

        <div className="tt-mono relative flex flex-wrap items-center gap-5 text-[11px] text-[var(--color-muted-dim)]">
          <span>{t('login.version')}</span>
          <span className="flex items-center gap-2">
            <span className="relative inline-flex h-2 w-2 flex-none">
              <span className="absolute inset-0 rounded-full bg-[var(--color-accent)]" />
              <span
                className="absolute inset-0 rounded-full bg-[var(--color-accent)]"
                style={{ animation: 'tt-halo 2s ease-out infinite' }}
              />
            </span>
            {t('login.online')}
          </span>
          <button onClick={() => setLanguage(other)} className="tt-link">
            {t('nav.language')}
          </button>
          <ThemeToggle compact />
        </div>
      </section>

      <section className="flex items-center justify-center px-8 py-14">
        <form onSubmit={submit} className="tt-fade w-full max-w-[360px]">
          <h1 className="m-0 mb-2 text-[26px] font-semibold tracking-[-0.01em]">
            {t('login.title')}
          </h1>
          <p className="m-0 mb-8 text-[12px] text-[var(--color-muted)]">
            {t('login.auditNote')}
          </p>

          <label className="tt-label mb-2 block">{t('login.email')}</label>
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="tt-field mb-5"
          />

          <label className="tt-label mb-2 block">{t('login.password')}</label>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="tt-field mb-6"
          />

          {error && (
            <p className="mb-4 text-[13px] text-[var(--color-danger)]">{t('login.error')}</p>
          )}

          <button type="submit" disabled={busy} className="tt-btn tt-btn-primary w-full py-3">
            {busy ? t('common.loading') : t('login.submit')}
          </button>

          <p className="mt-5 text-[12px] leading-relaxed text-[var(--color-muted)]">
            {t('login.lockedOut')}
          </p>
        </form>
      </section>
    </div>
  )
}
