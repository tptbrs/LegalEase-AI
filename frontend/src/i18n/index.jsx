import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import en from './en.json'
import hi from './hi.json'

const DICTS = { en, hi }
const STORAGE_KEY = 'legalease.lang'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    if (typeof window === 'undefined') return 'en'
    return window.localStorage.getItem(STORAGE_KEY) || 'en'
  })

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, lang)
    document.documentElement.lang = lang
  }, [lang])

  const value = useMemo(() => {
    const dict = DICTS[lang] || DICTS.en
    const t = (path, fallback = '') => {
      const parts = path.split('.')
      let cur = dict
      for (const p of parts) {
        if (cur && typeof cur === 'object' && p in cur) cur = cur[p]
        else return fallback || path
      }
      return cur
    }
    return { lang, setLang, t }
  }, [lang])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useI18n() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useI18n must be used within LanguageProvider')
  return ctx
}
