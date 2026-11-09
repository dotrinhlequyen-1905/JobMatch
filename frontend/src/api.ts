import axios from 'axios'

export const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function saveSession(data: { token: string; refresh_token?: string }) {
  localStorage.setItem('token', data.token)
  if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
}

export function clearSession() {
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
}

// Nhiều request cùng gặp 401 chỉ gọi /auth/refresh một lần (refresh token xoay vòng, dùng lại sẽ bị thu hồi).
let refreshing: Promise<boolean> | null = null
function refreshSession(): Promise<boolean> {
  const rt = localStorage.getItem('refresh_token')
  if (!rt) return Promise.resolve(false)
  refreshing ??= axios.post('/api/v1/auth/refresh', { refresh_token: rt })
    .then((r) => { saveSession(r.data); return true })
    .catch(() => false)
    .finally(() => { refreshing = null })
  return refreshing
}

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    // lỗi server / mất mạng: báo chung cho người dùng (lỗi nghiệp vụ 4xx do từng trang tự hiển thị)
    if (!err.response || err.response.status >= 500) {
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: err.response ? `Máy chủ gặp lỗi (${err.response.status}), vui lòng thử lại sau` : 'Không kết nối được máy chủ',
      }))
    }
    const original = err.config
    if (err.response?.status === 401 && localStorage.getItem('token') && original && !original._retried && !original.url?.startsWith('/auth/')) {
      original._retried = true
      if (await refreshSession()) return api(original)
      clearSession()
      if (!location.pathname.startsWith('/login')) location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export function errMsg(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x: { msg?: string }) => x.msg).join('; ')
  return 'Có lỗi xảy ra, vui lòng thử lại'
}

// ---------------------------------------------------------------- kiểu dữ liệu
export type Role = 'CANDIDATE' | 'HR' | 'ADMIN'
export interface User { id: number; email: string; full_name: string; phone?: string; role: Role; status: string; is_premium: boolean; premium_until?: string; created_at?: string; email_verified?: boolean; avatar_url?: string | null }
export interface CandidateProfile { headline?: string | null; summary?: string | null; location?: string | null; desired_role?: string | null; expected_salary?: number | null; is_public: boolean; updated_at?: string | null }
export interface Report { id: number; target_type: 'JOB' | 'COMPANY' | 'USER'; target_id: number; target_label?: string | null; reason: string; status: string; admin_note?: string | null; created_at: string; handled_at?: string | null; reporter?: { id: number; email: string; full_name: string } }
export interface Company { id: number; name: string; description?: string; location?: string; website?: string; logo_url?: string; status: string; open_jobs?: number; owner?: { email: string; full_name: string } }
export interface Job {
  id: number; title: string; role: string; role_display: string; seniority: string; min_years: number; skills: string[]
  city?: string; salary_min?: number; salary_max?: number; status: string; description?: string; created_at: string
  expires_at?: string; company: { id: number; name: string; logo_url?: string; description?: string; location?: string; website?: string }
  applications?: number; view_count?: number; avg_match_score?: number | null
}
export interface CV { processing_status: string; id: number; title: string; skills: string[]; years: number; seniority: string; role: string; role_display: string; is_default: boolean; created_at: string; has_file: boolean; file_type?: string; raw_text?: string; parsed?: { name?: string; email?: string; phone?: string; title?: string; sections?: Record<string, string> } }
export interface Match { score: number; semantic?: number; semantic_norm?: number; skill_coverage?: number; experience_match?: number; matched_skills: string[]; missing_skills: string[]; extra_skills?: string[]; cv_years?: number; required_years?: number }
export interface Slot { id: number; job_id: number; start_at: string; end_at: string; location?: string; status: string; held_by?: number; held_until?: string; application_id?: number; result?: string; feedback?: string; mine?: boolean; candidate_name?: string }
export interface Application {
  id: number; status: string; status_vi: string; match_score?: number; cover_letter?: string; created_at: string; updated_at: string
  job: Job; candidate: { id: number; full_name: string; email: string; phone?: string }; cv: CV; next_actions: string[]
  history: { from?: string; to: string; note?: string; at: string }[]; booked_slot?: Slot; match?: Match; slots?: Slot[]
}
export interface Package { id: number; code: string; name: string; target: string; price: number; duration_days: number; quota_jobs: number; description?: string; active?: boolean }
export interface Order { payment_demo_enabled?: boolean; payment_simulation_enabled?: boolean; id: number; order_code: string; amount: number; status: string; expires_at: string; paid_at?: string; created_at: string; package: Package; qr_url?: string | null; user: { email: string; full_name: string }; refund?: { id: number; status: string; reason: string; admin_note?: string }; bank?: { bank: string; account: string; name: string } | null }

// ---------------------------------------------------------------- tiện ích hiển thị
export const vnd = (n?: number | null) => (n == null ? '' : n.toLocaleString('vi-VN') + ' đ')
export const salary = (a?: number, b?: number) => {
  if (!a && !b) return 'Thỏa thuận'
  const m = (x: number) => `${Math.round(x / 1_000_000)} triệu`
  if (a && b) return `${m(a)} - ${m(b)}`
  return a ? `Từ ${m(a)}` : `Đến ${m(b!)}`
}
export const dt = (s?: string) => (s ? new Date(s).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' }) : '')
export const d = (s?: string) => (s ? new Date(s).toLocaleDateString('vi-VN') : '')
export const ago = (s: string) => {
  const m = Math.round((Date.now() - new Date(s).getTime()) / 60000)
  if (m < 60) return `${Math.max(m, 1)} phút trước`
  if (m < 1440) return `${Math.round(m / 60)} giờ trước`
  return `${Math.round(m / 1440)} ngày trước`
}
export const SENIORITY_VI: Record<string, string> = { intern: 'Thực tập', fresher: 'Fresher', junior: 'Junior', middle: 'Middle', senior: 'Senior', lead: 'Lead' }
