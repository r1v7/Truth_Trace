import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router-dom'

import { useAuth } from '../auth'
import { setLanguage, type Language } from '../i18n'

export function Layout() {
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const other: Language = i18n.language === 'ar' ? 'en' : 'ar'

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <Link to="/cases" className="text-lg font-semibold text-slate-900">
            {t('app.name')}
          </Link>
          <span className="hidden text-sm text-slate-500 sm:inline">{t('app.tagline')}</span>
          <div className="ms-auto flex items-center gap-3 text-sm">
            <button
              onClick={() => setLanguage(other)}
              className="rounded border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-100"
            >
              {t('nav.language')}
            </button>
            {user && (
              <>
                <span className="text-slate-600">{user.full_name}</span>
                <button onClick={logout} className="text-slate-500 hover:text-slate-900">
                  {t('nav.logout')}
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <p className="bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
        {t('app.disclaimer')}
      </p>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
