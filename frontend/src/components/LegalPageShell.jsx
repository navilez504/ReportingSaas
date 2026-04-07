import { Link } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

export default function LegalPageShell({ titleKey, children }) {
  const { t } = useLanguage()
  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <article className="max-w-2xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-sm p-8 md:p-10 text-sm text-slate-700 leading-relaxed space-y-4">
        <h1 className="text-2xl font-semibold text-slate-900">{t(titleKey)}</h1>
        {children}
        <p className="pt-6 border-t border-slate-100 text-xs text-slate-500">
          <Link to="/login" className="text-brand-600 hover:underline">
            {t('legal.backToSignIn')}
          </Link>
          {' · '}
          <Link to="/register" className="text-brand-600 hover:underline">
            {t('legal.backToRegister')}
          </Link>
        </p>
      </article>
    </div>
  )
}
