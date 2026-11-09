import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { ago, api } from '../api'
import { useAuth } from '../auth'
import BrandMark from './BrandMark'

const MENUS = {
  GUEST: [['/jobs', 'Việc làm'], ['/companies', 'Doanh nghiệp'], ['/#about', 'Về chúng tôi'], ['/premium', 'Bảng giá']],
  CANDIDATE: [['/jobs', 'Việc làm'], ['/candidate/recommendations', 'Gợi ý AI'], ['/candidate/cvs', 'CV của tôi'],
    ['/candidate/evaluation', 'Đánh giá CV'], ['/candidate/applications', 'Đơn ứng tuyển'], ['/premium', 'Premium']],
  HR: [['/hr', 'Tổng quan'], ['/hr/jobs', 'Tin tuyển dụng'], ['/hr/company', 'Công ty'], ['/hr/packages', 'Gói đăng tin']],
  ADMIN: [['/admin', 'Thống kê'], ['/admin/moderation', 'Kiểm duyệt'], ['/admin/users', 'Người dùng'],
    ['/admin/payments', 'Giao dịch'], ['/admin/reports', 'Báo cáo'], ['/admin/audit', 'Nhật ký']],
} as const

interface Noti { id: number; title: string; link?: string; read: boolean; created_at: string }

