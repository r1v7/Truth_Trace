import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import ar from './ar.json'
import en from './en.json'

const STORAGE_KEY = 'tt.lang'

export const languages = ['en', 'ar'] as const
export type Language = (typeof languages)[number]

function initial(): Language {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'ar' || saved === 'en' ? saved : 'en'
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: initial(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function applyDirection(lang: Language) {
  document.documentElement.lang = lang
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
}

export function setLanguage(lang: Language) {
  localStorage.setItem(STORAGE_KEY, lang)
  void i18n.changeLanguage(lang)
  applyDirection(lang)
}

applyDirection(initial())

export default i18n
