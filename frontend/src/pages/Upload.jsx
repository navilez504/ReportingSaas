import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatApiError } from '../api/errors'
import { useLanguage } from '../context/LanguageContext'

export default function Upload() {
  const { t } = useLanguage()
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const [datasets, setDatasets] = useState([])

  function load() {
    api.get('/upload/datasets').then((r) => setDatasets(r.data))
  }

  useEffect(() => {
    load()
  }, [])

  async function onSubmit(e) {
    e.preventDefault()
    if (!file) return
    setErr('')
    setMsg('')
    setLoading(true)
    const fd = new FormData()
    fd.append('file', file)
    if (name) fd.append('name', name)
    try {
      await api.post('/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMsg(t('upload.success'))
      setFile(null)
      setName('')
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
        <h1 className="text-2xl font-semibold text-slate-900">{t('upload.title')}</h1>
        <p className="text-slate-600 mt-1">{t('upload.subtitle')}</p>
      </div>

      <form onSubmit={onSubmit} className="p-8 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('upload.displayName')}</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder={t('upload.displayNamePlaceholder')}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">{t('upload.file')}</label>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-600"
          />
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        {msg && <p className="text-sm text-emerald-600">{msg}</p>}
        <button
          type="submit"
          disabled={loading || !file}
          className="px-5 py-2.5 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-500 disabled:opacity-50"
        >
          {loading ? t('upload.uploading') : t('upload.upload')}
        </button>
      </form>

      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">{t('upload.yourDatasets')}</h2>
        <ul className="divide-y divide-slate-200 border border-slate-200 rounded-xl overflow-hidden bg-white">
          {datasets.length === 0 && (
            <li className="px-4 py-6 text-slate-500 text-sm">{t('upload.empty')}</li>
          )}
          {datasets.map((d) => (
            <li key={d.id} className="px-4 py-3 flex justify-between gap-4 text-sm">
              <span className="font-medium text-slate-800">{d.name}</span>
              <span className="text-slate-500">
                {d.row_count} {t('dashboard.rowsSuffix')} · {(d.file_size_bytes / 1024).toFixed(1)}{' '}
                {t('upload.kb')}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
