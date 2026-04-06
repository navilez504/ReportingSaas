import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { translations } from '../i18n/translations'

const STORAGE_KEY = 'app_language'

const LanguageContext = createContext({
  lang: 'en',
  setLang: () => {},
  t: (key) => key,
})

function getNested(obj, path) {
  return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), obj)
}

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try {
      const s = localStorage.getItem(STORAGE_KEY)
      if (s === 'es' || s === 'en') return s
    } catch {
      /* ignore */
    }
    if (typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('es')) return 'es'
    return 'en'
  })

  const setLang = useCallback((next) => {
    const l = next === 'es' ? 'es' : 'en'
    setLangState(l)
    try {
      localStorage.setItem(STORAGE_KEY, l)
    } catch {
      /* ignore */
    }
  }, [])

  const t = useCallback(
    (path) => {
      const bundle = translations[lang] || translations.en
      const v = getNested(bundle, path)
      if (v !== undefined) return v
      const fb = getNested(translations.en, path)
      return fb !== undefined ? fb : path
    },
    [lang]
  )

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  return useContext(LanguageContext)
}
