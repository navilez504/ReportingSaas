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
import { api } from '../api/client'
import { formatApiError } from '../api/errors'
import BiAnalytics from '../components/bi/BiAnalytics'
import { useLanguage } from '../context/LanguageContext'

function metaMessage(msg, t) {
  if (msg === 'Upload a dataset to see KPIs') return t('dashboard.uploadDatasetMessage')
  return msg
}

const COLORS = ['#0ea5e9', '#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#14b8a6']
const CHART_H = 288

function inferPreviewColumnKind(colName) {
  const n = String(colName).toLowerCase()
  if (/(^|_)fecha|(^|_)date|(^|_)time|dia\b/.test(n)) return 'date'
  if (/(precio|price|importe|monto|total_|^total$|valor|cost|ganancia|venta|€|\$)/.test(n))
    return 'currency'
  if (/(cantidad|qty|quantity|units)/.test(n)) return 'integer'
  if (n === 'id' || /_id$/.test(n)) return 'integer'
  return 'text'
}

/** When API stores column names as one CSV string, split for the table header. */
function expandDisplayColumns(cols) {
  if (!Array.isArray(cols) || cols.length !== 1) return Array.isArray(cols) ? cols : []
  const s = String(cols[0])
  if (s.includes(',') && s.length > 2) {
    return s.split(',').map((c) => c.trim()).filter(Boolean)
  }
  return cols
}

