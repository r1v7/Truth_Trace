import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type {
  AnalysisRun,
  Evidence,
  EvidenceKind,
  Integrity,
  Interview,
} from '../api/types'

const KINDS: EvidenceKind[] = ['call_log', 'message_log', 'transcript', 'document', 'other']

const INTEGRITY_TONE: Record<string, string> = {
  verified: 'bg-emerald-100 text-emerald-800',
  altered: 'bg-red-100 text-red-800',
  missing_file: 'bg-amber-100 text-amber-800',
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface Props {
  caseId: string
  interviews: Interview[]
  onRun: (run: AnalysisRun) => void
}

export function EvidencePanel({ caseId, interviews, onRun }: Props) {
  const { t } = useTranslation()
  const [items, setItems] = useState<Evidence[]>([])
  const [integrity, setIntegrity] = useState<Record<number, Integrity>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [target, setTarget] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    const { data } = await api.get<Evidence[]>(`/cases/${caseId}/evidence`)
    setItems(data)
  }, [caseId])

  useEffect(() => {
    void load()
  }, [load])

  function reportError(err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
    setError(typeof detail === 'string' ? detail : t('common.error'))
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    if (!(form.get('file') as File)?.size) return

    setBusy(true)
    setError(null)
    try {
      await api.post(`/cases/${caseId}/evidence`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      element.reset()
      await load()
    } catch (err) {
      reportError(err)
    } finally {
      setBusy(false)
    }
  }

  async function verify(evidenceId: number) {
    setError(null)
    try {
      const { data } = await api.get<Integrity>(`/evidence/${evidenceId}/integrity`)
      setIntegrity((previous) => ({ ...previous, [evidenceId]: data }))
    } catch (err) {
      reportError(err)
    }
  }

  async function check(evidenceId: number) {
    const interviewId = target[evidenceId]
    if (!interviewId) return
    setError(null)
    try {
      const { data } = await api.post<AnalysisRun>(
        `/evidence/${evidenceId}/check?interview_id=${interviewId}`,
      )
      onRun(data)
    } catch (err) {
      reportError(err)
    }
  }

  return (
    <section>
      <h2 className="mb-3 font-semibold">{t('evidence.title')}</h2>

      <form
        onSubmit={upload}
        className="mb-4 flex flex-wrap items-end gap-2 rounded border border-slate-200 bg-white p-3"
      >
        <label className="text-sm">
          {t('evidence.file')}
          <input
            type="file"
            name="file"
            required
            className="mt-1 block max-w-xs text-sm file:me-2 file:rounded file:border file:border-slate-300 file:bg-slate-50 file:px-2 file:py-1"
          />
        </label>
        <label className="text-sm">
          {t('evidence.kind')}
          <select
            name="kind"
            defaultValue="other"
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
          >
            {KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {t(`evidenceKind.${kind}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          {t('evidence.description')}
          <input
            name="description"
            className="mt-1 block rounded border border-slate-300 px-2 py-1.5"
          />
        </label>
        <button
          disabled={busy}
          className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
        >
          {busy ? t('common.loading') : t('evidence.upload')}
        </button>
      </form>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">{t('evidence.empty')}</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => {
            const state = integrity[item.id]
            return (
              <li key={item.id} className="rounded border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span dir="auto" className="font-medium">
                    {item.original_filename}
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {t(`evidenceKind.${item.kind}`)}
                  </span>
                  <span className="text-xs text-slate-500">{formatSize(item.size_bytes)}</span>
                  {state && (
                    <span
                      className={`rounded px-2 py-0.5 text-xs ${INTEGRITY_TONE[state.status]}`}
                    >
                      {t(`integrity.${state.status}`)}
                    </span>
                  )}
                </div>

                {item.description && (
                  <p dir="auto" className="mt-1 text-sm text-slate-600">
                    {item.description}
                  </p>
                )}

                <p className="mt-2 break-all font-mono text-xs text-slate-400">
                  SHA-256 {item.sha256}
                </p>

                {state && (
                  <p className="mt-1 text-xs text-slate-500">
                    {state.status === 'verified' ? t('integrity.verifiedNote') : t('integrity.alteredNote')}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => verify(item.id)}
                    className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100"
                  >
                    {t('evidence.verify')}
                  </button>

                  <select
                    value={target[item.id] ?? ''}
                    onChange={(e) => setTarget({ ...target, [item.id]: e.target.value })}
                    className="rounded border border-slate-300 px-2 py-1 text-xs"
                  >
                    <option value="">{t('evidence.pickInterview')}</option>
                    {interviews.map((interview) => (
                      <option key={interview.id} value={interview.id}>
                        {interview.subject_name} — {interview.session_label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => check(item.id)}
                    disabled={!target[item.id]}
                    className="rounded bg-slate-900 px-2 py-1 text-xs text-white disabled:opacity-40"
                  >
                    {t('evidence.check')}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
