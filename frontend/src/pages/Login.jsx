import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { formatApiError } from '../api/errors'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

export default function Login() {
  const { login } = useAuth()
  const { lang, setLang, t } = useLanguage()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      await login(email, password)
      nav('/')
    } catch (ex) {
      setErr(formatApiError(ex, t))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100/80 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="flex justify-end items-center gap-2 mb-6 text-sm text-slate-600">
          <span className="sr-only">{t('login.language')}</span>
          <button
            type="button"
            onClick={() => setLang('en')}
            className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
              lang === 'en' ? 'bg-white text-brand-700 shadow-sm border border-slate-200' : 'hover:bg-white/60'
            }`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setLang('es')}
            className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
              lang === 'es' ? 'bg-white text-brand-700 shadow-sm border border-slate-200' : 'hover:bg-white/60'
            }`}
          >
            ES
          </button>
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-slate-200/80 px-8 py-10">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{t('login.title')}</h1>
            <p className="text-sm text-slate-500 mt-2">{t('login.subtitle')}</p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5">
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('login.email')}
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 outline-none transition-shadow"
              />
            </div>
            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-1.5">
                {t('login.password')}
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 outline-none transition-shadow"
              />
            </div>
            {err && (
              <div className="rounded-lg bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-700" role="alert">
                {typeof err === 'string' ? err : JSON.stringify(err)}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-colors"
            >
              {loading ? t('login.submitting') : t('login.submit')}
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-slate-600">
            {t('login.noAccount')}{' '}
            <Link to="/register" className="text-brand-600 font-semibold hover:underline">
              {t('login.register')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
