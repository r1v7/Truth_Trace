import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { Finding, Report, User } from '../api/types'

const STATUS_TONE: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  submitted: 'bg-blue-100 text-blue-800',
  approved: 'bg-emerald-100 text-emerald-800',
  returned: 'bg-amber-100 text-amber-900',
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
    <section>
      <h2 className="mb-3 font-semibold">{t('reports.title')}</h2>

      {findings.length > 0 && (
        <form onSubmit={create} className="mb-4 rounded border border-slate-200 bg-white p-3">
          <p className="mb-2 text-sm text-slate-600">{t('reports.pickFindings')}</p>
          <ul className="mb-3 max-h-48 space-y-1 overflow-y-auto">
            {findings.map((finding) => (
              <li key={finding.id}>
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.includes(finding.id)}
                    onChange={(e) =>
                      setSelected((previous) =>
                        e.target.checked
                          ? [...previous, finding.id]
                          : previous.filter((id) => id !== finding.id),
                      )
                    }
                  />
                  <span dir="auto">
                    <span className="font-medium">{t(`findings.${finding.finding_type}`)}</span>
                    {' — '}
                    {finding.explanation}
                  </span>
                </label>
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap items-end gap-2">
            <label className="text-sm">
              {t('reports.reportTitle')}
              <input
                name="title"
                required
                className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
            <label className="text-sm grow">
              {t('reports.summary')}
              <input
                name="summary"
                className="mt-1 block w-full rounded border border-slate-300 px-2 py-1.5"
              />
            </label>
            <button
              disabled={selected.length === 0}
              className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-40"
            >
              {t('reports.create')} ({selected.length})
            </button>
          </div>
        </form>
      )}

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {reports.length === 0 ? (
        <p className="text-sm text-slate-500">{t('reports.empty')}</p>
      ) : (
        <ul className="space-y-3">
          {reports.map((report) => {
            const editable = report.status === 'draft' || report.status === 'returned'
            const ownReport = report.prepared_by_id === user.id
            return (
              <li key={report.id} className="rounded border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span dir="auto" className="font-medium">
                    {report.title}
                  </span>
                  <span className="text-xs text-slate-500">v{report.version}</span>
                  <span className={`rounded px-2 py-0.5 text-xs ${STATUS_TONE[report.status]}`}>
                    {t(`reportStatus.${report.status}`)}
                  </span>
                  <span className="text-xs text-slate-500">
                    {t('reports.itemCount', { count: report.items.length })}
                  </span>
                </div>

                {report.decision_note && (
                  <p dir="auto" className="mt-2 text-sm text-slate-700">
                    {t('reports.supervisorNote')}: {report.decision_note}
                  </p>
                )}

                {report.content_sha256 && (
                  <p className="mt-2 break-all font-mono text-xs text-slate-400">
                    {t('reports.contentDigest')} {report.content_sha256}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={() => open(report.id, 'preview')}
                    className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100"
                  >
                    {t('reports.preview')}
                  </button>

                  {editable && (
                    <button
                      onClick={() => act(`/reports/${report.id}/submit`)}
                      className="rounded bg-slate-900 px-2 py-1 text-xs text-white"
                    >
                      {t('reports.submit')}
                    </button>
                  )}

                  {!editable && (
                    <button
                      onClick={() => open(report.id, 'pdf')}
                      className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100"
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
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      />
                      <button
                        onClick={() =>
                          act(`/reports/${report.id}/decision`, { approve: true, note: note || null })
                        }
                        className="rounded bg-emerald-700 px-2 py-1 text-xs text-white"
                      >
                        {t('reports.approve')}
                      </button>
                      <button
                        onClick={() =>
                          act(`/reports/${report.id}/decision`, { approve: false, note })
                        }
                        className="rounded bg-amber-700 px-2 py-1 text-xs text-white"
                      >
                        {t('reports.return')}
                      </button>
                    </>
                  )}

                  {report.status === 'submitted' && ownReport && (
                    <span className="self-center text-xs text-slate-500">
                      {t('reports.awaitingOther')}
                    </span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
