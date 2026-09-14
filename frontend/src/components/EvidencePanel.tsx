import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { AnalysisRun, Evidence, EvidenceKind, Integrity, Interview } from '../api/types'
import { Section } from './Section'

const KINDS: EvidenceKind[] = ['call_log', 'message_log', 'transcript', 'document', 'other']

const INTEGRITY_COLOR: Record<string, string> = {
  verified: 'var(--color-accent)',
  altered: 'var(--color-danger)',
  missing_file: 'var(--color-warn)',
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
    <Section title={t('evidence.title')} aside={t('evidence.hashNote')}>
      <form onSubmit={upload} className="mb-5 flex flex-wrap items-end gap-3">
        <label className="block">
          <span className="tt-label mb-2 block">{t('evidence.file')}</span>
          <input
            type="file"
            name="file"
            required
            className="tt-field max-w-xs text-[12px] file:me-3 file:rounded file:border-0 file:bg-[var(--color-raised)] file:px-2 file:py-1 file:text-[var(--color-ink-soft)]"
          />
        </label>
        <label className="block">
          <span className="tt-label mb-2 block">{t('evidence.kind')}</span>
          <select name="kind" defaultValue="other" className="tt-field w-44">
            {KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {t(`evidenceKind.${kind}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block grow">
          <span className="tt-label mb-2 block">{t('evidence.description')}</span>
          <input name="description" className="tt-field" />
        </label>
        <button disabled={busy} className="tt-btn tt-btn-ghost">
          {busy ? t('common.loading') : t('evidence.upload')}
        </button>
      </form>

      {error && <p className="mb-3 text-[13px] text-[var(--color-danger)]">{error}</p>}

      {items.length === 0 ? (
        <p className="m-0 text-[13px] text-[var(--color-muted)]">{t('evidence.empty')}</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => {
            const state = integrity[item.id]
            const tone = state ? INTEGRITY_COLOR[state.status] : undefined
            return (
              <li
                key={item.id}
                className="rounded-xl border border-[var(--color-line)] bg-[var(--color-surface-2)] p-4"
                style={tone ? { borderColor: `color-mix(in srgb, ${tone} 45%, transparent)` } : undefined}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span dir="auto" className="tt-mono font-medium text-[var(--color-ink)]">
                    {item.original_filename}
                  </span>
                  <span className="tt-tag">{t(`evidenceKind.${item.kind}`)}</span>
                  <span className="tt-mono text-[11px] text-[var(--color-muted-dim)]">
                    {formatSize(item.size_bytes)}
                  </span>
                  {state && (
                    <span
                      className="tt-tag"
                      style={{
                        color: tone,
                        background: `color-mix(in srgb, ${tone} 13%, transparent)`,
                      }}
                    >
                      {t(`integrity.${state.status}`)}
                    </span>
                  )}
                </div>

                {item.description && (
                  <p dir="auto" className="mt-1.5 mb-0 text-[13px] text-[var(--color-muted)]">
                    {item.description}
                  </p>
                )}

                <p className="tt-mono mt-2 mb-0 break-all text-[10.5px] text-[var(--color-muted-dim)]">
                  <span className="tt-label">sha-256</span> {item.sha256}
                </p>

                {state && (
                  <p
                    className="mt-2 mb-0 text-[12px] leading-relaxed"
                    style={{ color: state.status === 'verified' ? 'var(--color-muted)' : tone }}
                  >
                    {state.status === 'verified'
                      ? t('integrity.verifiedNote')
                      : t('integrity.alteredNote')}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => verify(item.id)}
                    className="tt-btn tt-btn-ghost tt-btn-sm"
                  >
                    {t('evidence.verify')}
                  </button>

                  <select
                    value={target[item.id] ?? ''}
                    onChange={(e) => setTarget({ ...target, [item.id]: e.target.value })}
                    className="tt-field w-52 py-1.5 text-[12px]"
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
                    className="tt-btn tt-btn-primary tt-btn-sm"
                  >
                    {t('evidence.check')}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Section>
  )
}
