import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { AuditPage as AuditPageData } from '../api/types'
import { Section } from '../components/Section'

const PAGE_SIZE = 25
const RANGES = [7, 30, 0] as const

export function AuditPage() {
  const { t } = useTranslation()
  const [data, setData] = useState<AuditPageData | null>(null)
  const [actions, setActions] = useState<string[]>([])
  const [action, setAction] = useState('')
  const [days, setDays] = useState<number>(0)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) })
      if (action) params.set('action', action)
      if (days) params.set('days', String(days))
      const { data: page } = await api.get<AuditPageData>(`/audit?${params}`)
      setData(page)
    } catch {
      setError(t('common.error'))
    }
  }, [action, days, offset, t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    api.get<string[]>('/audit/actions').then(({ data: list }) => setActions(list))
  }, [])

  const shown = data ? Math.min(offset + data.entries.length, data.total) : 0

  return (
    <div className="space-y-6">
      <div className="tt-rise">
        <div className="tt-label mb-2 text-[var(--color-accent)]">{t('audit.eyebrow')}</div>
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.02em]">{t('audit.title')}</h1>
        <p className="mt-2 mb-0 max-w-3xl text-[var(--color-muted)]">{t('audit.blurb')}</p>
      </div>

      <Section title={t('audit.entries')} aside={data ? t('audit.count', { shown, total: data.total }) : ''}>
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="tt-label mb-2 block">{t('audit.action')}</span>
            <select
              value={action}
              onChange={(e) => {
                setAction(e.target.value)
                setOffset(0)
              }}
              className="tt-field w-56"
            >
              <option value="">{t('audit.allActions')}</option>
              {actions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>

          <div className="flex flex-wrap gap-1.5">
            {RANGES.map((value) => (
              <button
                key={value}
                onClick={() => {
                  setDays(value)
                  setOffset(0)
                }}
                className={`tt-chip ${days === value ? 'tt-chip-on' : ''}`}
              >
                {value === 0 ? t('audit.allTime') : t('audit.lastDays', { count: value })}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="mb-3 text-[13px] text-[var(--color-danger)]">{error}</p>}

        {!data ? (
          <p className="m-0 text-[13px] text-[var(--color-muted)]">{t('common.loading')}</p>
        ) : data.entries.length === 0 ? (
          <p className="m-0 text-[13px] text-[var(--color-muted)]">{t('audit.empty')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="border-b border-[var(--color-line)]">
                  {['when', 'actor', 'action', 'entity', 'case', 'from'].map((key) => (
                    <th key={key} className="tt-label px-2 py-2 text-start">
                      {t(`audit.${key}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry) => (
                  <tr key={entry.id} className="border-b border-[var(--color-line)]">
                    <td className="tt-mono whitespace-nowrap px-2 py-2 text-[11.5px] text-[var(--color-muted)]">
                      {entry.created_at.slice(0, 19).replace('T', ' ')}
                    </td>
                    <td dir="auto" className="px-2 py-2">
                      {entry.actor_name ?? <span className="text-[var(--color-muted-dim)]">—</span>}
                    </td>
                    <td className="tt-mono px-2 py-2 text-[12px]">{entry.action}</td>
                    <td className="tt-mono px-2 py-2 text-[11.5px] text-[var(--color-muted)]">
                      {entry.entity_type}
                      {entry.entity_id ? ` #${entry.entity_id}` : ''}
                    </td>
                    <td className="tt-mono px-2 py-2 text-[11.5px] text-[var(--color-muted)]">
                      {entry.case_reference ?? '—'}
                    </td>
                    <td className="tt-mono px-2 py-2 text-[11.5px] text-[var(--color-muted-dim)]">
                      {entry.ip_address ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > PAGE_SIZE && (
          <div className="mt-4 flex items-center gap-2">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="tt-btn tt-btn-ghost tt-btn-sm"
            >
              {t('audit.previous')}
            </button>
            <button
              disabled={offset + PAGE_SIZE >= data.total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="tt-btn tt-btn-ghost tt-btn-sm"
            >
              {t('audit.next')}
            </button>
          </div>
        )}
      </Section>
    </div>
  )
}
