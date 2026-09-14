import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api } from '../api/client'
import type { Case } from '../api/types'

export function CasesPage() {
  const { t } = useTranslation()
  const [cases, setCases] = useState<Case[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ reference: '', title: '', description: '' })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<Case[]>('/cases').then(({ data }) => setCases(data))
  }, [])

  async function create(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const { data } = await api.post<Case>('/cases', {
        ...form,
        description: form.description || null,
      })
      setCases((previous) => [data, ...previous])
      setForm({ reference: '', title: '', description: '' })
      setShowForm(false)
    } catch {
      setError(t('common.error'))
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t('cases.title')}</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
        >
          {t('cases.new')}
        </button>
      </div>

      {showForm && (
        <form onSubmit={create} className="mb-6 grid gap-3 rounded border border-slate-200 bg-white p-4 sm:grid-cols-2">
          <label className="text-sm">
            {t('cases.reference')}
            <input
              required
              value={form.reference}
              onChange={(e) => setForm({ ...form, reference: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            {t('cases.caseTitle')}
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="text-sm sm:col-span-2">
            {t('cases.description')}
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              rows={2}
            />
          </label>
          {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
          <div className="sm:col-span-2">
            <button className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white">
              {t('cases.create')}
            </button>
          </div>
        </form>
      )}

      {cases.length === 0 ? (
        <p className="text-slate-500">{t('cases.empty')}</p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-white">
          {cases.map((c) => (
            <li key={c.id}>
              <Link to={`/cases/${c.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50">
                <span className="font-mono text-xs text-slate-500">{c.reference}</span>
                <span dir="auto" className="font-medium">{c.title}</span>
                <span className="ms-auto rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {t(`status.${c.status}`)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
