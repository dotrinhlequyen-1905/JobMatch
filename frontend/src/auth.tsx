import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, clearSession, saveSession, type Company, type Role, type User } from './api'

interface AuthState {
  user: User | null
  company: Company | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (body: Record<string, unknown>) => Promise<User>
  logout: () => void
  refresh: () => Promise<void>
}

const Ctx = createContext<AuthState>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!localStorage.getItem('token')) { setLoading(false); return }
    try {
      const r = await api.get('/users/me')
      setUser(r.data.user); setCompany(r.data.company ?? null)
    } catch { clearSession(); setUser(null) }
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const accept = (data: { token?: string; refresh_token?: string; user: User; company?: Company }) => {
    // Khi hệ thống bắt buộc xác minh email, đăng ký không trả token: người dùng xác minh rồi mới đăng nhập.
    if (!data.token) return data.user
    saveSession({ token: data.token, refresh_token: data.refresh_token })
    setUser(data.user); setCompany(data.company ?? null)
    return data.user
  }
  const login = async (email: string, password: string) => accept((await api.post('/auth/login', { email, password })).data)
  const register = async (body: Record<string, unknown>) => accept((await api.post('/auth/register', body)).data)
  const logout = () => {
    const rt = localStorage.getItem('refresh_token')
    if (rt) api.post('/auth/logout', { refresh_token: rt }).catch(() => undefined)
    clearSession(); setUser(null); setCompany(null)
  }

  return <Ctx.Provider value={{ user, company, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return null
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname)}`} replace />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />
  return <>{children}</>
}

export const homeOf = (role?: Role) => (role === 'HR' ? '/hr' : role === 'ADMIN' ? '/admin' : role === 'CANDIDATE' ? '/candidate/recommendations' : '/')