function PieSliceTooltip({ active, payload, total }) {
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

function formatPreviewCell(value, kind) {
  if (value == null || value === '') return '—'
  if (kind === 'integer') {
    const x = Number(value)
    if (!Number.isFinite(x)) return String(value)
    return Math.round(x).toLocaleString(undefined, { maximumFractionDigits: 0 })
  }
  if (kind === 'currency') {
    const x = Number(value)
    if (!Number.isFinite(x)) return String(value)
    return x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  if (kind === 'date') {
    const t = Date.parse(String(value))
    if (!Number.isFinite(t)) return String(value)
    return new Date(t).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
  }
  return String(value)
}

export default function Dashboard() {
  const { t } = useLanguage()
  const [data, setData] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [datasetId, setDatasetId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [chartX, setChartX] = useState('')
  const [chartY, setChartY] = useState('')
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [planSummary, setPlanSummary] = useState(null)

  useEffect(() => {
    api
      .get('/dashboard/plan-summary')
      .then((r) => setPlanSummary(r.data))
      .catch(() => setPlanSummary(null))
  }, [])

  useEffect(() => {
    api
      .get('/upload/datasets')
      .then((r) => {
        setDatasets(Array.isArray(r.data) ? r.data : [])
        if (r.data?.length && !datasetId) setDatasetId(String(r.data[0].id))
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    setChartX('')
    setChartY('')
  }, [datasetId])

  useEffect(() => {
    setLoading(true)
    setErr('')
    const params = {}
    if (datasetId) params.dataset_id = Number(datasetId)
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (chartX && chartY) {
      params.chart_x = chartX
      params.chart_y = chartY
    }
    api
      .get('/dashboard', { params })
      .then((r) => setData(r.data))
      .catch((e) => {
        setErr(formatApiError(e, t))
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [datasetId, dateFrom, dateTo, chartX, chartY])

  const fmt = (v) => {
    if (v == null || Number.isNaN(v)) return '—'
    return Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  const kpis = Array.isArray(data?.kpis) ? data.kpis : []
  const lineSeries = Array.isArray(data?.line_series) ? data.line_series : []
  const barSeries = Array.isArray(data?.bar_series) ? data.bar_series : []
  const pieSeries = Array.isArray(data?.pie_series) ? data.pie_series : []
  const previewRows = Array.isArray(data?.preview_rows) ? data.preview_rows : []
  const hasCharts = lineSeries.length > 0 || barSeries.length > 0 || pieSeries.length > 0
  const metaCols = expandDisplayColumns(Array.isArray(data?.meta?.columns) ? data.meta.columns : [])
  const tableColumns =
    metaCols.length > 0 ? metaCols : previewRows.length > 0 ? Object.keys(previewRows[0]) : []
  const labelX = data?.meta?.chart_x_selected ?? data?.meta?.chart_x_effective ?? 'X'
  const labelY = data?.meta?.chart_y_selected ?? data?.meta?.chart_y_effective ?? 'Y'
  const pieTotal =
    pieSeries.length > 0 ? pieSeries.reduce((s, p) => s + (Number(p.value) || 0), 0) : 0

  const renderPieLabel = (props) => {
    const { name, value, percent } = props
    let pct
    if (typeof percent === 'number' && Number.isFinite(percent)) {
      pct = percent * 100
    } else if (pieTotal > 0) {
      pct = (Number(value) / pieTotal) * 100
    } else {
      pct = 0
    }
    const n = String(name ?? '')
    const short = n.length > 14 ? `${n.slice(0, 14)}…` : n
    return `${short} ${pct.toFixed(1)}%`
  }

  if (!data && loading) {
    return <p className="text-slate-600 p-4">{t('dashboard.loading')}</p>
  }

  return (
    <div className={`space-y-8 ${loading ? 'opacity-80' : ''}`}>
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('dashboard.title')}</h1>
        <p className="text-slate-600 mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {planSummary?.plan === 'trial' && !planSummary.trial_expired && (
        <div className="rounded-xl border border-brand-200 bg-brand-50/90 px-4 py-3 text-sm text-brand-900">
          {t('dashboard.trialBanner')}
          {planSummary.trial_days_remaining != null && (
            <span className="block mt-1 text-brand-800">
              {t('upload.trialDaysLeft').replace(
                '{days}',
                String(Math.ceil(planSummary.trial_days_remaining)),
              )}
            </span>
          )}
        </div>
      )}
      {planSummary?.trial_expired && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {t('upload.trialExpiredUpload')}
        </div>
      )}
      {planSummary?.notifications?.includes('file_limit_reached') && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {t('upload.notifyLimit')}
        </div>
      )}

      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">{t('dashboard.dataset')}</label>
          <select
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm min-w-[200px]"
          >
            <option value="">{t('dashboard.latest')}</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.row_count} {t('dashboard.rowsSuffix')})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">{t('dashboard.from')}</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">{t('dashboard.to')}</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={() => {
            setDateFrom('')
            setDateTo('')
          }}
          className="text-sm text-brand-600 hover:underline px-2 py-2"
        >
          {t('dashboard.clearDates')}
        </button>
      </div>

      <p className="text-xs text-slate-500 max-w-2xl">
        {t('dashboard.dateFilterHint')}
      </p>

      <BiAnalytics
        datasetId={datasetId || (data?.dataset_id != null ? String(data.dataset_id) : '')}
        dateFrom={dateFrom}
        dateTo={dateTo}
      />

      {err && <p className="text-red-600 text-sm">{err}</p>}

      {data?.meta?.message && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">
          {metaMessage(data.meta.message, t)}
        </div>
      )}

      {data?.meta?.warning && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">
          {data.meta.warning}
        </div>
      )}

      {kpis.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((k, i) => (
            <div
              key={`${k.key}-${i}`}
              className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{k.label}</p>
              <p className="text-2xl font-semibold text-slate-900 mt-2">
                {fmt(k.value)}
                {k.unit ? ` ${k.unit}` : ''}
              </p>
              {k.change_pct != null && !Number.isNaN(k.change_pct) && (
                <p className="text-sm text-emerald-600 mt-1">Δ {Number(k.change_pct).toFixed(1)}%</p>
              )}
            </div>
          ))}
        </div>
      )}

      {data && data.dataset_id != null && kpis.length === 0 && (
        <p className="text-slate-600 text-sm">{t('dashboard.noKpis')}</p>
      )}

      {previewRows.length > 0 && tableColumns.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 rounded-t-2xl">
            <h2 className="text-lg font-semibold text-slate-900">{t('dashboard.dataPreview')}</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {previewRows.length}{' '}
              {previewRows.length !== 1 ? t('dashboard.rowPlural') : t('dashboard.rowSingular')}{' '}
              {t('dashboard.afterFilters')}
            </p>
          </div>
          <div className="relative max-h-[420px] overflow-auto rounded-b-2xl isolate">
            <table className="min-w-full text-sm border-collapse border border-slate-300 bg-white">
              <thead className="sticky top-0 z-[100] bg-slate-100">
                <tr>
                  {tableColumns.map((col) => (
                    <th
                      key={col}
                      scope="col"
                      className="border border-slate-300 px-2.5 py-2.5 font-semibold text-slate-900 text-left whitespace-nowrap shadow-[inset_0_-1px_0_0_#94a3b8]"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, ri) => (
                  <tr key={ri} className="odd:bg-white even:bg-slate-50/90 hover:bg-sky-50/60">
                    {tableColumns.map((col) => {
                      const kind = inferPreviewColumnKind(col)
                      const align =
                        kind === 'text' ? 'text-left' : 'text-right tabular-nums'
                      return (
                        <td
                          key={col}
                          className={`border border-slate-200 px-2.5 py-1.5 text-slate-900 whitespace-nowrap max-w-[min(280px,40vw)] truncate ${align}`}
                          title={row[col] != null ? String(row[col]) : ''}
                        >
                          {formatPreviewCell(row[col], kind)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data?.meta?.columns?.length > 0 && (
        <div className="text-xs text-slate-500 space-y-1">
          <p>
            {t('dashboard.columns')}: {Array.isArray(data.meta.columns) ? data.meta.columns.join(', ') : ''}
          </p>
          {(data.meta.measure_column || data.meta.time_column) && (
            <p>
              {t('dashboard.measure')}:{' '}
              <span className="font-medium text-slate-700">{data.meta.measure_column || '—'}</span>
              {' · '}
              {t('dashboard.time')}:{' '}
              <span className="font-medium text-slate-700">{data.meta.time_column || '—'}</span>
            </p>
          )}
        </div>
      )}

      {!hasCharts && data?.dataset_id != null && !loading && (
        <p className="text-sm text-slate-600">{t('dashboard.chartsHint')}</p>
      )}

      {data?.dataset_id != null && metaCols.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">{t('dashboard.chartX')}</label>
            <select
              value={chartX === '' ? '__auto__' : chartX}
              onChange={(e) => {
                const v = e.target.value
                setChartX(v === '__auto__' ? '' : v)
              }}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm min-w-[180px] bg-white"
            >
              <option value="__auto__">{t('dashboard.chartAuto')}</option>
              {metaCols.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">{t('dashboard.chartY')}</label>
            <select
              value={chartY === '' ? '__auto__' : chartY}
              onChange={(e) => {
                const v = e.target.value
                setChartY(v === '__auto__' ? '' : v)
              }}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm min-w-[180px] bg-white"
            >
              <option value="__auto__">{t('dashboard.chartAuto')}</option>
              {metaCols.map((c) => (
                <option key={`y-${c}`} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-slate-500 max-w-md pb-1">{t('dashboard.chartPickerHelp')}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {lineSeries.length > 0 && (
          <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[360px]">
            <h2 className="text-lg font-semibold">{t('dashboard.trend')}</h2>
            <p className="text-xs text-slate-500 mb-3">
              {labelX} → {labelY}
            </p>
            <div style={{ width: '100%', height: CHART_H }}>
              <ResponsiveContainer width="100%" height={CHART_H}>
                <LineChart data={lineSeries} margin={{ top: 8, right: 8, left: 8, bottom: 28 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    label={{ value: labelX, position: 'insideBottom', offset: -4, fontSize: 11, fill: '#64748b' }}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    label={{ value: labelY, angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' }}
                  />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={false}
                    name={labelY}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {barSeries.length > 0 && (
          <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-sm min-h-[360px]">
            <h2 className="text-lg font-semibold">{t('dashboard.byCategory')}</h2>
            <p className="text-xs text-slate-500 mb-3">
              {labelX} → {labelY}
            </p>
            <div style={{ width: '100%', height: CHART_H }}>
              <ResponsiveContainer width="100%" height={CHART_H}>
                <BarChart data={barSeries} margin={{ top: 8, right: 8, left: 8, bottom: 48 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10 }}
                    angle={-25}
                    textAnchor="end"
                    height={60}
                    label={{ value: labelX, position: 'insideBottom', offset: 2, fontSize: 11, fill: '#64748b' }}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    label={{ value: labelY, angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' }}
                  />
                  <Tooltip />
                  <Bar dataKey="value" fill="#6366f1" name={labelY} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {pieSeries.length > 0 && (
          <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 min-h-[420px]">
            <h2 className="text-lg font-semibold mb-1">{t('dashboard.distribution')}</h2>
            <p className="text-xs text-slate-500 mb-3">{t('dashboard.distributionHint')}</p>
            <div style={{ width: '100%', height: 360 }}>
              <ResponsiveContainer width="100%" height={360}>
                <PieChart>
                  <Pie
                    data={pieSeries}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    label={renderPieLabel}
                  >
                    {pieSeries.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={<PieSliceTooltip total={pieTotal} />}
                    wrapperStyle={{ outline: 'none' }}
                  />
                  <Legend
                    formatter={(value, entry) => {
                      const raw = entry?.payload?.value
                      const pct = pieTotal > 0 ? (Number(raw) / pieTotal) * 100 : 0
                      return `${value}: ${pct.toFixed(1)}%`
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
