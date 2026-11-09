import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, errMsg } from '../../api'
import { homeOf, useAuth } from '../../auth'
import { Alert } from '../../components/ui'

const DEMO = [['Ứng viên', 'candidate@demo.vn'], ['Nhà tuyển dụng', 'hr@demo.vn'], ['Quản trị viên', 'admin@demo.vn']]

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e?: React.FormEvent, em = email, p = pw) => {
    e?.preventDefault(); setBusy(true); setErr('')
    try { const u = await login(em, p); nav(sp.get('next') || homeOf(u.role)) } catch (x) { setErr(errMsg(x)) }
    setBusy(false)
  }
  return (
    <div className="mx-auto mt-6 max-w-md">
      <div className="card p-6">
        <h1 className="mb-4 text-xl font-bold">Đăng nhập</h1>
        <form className="space-y-3" onSubmit={submit}>
          <Alert>{err}</Alert>
          <div><label className="label">Email</label><input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
          <div><label className="label">Mật khẩu</label><input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} required /></div>
          <div className="text-right text-sm"><Link className="text-brand-700 hover:underline" to="/forgot-password">Quên mật khẩu?</Link></div>
          <button className="btn-primary w-full" disabled={busy}>Đăng nhập</button>
        </form>
        <div className="mt-4 text-center text-sm text-slate-600">Chưa có tài khoản? <Link className="text-brand-700 hover:underline" to="/register">Đăng ký</Link></div>
      </div>
      <div className="card mt-4 p-4">
        <div className="mb-2 text-xs font-semibold uppercase text-slate-500">Tài khoản demo (mật khẩu 123456)</div>
        <div className="flex flex-wrap gap-2">
          {DEMO.map(([label, em]) => <button key={em} className="btn-outline btn-sm" onClick={() => submit(undefined, em, '123456')}>{label}</button>)}
        </div>
      </div>
    </div>
  )
}

export function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const [f, setF] = useState({ email: '', password: '', full_name: '', phone: '', role: sp.get('role') === 'HR' ? 'HR' : 'CANDIDATE', company_name: '' })
  const [err, setErr] = useState('')
  const [done, setDone] = useState(false)
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr('')
    try {
      const u = await register({ ...f, company_name: f.role === 'HR' ? f.company_name : null })
      if (!localStorage.getItem('token')) return setDone(true)
      nav(u.role === 'HR' ? '/hr/company' : '/candidate/cvs')
    } catch (x) { setErr(errMsg(x)) }
  }
  if (done) return (
    <div className="mx-auto mt-6 max-w-md card p-6">
      <Alert kind="success">Đã tạo tài khoản. Vui lòng mở email <b>{f.email}</b> và bấm liên kết xác minh trước khi đăng nhập.</Alert>
      <Link className="btn-primary mt-4 w-full" to="/login">Tới trang đăng nhập</Link>
    </div>
  )
  return (
    <div className="mx-auto mt-6 max-w-md card p-6">
      <h1 className="mb-4 text-xl font-bold">Tạo tài khoản</h1>
      <div className="mb-4 grid grid-cols-2 gap-2">
        {[['CANDIDATE', 'Tôi tìm việc'], ['HR', 'Tôi tuyển dụng']].map(([v, l]) => (
          <button key={v} type="button" onClick={() => setF({ ...f, role: v })}
            className={`rounded-lg border p-3 text-sm font-medium ${f.role === v ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-slate-300'}`}>{l}</button>
        ))}
      </div>
      <form className="space-y-3" onSubmit={submit}>
        <Alert>{err}</Alert>
        <div><label className="label">Họ và tên</label><input className="input" value={f.full_name} onChange={set('full_name')} required /></div>
        {f.role === 'HR' && <div><label className="label">Tên công ty</label><input className="input" value={f.company_name} onChange={set('company_name')} required /></div>}
        <div><label className="label">Email</label><input className="input" type="email" value={f.email} onChange={set('email')} required /></div>
        <div><label className="label">Số điện thoại</label><input className="input" value={f.phone} onChange={set('phone')} /></div>
        <div><label className="label">Mật khẩu (tối thiểu 6 ký tự)</label><input className="input" type="password" value={f.password} onChange={set('password')} required minLength={6} /></div>
        <button className="btn-primary w-full">Đăng ký</button>
      </form>
    </div>
  )
}

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [msg, setMsg] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true); setMsg(null)
    try {
      const r = await api.post('/auth/forgot-password', { email: email.trim() })
      setMsg({ kind: 'success', text: r.data.message })
    }
    catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
    finally { inFlight.current = false; setBusy(false) }
  }
  return (
    <div className="mx-auto mt-6 max-w-md card p-6">
      <h1 className="mb-1 text-xl font-bold">Quên mật khẩu</h1>
      <p className="mb-4 text-sm text-slate-500">Nhập email đã đăng ký để nhận liên kết đặt lại mật khẩu. Mỗi liên kết chỉ dùng được một lần.</p>
      <form className="space-y-3" onSubmit={submit}>
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <div><label className="label" htmlFor="recovery-email">Email</label><input id="recovery-email" className="input" type="email" autoComplete="email" value={email} disabled={busy} onChange={(e) => { setEmail(e.target.value); setMsg(null) }} required /></div>
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Đang xử lý…' : 'Gửi liên kết'}</button>
      </form>
      <div className="mt-4 text-center text-sm"><Link className="text-brand-700 hover:underline" to="/login">← Quay lại đăng nhập</Link></div>
    </div>
  )
}

