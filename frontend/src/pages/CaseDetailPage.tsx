import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

import { api } from '../api/client'
import type { AnalysisRun, Case, Finding, FindingType, Interview, Statement } from '../api/types'
import { EvidencePanel } from '../components/EvidencePanel'
import { FindingCard } from '../components/FindingCard'

const FILTERS: (FindingType | 'all')[] = ['all', 'possible_conflict', 'unclear', 'missing', 'match']

export function CaseDetailPage() {
  const { t } = useTranslation()
  const { caseId } = useParams()
  const [kase, setKase] = useState<Case | null>(null)
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [statements, setStatements] = useState<Record<number, Statement[]>>({})
  const [run, setRun] = useState<AnalysisRun | null>(null)
  const [filter, setFilter] = useState<FindingType | 'all'>('all')
  const [pair, setPair] = useState({ a: '', b: '' })
  const [error, setError] = useState<string | null>(null)

  const loadInterviews = useCallback(async () => {
    const { data } = await api.get<Interview[]>(`/cases/${caseId}/interviews`)
    setInterviews(data)
    const loaded = await Promise.all(
      data.map(async (i) => {
        const res = await api.get<Statement[]>(`/interviews/${i.id}/statements`)
        return [i.id, res.data] as const
      }),
    )
    setStatements(Object.fromEntries(loaded))
  }, [caseId])

  useEffect(() => {
    api.get<Case>(`/cases/${caseId}`).then(({ data }) => setKase(data))
    void loadInterviews()
  }, [caseId, loadInterviews])

  async function addInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    await api.post(`/cases/${caseId}/interviews`, {
      subject_name: form.get('subject_name'),
      session_label: form.get('session_label'),
      interviewed_on: form.get('interviewed_on') || null,
    })
    element.reset()
    await loadInterviews()
  }

  async function addStatement(interviewId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    await api.post(`/interviews/${interviewId}/statements`, { body: form.get('body') })
    element.reset()
    await loadInterviews()
  }

  async function compare(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const { data } = await api.post<AnalysisRun>(`/cases/${caseId}/analysis-runs`, {
        interview_a_id: Number(pair.a),
        interview_b_id: Number(pair.b),
      })
      setRun(data)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(typeof detail === 'string' ? detail : t('common.error'))
    }
  }

  const findings: Finding[] = run?.findings ?? []
  const visible = filter === 'all' ? findings : findings.filter((f) => f.finding_type === filter)

  if (!kase) return <p className="text-slate-500">{t('common.loading')}</p>

  return (
    <div className="space-y-8">
      <div>
        <p className="font-mono text-xs text-slate-500">{kase.reference}</p>
        <h1 dir="auto" className="text-xl font-semibold">{kase.title}</h1>
        {kase.description && (
          <p dir="auto" className="mt-1 text-sm text-slate-600">
            {kase.description}
          </p>
        )}
      </div>

      <section>
        <h2 className="mb-3 font-semibold">{t('case.interviews')}</h2>

        <form
          onSubmit={addInterview}
          className="mb-4 flex flex-wrap items-end gap-2 rounded border border-slate-200 bg-white p-3"
        >
          <label className="text-sm">
            {t('case.subject')}
            <input
              name="subject_name"
              required
              className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="text-sm">
            {t('case.session')}
            <input
              name="session_label"
              required
              className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <label className="text-sm">
            {t('case.date')}
            <input
              name="interviewed_on"
              type="date"
              className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
            />
          </label>
          <button className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white">
            {t('case.newInterview')}
          </button>
        </form>

        <div className="grid gap-4 md:grid-cols-2">
          {interviews.map((interview) => (
            <div key={interview.id} className="rounded border border-slate-200 bg-white p-4">
              <p dir="auto" className="font-medium">
                {interview.subject_name} — {interview.session_label}
              </p>
              <p className="mb-2 text-xs text-slate-500">{interview.interviewed_on ?? ''}</p>

              <ul className="mb-3 space-y-2">
                {(statements[interview.id] ?? []).map((s) => (
                  <li key={s.id} className="rounded bg-slate-50 p-2 text-sm">
                    <p dir="auto" className="whitespace-pre-wrap">{s.body}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {t('case.claims', { count: s.claims.length })}
                    </p>
                  </li>
                ))}
              </ul>

              <form onSubmit={(e) => addStatement(interview.id, e)}>
                <textarea
                  name="body"
                  required
                  rows={3}
                  placeholder={t('case.statementBody')}
                  className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
                <button className="mt-2 rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100">
                  {t('case.addStatement')}
                </button>
              </form>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">{t('case.compare')}</h2>
        {interviews.length < 2 ? (
          <p className="text-sm text-slate-500">{t('case.noInterviews')}</p>
        ) : (
          <form
            onSubmit={compare}
            className="flex flex-wrap items-end gap-2 rounded border border-slate-200 bg-white p-3"
          >
            {(['a', 'b'] as const).map((side) => (
              <label key={side} className="text-sm">
                {t(side === 'a' ? 'case.interviewA' : 'case.interviewB')}
                <select
                  required
                  value={pair[side]}
                  onChange={(e) => setPair({ ...pair, [side]: e.target.value })}
                  className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
                >
                  <option value="">—</option>
                  {interviews.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.subject_name} — {i.session_label}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <button className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white">
              {t('case.run')}
            </button>
            {error && <p className="w-full text-sm text-red-600">{error}</p>}
          </form>
        )}
      </section>

      <EvidencePanel caseId={caseId!} interviews={interviews} onRun={setRun} />

      {run && (
        <section>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <h2 className="font-semibold">{t('findings.title')}</h2>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {t(run.kind === 'evidence' ? 'findings.vsEvidence' : 'findings.vsInterview')}
            </span>
            <span className="text-xs text-slate-500">
              {t('findings.engine')}: {run.analyzer_backend} {run.analyzer_version}
            </span>
            <div className="ms-auto flex flex-wrap gap-1">
              {FILTERS.map((value) => (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={`rounded border px-2 py-1 text-xs ${
                    filter === value
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {t(value === 'all' ? 'findings.all' : `findings.${value}`)}
                  {value !== 'all' && (
                    <span className="ms-1 opacity-70">
                      {findings.filter((f) => f.finding_type === value).length}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <p className="mb-3 text-xs text-slate-500">{t('findings.scoreHint')}</p>

          {visible.length === 0 ? (
            <p className="text-sm text-slate-500">{t('findings.empty')}</p>
          ) : (
            <ul className="space-y-3">
              {visible.map((f) => (
                <FindingCard key={f.id} finding={f} kind={run.kind} />
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
