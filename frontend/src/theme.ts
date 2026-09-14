export const themes = ['light', 'dark', 'system'] as const
export type Theme = (typeof themes)[number]

const STORAGE_KEY = 'tt.theme'

function stored(): Theme {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    if (value === 'light' || value === 'dark' || value === 'system') return value
  } catch {
    // Private windows and blocked site data both throw here; the default is fine.
  }
  return 'system'
}

/** Writes the resolved theme onto <html>, which is what the CSS variables key off. */
function paint(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') {
    // Remove the attribute so the media query in index.css decides.
    root.removeAttribute('data-theme')
    root.setAttribute(
      'data-theme',
      window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    )
    return
  }
  root.setAttribute('data-theme', theme)
}

export function getTheme(): Theme {
  return stored()
}

export function setTheme(theme: Theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // A theme that cannot be remembered still applies for this visit.
  }
  paint(theme)
}

/** Applied before React renders, so the first paint is already the right theme. */
export function initTheme() {
  paint(stored())
  // Follow the operating system while the choice is "system".
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => {
      if (stored() === 'system') paint('system')
    })
}
