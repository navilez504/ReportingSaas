import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../api/client'
import { formatApiError } from '../../api/errors'
import { useLanguage } from '../../context/LanguageContext'

const COLORS = ['#0ea5e9', '#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#14b8a6']
const H = 260

function PieTip({ active, payload, total }) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  const v = Number(p.value)
  const pct = total > 0 ? (v / total) * 100 : 0
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
      <span className="font-medium text-slate-800">{p.name}</span>
      <span className="text-slate-600"> · {pct.toFixed(1)}%</span>
    </div>
  )
}

function fmtMoney(v) {
  if (v == null || Number.isNaN(v)) return '—'
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function BiAnalytics({ datasetId, dateFrom, dateTo }) {
  const { t, lang } = useLanguage()
  const [summary, setSummary] = useState(null)
  const [charts, setCharts] = useState(null)
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    if (!datasetId) {
      setSummary(null)
      setCharts(null)
      setInsights(null)
      return
    }
    const params = { dataset_id: Number(datasetId) }
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo

    let cancelled = false
    setLoading(true)
    setErr('')
    Promise.all([
      api.get('/dashboard/summary', { params }),
      api.get('/dashboard/charts', { params }),
      api.get('/dashboard/insights', { params }),
    ])
      .then(([s, c, i]) => {
        if (cancelled) return
        setSummary(s.data)
        setCharts(c.data)
        setInsights(i.data)
      })
      .catch((e) => {
        if (cancelled) return
        setErr(formatApiError(e, t))
        setSummary(null)
        setCharts(null)
        setInsights(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [datasetId, dateFrom, dateTo, lang])

  if (!datasetId) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-sm text-slate-500">
        {t('bi.selectDataset')}
      </div>
    )
  }

  if (loading && !summary) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-600">
        <p className="animate-pulse">{t('bi.loading')}</p>
      </div>
    )
  }

  if (err) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-medium">{t('bi.unavailable')}</p>
        <p className="mt-1 text-amber-800/90">{err}</p>
      </div>
    )
  }

  if (!summary) {
    return null
  }

  const regionPie = charts?.sales_by_region ?? []
  const regionTotal = regionPie.reduce((s, p) => s + (Number(p.value) || 0), 0)
  const renderPieLabel = (props) => {
    const { name, value, percent } = props
    let pct
    if (typeof percent === 'number' && Number.isFinite(percent)) {
      pct = percent * 100
    } else if (regionTotal > 0) {
      pct = (Number(value) / regionTotal) * 100
    } else {
      pct = 0
    }
    const n = String(name ?? '')
    const short = n.length > 12 ? `${n.slice(0, 12)}…` : n
    return `${short} ${pct.toFixed(1)}%`
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{t('bi.title')}</h2>
        <p className="text-sm text-slate-600 mt-0.5">{t('bi.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-gradient-to-br from-sky-50 to-white border border-sky-100 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-sky-700">{t('bi.totalSales')}</p>
          <p className="text-2xl font-semibold text-slate-900 mt-2">{fmtMoney(summary.total_sales)}</p>
        </div>
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('bi.totalOrders')}</p>
          <p className="text-2xl font-semibold text-slate-900 mt-2">{summary.total_orders}</p>
        </div>
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('bi.avgOrder')}</p>
          <p className="text-2xl font-semibold text-slate-900 mt-2">{fmtMoney(summary.average_order_value)}</p>
        </div>
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('bi.totalQty')}</p>
          <p className="text-2xl font-semibold text-slate-900 mt-2">
            {Number(summary.total_quantity).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {(summary.total_cost != null || summary.profit != null) && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {summary.total_cost != null && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <p className="text-xs text-slate-500">{t('bi.totalCost')}</p>
              <p className="text-lg font-semibold text-slate-900">{fmtMoney(summary.total_cost)}</p>
            </div>
          )}
          {summary.profit != null && (
            <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-100">
              <p className="text-xs text-emerald-800">{t('bi.profit')}</p>
              <p className="text-lg font-semibold text-emerald-900">{fmtMoney(summary.profit)}</p>
            </div>
          )}
          {summary.profit_margin != null && (
            <div className="p-4 rounded-xl bg-white border border-slate-200">
              <p className="text-xs text-slate-500">{t('bi.profitMargin')}</p>
              <p className="text-lg font-semibold text-slate-900">
                {(summary.profit_margin * 100).toFixed(1)}%
              </p>
            </div>
          )}
        </div>
      )}

      {insights?.messages?.length > 0 && (
        <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5">
          <h3 className="text-sm font-semibold text-indigo-950 mb-3">{t('bi.insights')}</h3>
          <ul className="space-y-2">
            {insights.messages.map((m, i) => (
              <li key={i} className="flex gap-2 text-sm text-indigo-900/90">
                <span className="text-indigo-400 shrink-0">▸</span>
                <span>{m}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[320px]">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">{t('bi.salesByProduct')}</h3>
          <p className="text-xs text-slate-500 mb-3">{t('bi.salesByProductHint')}</p>
          {charts?.sales_by_product?.length ? (
            <div style={{ width: '100%', height: H }}>
              <ResponsiveContainer width="100%" height={H}>
                <BarChart data={charts.sales_by_product} margin={{ top: 8, right: 8, left: 8, bottom: 64 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={70} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => fmtMoney(v)} />
                  <Bar dataKey="value" fill="#0ea5e9" name={t('bi.seriesSales')} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-8 text-center">{t('bi.noProductCol')}</p>
          )}
        </div>

        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[320px]">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">{t('bi.salesByRegion')}</h3>
          <p className="text-xs text-slate-500 mb-3">{t('bi.salesByRegionHint')}</p>
          {regionPie.length ? (
            <div style={{ width: '100%', height: H + 40 }}>
              <ResponsiveContainer width="100%" height={H + 40}>
                <PieChart>
                  <Pie
                    data={regionPie}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={renderPieLabel}
                  >
                    {regionPie.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTip total={regionTotal} />} wrapperStyle={{ outline: 'none' }} />
                  <Legend
                    formatter={(value, entry) => {
                      const raw = entry?.payload?.value
                      const pct = regionTotal > 0 ? (Number(raw) / regionTotal) * 100 : 0
                      return `${value}: ${pct.toFixed(1)}%`
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-8 text-center">{t('bi.noRegionCol')}</p>
          )}
        </div>

        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[320px]">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">{t('bi.salesBySeller')}</h3>
          <p className="text-xs text-slate-500 mb-3">{t('bi.salesBySellerHint')}</p>
          {charts?.sales_by_seller?.length ? (
            <div style={{ width: '100%', height: H }}>
              <ResponsiveContainer width="100%" height={H}>
                <BarChart data={charts.sales_by_seller} margin={{ top: 8, right: 8, left: 8, bottom: 64 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => fmtMoney(v)} />
                  <Bar dataKey="value" fill="#6366f1" name={t('bi.seriesSales')} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-8 text-center">{t('bi.noSellerCol')}</p>
          )}
        </div>

        <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[320px]">
          <h3 className="text-sm font-semibold text-slate-900 mb-1">{t('bi.salesOverTime')}</h3>
          <p className="text-xs text-slate-500 mb-3">{t('bi.salesOverTimeHint')}</p>
          {charts?.sales_over_time?.length ? (
            <div style={{ width: '100%', height: H }}>
              <ResponsiveContainer width="100%" height={H}>
                <LineChart data={charts.sales_over_time} margin={{ top: 8, right: 8, left: 8, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => fmtMoney(v)} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                    name={t('bi.seriesSales')}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-8 text-center">{t('bi.noDatedRows')}</p>
          )}
        </div>
      </div>

      {loading && <p className="text-xs text-slate-400 text-center">{t('bi.refreshing')}</p>}
    </div>
  )
}
