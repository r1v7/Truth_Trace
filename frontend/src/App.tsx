import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth'
import { Layout } from './components/Layout'
import { Waking } from './components/Waking'
import { CaseDetailPage } from './pages/CaseDetailPage'
import { AuditPage } from './pages/AuditPage'
import { CasesPage } from './pages/CasesPage'
import { LoginPage } from './pages/LoginPage'
import { UsersPage } from './pages/UsersPage'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const { t } = useTranslation()
  if (loading) return <p className="tt-mono p-6 text-[var(--color-muted)]">{t('common.loading')}</p>
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <>
      <Waking />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <Protected>
              <Layout />
            </Protected>
          }
        >
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Routes>
    </>
  )
}
