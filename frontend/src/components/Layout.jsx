import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { isAdminUser } from '../utils/roles'
import { GuideProvider, useGuide } from '../context/GuideContext'
import { useLanguage } from '../context/LanguageContext'
import GuideTour from './GuideTour'

function LayoutShell() {
  const { user, logout } = useAuth()
  const { lang, setLang, t } = useLanguage()
  const { startTour } = useGuide()
  const roleLabel = isAdminUser(user) ? t('layout.roleAdmin') : t('layout.roleUser')
  const link = 'px-3 py-2 rounded-lg text-sm font-medium transition-colors'
  const active = 'bg-brand-600 text-white'
  const idle = 'text-slate-600 hover:bg-slate-100'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <Link to="/" className="font-semibold text-brand-900">
            {t('layout.appName')}
          </Link>
          <nav className="flex items-center gap-1 flex-wrap" aria-label={t('guide.button')}>
            <NavLink
              data-tour="tour-dashboard"
              to="/"
              end
              className={({ isActive }) => `${link} ${isActive ? active : idle}`}
            >
              {t('layout.dashboard')}
            </NavLink>
            <NavLink
              data-tour="tour-upload"
              to="/upload"
              className={({ isActive }) => `${link} ${isActive ? active : idle}`}
            >
              {t('layout.upload')}
            </NavLink>
            <NavLink
              data-tour="tour-reports"
              to="/reports"
              className={({ isActive }) => `${link} ${isActive ? active : idle}`}
            >
              {t('layout.reports')}
            </NavLink>
            <NavLink
              to="/billing"
              className={({ isActive }) => `${link} ${isActive ? active : idle}`}
            >
              {t('layout.billing')}
            </NavLink>
            {isAdminUser(user) && (
              <NavLink
                to="/admin"
                className={({ isActive }) => `${link} ${isActive ? active : idle}`}
              >
                {t('layout.admin')}
              </NavLink>
            )}
          </nav>
          <div className="flex items-center gap-2 sm:gap-3 text-sm text-slate-600 flex-wrap justify-end">
            <button
              type="button"
              onClick={startTour}
              className="text-xs font-medium text-brand-700 border border-brand-200 bg-brand-50/80 hover:bg-brand-100/90 px-2 sm:px-2.5 py-1 rounded-lg shrink-0"
              title={t('guide.button')}
              aria-label={t('guide.button')}
            >
              <span className="hidden sm:inline">{t('guide.button')}</span>
              <span className="sm:hidden" aria-hidden>
                ?
              </span>
            </button>
            <div
              data-tour="tour-language"
              className="flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs"
            >
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`px-2 py-0.5 rounded ${lang === 'en' ? 'bg-white shadow-sm font-medium text-slate-900' : 'text-slate-500'}`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang('es')}
                className={`px-2 py-0.5 rounded ${lang === 'es' ? 'bg-white shadow-sm font-medium text-slate-900' : 'text-slate-500'}`}
              >
                ES
              </button>
            </div>
            <span className="hidden sm:inline truncate max-w-[180px]">{user?.email}</span>
            {user?.role != null && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100">{roleLabel}</span>
            )}
            <button type="button" onClick={logout} className="text-brand-600 hover:underline">
              {t('layout.signOut')}
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <Outlet />
      </main>
      <GuideTour />
    </div>
  )
}

export default function Layout() {
  return (
    <GuideProvider>
      <LayoutShell />
    </GuideProvider>
  )
}
