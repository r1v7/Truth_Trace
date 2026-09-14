import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'

const SLOW_AFTER_MS = 2500

/**
 * A free-tier API server sleeps when idle and takes up to a minute to answer the first
 * request. Without this, the first visitor sees a page that looks broken and leaves.
 * The banner only appears once a request has actually been slow, so a warm server
 * never shows it.
 */
export function Waking() {
  const { t } = useTranslation()
  const [waking, setWaking] = useState(false)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    let pending = 0
    let slowTimer: ReturnType<typeof setTimeout> | undefined

    function started() {
      pending += 1
      if (pending === 1) {
        slowTimer = setTimeout(() => setWaking(true), SLOW_AFTER_MS)
      }
    }

    function finished() {
      pending = Math.max(0, pending - 1)
      if (pending === 0) {
        clearTimeout(slowTimer)
        setWaking(false)
      }
    }

    const request = api.interceptors.request.use((config) => {
      started()
      return config
    })
    const response = api.interceptors.response.use(
      (value) => {
        finished()
        return value
      },
      (error) => {
        finished()
        throw error
      },
    )

    return () => {
      api.interceptors.request.eject(request)
      api.interceptors.response.eject(response)
      clearTimeout(slowTimer)
    }
  }, [])

  useEffect(() => {
    if (!waking) {
      setSeconds(0)
      return
    }
    const tick = setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => clearInterval(tick)
  }, [waking])

  if (!waking) return null

  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-0 z-20 flex flex-wrap items-center justify-center gap-3 border-t border-[var(--color-line)] px-5 py-3 text-[13px]"
      style={{ background: 'rgba(11,15,22,.96)', backdropFilter: 'blur(8px)' }}
    >
      <span
        className="h-3.5 w-3.5 flex-none rounded-full border-2 border-[var(--color-line-3)] border-t-[var(--color-accent)]"
        style={{ animation: 'tt-spin .8s linear infinite' }}
      />
      <span className="text-[var(--color-ink-soft)]">{t('waking.title')}</span>
      <span className="text-[var(--color-muted)]">{t('waking.detail')}</span>
      <span className="tt-mono text-[var(--color-muted-dim)]">{seconds}s</span>
    </div>
  )
}
