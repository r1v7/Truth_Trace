import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { getTheme, setTheme, themes, type Theme } from '../theme'

const ICON: Record<Theme, string> = { light: '☀', dark: '☾', system: '◐' }

/** Cycles light → dark → follow the system. Shown on the login screen too: the first
 *  page a visitor sees is where a mismatched theme is most jarring. */
export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation()
  const [theme, setCurrent] = useState<Theme>(getTheme)

  function next() {
    const value = themes[(themes.indexOf(theme) + 1) % themes.length]
    setTheme(value)
    setCurrent(value)
  }

  const label = t(`theme.${theme}`)
  return (
    <button
      onClick={next}
      className={compact ? 'tt-link' : 'tt-btn tt-btn-ghost tt-btn-sm'}
      title={label}
      aria-label={label}
    >
      <span aria-hidden>{ICON[theme]}</span>
      <span className={compact ? 'ms-1.5' : 'ms-2 hidden sm:inline'}>{label}</span>
    </button>
  )
}
