import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, d, dt, errMsg, saveSession, type CandidateProfile, type Report } from '../../api'
import { useAuth } from '../../auth'
import { Alert, PageTitle, StatusBadge } from '../../components/ui'

const ROLE_VI = { CANDIDATE: 'Ứng viên', HR: 'Nhà tuyển dụng', ADMIN: 'Quản trị viên' }
const REPORT_STATUS_VI: Record<string, string> = { OPEN: 'Chờ xử lý', RESOLVED: 'Đã xử lý', DISMISSED: 'Không vi phạm' }
const TARGET_VI: Record<string, string> = { JOB: 'Tin tuyển dụng', COMPANY: 'Công ty', USER: 'Người dùng' }

type Msg = { kind: 'error' | 'success'; text: string } | null

function Avatar({ url, name }: { url?: string | null; name: string }) {
  if (url) return <img src={url} alt="" className="h-16 w-16 rounded-full object-cover" />
  return <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 text-xl font-bold text-brand-700">{name.charAt(0).toUpperCase()}</div>
}

function CareerProfile() {
  const [p, setP] = useState<CandidateProfile | null>(null)
  const [msg, setMsg] = useState<Msg>(null)
  useEffect(() => { api.get('/users/me/profile').then((r) => setP(r.data)) }, [])
  if (!p) return null
  const set = (k: keyof CandidateProfile) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setP({ ...p, [k]: e.target.value })
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setMsg(null)
    try {
      const r = await api.put('/users/me/profile', { ...p, expected_salary: p.expected_salary ? Number(p.expected_salary) : null })
      setP(r.data); setMsg({ kind: 'success', text: 'Đã lưu hồ sơ nghề nghiệp' })
    } catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
  }
  return (
    <form className="card mt-4 space-y-3 p-5" onSubmit={save}>
      <h2 className="font-semibold">Hồ sơ nghề nghiệp</h2>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <div><label className="label">Tiêu đề hồ sơ</label><input className="input" value={p.headline ?? ''} onChange={set('headline')} placeholder="Backend Developer 3 năm kinh nghiệm" /></div>
      <div><label className="label">Giới thiệu bản thân</label><textarea className="input h-28" value={p.summary ?? ''} onChange={set('summary')} /></div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div><label className="label">Vị trí mong muốn</label><input className="input" value={p.desired_role ?? ''} onChange={set('desired_role')} /></div>
        <div><label className="label">Nơi làm việc</label><input className="input" value={p.location ?? ''} onChange={set('location')} /></div>
        <div><label className="label">Lương mong muốn (đ)</label><input className="input" type="number" min={0} value={p.expected_salary ?? ''} onChange={set('expected_salary')} /></div>
      </div>
      <label className="flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-sm">
        <input type="checkbox" className="mt-0.5" checked={p.is_public} onChange={(e) => setP({ ...p, is_public: e.target.checked })} />
        <span><b>Cho phép nhà tuyển dụng tìm thấy hồ sơ của tôi</b><br />
          <span className="text-slate-500">Khi tắt, CV của bạn không xuất hiện trong danh sách ứng viên AI gợi ý cho nhà tuyển dụng. Các tin bạn đã ứng tuyển vẫn xem được hồ sơ.</span></span>
      </label>
      <button className="btn-primary">Lưu hồ sơ nghề nghiệp</button>
    </form>
  )
}

