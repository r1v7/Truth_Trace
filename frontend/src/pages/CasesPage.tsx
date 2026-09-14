import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api } from '../api/client'
import type { Case, CaseStatus } from '../api/types'

const FILTERS: (CaseStatus | 'all')[] = ['all', 'open', 'under_review', 'closed', 'archived']

const STATUS_COLOR: Record<CaseStatus, string> = {
  open: 'var(--color-accent)',
  under_review: 'var(--color-warn)',
  closed: 'var(--color-muted)',
  archived: 'var(--color-muted-dim)',
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="tt-card tt-rise p-4">
      <div className="tt-label mb-2">{label}</div>
      <div className="tt-mono text-[32px] font-bold leading-none" style={{ color }}>
        {value}
      </div>
      <div className="mt-3 h-[3px] overflow-hidden rounded-sm bg-[var(--color-line)]">
        <div
          className="tt-bar h-full"
          style={{
            width: value === 0 ? '4%' : '55%',
            background: color,
            animation: 'tt-grow .9s .25s cubic-bezier(.2,.8,.2,1) both',
          }}
        />
      </div>
    </div>
  )
}

export function CasesPage() {
  const { t } = useTranslation()
  const [cases, setCases] = useState<Case[]>([])
  const [filter, setFilter] = useState<CaseStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ reference: '', title: '', description: '' })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<Case[]>('/cases').then(({ data }) => setCases(data))
  }, [])

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return cases
      .filter((c) => filter === 'all' || c.status === filter)
      .filter(
        (c) =>
          !needle ||
          c.reference.toLowerCase().includes(needle) ||
          c.title.toLowerCase().includes(needle),
      )
  }, [cases, filter, search])

  const counts = useMemo(
    () => ({
      active: cases.filter((c) => c.status === 'open').length,
      review: cases.filter((c) => c.status === 'under_review').length,
      total: cases.length,
    }),
    [cases],
  )

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
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(typeof detail === 'string' ? detail : t('common.error'))
    }
  }

  return (
    <div className="space-y-4">
      <section
        className="tt-card tt-rise relative overflow-hidden p-8"
        style={{
          backgroundImage:
            'radial-gradient(760px 320px at 88% 10%, rgba(155,140,255,.10), transparent 62%)',
        }}
      >
        <div className="tt-label mb-3 text-[var(--color-accent)]">{t('cases.eyebrow')}</div>
        <h1 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">{t('cases.headline')}</h1>
        <p className="mt-2 mb-6 text-[var(--color-muted)]">{t('cases.subhead')}</p>
        <button onClick={() => setShowForm((v) => !v)} className="tt-btn tt-btn-primary">
          {t('cases.new')}
        </button>
      </section>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label={t('cases.statActive')} value={counts.active} color="var(--color-accent)" />
        <Stat label={t('cases.statReview')} value={counts.review} color="var(--color-warn)" />
        <Stat label={t('cases.statTotal')} value={counts.total} color="var(--color-violet)" />
      </div>

      {showForm && (
        <form onSubmit={create} className="tt-card tt-fade grid gap-4 p-5 sm:grid-cols-2">
          <label className="block">
            <span className="tt-label mb-2 block">{t('cases.reference')}</span>
            <input
              required
              value={form.reference}
              onChange={(e) => setForm({ ...form, reference: e.target.value })}
              className="tt-field tt-mono"
              placeholder="CASE-2026-0001"
            />
          </label>
          <label className="block">
            <span className="tt-label mb-2 block">{t('cases.caseTitle')}</span>
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="tt-field"
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="tt-label mb-2 block">{t('cases.description')}</span>
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="tt-field resize-y"
            />
          </label>
          {error && <p className="text-[13px] text-[var(--color-danger)] sm:col-span-2">{error}</p>}
          <div className="flex gap-2 sm:col-span-2">
            <button className="tt-btn tt-btn-primary">{t('cases.create')}</button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="tt-btn tt-btn-ghost"
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('cases.search')}
          className="tt-field min-w-[210px] flex-1"
        />
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((value) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`tt-chip ${filter === value ? 'tt-chip-on' : ''}`}
            >
              {value === 'all' ? t('cases.all') : t(`status.${value}`)}
            </button>
          ))}
        </div>
      </div>

      {visible.length === 0 ? (
        <p className="tt-card p-8 text-center text-[var(--color-muted)]">
          {cases.length === 0 ? t('cases.empty') : t('cases.noMatches')}
        </p>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {visible.map((c) => (
            <li key={c.id}>
              <Link
                to={`/cases/${c.id}`}
                className="tt-card tt-rise block overflow-hidden p-0 no-underline transition-[border-color,transform] hover:-translate-y-[2px] hover:border-[var(--color-line-3)]"
              >
                <div
                  className="flex items-start gap-3 border-s-[3px] p-4"
                  style={{ borderInlineStartColor: STATUS_COLOR[c.status] }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="tt-mono text-[11px] text-[var(--color-muted)]">
                        {c.reference}
                      </span>
                      <span
                        className="tt-tag"
                        style={{
                          color: STATUS_COLOR[c.status],
                          background: 'color-mix(in srgb, currentColor 12%, transparent)',
                        }}
                      >
                        {t(`status.${c.status}`)}
                      </span>
                    </div>
                    <p
                      dir="auto"
                      className="mt-1.5 mb-0 text-[16px] font-semibold text-[var(--color-ink)]"
                    >
                      {c.title}
                    </p>
                    {c.description && (
                      <p
                        dir="auto"
                        className="mt-1 mb-0 line-clamp-2 text-[13px] text-[var(--color-muted)]"
                      >
                        {c.description}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <p className="tt-mono text-[11px] text-[var(--color-muted-dim)]">
        {t('cases.shown', { shown: visible.length, total: cases.length })}
      </p>
    </div>
  )
}
