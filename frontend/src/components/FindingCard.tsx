import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import type { Finding, FindingType, ReviewDecision, RunKind } from '../api/types'

const TONE: Record<FindingType, string> = {
  possible_conflict: 'var(--color-danger)',
  unclear: 'var(--color-warn)',
  missing: 'var(--color-violet)',
  match: 'var(--color-accent)',
}

const DECISIONS: ReviewDecision[] = ['accepted', 'rejected', 'needs_more_info']

/** The engine's own words for a claim, quoted and never paraphrased. */
function Side({ label, text, tone }: { label: string; text: string | null; tone: string }) {
  return (
    <div className="min-w-0 flex-1 p-4">
      <div className="tt-label mb-2" style={{ color: tone }}>
        {label}
      </div>
      {text ? (
        <p dir="auto" className="m-0 text-[14px] leading-relaxed text-[var(--color-ink)]">
          &ldquo;{text}&rdquo;
        </p>
      ) : (
        <p className="tt-mono m-0 text-[12px] text-[var(--color-muted-dim)]">&mdash; not mentioned &mdash;</p>
      )}
    </div>
  )
}

export function FindingCard({ finding, kind }: { finding: Finding; kind?: RunKind }) {
  const { t } = useTranslation()
  const [decision, setDecision] = useState(finding.latest_decision)
  const [busy, setBusy] = useState(false)

  // On an evidence run the right-hand side is evidence text, which has no Claim row
  // of its own, so it travels in `details`.
  const evidenceText =
    typeof finding.details?.evidence_text === 'string' ? finding.details.evidence_text : null
  const leftLabel = kind === 'evidence' ? 'findings.statementSide' : 'findings.firstStatement'
  const rightLabel = kind === 'evidence' ? 'evidence.evidenceSide' : 'findings.secondStatement'

  const tone = TONE[finding.finding_type]
  const isConflict = finding.finding_type === 'possible_conflict'

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
    <li
      className="tt-card tt-rise overflow-hidden border-s-[3px] p-0"
      style={{ borderInlineStartColor: tone }}
    >
      <div className="flex flex-wrap items-center gap-2.5 border-b border-[var(--color-raised)] px-4 py-3">
        <span className="relative inline-flex h-2 w-2 flex-none">
          <span className="absolute inset-0 rounded-full" style={{ background: tone }} />
          {isConflict && (
            <span
              className="absolute inset-0 rounded-full"
              style={{ background: tone, animation: 'tt-halo 2s ease-out infinite' }}
            />
          )}
        </span>

        <span
          className="tt-mono text-[10.5px] font-bold uppercase tracking-[0.1em]"
          style={{ color: tone }}
        >
          {t(`findings.${finding.finding_type}`)}
        </span>

        {finding.field !== 'other' && <span className="tt-tag">{t(`field.${finding.field}`)}</span>}

        <span className="tt-mono ms-auto text-[11px] text-[var(--color-muted)]">
          {t('findings.linkScore')} {finding.score.toFixed(2)}
        </span>
        <span
          className="tt-tag"
          style={
            decision
              ? { color: 'var(--color-accent)', background: 'rgba(53,224,196,.12)' }
              : undefined
          }
        >
          {decision ? t(`findings.${decision}`) : t('findings.unreviewed')}
        </span>
      </div>

      <div className="flex flex-wrap divide-[var(--color-raised)] sm:flex-nowrap sm:divide-x sm:rtl:divide-x-reverse">
        <Side label={t(leftLabel)} text={finding.claim_a?.text ?? null} tone="var(--color-accent)" />
        <Side
          label={t(rightLabel)}
          text={finding.claim_b?.text ?? evidenceText}
          tone="var(--color-violet)"
        />
      </div>

      <p
        dir="auto"
        className="m-0 border-t border-[var(--color-raised)] px-4 py-3 text-[13px] leading-relaxed"
        style={{ background: `color-mix(in srgb, ${tone} 7%, transparent)`, color: tone }}
      >
        {finding.explanation}
      </p>

      <div className="flex flex-wrap items-center gap-2 border-t border-[var(--color-raised)] px-4 py-3">
        <span className="tt-label">{t('findings.review')}</span>
        {DECISIONS.map((value) => (
          <button
            key={value}
            disabled={busy}
            onClick={() => review(value)}
            className={`tt-btn tt-btn-sm ${decision === value ? 'tt-btn-primary' : 'tt-btn-ghost'}`}
          >
            {t(`findings.${value}`)}
          </button>
        ))}
      </div>
    </li>
  )
}
