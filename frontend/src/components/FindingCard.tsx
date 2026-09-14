import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { Finding, FindingType, ReviewDecision, RunKind } from '../api/types'

const TONE: Record<FindingType, string> = {
  possible_conflict: 'border-red-300 bg-red-50',
  unclear: 'border-amber-300 bg-amber-50',
  missing: 'border-slate-300 bg-slate-50',
  match: 'border-emerald-300 bg-emerald-50',
}

const BADGE: Record<FindingType, string> = {
  possible_conflict: 'bg-red-600',
  unclear: 'bg-amber-600',
  missing: 'bg-slate-500',
  match: 'bg-emerald-600',
}

const DECISIONS: ReviewDecision[] = ['accepted', 'rejected', 'needs_more_info']

export function FindingCard({ finding, kind }: { finding: Finding; kind?: RunKind }) {
  const { t } = useTranslation()
  // On an evidence run the right-hand side is the evidence text, which has no Claim
  // row of its own, so it travels in `details`.
  const evidenceText =
    typeof finding.details?.evidence_text === 'string' ? finding.details.evidence_text : null
  const rightLabel = kind === 'evidence' ? 'evidence.evidenceSide' : 'findings.secondStatement'
  const leftLabel = kind === 'evidence' ? 'findings.statementSide' : 'findings.firstStatement'
  const [decision, setDecision] = useState(finding.latest_decision)
  const [busy, setBusy] = useState(false)

  async function review(value: ReviewDecision) {
    setBusy(true)
    try {
      await api.post(`/findings/${finding.id}/reviews`, { decision: value })
      setDecision(value)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className={`rounded-lg border p-4 ${TONE[finding.finding_type]}`}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium text-white ${BADGE[finding.finding_type]}`}>
          {t(`findings.${finding.finding_type}`)}
        </span>
        {finding.field !== 'other' && (
          <span className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs text-slate-700">
            {t(`field.${finding.field}`)}
          </span>
        )}
        <span
          className="ms-auto text-xs text-slate-500"
          title={t('findings.scoreHint')}
        >
          {t('findings.score')}: {finding.score.toFixed(2)}
        </span>
      </div>

      <p dir="auto" className="mb-3 text-sm text-slate-800">{finding.explanation}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        {(
          [
            [leftLabel, finding.claim_a?.text ?? null],
            [rightLabel, finding.claim_b?.text ?? evidenceText],
          ] as const
        ).map(([label, text]) => (
          <div key={label} className="rounded border border-slate-200 bg-white p-3">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
              {t(label)}
            </p>
            {text ? (
              <p dir="auto" className="text-sm text-slate-900">“{text}”</p>
            ) : (
              <p className="text-sm italic text-slate-400">{t('findings.notMentioned')}</p>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">{t('findings.review')}:</span>
        {DECISIONS.map((value) => (
          <button
            key={value}
            disabled={busy}
            onClick={() => review(value)}
            className={`rounded border px-2 py-1 text-xs ${
              decision === value
                ? 'border-slate-900 bg-slate-900 text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
            }`}
          >
            {t(`findings.${value}`)}
          </button>
        ))}
      </div>
    </li>
  )
}
