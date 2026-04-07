import axios from 'axios'

/**
 * If VITE_API_URL is set (non-empty), call that host + /api (common for split deploys).
 * Otherwise use same-origin `/api` — Docker nginx and Vite dev proxy forward to the backend.
 */
const explicit = import.meta.env.VITE_API_URL
const useExplicit = explicit != null && String(explicit).trim() !== ''
const baseURL = useExplicit ? `${String(explicit).replace(/\/+$/, '')}/api` : '/api'

export const api = axios.create({
  baseURL,
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