export function ResetPassword() {
  const [sp] = useSearchParams()
  const { logout } = useAuth()
  const token = sp.get('token') ?? ''
  const [pw, setPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState(false)
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (inFlight.current) return
    setErr('')
    if (pw !== confirm) return setErr('Mật khẩu nhập lại không khớp')
    if (new TextEncoder().encode(pw).length > 72) return setErr('Mật khẩu không được vượt quá 72 byte UTF-8')
    inFlight.current = true
    setBusy(true)
    try { await api.post('/auth/reset-password', { token, password: pw }); logout(); setOk(true) }
    catch (x) { setErr(errMsg(x)) }
    finally { inFlight.current = false; setBusy(false) }
  }
  return (
    <div className="mx-auto mt-6 max-w-md card p-6">
      <h1 className="mb-4 text-xl font-bold">Đặt lại mật khẩu</h1>
      {!token ? <Alert>Liên kết đặt lại mật khẩu bị thiếu hoặc không hợp lệ. Vui lòng yêu cầu liên kết mới.</Alert> : ok ? <div className="space-y-4" role="status">
        <Alert kind="success">Đã đặt lại mật khẩu thành công. Bạn có thể đăng nhập bằng mật khẩu mới.</Alert>
        <Link className="btn-primary w-full" to="/login">Đăng nhập bằng mật khẩu mới</Link>
      </div> : (
        <form className="space-y-3" onSubmit={submit}>
          <Alert>{err}</Alert>
          <div><label className="label" htmlFor="new-password">Mật khẩu mới (tối thiểu 6 ký tự)</label><input id="new-password" className="input" type="password" autoComplete="new-password" minLength={6} value={pw} disabled={busy} onChange={(e) => setPw(e.target.value)} required /></div>
          <div><label className="label" htmlFor="confirm-password">Nhập lại mật khẩu</label><input id="confirm-password" className="input" type="password" autoComplete="new-password" value={confirm} disabled={busy} onChange={(e) => setConfirm(e.target.value)} required /></div>
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Đang đặt lại mật khẩu…' : 'Đặt lại mật khẩu'}</button>
        </form>
      )}
      {!ok && <div className="mt-4 text-center text-sm"><Link className="text-brand-700 hover:underline" to="/forgot-password">Nhận liên kết đặt lại mật khẩu mới</Link></div>}
    </div>
  )
}

export function VerifyEmail() {
  const [sp] = useSearchParams()
  const { refresh } = useAuth()
  const token = sp.get('token') ?? ''
  const [state, setState] = useState<{ kind: 'info' | 'success' | 'error'; text: string }>(() =>
    token ? { kind: 'info', text: 'Đang xác minh...' } : { kind: 'error', text: 'Liên kết không hợp lệ.' })
  const started = useRef(false)
  useEffect(() => {
    if (!token || started.current) return  // token chỉ dùng một lần; StrictMode chạy effect hai lần
    started.current = true
    api.post('/auth/verify-email', { token })
      .then(() => { setState({ kind: 'success', text: 'Email đã được xác minh. Cảm ơn bạn!' }); refresh() })
      .catch((x) => setState({ kind: 'error', text: errMsg(x) }))
  }, [token, refresh])
  return (
    <div className="mx-auto mt-6 max-w-md card p-6">
      <h1 className="mb-4 text-xl font-bold">Xác minh email</h1>
      <Alert kind={state.kind}>{state.text}</Alert>
      <Link className="btn-primary mt-4 w-full" to="/">Về trang chủ</Link>
    </div>
  )
}
