import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Navigate, useLocation } from 'react-router'
import axios from 'axios'
import { API_BASE_URL, SESSION_EXPIRED_EVENT, tokens } from '../lib/api'
import { useMe } from '../lib/queries'
import type { Me, Role } from '../lib/types'
import { Loading } from '../components/ui'

interface AuthValue {
  me: Me | undefined
  role: Role | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [hasToken, setHasToken] = useState(() => !!tokens.access())
  const meQuery = useMe(hasToken)

  const logout = useCallback(() => {
    tokens.clear()
    setHasToken(false)
    qc.clear()
  }, [qc])

  useEffect(() => {
    window.addEventListener(SESSION_EXPIRED_EVENT, logout)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, logout)
  }, [logout])

  useEffect(() => {
    if (meQuery.isError) logout()
  }, [meQuery.isError, logout])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await axios.post<{ access: string; refresh: string }>(`${API_BASE_URL}/auth/token/`, { email, password })
    tokens.set(data.access, data.refresh)
    qc.clear()
    setHasToken(true)
    await qc.fetchQuery({ queryKey: ['me'], queryFn: async () => (await axios.get<Me>(`${API_BASE_URL}/auth/me/`, { headers: { Authorization: `Bearer ${data.access}` } })).data })
  }, [qc])

  const value = useMemo<AuthValue>(() => ({
    me: hasToken ? meQuery.data : undefined,
    // Navigation and route access derive only from the backend-computed effective role.
    role: hasToken ? meQuery.data?.effective_role ?? null : null,
    loading: hasToken && meQuery.isPending,
    login, logout,
  }), [hasToken, meQuery.data, meQuery.isPending, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="min-h-screen grid place-items-center"><Loading /></div>
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <>{children}</>
}

/** UX guard only: the Django API enforces every permission independently. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { role } = useAuth()
  if (!role || !roles.includes(role)) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}
