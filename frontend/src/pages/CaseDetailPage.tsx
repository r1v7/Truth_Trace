import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api/client'
import type { AnalysisRun, Case, Finding, FindingType, Interview, Statement } from '../api/types'
import { useAuth } from '../auth'
import { EvidencePanel } from '../components/EvidencePanel'
import { FindingCard } from '../components/FindingCard'
import { Avatar } from '../components/Mark'
import { ReportsPanel } from '../components/ReportsPanel'
import { Section } from '../components/Section'

const FILTERS: (FindingType | 'all')[] = ['all', 'possible_conflict', 'unclear', 'missing', 'match']

const FILTER_COLOR: Record<FindingType, string> = {
  possible_conflict: 'var(--color-danger)',
  unclear: 'var(--color-warn)',
  missing: 'var(--color-violet)',
  match: 'var(--color-accent)',
}

const CASE_STATUS_COLOR: Record<string, string> = {
  open: 'var(--color-accent)',
  under_review: 'var(--color-warn)',
  closed: 'var(--color-muted)',
  archived: 'var(--color-muted-dim)',
}

export function CaseDetailPage() {
  const { t } = useTranslation()
  const { caseId } = useParams()
  const { user } = useAuth()
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

    // Show the most recent comparison on arrival: without this, someone returning to a
    // case sees no findings and cannot build a report from work already done.
    api.get<AnalysisRun[]>(`/cases/${caseId}/analysis-runs`).then(async ({ data }) => {
      if (data.length === 0) return
      const { data: latest } = await api.get<AnalysisRun>(`/analysis-runs/${data[0].id}`)
      setRun(latest)
    })
  }, [caseId, loadInterviews])

  function reportError(err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
    setError(typeof detail === 'string' ? detail : t('common.error'))
  }

  async function addInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    setError(null)
    try {
      await api.post(`/cases/${caseId}/interviews`, {
        subject_name: form.get('subject_name'),
        session_label: form.get('session_label'),
        interviewed_on: form.get('interviewed_on') || null,
      })
      element.reset()
      await loadInterviews()
    } catch (err) {
      reportError(err)
    }
  }

  async function addStatement(interviewId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    setError(null)
    try {
      await api.post(`/interviews/${interviewId}/statements`, { body: form.get('body') })
      element.reset()
      await loadInterviews()
    } catch (err) {
      reportError(err)
    }
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
      reportError(err)
    }
  }

  const findings: Finding[] = run?.findings ?? []
  const visible = filter === 'all' ? findings : findings.filter((f) => f.finding_type === filter)

  if (!kase) {
    return <p className="tt-mono text-[var(--color-muted)]">{t('common.loading')}</p>
  }

  return (
    <div className="space-y-6">
      <div className="tt-rise">
        <nav className="tt-breadcrumb mb-3 flex items-center gap-2">
          <Link to="/cases" className="tt-link">
            {t('nav.cases')}
          </Link>
          <span>/</span>
          <span className="tt-mono">{kase.reference}</span>
        </nav>

        <div className="flex flex-wrap items-center gap-3">
          <h1 dir="auto" className="m-0 text-[28px] font-semibold tracking-[-0.02em]">
            {kase.title}
          </h1>
          <span
            className="tt-tag"
            style={{
              color: CASE_STATUS_COLOR[kase.status],
              background: 'color-mix(in srgb, currentColor 12%, transparent)',
            }}
          >
            {t(`status.${kase.status}`)}
          </span>
        </div>

        {kase.description && (
          <p dir="auto" className="mt-2 mb-0 max-w-3xl text-[var(--color-muted)]">
            {kase.description}
          </p>
        )}
      </div>

      {error && (
        <p className="tt-card m-0 border-[var(--color-danger)] px-4 py-3 text-[13px] text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <Section title={t('case.interviews')} aside={t('case.sameSubjectOnly')}>
        <form onSubmit={addInterview} className="mb-5 flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="tt-label mb-2 block">{t('case.subject')}</span>
            <input name="subject_name" required className="tt-field w-48" />
          </label>
          <label className="block">
            <span className="tt-label mb-2 block">{t('case.session')}</span>
            <input name="session_label" required className="tt-field w-40" />
          </label>
          <label className="block">
            <span className="tt-label mb-2 block">{t('case.date')}</span>
            <input name="interviewed_on" type="date" className="tt-field w-44" />
          </label>
          <button className="tt-btn tt-btn-ghost">{t('case.newInterview')}</button>
        </form>

        <div className="grid gap-3 md:grid-cols-2">
          {interviews.map((interview) => (
            <div
              key={interview.id}
              className="rounded-xl border border-[var(--color-line)] bg-[var(--color-surface-2)] p-4"
            >
              <div className="flex items-center gap-3">
                <Avatar name={interview.subject_name} tone="violet" />
                <div className="min-w-0">
                  <p dir="auto" className="m-0 font-semibold">
                    {interview.subject_name}
                  </p>
                  <p className="tt-mono m-0 text-[11px] text-[var(--color-muted)]">
                    {interview.session_label}
                    {interview.interviewed_on ? ` · ${interview.interviewed_on}` : ''}
                  </p>
                </div>
              </div>

              <ul className="my-3 space-y-2">
                {(statements[interview.id] ?? []).map((s) => (
                  <li
                    key={s.id}
                    className="rounded-lg border border-[var(--color-line)] bg-[var(--color-page)] p-3"
                  >
                    <p dir="auto" className="m-0 whitespace-pre-wrap text-[13px]">
                      {s.body}
                    </p>
                    <p className="tt-mono mt-2 mb-0 text-[10.5px] text-[var(--color-muted-dim)]">
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
                  className="tt-field resize-y text-[13px]"
                />
                <button className="tt-btn tt-btn-ghost tt-btn-sm mt-2">
                  {t('case.addStatement')}
                </button>
              </form>
            </div>
          ))}
        </div>
      </Section>

      <Section title={t('case.compare')}>
        {interviews.length < 2 ? (
          <p className="m-0 text-[13px] text-[var(--color-muted)]">{t('case.noInterviews')}</p>
        ) : (
          <form onSubmit={compare} className="flex flex-wrap items-end gap-3">
            {(['a', 'b'] as const).map((side) => (
              <label key={side} className="block">
                <span className="tt-label mb-2 block">
                  {t(side === 'a' ? 'case.interviewA' : 'case.interviewB')}
                </span>
                <select
                  required
                  value={pair[side]}
                  onChange={(e) => setPair({ ...pair, [side]: e.target.value })}
                  className="tt-field w-56"
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
            <button className="tt-btn tt-btn-primary">{t('case.run')}</button>
          </form>
        )}
      </Section>

      <EvidencePanel caseId={caseId!} interviews={interviews} onRun={setRun} />

      {run && (
        <Section
          title={t('findings.title')}
          aside={`${run.analyzer_backend} ${run.analyzer_version}`}
        >
          <div className="mb-4 flex flex-wrap items-center gap-1.5">
            <span className="tt-tag me-1">
              {t(run.kind === 'evidence' ? 'findings.vsEvidence' : 'findings.vsInterview')}
            </span>
            {FILTERS.map((value) => {
              const count =
                value === 'all'
                  ? findings.length
                  : findings.filter((f) => f.finding_type === value).length
              return (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={`tt-chip ${filter === value ? 'tt-chip-on' : ''}`}
                  style={
                    filter !== value && value !== 'all' && count > 0
                      ? { color: FILTER_COLOR[value] }
                      : undefined
                  }
                >
                  {value === 'all' ? t('findings.all') : t(`findings.${value}`)}
                  <span className="tt-mono ms-1.5 opacity-70">{count}</span>
                </button>
              )
            })}
          </div>

          {visible.length === 0 ? (
            <p className="m-0 text-[13px] text-[var(--color-muted)]">{t('findings.empty')}</p>
          ) : (
            <ul className="space-y-3">
              {visible.map((f) => (
                <FindingCard key={f.id} finding={f} kind={run.kind} />
              ))}
            </ul>
          )}

          <p className="mt-4 mb-0 text-[12px] leading-relaxed text-[var(--color-muted-dim)]">
            {t('findings.scoreHint')}
          </p>
        </Section>
      )}

      {user && <ReportsPanel caseId={caseId!} findings={findings} user={user} />}
    </div>
  )
}
