import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { Finding, Report, User } from '../api/types'
import { Section } from './Section'

const STATUS_COLOR: Record<string, string> = {
  draft: 'var(--color-muted)',
  submitted: 'var(--color-violet)',
  approved: 'var(--color-accent)',
  returned: 'var(--color-warn)',
}

interface Props {
  caseId: string
  findings: Finding[]
  user: User
}

export function ReportsPanel({ caseId, findings, user }: Props) {
  const { t } = useTranslation()
  const [reports, setReports] = useState<Report[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)
  const canDecide = user.role === 'supervisor' || user.role === 'admin'

  const load = useCallback(async () => {
    const { data } = await api.get<Report[]>(`/cases/${caseId}/reports`)
    setReports(data)
  }, [caseId])

  useEffect(() => {
    void load()
  }, [load])

  function reportError(err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
    setError(typeof detail === 'string' ? detail : t('common.error'))
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    setError(null)
    try {
      await api.post(`/cases/${caseId}/reports`, {
        title: form.get('title'),
        summary: form.get('summary') || null,
        items: selected.map((finding_id) => ({ finding_id })),
      })
      element.reset()
      setSelected([])
      await load()
    } catch (err) {
      reportError(err)
    }
  }

  async function act(path: string, body?: unknown) {
    setError(null)
    try {
      await api.post(path, body ?? {})
      await load()
    } catch (err) {
      reportError(err)
    }
  }

  async function open(reportId: number, format: 'preview' | 'pdf') {
    setError(null)
    try {
      const { data } = await api.get(`/reports/${reportId}/${format}`, { responseType: 'blob' })
      // The API needs an Authorization header, so the file is fetched and then handed
      // to the browser as a blob rather than linked to directly.
      const url = URL.createObjectURL(data as Blob)
      window.open(url, '_blank', 'noopener')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (err) {
      reportError(err)
    }
  }

  return (
    <Section title={t('reports.title')}>
      {findings.length > 0 && (
        <form onSubmit={create} className="mb-5">
          <p className="mt-0 mb-3 text-[12px] leading-relaxed text-[var(--color-muted)]">
            {t('reports.pickFindings')}
          </p>

          <ul className="mb-4 max-h-52 space-y-1.5 overflow-y-auto pe-1">
            {findings.map((finding) => (
              <li key={finding.id}>
                <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-2)] p-2.5 text-[13px] hover:border-[var(--color-line-3)]">
                  <input
                    type="checkbox"
                    className="mt-1 accent-[var(--color-accent)]"
                    checked={selected.includes(finding.id)}
                    onChange={(e) =>
                      setSelected((previous) =>
                        e.target.checked
                          ? [...previous, finding.id]
                          : previous.filter((id) => id !== finding.id),
                      )
                    }
                  />
                  <span dir="auto" className="min-w-0">
                    <span className="tt-mono text-[10.5px] uppercase tracking-[0.1em] text-[var(--color-muted)]">
                      {t(`findings.${finding.finding_type}`)}
                    </span>
                    <span className="block text-[var(--color-ink-soft)]">
                      {finding.explanation}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap items-end gap-3">
            <label className="block">
              <span className="tt-label mb-2 block">{t('reports.reportTitle')}</span>
              <input name="title" required className="tt-field w-64" />
            </label>
            <label className="block grow">
              <span className="tt-label mb-2 block">{t('reports.summary')}</span>
              <input name="summary" className="tt-field" />
            </label>
            <button disabled={selected.length === 0} className="tt-btn tt-btn-primary">
              {t('reports.create')} ({selected.length})
            </button>
          </div>
        </form>
      )}

      {error && <p className="mb-3 text-[13px] text-[var(--color-danger)]">{error}</p>}

      {reports.length === 0 ? (
        <p className="m-0 text-[13px] text-[var(--color-muted)]">{t('reports.empty')}</p>
      ) : (
        <ul className="space-y-3">
          {reports.map((report) => {
            const editable = report.status === 'draft' || report.status === 'returned'
            const ownReport = report.prepared_by_id === user.id
            const tone = STATUS_COLOR[report.status]
            return (
              <li
                key={report.id}
                className="overflow-hidden rounded-xl border border-s-[3px] border-[var(--color-line)] bg-[var(--color-surface-2)] p-4"
                style={{ borderInlineStartColor: tone }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span dir="auto" className="font-semibold">
                    {report.title}
                  </span>
                  <span className="tt-mono text-[11px] text-[var(--color-muted-dim)]">
                    v{report.version}
                  </span>
                  <span
                    className="tt-tag"
                    style={{
                      color: tone,
                      background: `color-mix(in srgb, ${tone} 13%, transparent)`,
                    }}
                  >
                    {t(`reportStatus.${report.status}`)}
                  </span>
                  <span className="tt-mono text-[11px] text-[var(--color-muted-dim)]">
                    {t('reports.itemCount', { count: report.items.length })}
                  </span>
                </div>

                {report.decision_note && (
                  <p dir="auto" className="mt-2 mb-0 text-[13px] text-[var(--color-ink-soft)]">
                    <span className="tt-label">{t('reports.supervisorNote')}</span>{' '}
                    {report.decision_note}
                  </p>
                )}

                {report.content_sha256 && (
                  <p className="tt-mono mt-2 mb-0 break-all text-[10.5px] text-[var(--color-muted-dim)]">
                    <span className="tt-label">{t('reports.contentDigest')}</span>{' '}
                    {report.content_sha256}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => open(report.id, 'preview')}
                    className="tt-btn tt-btn-ghost tt-btn-sm"
                  >
                    {t('reports.preview')}
                  </button>

                  {editable ? (
                    <button
                      onClick={() => act(`/reports/${report.id}/submit`)}
                      className="tt-btn tt-btn-primary tt-btn-sm"
                    >
                      {t('reports.submit')}
                    </button>
                  ) : (
                    <button
                      onClick={() => open(report.id, 'pdf')}
                      className="tt-btn tt-btn-ghost tt-btn-sm"
                    >
                      {t('reports.pdf')}
                    </button>
                  )}

                  {report.status === 'submitted' && canDecide && !ownReport && (
                    <>
                      <input
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder={t('reports.decisionNote')}
                        className="tt-field w-56 py-1.5 text-[12px]"
                      />
                      <button
                        onClick={() =>
                          act(`/reports/${report.id}/decision`, {
                            approve: true,
                            note: note || null,
                          })
                        }
                        className="tt-btn tt-btn-sm"
                        style={{ background: 'var(--color-accent)', color: 'var(--color-accent-ink)' }}
                      >
                        {t('reports.approve')}
                      </button>
                      <button
                        onClick={() => act(`/reports/${report.id}/decision`, { approve: false, note })}
                        className="tt-btn tt-btn-sm"
                        style={{ background: 'var(--color-warn)', color: '#241700' }}
                      >
                        {t('reports.return')}
                      </button>
                    </>
                  )}

                  {report.status === 'submitted' && ownReport && (
                    <span className="self-center text-[12px] text-[var(--color-muted)]">
                      {t('reports.awaitingOther')}
                    </span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Section>
  )
}
