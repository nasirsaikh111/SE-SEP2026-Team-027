import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'

// The single HTTP client for the Django REST API. All business data flows through here.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? 'https://team-027-pre-prod.vercel.app/api/v1'

const ACCESS = 'sangam.access'
const REFRESH = 'sangam.refresh'

function read(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}
function write(key: string, value: string | null) {
  try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key) } catch { /* storage unavailable */ }
}

export const tokens = {
  access: () => read(ACCESS),
  refresh: () => read(REFRESH),
  set(access: string, refresh?: string) { write(ACCESS, access); if (refresh) write(REFRESH, refresh) },
  clear() { write(ACCESS, null); write(REFRESH, null) },
}

export const SESSION_EXPIRED_EVENT = 'sangam:session-expired'

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 20000 })

api.interceptors.request.use((config) => {
  const token = tokens.access()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = tokens.refresh()
  if (!refresh) throw new Error('No refresh token')
  const { data } = await axios.post<{ access: string; refresh?: string }>(`${API_BASE_URL}/auth/token/refresh/`, { refresh })
  tokens.set(data.access, data.refresh)
  return data.access
}

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
  const isAuthCall = original?.url?.includes('/auth/token/')
  if (error.response?.status === 401 && original && !original._retried && !isAuthCall && tokens.refresh()) {
    original._retried = true
    try {
      refreshing = refreshing ?? refreshAccessToken().finally(() => { refreshing = null })
      const access = await refreshing
      original.headers.Authorization = `Bearer ${access}`
      return api(original)
    } catch {
      tokens.clear()
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
    }
  }
  return Promise.reject(error)
})

export async function get<T>(url: string, config?: AxiosRequestConfig) { return (await api.get<T>(url, config)).data }
export async function post<T>(url: string, body?: unknown) { return (await api.post<T>(url, body)).data }
export async function patch<T>(url: string, body?: unknown) { return (await api.patch<T>(url, body)).data }
export async function del(url: string) { await api.delete(url) }

interface ErrorBody { detail?: string; code?: string; errors?: unknown; [field: string]: unknown }

export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Cannot reach the Sangam server. Check your connection.'
    const body = error.response.data as ErrorBody | undefined
    if (body && typeof body.detail === 'string' && body.detail) return body.detail
    if (error.response.status === 403) return 'You do not have permission to do this.'
    if (error.response.status === 404) return 'Not found.'
  }
  return fallback
}

/** Field-level validation messages from a DRF 400 response, keyed by field name. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error) || error.response?.status !== 400) return {}
  const body = error.response.data as ErrorBody
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(body ?? {})) {
    if (['detail', 'code', 'status_code', 'errors'].includes(key)) continue
    out[key] = Array.isArray(value) ? String(value[0]) : String(value)
  }
  return out
}

export function errorStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

export async function downloadFile(url: string, filename: string) {
  const response = await api.get(url, { responseType: 'blob' })
  const href = URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.click()
  URL.revokeObjectURL(href)
}
