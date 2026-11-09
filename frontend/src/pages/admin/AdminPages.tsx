import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, dt, errMsg, vnd, type Company, type Job, type Order, type Package, type Report, type User } from '../../api'
import { Alert, Empty, Modal, Pager, PageTitle, SkillChips, Spinner, Stat, ORDER_STATUS_VI, StatusBadge, STATUS_VI } from '../../components/ui'

interface Stats {
  users: Record<string, number>; companies: Record<string, number>; jobs: Record<string, number>; applications: Record<string, number>
  cvs: number; orders: Record<string, number>; revenue: number; revenue_daily: { date: string; amount: number }[]
  applications_daily: { date: string; count: number }[]; pending_refunds: number; stray_transactions: number
  reconciling_orders: number; open_reports: number; avg_match_score: number
}

function Bars({ data, fmt }: { data: { label: string; value: number }[]; fmt?: (n: number) => string }) {
  const max = Math.max(1, ...data.map((x) => x.value))
  if (!data.length) return <div className="py-6 text-center text-sm text-slate-400">Chưa có dữ liệu</div>
  const short = (iso: string) => { const [, m, d] = iso.split('-'); return `${d}/${m}` }
  const every = Math.ceil(data.length / 8)   // tối đa ~8 nhãn ngày cho khỏi chồng chữ
  return (
    <div>
      <div className="flex h-40 items-end justify-center gap-1 border-b border-slate-200">
        {data.map((x) => (
          <div key={x.label} className="group relative flex h-full max-w-14 flex-1 flex-col justify-end">
            {data.length <= 10 && <div className="mb-0.5 text-center text-[10px] text-slate-600">{fmt ? fmt(x.value) : x.value}</div>}
            <div className="rounded-t bg-brand-500 group-hover:bg-brand-700" style={{ height: `${Math.max(2, (x.value / max) * 130)}px` }} />
            <div className="pointer-events-none absolute -top-6 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-white group-hover:block">
              {short(x.label)}: {fmt ? fmt(x.value) : x.value}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-center gap-1">
        {data.map((x, i) => <div key={x.label} className="max-w-14 flex-1 text-center text-[10px] text-slate-500">{i % every === 0 ? short(x.label) : ''}</div>)}
      </div>
    </div>
  )
}

const sum = (o?: Record<string, number>) => Object.values(o ?? {}).reduce((a, b) => a + b, 0)

export function AdminDashboard() {
  const [s, setS] = useState<Stats | null>(null)
  useEffect(() => { api.get('/admin/stats').then((r) => setS(r.data)) }, [])
  if (!s) return <Spinner />
  return (
    <div className="space-y-5">
      <PageTitle title="Thống kê hệ thống" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Người dùng" value={sum(s.users).toLocaleString('vi-VN')} hint={`${s.users.CANDIDATE ?? 0} ứng viên · ${s.users.HR ?? 0} HR`} />
        <Stat label="Tin tuyển dụng" value={sum(s.jobs).toLocaleString('vi-VN')} hint={`${s.jobs.PENDING ?? 0} chờ duyệt`} />
        <Stat label="Hồ sơ ứng tuyển" value={sum(s.applications)} hint={`${s.cvs.toLocaleString('vi-VN')} CV trong hệ thống`} />
        <Stat label="Doanh thu" value={vnd(s.revenue)} hint={`${s.orders.PAID ?? 0} đơn đã thanh toán`} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Điểm phù hợp TB" value={`${Math.round(s.avg_match_score * 100)}%`} hint="Trung bình điểm AI của các đơn ứng tuyển" />
        <Stat label="Đơn chờ đối soát" value={s.reconciling_orders} />
        <Stat label="Báo cáo vi phạm mở" value={s.open_reports} />
        <Stat label="Yêu cầu hoàn tiền" value={s.pending_refunds} />
      </div>
      {(s.pending_refunds > 0 || s.stray_transactions > 0 || (s.companies.PENDING ?? 0) > 0 || s.open_reports > 0 || s.reconciling_orders > 0) && (
        <Alert kind="warn">Cần xử lý: {s.companies.PENDING ?? 0} công ty chờ duyệt · {s.jobs.PENDING ?? 0} tin chờ duyệt · {s.pending_refunds} yêu cầu hoàn tiền · {s.reconciling_orders} đơn chờ đối soát · {s.stray_transactions} giao dịch cần đối soát · {s.open_reports} báo cáo vi phạm</Alert>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4"><h3 className="mb-3 font-semibold">Doanh thu 30 ngày</h3><Bars data={s.revenue_daily.map((x) => ({ label: x.date, value: x.amount }))} fmt={vnd} /></div>
        <div className="card p-4"><h3 className="mb-3 font-semibold">Hồ sơ ứng tuyển 30 ngày</h3><Bars data={s.applications_daily.map((x) => ({ label: x.date, value: x.count }))} /></div>
        <div className="card p-4">
          <h3 className="mb-3 font-semibold">Đơn ứng tuyển theo trạng thái</h3>
          <div className="flex flex-wrap gap-2">{Object.entries(s.applications).map(([k, v]) => <span key={k} className="flex items-center gap-1"><StatusBadge status={k} /> <b className="text-sm">{v}</b></span>)}</div>
        </div>
        <div className="card p-4">
          <h3 className="mb-3 font-semibold">Đơn hàng theo trạng thái</h3>
          <div className="flex flex-wrap gap-2">{Object.entries(s.orders).map(([k, v]) => <span key={k} className="flex items-center gap-1"><StatusBadge status={k} /> <b className="text-sm">{v}</b></span>)}</div>
        </div>
      </div>
    </div>
  )
}

export function AdminModeration() {
  const [tab, setTab] = useState<'companies' | 'jobs'>('jobs')
  const [status, setStatus] = useState('PENDING')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<{ total: number; items: (Company | Job)[] } | null>(null)
  const [view, setView] = useState<Job | null>(null)
  const load = useCallback(() => { setData(null); api.get(`/admin/${tab}`, { params: { status: status || undefined, page } }).then((r) => setData(r.data)) }, [tab, status, page])
  useEffect(() => { load() }, [load])
  const review = async (id: number, st: string) => {
    const note = st === 'REJECTED' ? prompt('Lý do từ chối:') ?? '' : ''
    try { await api.request({ method: tab === "jobs" ? "patch" : "post", url: `/admin/${tab}/${id}/${tab === "jobs" ? "moderate" : "review"}`, data: { status: st, note } }); setView(null); load() } catch (x) { alert(errMsg(x)) }
  }
  const approveVal = tab === 'jobs' ? 'PUBLISHED' : 'APPROVED'
  return (
    <div>
      <PageTitle title="Kiểm duyệt" />
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 border-b border-slate-200">
          <button className={`tab ${tab === 'jobs' ? 'tab-active' : ''}`} onClick={() => { setTab('jobs'); setPage(1) }}>Tin tuyển dụng</button>
          <button className={`tab ${tab === 'companies' ? 'tab-active' : ''}`} onClick={() => { setTab('companies'); setPage(1) }}>Công ty</button>
        </div>
        <select className="input !w-48" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="PENDING">Chờ duyệt</option><option value={approveVal}>Đã duyệt</option><option value="REJECTED">Từ chối</option><option value="">Tất cả</option>
        </select>
      </div>
      {!data ? <Spinner /> : data.items.length === 0 ? <Empty>Không có mục nào.</Empty> : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead><tr><th>{tab === 'jobs' ? 'Tin' : 'Công ty'}</th><th>Chi tiết</th><th>Trạng thái</th><th>Ngày tạo</th><th></th></tr></thead>
            <tbody>
              {data.items.map((x) => {
                const job = tab === 'jobs' ? (x as Job) : null
                const c = x as Company & { created_at?: string }
                return (
                  <tr key={x.id}>
                    <td>{job ? <button className="text-left font-medium hover:text-brand-700" onClick={() => setView(job)}>{job.title}</button> : <b>{c.name}</b>}
                      <div className="text-xs text-slate-500">{job ? job.company.name : `${c.owner?.full_name} · ${c.owner?.email}`}</div></td>
                    <td className="max-w-sm">{job ? <SkillChips skills={job.skills} max={6} /> : <span className="text-xs text-slate-600">{c.location} {c.website}</span>}</td>
                    <td><StatusBadge status={x.status} /></td>
                    <td className="text-xs text-slate-500">{dt((x as Job).created_at ?? c.created_at)}</td>
                    <td className="whitespace-nowrap text-right">
                      {x.status === 'PENDING' && <>
                        <button className="btn-success btn-sm" onClick={() => review(x.id, approveVal)}>Duyệt</button>{' '}
                        <button className="btn-danger btn-sm" onClick={() => review(x.id, 'REJECTED')}>Từ chối</button></>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pager page={page} total={data.total} size={30} onChange={setPage} />}
      <Modal open={!!view} onClose={() => setView(null)} title={view?.title ?? ''} wide>
        {view && <div className="space-y-3"><div className="text-sm text-slate-500">{view.company.name}</div><SkillChips skills={view.skills} tone="blue" />
          <div className="max-h-96 overflow-auto whitespace-pre-line rounded bg-slate-50 p-3 text-sm">{view.description}</div>
          {view.status === 'PENDING' && <div className="flex justify-end gap-2"><button className="btn-danger" onClick={() => review(view.id, 'REJECTED')}>Từ chối</button><button className="btn-success" onClick={() => review(view.id, 'PUBLISHED')}>Duyệt</button></div>}</div>}
      </Modal>
    </div>
  )
}

export function AdminUsers() {
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<{ total: number; items: User[] } | null>(null)
  const load = useCallback(() => api.get('/admin/users', { params: { q: q || undefined, role: role || undefined, page } }).then((r) => setData(r.data)), [q, role, page])
  useEffect(() => { load() }, [load])
  const toggle = async (u: User) => {
    try { await api.post(`/admin/users/${u.id}/status`, { status: u.status === 'ACTIVE' ? 'LOCKED' : 'ACTIVE' }); load() } catch (x) { alert(errMsg(x)) }
  }
  return (
    <div>
      <PageTitle title="Người dùng" right={<div className="flex gap-2">
        <input className="input !w-56" placeholder="Tìm email, tên..." value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
        <select className="input !w-40" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}><option value="">Mọi vai trò</option><option value="CANDIDATE">Ứng viên</option><option value="HR">HR</option><option value="ADMIN">Admin</option></select>
      </div>} />
      {!data ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead><tr><th>Họ tên</th><th>Email</th><th>Vai trò</th><th>Trạng thái</th><th>Ngày tạo</th><th></th></tr></thead>
            <tbody>{data.items.map((u) => (
              <tr key={u.id}><td>{u.full_name} {u.is_premium && <span className="chip bg-amber-100 text-amber-800">Premium</span>}</td><td>{u.email}</td><td>{u.role}</td>
                <td><StatusBadge status={u.status} /></td><td className="text-xs text-slate-500">{dt(u.created_at)}</td>
                <td className="whitespace-nowrap text-right"><Link className="btn-outline btn-sm" to={`/admin/audit?actor_id=${u.id}`}>Lịch sử</Link>{' '}{u.role !== 'ADMIN' && <button className={u.status === 'ACTIVE' ? 'btn-outline btn-sm text-rose-600' : 'btn-success btn-sm'} onClick={() => toggle(u)}>{u.status === 'ACTIVE' ? 'Khóa' : 'Mở khóa'}</button>}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {data && <Pager page={page} total={data.total} size={30} onChange={setPage} />}
    </div>
  )
}

interface Tx { id: number; sepay_tx_id: string; order_id?: number; amount: number; content?: string; status: string; received_at: string }
interface Recon { checked_at: string; total_received: number; total_paid_orders: number; total_refunded: number; stuck_pending_orders: number; reconciling_orders: number; sepay?: { enabled: boolean; checked?: number; error?: string }; problems: Record<string, string | number>[] }
interface RefundRow { id: number; status: string; reason: string; created_at: string; order: Order }

export function AdminPayments() {
  const [tab, setTab] = useState<'orders' | 'tx' | 'recon' | 'refunds' | 'packages'>('orders')
  const [orders, setOrders] = useState<{ total: number; items: Order[] } | null>(null)
  const [tx, setTx] = useState<{ total: number; items: Tx[] } | null>(null)
  const [recon, setRecon] = useState<Recon | null>(null)
  const [refunds, setRefunds] = useState<RefundRow[] | null>(null)
  const [status, setStatus] = useState('')
  const loadSeq = useRef(0)
  const load = useCallback(() => {
    // Chỉ nhận phản hồi của lần tải mới nhất: phản hồi cũ về muộn không được ghi đè bộ lọc vừa chọn.
    const seq = ++loadSeq.current
    const latest = <T,>(set: (v: T) => void) => (r: { data: T }) => { if (seq === loadSeq.current) set(r.data) }
    if (tab === 'orders') api.get('/admin/orders', { params: { status: status || undefined } }).then(latest(setOrders))
    if (tab === 'tx') api.get('/admin/transactions', { params: { status: status || undefined } }).then(latest(setTx))
    if (tab === 'recon') api.get('/admin/reconcile').then(latest(setRecon))
    if (tab === 'refunds') api.get('/admin/refunds', { params: { status: status || undefined } }).then(latest(setRefunds))
  }, [tab, status])
  useEffect(() => { load() }, [load])
  const resolve = async (o: Order, approve: boolean) => {
    const note = prompt(approve ? 'Ghi chú khi chấp nhận (VD: khách chuyển dư, đã xác minh)' : 'Lý do không chấp nhận (cần hoàn lại tiền cho khách)')
    if (note === null) return
    try { await api.post(`/admin/orders/${o.id}/resolve`, { approve, note }); load() } catch (x) { alert(errMsg(x)) }
  }
  const assign = async (t: Tx) => {
    const code = prompt('Gắn giao dịch này vào mã đơn nào? (VD: QTD000123)')
    if (!code) return
    try { await api.post(`/admin/transactions/${t.id}/assign`, { order_code: code }); load() } catch (x) { alert(errMsg(x)) }
  }
  const decide = async (r: RefundRow, approve: boolean) => {
    const note = prompt(approve ? 'Ghi chú (VD: đã chuyển khoản hoàn lúc...)' : 'Lý do từ chối') ?? ''
    try { await api.post(`/admin/refunds/${r.id}`, { approve, note }); load() } catch (x) { alert(errMsg(x)) }
  }
  const TABS: [typeof tab, string][] = [['orders', 'Đơn hàng'], ['tx', 'Giao dịch SePay'], ['recon', 'Đối soát'], ['refunds', 'Hoàn tiền'], ['packages', 'Gói dịch vụ']]
  return (
    <div>
      <PageTitle title="Thanh toán & đối soát" />
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 border-b border-slate-200">{TABS.map(([k, l]) => <button key={k} className={`tab ${tab === k ? 'tab-active' : ''}`} onClick={() => { setTab(k); setStatus(k === 'refunds' ? 'REQUESTED' : '') }}>{l}</button>)}</div>
        {tab !== 'recon' && tab !== 'packages' && (
          <select className="input !w-48" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Tất cả trạng thái</option>
            {(tab === 'orders' ? ['PENDING', 'RECONCILING', 'PAID', 'EXPIRED', 'CANCELLED', 'REFUND_REQUESTED', 'REFUNDED'] : tab === 'tx' ? ['MATCHED', 'UNMATCHED', 'LATE', 'AMOUNT_MISMATCH', 'RESOLVED', 'REFUND_DUE'] : ['REQUESTED', 'DONE', 'REJECTED'])
              .map((s) => <option key={s} value={s}>{(tab === 'orders' ? ORDER_STATUS_VI : STATUS_VI)[s] ?? s}</option>)}
          </select>
        )}
        {tab === 'recon' && <button className="btn-primary btn-sm" onClick={load}>Chạy đối soát</button>}
      </div>

      {tab === 'orders' && (!orders ? <Spinner /> : (
        <div className="card overflow-x-auto"><table className="table">
          <thead><tr><th>Mã đơn</th><th>Khách hàng</th><th>Gói</th><th>Số tiền</th><th>Trạng thái</th><th>Tạo lúc</th><th>Thanh toán</th><th></th></tr></thead>
          <tbody>{orders.items.map((o) => <tr key={o.id}><td className="font-mono">{o.order_code}</td><td>{o.user.full_name}<div className="text-xs text-slate-500">{o.user.email}</div></td><td>{o.package.name}</td><td>{vnd(o.amount)}</td><td><StatusBadge status={o.status} label={ORDER_STATUS_VI[o.status]} /></td><td className="text-xs">{dt(o.created_at)}</td><td className="text-xs">{dt(o.paid_at)}</td>
            <td className="whitespace-nowrap text-right">{o.status === 'RECONCILING' && <><button className="btn-success btn-sm" onClick={() => resolve(o, true)}>Chấp nhận</button>{' '}<button className="btn-danger btn-sm" onClick={() => resolve(o, false)}>Từ chối</button></>}</td></tr>)}</tbody>
        </table>{orders.items.length === 0 && <Empty>Không có đơn.</Empty>}</div>))}

      {tab === 'tx' && (!tx ? <Spinner /> : (
        <div className="card overflow-x-auto"><table className="table">
          <thead><tr><th>Mã GD SePay</th><th>Số tiền</th><th>Nội dung</th><th>Đơn</th><th>Kết quả</th><th>Nhận lúc</th><th></th></tr></thead>
          <tbody>{tx.items.map((t) => <tr key={t.id}><td className="font-mono text-xs">{t.sepay_tx_id}</td><td>{vnd(t.amount)}</td><td className="max-w-xs text-xs">{t.content}</td><td>{t.order_id ?? '—'}</td><td><StatusBadge status={t.status} /></td><td className="text-xs">{dt(t.received_at)}</td>
            <td className="text-right">{t.status === 'UNMATCHED' && !t.order_id && <button className="btn-outline btn-sm" onClick={() => assign(t)}>Gắn vào đơn</button>}</td></tr>)}</tbody>
        </table>{tx.items.length === 0 && <Empty>Chưa có giao dịch.</Empty>}</div>))}

      {tab === 'recon' && (!recon ? <Spinner /> : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Tổng tiền nhận (SePay)" value={vnd(recon.total_received)} />
            <Stat label="Tổng đơn đã thanh toán" value={vnd(recon.total_paid_orders)} />
            <Stat label="Đã hoàn tiền" value={vnd(recon.total_refunded)} />
            <Stat label="Đơn treo quá hạn" value={recon.stuck_pending_orders} hint={`${recon.reconciling_orders} đơn chờ đối soát`} />
          </div>
          <div className="text-xs text-slate-500">Đối soát lúc {dt(recon.checked_at)} (tự động chạy mỗi ngày lúc 0h) · {recon.sepay?.enabled
            ? (recon.sepay.error ? `Không lấy được dữ liệu SePay: ${recon.sepay.error}` : `Đã đối chiếu ${recon.sepay.checked ?? 0} giao dịch từ API SePay`)
            : 'Chưa cấu hình SEPAY_API_TOKEN: chỉ đối soát với webhook đã nhận'}</div>
          {recon.problems.length === 0 ? <Alert kind="success">Không phát hiện chênh lệch.</Alert> : (
            <div className="card overflow-x-auto"><table className="table">
              <thead><tr><th>Loại vấn đề</th><th>Chi tiết</th></tr></thead>
              <tbody>{recon.problems.map((p, i) => <tr key={i}><td><span className="chip bg-rose-100 text-rose-700">{String(p.type)}</span></td>
                <td className="text-xs">{Object.entries(p).filter(([k]) => k !== 'type').map(([k, v]) => `${k}: ${v}`).join(' · ')}</td></tr>)}</tbody>
            </table></div>)}
        </div>))}

      {tab === 'packages' && <PackagesAdmin />}

      {tab === 'refunds' && (!refunds ? <Spinner /> : refunds.length === 0 ? <Empty>Không có yêu cầu.</Empty> : (
        <div className="card overflow-x-auto"><table className="table">
          <thead><tr><th>Đơn</th><th>Khách hàng</th><th>Số tiền</th><th>Lý do</th><th>Trạng thái</th><th>Gửi lúc</th><th></th></tr></thead>
          <tbody>{refunds.map((r) => <tr key={r.id}><td className="font-mono">{r.order.order_code}</td><td>{r.order.user.full_name}</td><td>{vnd(r.order.amount)}</td><td className="max-w-xs text-sm">{r.reason}</td><td><StatusBadge status={r.status} /></td><td className="text-xs">{dt(r.created_at)}</td>
            <td className="whitespace-nowrap text-right">{r.status === 'REQUESTED' && <><button className="btn-success btn-sm" onClick={() => decide(r, true)}>Đã hoàn tiền</button>{' '}<button className="btn-danger btn-sm" onClick={() => decide(r, false)}>Từ chối</button></>}</td></tr>)}</tbody>
        </table></div>))}
    </div>
  )
}

const EMPTY_PKG = { code: '', name: '', target: 'CANDIDATE', price: 0, duration_days: 30, quota_jobs: 0, description: '', active: true }

function PackagesAdmin() {
  const [pkgs, setPkgs] = useState<Package[] | null>(null)
  const [edit, setEdit] = useState<(typeof EMPTY_PKG) | null>(null)
  const [err, setErr] = useState('')
  const load = () => api.get('/admin/packages').then((r) => setPkgs(r.data))
  useEffect(() => { load() }, [])
  const save = async () => {
    setErr('')
    try { await api.post('/admin/packages', edit); setEdit(null); load() } catch (x) { setErr(errMsg(x)) }
  }
  const toggle = async (p: Package) => { await api.post('/admin/packages', { ...p, active: !p.active }); load() }
  if (!pkgs) return <Spinner />
  return (
    <div className="space-y-3">
      <div className="flex justify-end"><button className="btn-primary btn-sm" onClick={() => setEdit({ ...EMPTY_PKG })}>+ Thêm gói</button></div>
      <div className="card overflow-x-auto"><table className="table">
        <thead><tr><th>Mã</th><th>Tên gói</th><th>Đối tượng</th><th>Giá</th><th>Thời hạn</th><th>Số tin</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{pkgs.map((p) => <tr key={p.id}><td className="font-mono text-xs">{p.code}</td><td>{p.name}</td><td>{p.target === 'HR' ? 'Nhà tuyển dụng' : 'Ứng viên'}</td>
          <td>{vnd(p.price)}</td><td>{p.duration_days} ngày</td><td>{p.quota_jobs || '—'}</td>
          <td><StatusBadge status={p.active ? 'ACTIVE' : 'CLOSED'} label={p.active ? 'Đang bán' : 'Ngừng bán'} /></td>
          <td className="whitespace-nowrap text-right"><button className="btn-outline btn-sm" onClick={() => setEdit({ ...EMPTY_PKG, ...p, description: p.description ?? '', active: !!p.active })}>Sửa</button>{' '}
            <button className="btn-outline btn-sm" onClick={() => toggle(p)}>{p.active ? 'Ngừng bán' : 'Mở bán'}</button></td></tr>)}</tbody>
      </table></div>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.code ? `Gói ${edit.code}` : 'Thêm gói'}>
        {edit && <div className="space-y-3">
          <Alert>{err}</Alert>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Mã gói</label><input className="input" value={edit.code} onChange={(e) => setEdit({ ...edit, code: e.target.value.toUpperCase() })} /></div>
            <div><label className="label">Đối tượng</label><select className="input" value={edit.target} onChange={(e) => setEdit({ ...edit, target: e.target.value })}><option value="CANDIDATE">Ứng viên</option><option value="HR">Nhà tuyển dụng</option></select></div>
          </div>
          <div><label className="label">Tên gói</label><input className="input" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></div>
          <div className="grid grid-cols-3 gap-3">
            <div><label className="label">Giá (đ)</label><input className="input" type="number" min={1000} value={edit.price} onChange={(e) => setEdit({ ...edit, price: Number(e.target.value) })} /></div>
            <div><label className="label">Số ngày</label><input className="input" type="number" min={1} value={edit.duration_days} onChange={(e) => setEdit({ ...edit, duration_days: Number(e.target.value) })} /></div>
            <div><label className="label">Số tin</label><input className="input" type="number" min={0} value={edit.quota_jobs} onChange={(e) => setEdit({ ...edit, quota_jobs: Number(e.target.value) })} /></div>
          </div>
          <div><label className="label">Mô tả</label><textarea className="input h-20" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></div>
          <div className="flex justify-end"><button className="btn-primary" disabled={!edit.code || !edit.name || edit.price < 1000} onClick={save}>Lưu</button></div>
        </div>}
      </Modal>
    </div>
  )
}

interface Log { id: number; actor_id?: number; action: string; entity: string; entity_id?: number; data?: unknown; created_at: string }

export function AdminAudit() {
  const [sp, setSp] = useSearchParams()
  const actor = sp.get('actor_id')
  const [q, setQ] = useState('')
  const [logs, setLogs] = useState<Log[] | null>(null)
  useEffect(() => { api.get('/admin/audit-logs', { params: { action: q || undefined, actor_id: actor || undefined } }).then((r) => setLogs(r.data)) }, [q, actor])
  return (
    <div>
      <PageTitle title="Nhật ký thao tác" sub={actor ? `Lịch sử hoạt động của người dùng #${actor}` : undefined} right={<div className="flex gap-2">
        {actor && <button className="btn-outline btn-sm" onClick={() => setSp({})}>Bỏ lọc người dùng</button>}
        <input className="input !w-64" placeholder="Lọc theo hành động (VD: LOGIN)" value={q} onChange={(e) => setQ(e.target.value)} /></div>} />
      {!logs ? <Spinner /> : (
        <div className="card overflow-x-auto"><table className="table">
          <thead><tr><th>Thời gian</th><th>Người thực hiện</th><th>Hành động</th><th>Đối tượng</th><th>Dữ liệu</th></tr></thead>
          <tbody>{logs.map((l) => <tr key={l.id}><td className="whitespace-nowrap text-xs">{dt(l.created_at)}</td><td>{l.actor_id ?? 'Hệ thống'}</td><td><span className="chip bg-slate-100">{l.action}</span></td><td>{l.entity} #{l.entity_id}</td><td className="max-w-md truncate font-mono text-xs text-slate-500">{l.data ? JSON.stringify(l.data) : ''}</td></tr>)}</tbody>
        </table></div>
      )}
    </div>
  )
}

const REPORT_VI: Record<string, string> = { OPEN: 'Chờ xử lý', RESOLVED: 'Vi phạm', DISMISSED: 'Không vi phạm' }
const TARGET_VI: Record<string, string> = { JOB: 'Tin tuyển dụng', COMPANY: 'Công ty', USER: 'Người dùng' }
const TARGET_LINK: Record<string, (id: number) => string> = { JOB: (id) => `/jobs/${id}`, COMPANY: (id) => `/companies/${id}`, USER: (id) => `/admin/audit?actor_id=${id}` }

export function AdminReports() {
  const [status, setStatus] = useState('OPEN')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<{ total: number; items: Report[] } | null>(null)
  const [handling, setHandling] = useState<Report | null>(null)
  const [form, setForm] = useState({ status: 'RESOLVED', action: 'NONE', note: '' })
  const [err, setErr] = useState('')
  const load = useCallback(() => { setData(null); api.get('/admin/reports', { params: { status: status || undefined, page } }).then((r) => setData(r.data)) }, [status, page])
  useEffect(() => { load() }, [load])
  const submit = async () => {
    if (!handling) return
    setErr('')
    try { await api.post(`/admin/reports/${handling.id}`, { ...form, note: form.note || null }); setHandling(null); load() } catch (x) { setErr(errMsg(x)) }
  }
  return (
    <div>
      <PageTitle title="Báo cáo vi phạm" right={
        <select className="input !w-48" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="OPEN">Chờ xử lý</option><option value="RESOLVED">Đã xác nhận vi phạm</option><option value="DISMISSED">Không vi phạm</option><option value="">Tất cả</option>
        </select>} />
      {!data ? <Spinner /> : data.items.length === 0 ? <Empty>Không có báo cáo.</Empty> : (
        <div className="card overflow-x-auto"><table className="table">
          <thead><tr><th>Đối tượng</th><th>Lý do</th><th>Người báo cáo</th><th>Trạng thái</th><th>Gửi lúc</th><th></th></tr></thead>
          <tbody>{data.items.map((r) => (
            <tr key={r.id}>
              <td><div className="text-xs text-slate-500">{TARGET_VI[r.target_type]}</div><Link className="font-medium hover:text-brand-700" to={TARGET_LINK[r.target_type](r.target_id)}>{r.target_label ?? `#${r.target_id}`}</Link></td>
              <td className="max-w-sm text-sm">{r.reason}{r.admin_note && <div className="text-xs text-slate-500">Ghi chú: {r.admin_note}</div>}</td>
              <td className="text-sm">{r.reporter?.full_name}<div className="text-xs text-slate-500">{r.reporter?.email}</div></td>
              <td><StatusBadge status={r.status === 'OPEN' ? 'PENDING' : r.status === 'RESOLVED' ? 'REJECTED' : 'CLOSED'} label={REPORT_VI[r.status]} /></td>
              <td className="text-xs">{dt(r.created_at)}</td>
              <td className="text-right">{r.status === 'OPEN' && <button className="btn-primary btn-sm" onClick={() => { setErr(''); setForm({ status: 'RESOLVED', action: 'NONE', note: '' }); setHandling(r) }}>Xử lý</button>}</td>
            </tr>))}</tbody>
        </table></div>
      )}
      {data && <Pager page={page} total={data.total} size={30} onChange={setPage} />}
      <Modal open={!!handling} onClose={() => setHandling(null)} title="Xử lý báo cáo">
        {handling && <div className="space-y-3">
          <Alert>{err}</Alert>
          <div className="rounded bg-slate-50 p-3 text-sm"><b>{TARGET_VI[handling.target_type]}: {handling.target_label}</b><div className="mt-1 text-slate-600">{handling.reason}</div></div>
          <div><label className="label">Kết luận</label>
            <select className="input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value, action: e.target.value === 'DISMISSED' ? 'NONE' : form.action })}>
              <option value="RESOLVED">Xác nhận vi phạm</option><option value="DISMISSED">Không vi phạm</option></select></div>
          {form.status === 'RESOLVED' && <div><label className="label">Biện pháp</label>
            <select className="input" value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })}>
              <option value="NONE">Chỉ ghi nhận</option>
              {handling.target_type === 'JOB' && <option value="CLOSE_JOB">Đóng tin tuyển dụng</option>}
              <option value="LOCK_USER">{handling.target_type === 'USER' ? 'Khóa tài khoản' : 'Khóa tài khoản nhà tuyển dụng'}</option>
            </select></div>}
          <div><label className="label">Ghi chú gửi người báo cáo</label><textarea className="input h-20" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></div>
          <div className="flex justify-end gap-2"><button className="btn-outline" onClick={() => setHandling(null)}>Hủy</button><button className="btn-primary" onClick={submit}>Lưu kết quả</button></div>
        </div>}
      </Modal>
    </div>
  )
}
