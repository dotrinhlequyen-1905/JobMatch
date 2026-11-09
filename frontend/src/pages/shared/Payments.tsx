import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, dt, errMsg, vnd, type Order, type Package } from '../../api'
import { useAuth } from '../../auth'
import PremiumPlans from '../../components/PremiumPlans'
import EmployerPlans, { type EmployerQuota } from '../../components/EmployerPlans'
import HomeIcon from '../../components/HomeIcon'
import { Alert, Countdown, Empty, Modal, ORDER_STATUS_VI, PageTitle, Spinner, StatusBadge } from '../../components/ui'

/** Danh sách gói: dùng cho ứng viên (Premium) và HR (gói đăng tin). */
export function Packages() {
  const { user } = useAuth()
  const nav = useNavigate()
  const [pkgs, setPkgs] = useState<Package[] | null>(null)
  const [quota, setQuota] = useState<EmployerQuota | null>(null)
  const [err, setErr] = useState('')
  const [buying, setBuying] = useState<number | null>(null)
  const purchaseInFlight = useRef(false)
  const isHR = user?.role === 'HR'
  useEffect(() => {
    api.get('/packages', { params: { target: isHR ? 'HR' : 'CANDIDATE' } }).then((r) => setPkgs(r.data)).catch((x) => { setErr(errMsg(x)); setPkgs([]) })
    if (isHR) api.get('/jobs/quota').then((r) => setQuota(r.data)).catch((x) => setErr(errMsg(x)))
  }, [isHR])
  const buy = async (p: Package) => {
    if (!user) return nav('/login?next=/premium')
    if (purchaseInFlight.current) return
    purchaseInFlight.current = true
    setBuying(p.id); setErr('')
    try { const r = await api.post('/orders', { package_id: p.id }); nav(`/orders/${r.data.id}`) } catch (x) { setErr(errMsg(x)) } finally { purchaseInFlight.current = false; setBuying(null) }
  }
  return isHR
    ? <EmployerPlans packages={pkgs} quota={quota} error={err} buying={buying} onBuy={buy} />
    : <PremiumPlans packages={pkgs} user={user} error={err} buying={buying} onBuy={buy} />
}