function MyReports() {
  const [items, setItems] = useState<Report[]>([])
  useEffect(() => { api.get('/reports/mine').then((r) => setItems(r.data)) }, [])
  if (!items.length) return null
  return (
    <div className="card mt-4 p-5">
      <h2 className="mb-3 font-semibold">Báo cáo vi phạm đã gửi</h2>
      <div className="space-y-2 text-sm">
        {items.map((r) => (
          <div key={r.id} className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2">
            <div className="min-w-0">
              <div className="font-medium">{TARGET_VI[r.target_type]}: {r.target_label ?? `#${r.target_id}`}</div>
              <div className="text-slate-500">{r.reason}</div>
              {r.admin_note && <div className="text-xs text-slate-500">Phản hồi: {r.admin_note}</div>}
            </div>
            <div className="shrink-0 text-right"><StatusBadge status={r.status} label={REPORT_STATUS_VI[r.status]} /><div className="text-xs text-slate-400">{d(r.created_at)}</div></div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Profile() {
  const { user, refresh } = useAuth()
  const [f, setF] = useState({ full_name: user?.full_name ?? '', phone: user?.phone ?? '', current: '', password: '', confirm: '' })
  const [msg, setMsg] = useState<Msg>(null)
  if (!user) return null
  const save = async (e: React.FormEvent) => {
    e.preventDefault(); setMsg(null)
    if (f.password && f.password !== f.confirm) return setMsg({ kind: 'error', text: 'Mật khẩu nhập lại không khớp' })
    if (f.password && !f.current) return setMsg({ kind: 'error', text: 'Vui lòng nhập mật khẩu hiện tại' })
    try {
      const r = await api.put('/users/me', { full_name: f.full_name, phone: f.phone, password: f.password || null, current_password: f.current || null })
      if (r.data.token) saveSession(r.data)
      await refresh()
      setF({ ...f, current: '', password: '', confirm: '' })
      setMsg({ kind: 'success', text: f.password ? 'Đã đổi mật khẩu. Các phiên đăng nhập khác đã bị đăng xuất.' : 'Đã cập nhật thông tin' })
    } catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
  }
  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData(); form.append('file', file)
    try { await api.post('/users/me/avatar', form); await refresh(); setMsg({ kind: 'success', text: 'Đã cập nhật ảnh đại diện' }) }
    catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
    e.target.value = ''
  }
  const resend = async () => {
    try { await api.post('/auth/resend-verification'); setMsg({ kind: 'success', text: `Đã gửi lại email xác minh tới ${user.email}` }) }
    catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
  }
  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle title="Tài khoản của tôi" sub={`${ROLE_VI[user.role]} · ${user.email}`} />
      {user.email_verified === false && (
        <div className="mb-4"><Alert kind="warn">Email chưa được xác minh. <button className="font-semibold underline" onClick={resend}>Gửi lại email xác minh</button></Alert></div>
      )}
      <form className="card space-y-3 p-5" onSubmit={save}>
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <div className="flex items-center gap-4">
          <Avatar url={user.avatar_url} name={user.full_name} />
          <label className="btn-outline btn-sm cursor-pointer">Đổi ảnh đại diện<input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={upload} /></label>
          <span className="text-xs text-slate-500">PNG, JPG hoặc WEBP, tối đa 2MB</span>
        </div>
        {user.role === 'HR' && <p className="text-xs text-slate-500">Logo trên tin tuyển dụng là logo công ty, đổi tại <Link className="text-brand-700 hover:underline" to="/hr/company">Hồ sơ công ty</Link>.</p>}
        {user.role === 'CANDIDATE' && (
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            {user.is_premium ? <>★ Premium đến <b>{dt(user.premium_until)}</b></> : 'Tài khoản thường'}
          </div>
        )}
        <div><label className="label">Họ và tên</label><input className="input" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} required /></div>
        <div><label className="label">Số điện thoại</label><input className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></div>
        <div className="border-t border-slate-100 pt-3 text-sm font-medium text-slate-700">Đổi mật khẩu (để trống nếu không đổi)</div>
        <div><label className="label">Mật khẩu hiện tại</label><input className="input" type="password" autoComplete="current-password" value={f.current} onChange={(e) => setF({ ...f, current: e.target.value })} /></div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div><label className="label">Mật khẩu mới</label><input className="input" type="password" autoComplete="new-password" minLength={6} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div>
          <div><label className="label">Nhập lại</label><input className="input" type="password" autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></div>
        </div>
        <button className="btn-primary">Lưu thay đổi</button>
      </form>
      {user.role === 'CANDIDATE' && <CareerProfile />}
      {user.role !== 'ADMIN' && <MyReports />}
    </div>
  )
}