function Bell() {
  const [data, setData] = useState<{ unread: number; items: Noti[] }>({ unread: 0, items: [] })
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const load = () => api.get('/notifications').then((r) => setData(r.data)).catch(() => {})
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [])
  const toggle = async () => {
    setOpen(!open)
    if (!open && data.unread) { await api.post('/notifications/read-all'); setData({ ...data, unread: 0 }) }
  }
  return (
    <div className="relative">
      <button className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100" onClick={toggle} aria-label="Thông báo">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>
        {data.unread > 0 && <span className="absolute -right-0.5 -top-0.5 rounded-full bg-rose-600 px-1.5 text-[10px] font-bold text-white">{data.unread}</span>}
      </button>
      {open && (
        <div className="notification-panel card absolute right-0 z-40 mt-2 max-h-96 w-80 overflow-y-auto p-2">
          {data.items.length === 0 && <div className="p-3 text-sm text-slate-500">Chưa có thông báo</div>}
          {data.items.map((n) => (
            <button key={n.id} className="block w-full rounded-lg p-2 text-left text-sm hover:bg-slate-50"
              onClick={() => { setOpen(false); if (n.link) nav(n.link) }}>
              <div className={n.read ? 'text-slate-600' : 'font-medium text-slate-900'}>{n.title}</div>
              <div className="text-xs text-slate-400">{ago(n.created_at)}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ErrorToast() {
  const [msg, setMsg] = useState('')
  useEffect(() => {
    let t: ReturnType<typeof setTimeout>
    const f = (e: Event) => { setMsg((e as CustomEvent<string>).detail); clearTimeout(t); t = setTimeout(() => setMsg(''), 5000) }
    window.addEventListener('api-error', f)
    return () => { window.removeEventListener('api-error', f); clearTimeout(t) }
  }, [])
  if (!msg) return null
  return (
    <div role="alert" className="fixed bottom-4 right-4 z-[60] flex max-w-sm items-start gap-2 rounded-lg bg-rose-600 px-4 py-3 text-sm text-white shadow-lg">
      <span>⚠️ {msg}</span><button className="ml-2 opacity-80 hover:opacity-100" onClick={() => setMsg('')} aria-label="Đóng">✕</button>
    </div>
  )
}

export default function Layout() {
  const { user, company, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [loc.pathname, loc.hash])
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])
  const isHome = loc.pathname === '/'
  const isJobs = loc.pathname === '/jobs'
  const isPremium = loc.pathname === '/premium' || loc.pathname === '/hr/packages'
  const menu = MENUS[user?.role ?? 'GUEST']
  const sub = user?.role === 'HR' ? company?.name : user?.role === 'ADMIN' ? 'Quản trị viên' : user?.is_premium ? '★ Premium' : 'Ứng viên'
  const doLogout = () => { logout(); nav('/') }
  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'}`
  const publicLinkCls = ({ isActive }: { isActive: boolean }) => `public-nav-link${isActive ? ' active' : ''}`
  const menuLinks = (mobile = false) => menu.map(([to, label]) => to.includes('#') ? (
    <Link key={to} to={to} className={mobile ? linkCls({ isActive: false }) : 'public-nav-link'} onClick={() => setOpen(false)}>{label}</Link>
  ) : (
    <NavLink key={to} to={to} end={to === '/hr' || to === '/admin'} className={!user && !mobile ? publicLinkCls : linkCls} onClick={() => setOpen(false)}>{label}</NavLink>
  ))
  return (
    <div className="site-shell flex min-h-screen flex-col">
      <header className={`site-header sticky top-0 z-30 bg-white${user ? ' site-header-authenticated' : ''}${isJobs ? ' site-header-jobs' : ''}${isPremium ? ' site-header-premium' : ''}`}>
        <div className="site-header-inner">
          <Link to="/" className="brand-link" aria-label="JobMatch — Trang chủ">
            <BrandMark />
          </Link>
          <nav className={user ? 'role-nav hidden flex-1 items-center gap-1 md:flex' : 'public-nav hidden md:flex'} aria-label="Điều hướng chính">
            {menuLinks()}
          </nav>
          <div className="header-spacer flex-1 md:hidden" />
          {user ? (
            <div className="header-account-actions flex items-center gap-2">
              <Bell />
              {user.role !== 'ADMIN' && <Link to="/orders" className="header-orders hidden text-sm text-slate-600 hover:text-slate-900 md:block">Đơn hàng</Link>}
              <Link to="/profile" title="Tài khoản của tôi" className="header-profile hidden rounded-lg px-2 py-1 text-right text-xs leading-tight hover:bg-slate-100 md:block">
                <div className="font-medium text-slate-800">{user.full_name}</div>
                <div className="text-slate-500">{sub}</div>
              </Link>
              <button className="header-logout btn-outline btn-sm hidden md:inline-flex" onClick={doLogout}>Đăng xuất</button>
            </div>
          ) : (
            <div className="header-auth hidden md:flex">
              <Link className="header-login" to="/login">Đăng nhập</Link>
              <Link className="header-register" to="/register">Đăng ký</Link>
            </div>
          )}
          <button className="mobile-menu-toggle rounded-lg p-2 text-slate-700 hover:bg-slate-100 md:hidden" onClick={() => setOpen(!open)} aria-label={open ? 'Đóng menu' : 'Mở menu'} aria-expanded={open} aria-controls="mobile-navigation">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
        {open && (
          <div id="mobile-navigation" className="mobile-navigation border-t border-slate-200 bg-white px-4 py-3 md:hidden">
            {user && (
              <Link to="/profile" className="mb-2 block rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <div className="font-medium">{user.full_name}</div><div className="text-xs text-slate-500">{sub}</div>
              </Link>
            )}
            <nav className="flex flex-col gap-1" aria-label="Điều hướng trên điện thoại">
              {menuLinks(true)}
              {user && user.role !== 'ADMIN' && <NavLink to="/orders" className={linkCls}>Đơn hàng</NavLink>}
            </nav>
            <div className="mt-3 flex gap-2">
              {user ? <button className="btn-outline btn-sm w-full" onClick={doLogout}>Đăng xuất</button> : <>
                <Link className="btn-outline btn-sm flex-1" to="/login">Đăng nhập</Link>
                <Link className="btn-primary btn-sm flex-1" to="/register">Đăng ký</Link></>}
            </div>
          </div>
        )}
      </header>
      <main className={isHome ? 'home-main w-full flex-1' : isJobs ? 'jobs-main w-full flex-1' : 'mx-auto w-full max-w-7xl flex-1 px-4 py-6'}><Outlet /></main>
      <ErrorToast />
      <footer className={`site-footer border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500${isHome ? ' home-footer' : ''}`}>
        <p>© 2026 JobMatch — Hệ thống tuyển dụng thông minh hai chiều tích hợp AI so khớp CV–JD</p>
        <p className="mt-1">
          Hotline: <a href="tel:0971961050" className="hover:text-slate-700">0971961050</a>
          {' · '}
          Email: <a href="mailto:quyendotrinhle@gmail.com" className="hover:text-slate-700">quyendotrinhle@gmail.com</a>
        </p>
      </footer>
    </div>
  )
}
