/**
 * Turns axios/FastAPI errors into a single user-visible string.
 * Pass `t` from useLanguage() for localized fixed messages and known API `detail` strings.
 */

/** English fallbacks when `t` is omitted */
const FALLBACK = {
  network:
    'Cannot reach the API. Start the backend (for example uvicorn on port 8000 or docker compose), and set VITE_API_URL to the URL your browser can use (often http://localhost:8000).',
  requestFailed: 'Request failed',
  serverError:
    'Server error. Check that PostgreSQL is running and DATABASE_URL is correct.',
}

/** Exact backend `detail` strings (English) → translation key under `errors.*` */
const BACKEND_DETAIL_TO_KEY = {
  'Report not found': 'errors.reportNotFound',
  'File missing on server': 'errors.fileMissing',
  'No dataset found. Upload data first.': 'errors.noDataset',
  'Dataset not found': 'errors.datasetNotFound',
  'Metric not found': 'errors.metricNotFound',
  'Unsupported file type': 'errors.unsupportedFile',
  'Filename required': 'errors.filenameRequired',
  'No data rows found': 'errors.noDataRows',
  'Email already registered': 'errors.emailRegistered',
  'Incorrect email or password': 'errors.incorrectCredentials',
  'Not authenticated': 'errors.notAuthenticated',
  'Invalid authentication credentials': 'errors.invalidToken',
  'Invalid or expired token': 'errors.invalidToken',
  'Invalid token subject': 'errors.invalidTokenSubject',
  'User not found': 'errors.userNotFound',
  'Admin role required': 'errors.adminRequired',
  'This account has been deactivated': 'errors.accountDeactivated',
  'Your session is no longer valid. Please sign in again.': 'errors.sessionInvalid',
  'Su sesión ya no es válida. Inicie sesión de nuevo.': 'errors.sessionInvalid',
  'Your trial has expired. Contact support or upgrade to continue.': 'errors.trialExpired',
  'You have reached the file limit for your plan.': 'errors.fileLimitReached',
  'Upload is not allowed for your current subscription.': 'errors.trialExpired',
  'Esta cuenta ha sido desactivada': 'errors.accountDeactivated',
  'Su periodo de prueba ha finalizado. Contacte soporte o mejore su plan para continuar.':
    'errors.trialExpired',
  'Ha alcanzado el límite de archivos de su plan.': 'errors.fileLimitReached',
  'No está permitida la subida con su suscripción actual.': 'errors.trialExpired',
  'This feature is not included in your current plan. Upgrade to unlock it.':
    'errors.planFeatureNotAvailable',
  'Esta función no está incluida en su plan actual. Mejore el plan para desbloquearla.':
    'errors.planFeatureNotAvailable',
  'Online billing is not configured on this server.': 'errors.stripeNotConfigured',
  'La facturación en línea no está configurada en este servidor.': 'errors.stripeNotConfigured',
  'Complete a subscription checkout first to manage billing.': 'errors.stripePortalRequiresCustomer',
  'Complete primero el pago de una suscripción para gestionar la facturación.':
    'errors.stripePortalRequiresCustomer',
}

function translateDetailString(raw, t) {
  if (!t || typeof raw !== 'string') return raw
  const key = BACKEND_DETAIL_TO_KEY[raw]
  if (key) return t(key)
  if (raw.startsWith('BI requires columns:')) return t('errors.biRequires')
  if (
    raw.includes('fecha') &&
    raw.includes('cantidad') &&
    raw.includes('precio_unitario') &&
    (raw.includes('BI requires') || raw.includes('análisis BI') || raw.includes('analisis BI'))
  ) {
    return t('errors.biRequires')
  }
  return raw
}

/**
 * @param {unknown} error - Axios error
 * @param {(key: string) => string} [t] - optional translator from useLanguage
 */
export function formatApiError(error, t) {
  if (!error?.response) {
    const code = error?.code
    if (code === 'ERR_NETWORK' || code === 'ECONNABORTED' || code === 'ECONNREFUSED') {
      return typeof t === 'function' ? t('errors.network') : FALLBACK.network
    }
    return error?.message || (typeof t === 'function' ? t('errors.requestFailed') : FALLBACK.requestFailed)
  }

  const d = error.response.data?.detail
  if (typeof d === 'string') return translateDetailString(d, t)

  if (Array.isArray(d)) {
    return d
      .map((item) => {
        const loc = Array.isArray(item.loc) ? item.loc.filter((x) => x !== 'body').join('.') : ''
        const msg = item.msg || item.message || ''
        const translated = translateDetailString(typeof msg === 'string' ? msg : '', t)
        const piece = loc ? `${loc}: ${translated || msg}` : translated || msg || JSON.stringify(item)
        return piece
      })
      .filter(Boolean)
      .join('; ')
  }

  if (d && typeof d === 'object' && !Array.isArray(d)) {
    if (typeof d.error === 'string' && Array.isArray(d.missing_columns)) {
      const base =
        typeof t === 'function' &&
        d.error.includes('precio_unitario') &&
        d.error.includes('fecha') &&
        d.error.includes('cantidad')
          ? t('errors.biRequires')
          : translateDetailString(d.error, t)
      const miss = d.missing_columns.length
        ? ` ${typeof t === 'function' ? t('errors.missingColumns') : 'Missing'}: ${d.missing_columns.join(', ')}.`
        : ''
      return `${base}${miss}`
    }
    const inner = d.error || d.detail
    if (typeof inner === 'string') return translateDetailString(inner, t)
    return JSON.stringify(d)
  }

  const status = error.response.status
  if (status === 500) {
    return typeof t === 'function' ? t('errors.serverError') : FALLBACK.serverError
  }
  return error.response.statusText || (typeof t === 'function' ? t('errors.requestFailed') : FALLBACK.requestFailed)
}
