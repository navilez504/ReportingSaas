import axios from 'axios'

const raw = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const baseURL = String(raw).replace(/\/+$/, '')

export const api = axios.create({
  baseURL: `${baseURL}/api`,
  headers: { 'Content-Type': 'application/json' },
})

const STORAGE_LANG = 'app_language'

api.interceptors.request.use((config) => {
  let lang = 'en'
  try {
    const s = localStorage.getItem(STORAGE_LANG)
    if (s === 'es' || s === 'en') lang = s
  } catch {
    /* ignore */
  }
  config.headers = config.headers || {}
  config.headers['Accept-Language'] = lang
  return config
})

export function setAuthToken(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`
    localStorage.setItem('token', token)
  } else {
    delete api.defaults.headers.common.Authorization
    localStorage.removeItem('token')
  }
}

export function loadStoredToken() {
  const t = localStorage.getItem('token')
  if (t) setAuthToken(t)
}