/** Thanh toán VietQR qua SePay cho mọi gói; chế độ demo thêm nút giả lập SePay gửi webhook xác nhận. */
export function Checkout() {
  const { id } = useParams()
  const { user, refresh } = useAuth()
  const [o, setO] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [qrOk, setQrOk] = useState(true)
  const [busy, setBusy] = useState<'pay' | 'underpay' | 'cancel' | null>(null)
  const actionInFlight = useRef(false)
  const load = useCallback(async () => {
    try { const r = await api.get<Order>(`/orders/${id}`); setO(r.data) }
    catch (x) { setErr(errMsg(x)) }
  }, [id])
  const reload = useCallback(async () => {
    setLoading(true); setErr('')
    await load()
    setLoading(false)
  }, [load])
  useEffect(() => { setO(null); setQrOk(true); void reload() }, [reload])
  useEffect(() => {
    if (o?.status !== 'PENDING' && o?.status !== 'RECONCILING') { if (o?.status === 'PAID') void refresh(); return }
    // Chờ SePay gửi webhook: hỏi lại trạng thái đơn mỗi 3 giây.
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [o?.id, o?.status, load, refresh])
  const runAction = async (action: 'pay' | 'underpay' | 'cancel', request: () => Promise<void>) => {
    if (actionInFlight.current) return
    actionInFlight.current = true
    setBusy(action); setErr('')
    try { await request() }
    catch (x) { await load(); setErr(errMsg(x)) }
    finally { actionInFlight.current = false; setBusy(null) }
  }
  const payDemo = (amount?: number) => runAction(amount ? 'underpay' : 'pay', async () => {
    const r = await api.post<Order>(`/orders/${id}/demo-payment`, amount ? { amount } : {})
    setO(r.data)
  })
  const cancel = () => runAction('cancel', async () => { await api.post(`/orders/${id}/cancel`); await load() })
  if (loading) return <Spinner />
  if (!o) return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageTitle title="Thanh toán" />
      <Alert>{err}</Alert>
      <div className="flex flex-wrap gap-3"><button className="btn-primary" onClick={reload}>Thử lại</button><Link className="btn-outline" to="/orders">Xem đơn hàng</Link></div>
    </div>
  )
  const premium = o.package.target === 'CANDIDATE'
  const plansUrl = premium ? '/premium' : '/hr/packages'
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageTitle title={`Thanh toán đơn ${o.order_code}`} sub={o.package.name} right={<StatusBadge status={o.status} label={ORDER_STATUS_VI[o.status]} />} />
      <Alert>{err}</Alert>
      {o.status === 'PAID' && (
        <div className="card space-y-5 p-6" role="status">
          <div className="flex items-start gap-3">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><HomeIcon name="check" /></span>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Thanh toán thành công!</h2>
              <p className="mt-1 text-sm text-slate-600">SePay đã xác nhận giao dịch. {o.package.name} được kích hoạt lúc {dt(o.paid_at)}.</p>
              {premium && user?.premium_until && <p className="mt-2 text-sm font-medium text-brand-700">Premium có hiệu lực đến {dt(user.premium_until)}.</p>}
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="btn-primary" to={premium ? '/candidate/cvs' : '/hr/jobs'}>{premium ? 'Trải nghiệm Premium' : 'Quản lý tin tuyển dụng'}</Link>
            <Link className="btn-outline" to="/orders">Xem đơn hàng</Link>
          </div>
        </div>
      )}
      {(o.status === 'EXPIRED' || o.status === 'CANCELLED') && <Alert kind="warn">Đơn đã {o.status === 'EXPIRED' ? 'hết hạn thanh toán' : 'bị hủy'}. <Link to={plansUrl} className="font-medium underline">Chọn gói và tạo đơn mới</Link>.</Alert>}
      {o.status === 'RECONCILING' && <Alert kind="warn">Hệ thống đã nhận giao dịch nhưng số tiền hoặc thời điểm chuyển khoản chưa khớp với đơn. Quản trị viên đang đối soát; gói sẽ được kích hoạt ngay khi giao dịch được xác nhận.</Alert>}
      {o.status === 'PENDING' && (
        <div className="card grid gap-6 p-6 md:grid-cols-2">
          <div className="text-center">
            {qrOk && o.qr_url ? (
              <img src={o.qr_url} alt={`Mã VietQR thanh toán đơn ${o.order_code}`} className="mx-auto min-h-40 w-64 rounded-lg border" onError={() => setQrOk(false)}
                onLoad={(e) => { if ((e.target as HTMLImageElement).naturalWidth < 50) setQrOk(false) }} />
            ) : (
              <div className="mx-auto grid h-64 w-64 place-items-center rounded-lg border-2 border-dashed border-slate-300 p-4 text-xs text-slate-500">
                Không tải được mã QR. Bạn có thể chuyển khoản thủ công theo thông tin bên cạnh.
              </div>
            )}
            <div className="mt-2 text-xs text-slate-500">Mở app ngân hàng bất kỳ và quét mã VietQR</div>
            <div className="mt-1 text-xs text-slate-500">Đơn hết hạn sau <Countdown key={o.id} until={o.expires_at} onEnd={load} /></div>
          </div>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Thông tin chuyển khoản</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Ngân hàng</dt><dd className="font-medium">{o.bank?.bank}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Số tài khoản</dt><dd className="font-mono font-medium">{o.bank?.account}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Chủ tài khoản</dt><dd className="font-medium">{o.bank?.name}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-slate-500">Nội dung CK</dt><dd><span className="rounded bg-amber-100 px-1.5 font-mono font-semibold">{o.order_code}</span></dd></div>
              <div className="flex justify-between gap-3 border-t border-slate-200 pt-2"><dt className="font-medium">Số tiền</dt><dd className="text-xl font-bold text-brand-700">{vnd(o.amount)}</dd></div>
            </dl>
            <p className="text-xs text-slate-500">Chuyển đúng số tiền và giữ nguyên nội dung chứa mã đơn. Hệ thống tự xác nhận khi SePay báo có giao dịch, không cần thao tác thêm.</p>
            <div className="flex items-center gap-2 text-sm text-slate-600" role="status"><span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" /> Đang chờ xác nhận thanh toán…</div>
            <button className="btn-outline w-full" disabled={busy !== null} onClick={cancel}>{busy === 'cancel' ? 'Đang hủy…' : 'Hủy đơn'}</button>
          </div>
          {o.payment_demo_enabled && (
            <div className="space-y-3 rounded-lg border border-dashed border-brand-300 bg-brand-50 p-4 text-sm md:col-span-2">
              <p><b className="text-brand-700">Chế độ demo</b> · Không cần chuyển khoản thật. Nút bên dưới mô phỏng SePay gửi webhook giao dịch tới hệ thống; đơn được xác nhận qua đúng luồng thật (chống ghi nhận trùng, đối chiếu mã đơn và số tiền).</p>
              <div className="flex flex-wrap gap-2">
                <button className="btn-primary btn-sm" disabled={busy !== null} onClick={() => payDemo()}>{busy === 'pay' ? 'Đang gửi webhook…' : 'Giả lập chuyển khoản thành công'}</button>
                <button className="btn-outline btn-sm" disabled={busy !== null} onClick={() => payDemo(Math.max(1000, o.amount - 1000))}>{busy === 'underpay' ? 'Đang gửi webhook…' : 'Giả lập chuyển thiếu tiền'}</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function Orders() {
  const [orders, setOrders] = useState<Order[] | null>(null)
  const [refundFor, setRefundFor] = useState<Order | null>(null)
  const [reason, setReason] = useState('')
  const [err, setErr] = useState('')
  const load = () => api.get('/orders').then((r) => setOrders(r.data))
  useEffect(() => { load() }, [])
  const submitRefund = async () => {
    try { await api.post(`/orders/${refundFor!.id}/refund`, { reason }); setRefundFor(null); setReason(''); load() }
    catch (x) { setErr(errMsg(x)) }
  }
  return (
    <div>
      <PageTitle title="Đơn hàng của tôi" />
      {!orders ? <Spinner /> : orders.length === 0 ? <Empty>Chưa có đơn hàng.</Empty> : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead><tr><th>Mã đơn</th><th>Gói</th><th>Số tiền</th><th>Trạng thái</th><th>Thời gian</th><th></th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td className="font-mono">{o.order_code}</td><td>{o.package.name}</td><td>{vnd(o.amount)}</td>
                  <td><StatusBadge status={o.status} label={ORDER_STATUS_VI[o.status]} />{o.refund?.admin_note && <div className="mt-1 text-xs text-slate-500">Admin: {o.refund.admin_note}</div>}</td>
                  <td className="text-xs text-slate-500">{dt(o.paid_at ?? o.created_at)}</td>
                  <td className="text-right">
                    {o.status === 'PENDING' && <Link className="btn-primary btn-sm" to={`/orders/${o.id}`}>Thanh toán</Link>}
                    {o.status === 'PAID' && <button className="btn-outline btn-sm" onClick={() => { setErr(''); setRefundFor(o) }}>Yêu cầu hoàn tiền</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={!!refundFor} onClose={() => setRefundFor(null)} title={`Hoàn tiền đơn ${refundFor?.order_code}`}>
        <div className="space-y-3">
          <Alert>{err}</Alert>
          <Alert kind="info">Điều kiện: trong 7 ngày kể từ khi thanh toán và gói chưa được sử dụng (với gói đăng tin).</Alert>
          <textarea className="input h-24" placeholder="Lý do hoàn tiền" value={reason} onChange={(e) => setReason(e.target.value)} />
          <div className="flex justify-end"><button className="btn-primary" disabled={!reason.trim()} onClick={submitRefund}>Gửi yêu cầu</button></div>
        </div>
      </Modal>
    </div>
  )
}
