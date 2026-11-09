import { useEffect, useState, type ReactNode } from 'react'

export function Spinner({ label = 'Đang tải...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      {label}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{children}</div>
}

export function Alert({ kind = 'error', children }: { kind?: 'error' | 'success' | 'info' | 'warn'; children: ReactNode }) {
  if (!children) return null
  const cls = { error: 'bg-rose-50 text-rose-700 border-rose-200', success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    info: 'bg-brand-50 text-brand-700 border-brand-100', warn: 'bg-amber-50 text-amber-800 border-amber-200' }[kind]
  return <div className={`rounded-lg border px-3 py-2 text-sm ${cls}`}>{children}</div>
}

export function SkillChips({ skills, tone = 'slate', max }: { skills: string[]; tone?: 'slate' | 'green' | 'red' | 'blue'; max?: number }) {
  const cls = { slate: 'bg-slate-100 text-slate-700', green: 'bg-emerald-100 text-emerald-800', red: 'bg-rose-100 text-rose-700', blue: 'bg-brand-100 text-brand-700' }[tone]
  const list = max ? skills.slice(0, max) : skills
  return (
    <div className="flex flex-wrap gap-1">
      {list.map((s) => <span key={s} className={`chip ${cls}`}>{s}</span>)}
      {max && skills.length > max && <span className="chip bg-slate-50 text-slate-500">+{skills.length - max}</span>}
    </div>
  )
}

export function ScoreBadge({ score }: { score?: number | null }) {
  if (score == null) return null
  const pct = Math.round(score * 100)
  const cls = pct >= 70 ? 'bg-emerald-100 text-emerald-800' : pct >= 50 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
  return <span className={`chip ${cls}`} title="Mức độ phù hợp do AI tính">{pct}% phù hợp</span>
}

export function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(value * 100)
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-xs text-slate-600"><span>{label}</span><span>{pct}%</span></div>
      <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-brand-500" style={{ width: `${pct}%` }} /></div>
    </div>
  )
}

const STATUS_COLOR: Record<string, string> = {
  NEW: 'bg-sky-100 text-sky-800', SCREENING: 'bg-indigo-100 text-indigo-800', INTERVIEW_INVITED: 'bg-violet-100 text-violet-800',
  INTERVIEW_SCHEDULED: 'bg-fuchsia-100 text-fuchsia-800', INTERVIEWED: 'bg-amber-100 text-amber-800', OFFERED: 'bg-emerald-100 text-emerald-800',
  REJECTED: 'bg-rose-100 text-rose-700', WITHDRAWN: 'bg-slate-200 text-slate-600',
  PENDING: 'bg-amber-100 text-amber-800', APPROVED: 'bg-emerald-100 text-emerald-800', PUBLISHED: 'bg-emerald-100 text-emerald-800',
  CLOSED: 'bg-slate-200 text-slate-600', PAID: 'bg-emerald-100 text-emerald-800', EXPIRED: 'bg-slate-200 text-slate-600',
  CANCELLED: 'bg-slate-200 text-slate-600', REFUND_REQUESTED: 'bg-amber-100 text-amber-800', REFUNDED: 'bg-violet-100 text-violet-800',
  OPEN: 'bg-emerald-100 text-emerald-800', HELD: 'bg-amber-100 text-amber-800', BOOKED: 'bg-brand-100 text-brand-700',
  ACTIVE: 'bg-emerald-100 text-emerald-800', LOCKED: 'bg-rose-100 text-rose-700', MATCHED: 'bg-emerald-100 text-emerald-800',
  UNMATCHED: 'bg-rose-100 text-rose-700', LATE: 'bg-amber-100 text-amber-800', AMOUNT_MISMATCH: 'bg-rose-100 text-rose-700',
  REQUESTED: 'bg-amber-100 text-amber-800', DONE: 'bg-emerald-100 text-emerald-800',
  RECONCILING: 'bg-orange-100 text-orange-800', RESOLVED: 'bg-emerald-100 text-emerald-800', REFUND_DUE: 'bg-rose-100 text-rose-700',
  DRAFT: 'bg-slate-100 text-slate-600',
}
export const STATUS_VI: Record<string, string> = {
  NEW: 'Đã nộp', SCREENING: 'Sàng lọc', INTERVIEW_INVITED: 'Mời phỏng vấn', INTERVIEW_SCHEDULED: 'Đã đặt lịch PV',
  INTERVIEWED: 'Đã phỏng vấn', OFFERED: 'Trúng tuyển', REJECTED: 'Từ chối', WITHDRAWN: 'Đã rút',
  PENDING: 'Chờ xử lý', APPROVED: 'Đã duyệt', PUBLISHED: 'Đang hiển thị', CLOSED: 'Đã đóng', DRAFT: 'Nháp',
  PAID: 'Đã thanh toán', EXPIRED: 'Hết hạn', CANCELLED: 'Đã hủy', REFUND_REQUESTED: 'Chờ hoàn tiền', REFUNDED: 'Đã hoàn tiền',
  OPEN: 'Trống', HELD: 'Đang giữ', BOOKED: 'Đã đặt', ACTIVE: 'Hoạt động', LOCKED: 'Đã khóa',
  MATCHED: 'Khớp', UNMATCHED: 'Không khớp đơn', LATE: 'Đến muộn/trùng', AMOUNT_MISMATCH: 'Sai số tiền',
  REQUESTED: 'Chờ duyệt', DONE: 'Đã hoàn',
  RECONCILING: 'Chờ đối soát', RESOLVED: 'Đã đối soát', REFUND_DUE: 'Cần hoàn tiền',
}

// Đơn thanh toán: PENDING hiển thị "Chờ thanh toán" theo đặc tả, khác nghĩa "Chờ xử lý" của tin/công ty.
export const ORDER_STATUS_VI: Record<string, string> = { ...STATUS_VI, PENDING: 'Chờ thanh toán' }

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <span className={`chip ${STATUS_COLOR[status] ?? 'bg-slate-100 text-slate-700'}`}>{label ?? STATUS_VI[status] ?? status}</span>
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  }, [onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4" onMouseDown={onClose}>
      <div className={`card mt-10 w-full ${wide ? 'max-w-4xl' : 'max-w-lg'} p-5`} onMouseDown={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button className="text-slate-400 hover:text-slate-700" onClick={onClose} aria-label="Đóng">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Pager({ page, total, size, onChange }: { page: number; total: number; size: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size))
  if (pages <= 1) return null
  return (
    <div className="mt-4 flex items-center justify-center gap-2 text-sm">
      <button className="btn-outline btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Trước</button>
      <span className="text-slate-600">Trang {page}/{pages}</span>
      <button className="btn-outline btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>Sau ›</button>
    </div>
  )
}

export function Countdown({ until, onEnd }: { until: string; onEnd?: () => void }) {
  const [left, setLeft] = useState(() => new Date(until).getTime() - Date.now())
  useEffect(() => {
    const t = setInterval(() => {
      const l = new Date(until).getTime() - Date.now()
      setLeft(l)
      if (l <= 0) { clearInterval(t); onEnd?.() }
    }, 1000)
    return () => clearInterval(t)
  }, [until, onEnd])
  const s = Math.max(0, Math.floor(left / 1000))
  return <span className="font-mono">{String(Math.floor(s / 60)).padStart(2, '0')}:{String(s % 60).padStart(2, '0')}</span>
}

export function PageTitle({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        {sub && <p className="mt-1 text-sm text-slate-500">{sub}</p>}
      </div>
      {right}
    </div>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-900">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  )
}
