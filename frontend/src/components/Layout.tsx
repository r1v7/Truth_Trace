import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router-dom'

import { useAuth } from '../auth'
import { setLanguage, type Language } from '../i18n'
import { Avatar, Mark } from './Mark'

export function Layout() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const other: Language = i18n.language === 'ar' ? 'en' : 'ar'

  return (
    <div className="min-h-screen">
      <header
        className="sticky top-0 z-10 flex min-h-[54px] flex-wrap items-center gap-4 border-b border-[var(--color-line)] px-5"
        style={{ background: 'rgba(11,15,22,.92)', backdropFilter: 'blur(8px)' }}
      >
        <Link to="/cases" className="flex items-center gap-3 py-2 no-underline">
          <Mark size={20} />
          <span className="tt-wordmark text-[12px] font-bold uppercase tracking-[0.3em] text-[var(--color-ink)]">
            {t('app.name')}
          </span>
        </Link>

        <div className="ms-auto flex items-center gap-3">
          <button onClick={() => setLanguage(other)} className="tt-btn tt-btn-ghost tt-btn-sm">
            {t('nav.language')}
          </button>

          {user && (
            <>
              <span className="tt-tag hidden sm:inline">{t(`role.${user.role}`)}</span>
              <span className="flex items-center gap-2">
                <Avatar name={user.full_name} />
                <span className="hidden text-[13px] text-[var(--color-ink-soft)] sm:inline">
                  {user.full_name}
                </span>
              </span>
              <button
                onClick={logout}
                className="text-[12px] text-[var(--color-muted)] hover:text-[var(--color-ink)]"
              >
                {t('nav.logout')}
              </button>
            </>
          )}
        </div>
      </header>

      {/* The tool's limits belong in the chrome, not in a dialog someone dismisses once. */}
      <p
        className="border-b border-[var(--color-line)] px-5 py-2 text-center text-[12px] leading-relaxed text-[var(--color-muted)]"
        style={{ background: 'rgba(53,224,196,.04)' }}
      >
        {t('app.disclaimer')}
      </p>

      <main className="mx-auto max-w-6xl px-5 py-7">
        <Outlet />
      </main>
    </div>
  )
}
