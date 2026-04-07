import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { formatApiError } from '../api/errors'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

export default function Register() {
  const { register } = useAuth()
  const { t } = useLanguage()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const [agreedLegal, setAgreedLegal] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    if (!agreedLegal) {
      setErr(t('register.legalRequired'))
      return
    }
    setErr('')
    setLoading(true)
    try {
      await register(email, password, fullName)
      nav('/')
    } catch (ex) {
      setErr(formatApiError(ex, t))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 p-8 bg-white rounded-2xl shadow-sm border border-slate-200">
      <h1 className="text-2xl font-semibold text-slate-900 mb-6">{t('register.title')}</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('register.fullName')}</label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('register.email')}</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('register.password')}</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={agreedLegal}
            onChange={(e) => setAgreedLegal(e.target.checked)}
            className="mt-1 rounded border-slate-300"
          />
          <span>
            {t('register.agreeIntro')}{' '}
            <Link to="/terms" className="text-brand-600 font-medium hover:underline" target="_blank" rel="noreferrer">
              {t('legal.termsNav')}
            </Link>
            {t('register.agreeAnd')}{' '}
            <Link to="/privacy" className="text-brand-600 font-medium hover:underline" target="_blank" rel="noreferrer">
              {t('legal.privacyNav')}
            </Link>
            {t('register.agreeOutro')}
          </span>
        </label>
        {err && <p className="text-sm text-red-600">{typeof err === 'string' ? err : JSON.stringify(err)}</p>}
        <button
          type="submit"
          disabled={loading || !agreedLegal}
          className="w-full py-2.5 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-500 disabled:opacity-50"
        >
          {loading ? t('register.creating') : t('register.submit')}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate-600 text-center">
        {t('register.hasAccount')}{' '}
        <Link to="/login" className="text-brand-600 font-medium hover:underline">
          {t('register.signIn')}
        </Link>
      </p>
      <p className="mt-4 text-xs text-slate-500 text-center">
        <Link to="/refunds" className="text-brand-600 hover:underline">
          {t('legal.refundsNav')}
        </Link>
      </p>
    </div>
  )
}
