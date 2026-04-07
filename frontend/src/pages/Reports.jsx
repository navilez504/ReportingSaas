import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatApiError } from '../api/errors'
import { useLanguage } from '../context/LanguageContext'

async function downloadReport(id) {
  const res = await api.get(`/reports/${id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `report_${id}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default function Reports() {
  const { lang, t } = useLanguage()
  const [title, setTitle] = useState(() => t('reports.defaultTitle'))
  const [datasetId, setDatasetId] = useState('')
  const [reports, setReports] = useState([])
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [plan, setPlan] = useState(null)

  function load() {
    api.get('/reports').then((r) => setReports(r.data))
    api.get('/upload/datasets').then((r) => setDatasets(r.data))
    api
      .get('/dashboard/plan-summary')
      .then((r) => setPlan(r.data))
      .catch(() => setPlan(null))
  }

  useEffect(() => {
    load()
  }, [])

  async function generate(e) {
    e.preventDefault()
    if (plan && plan.can_write === false) return
    setErr('')
    setMsg('')
    setLoading(true)
    try {
      const body = { title, language: lang }
      if (datasetId) body.dataset_id = Number(datasetId)
      await api.post('/reports', body)
      setMsg(t('reports.success'))
      load()
    } catch (ex) {
      setErr(formatApiError(ex, t))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-10 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{t('reports.title')}</h1>
        <p className="text-slate-600 mt-1">{t('reports.subtitle')}</p>
        <p className="text-xs text-slate-500 mt-2">
          {t('reports.languageHint')}: <span className="font-medium uppercase">{lang}</span>
        </p>
      </div>

      {plan?.trial_expired && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {t('upload.trialExpiredUpload')}
        </div>
      )}

      <form onSubmit={generate} className="p-8 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('reports.reportTitle')}</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('reports.dataset')}</label>
          <select
            value={datasetId}
            onChange={(e) => setDatasetId(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">{t('reports.datasetDefault')}</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        {msg && <p className="text-sm text-emerald-600">{msg}</p>}
        <button
          type="submit"
          disabled={loading || (plan && plan.can_write === false)}
          className="px-5 py-2.5 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-500 disabled:opacity-50"
        >
          {loading ? t('reports.generating') : t('reports.generate')}
        </button>
      </form>

      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">{t('reports.history')}</h2>
        <ul className="divide-y divide-slate-200 border border-slate-200 rounded-xl overflow-hidden bg-white">
          {reports.length === 0 && (
            <li className="px-4 py-6 text-slate-500 text-sm">{t('reports.empty')}</li>
          )}
          {reports.map((r) => (
            <li key={r.id} className="px-4 py-3 flex flex-wrap items-center justify-between gap-2 text-sm">
              <div>
                <span className="font-medium text-slate-800">{r.title}</span>
                <span className="text-slate-500 ml-2">
                  {(r.file_size_bytes / 1024).toFixed(1)} KB · {new Date(r.created_at).toLocaleString()}
                </span>
              </div>
              <button
                type="button"
                onClick={() => downloadReport(r.id)}
                className="text-brand-600 font-medium hover:underline bg-transparent border-0 cursor-pointer p-0"
              >
                {t('reports.download')}
              </button>
            </li>
          ))}
        </ul>
        <p className="text-xs text-slate-500 mt-2">{t('reports.footer')}</p>
      </div>
    </div>
  )
}
