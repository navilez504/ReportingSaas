import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { formatApiError } from '../api/errors'
import { useLanguage } from '../context/LanguageContext'

function formatPlanPrice(amount, currency, perMonthLabel) {
  const c = (currency || 'usd').toLowerCase()
  if (c === 'usd') {
    return (
      <>
        ${amount}
        <span className="text-sm font-normal text-slate-500">{perMonthLabel}</span>
      </>
    )
  }
  return (
    <>
      {amount} {c.toUpperCase()}
      <span className="text-sm font-normal text-slate-500">{perMonthLabel}</span>
    </>
  )
}

export default function Billing() {
  const { t } = useLanguage()
  const [searchParams] = useSearchParams()
  const [plans, setPlans] = useState([])
  const [pricingSource, setPricingSource] = useState('default')
  const [summary, setSummary] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [checkoutPlan, setCheckoutPlan] = useState(null)
  const [portalLoading, setPortalLoading] = useState(false)

  const success = searchParams.get('success')
  const canceled = searchParams.get('canceled')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([api.get('/billing/plans'), api.get('/dashboard/plan-summary')])
      .then(([p, s]) => {
        if (!cancelled) {
          setPlans(p.data?.plans || [])
          setPricingSource(p.data?.pricing_source || 'default')
          setSummary(s.data)
        }
      })
      .catch((e) => {
        if (!cancelled) setErr(formatApiError(e, t))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [success, canceled, t])

  async function startCheckout(planId) {
    setErr('')
    setCheckoutPlan(planId)
    try {
      const { data } = await api.post('/billing/checkout-session', { plan: planId })
      if (data?.url) window.location.href = data.url
    } catch (e) {
      setErr(formatApiError(e, t))
    } finally {
      setCheckoutPlan(null)
    }
  }

  async function startPortal() {
    setErr('')
    setPortalLoading(true)
    try {
      const { data } = await api.post('/billing/portal-session')
      if (data?.url) window.location.href = data.url
    } catch (e) {
      setErr(formatApiError(e, t))
    } finally {
      setPortalLoading(false)
    }
  }

  const canSubscribe = summary?.stripe_checkout_available === true
  const canPortal = summary?.stripe_billing_portal_available === true
  const features = summary?.features || {}

  function yesNo(v) {
    return v ? '✓' : '—'
  }

  return (
    <div className="space-y-10 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('billing.title')}</h1>
        <p className="text-slate-600 mt-1">{t('billing.subtitle')}</p>
      </div>

      {success && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {t('billing.checkoutSuccess')}
        </div>
      )}
      {canceled && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          {t('billing.checkoutCanceled')}
        </div>
      )}

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && <p className="text-sm text-red-600">{err}</p>}

      {summary && !loading && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-3">
          <h2 className="font-semibold text-slate-900">{t('billing.currentPlan')}</h2>
          <dl className="text-sm grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700">
            <div>
              <dt className="text-slate-500">{t('billing.planLabel')}</dt>
              <dd className="font-medium capitalize">{summary.plan}</dd>
            </div>
            {summary.subscription_status && (
              <div>
                <dt className="text-slate-500">{t('billing.subscriptionStatus')}</dt>
                <dd className="font-medium">{summary.subscription_status}</dd>
              </div>
            )}
            {summary.plan === 'trial' && summary.trial_ends_at && !summary.trial_expired && (
              <div className="sm:col-span-2">
                <dt className="text-slate-500">{t('billing.trialEnds')}</dt>
                <dd className="font-medium">
                  {new Date(summary.trial_ends_at).toLocaleString()}
                  {summary.trial_days_remaining != null && (
                    <span className="text-slate-500 ml-2">
                      (
                      {t('billing.trialDaysLeft').replace(
                        '{days}',
                        String(Math.ceil(summary.trial_days_remaining)),
                      )}
                      )
                    </span>
                  )}
                </dd>
              </div>
            )}
          </dl>
          {canPortal && (
            <div className="pt-2 border-t border-slate-100">
              <button
                type="button"
                disabled={portalLoading}
                onClick={startPortal}
                className="text-sm px-4 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 font-medium text-slate-800 disabled:opacity-50"
              >
                {portalLoading ? t('billing.redirecting') : t('billing.manageBilling')}
              </button>
              <p className="text-xs text-slate-500 mt-2">{t('billing.portalHint')}</p>
            </div>
          )}
          <ul className="text-xs text-slate-500 space-y-1 pt-2 border-t border-slate-100">
            <li>
              {t('billing.incBi')}: <span className="font-medium text-slate-700">{yesNo(features.bi_summary)}</span>
            </li>
            <li>
              {t('billing.incCharts')}: <span className="font-medium text-slate-700">{yesNo(features.bi_charts)}</span>
            </li>
            <li>
              {t('billing.incInsights')}:{' '}
              <span className="font-medium text-slate-700">{yesNo(features.bi_insights)}</span>
            </li>
            <li>
              {t('billing.incPdf')}:{' '}
              <span className="font-medium text-slate-700">{yesNo(features.pdf_reports)}</span>
            </li>
          </ul>
        </div>
      )}

      {!canSubscribe && !loading && (
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-4 py-3">
          {t('billing.stripeNotConfigured')}
        </p>
      )}

      {pricingSource === 'stripe' && canSubscribe && !loading && (
        <p className="text-xs text-slate-500">{t('billing.pricingFromStripe')}</p>
      )}

      <p className="text-xs text-slate-500 -mb-4">
        {t('billing.legalCheckoutHint')}{' '}
        <Link to="/terms" className="text-brand-600 hover:underline">
          {t('legal.termsNav')}
        </Link>
        {' · '}
        <Link to="/privacy" className="text-brand-600 hover:underline">
          {t('legal.privacyNav')}
        </Link>
        {' · '}
        <Link to="/refunds" className="text-brand-600 hover:underline">
          {t('legal.refundsNav')}
        </Link>
      </p>

      <div className="grid gap-4 sm:grid-cols-3">
        {plans.map((p) => (
          <div
            key={p.id}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex flex-col"
          >
            <h3 className="font-semibold text-slate-900">{p.name}</h3>
            <p className="text-2xl font-bold text-brand-700 mt-2">
              {formatPlanPrice(p.price_usd_month, p.currency, t('billing.perMonth'))}
            </p>
            <p className="text-sm text-slate-600 mt-3 flex-1">{p.description}</p>
            <button
              type="button"
              disabled={!canSubscribe || checkoutPlan != null || summary?.plan === p.id}
              onClick={() => startCheckout(p.id)}
              className="mt-4 w-full py-2.5 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500 disabled:opacity-50"
            >
              {checkoutPlan === p.id ? t('billing.redirecting') : t('billing.subscribe')}
            </button>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-500">
        <Link to="/" className="text-brand-600 hover:underline">
          {t('billing.backDashboard')}
        </Link>
      </p>
    </div>
  )
}
