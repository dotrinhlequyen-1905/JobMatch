import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, dt, errMsg, type Application, type Slot } from '../../api'
import { Alert, Countdown, Empty, Modal, PageTitle, ScoreBadge, Spinner, StatusBadge } from '../../components/ui'

const STEPS = ['NEW', 'SCREENING', 'INTERVIEW_INVITED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED']
const STEP_VI = ['Nộp đơn', 'Sàng lọc', 'Mời PV', 'Đặt lịch', 'Phỏng vấn', 'Kết quả']

function Timeline({ app }: { app: Application }) {
  const reached = new Set(app.history.map((h) => h.to))
  const end = app.status === 'REJECTED' || app.status === 'WITHDRAWN'
  return (
    <div className="mt-3 flex items-center gap-1 overflow-x-auto pb-1">
      {STEPS.map((s, i) => {
        const done = reached.has(s)
        return (
          <div key={s} className="flex items-center gap-1">
            <div className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium ${done ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-400'}`}>{STEP_VI[i]}</div>
            {i < STEPS.length - 1 && <div className={`h-0.5 w-4 ${done ? 'bg-brand-600' : 'bg-slate-200'}`} />}
          </div>
        )
      })}
      {end && <StatusBadge status={app.status} />}
    </div>
  )
}

function SlotPicker({ app, onDone }: { app: Application; onDone: () => void }) {
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [held, setHeld] = useState<Slot | null>(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => api.get(`/applications/${app.id}/slots`).then((r) => {
    setSlots(r.data); setHeld(r.data.find((s: Slot) => s.mine && s.status === 'HELD') ?? null)
  }), [app.id])
  useEffect(() => { load() }, [load])

  const hold = async (s: Slot) => {
    setErr('')
    try { const r = await api.post(`/interview-slots/${s.id}/hold`, { application_id: app.id }); setHeld(r.data); load() }
    catch (x) { setErr(errMsg(x)); load() }
  }
  const confirm = async () => {
    if (!held) return
    try { await api.post(`/interview-slots/${held.id}/book`); onDone() } catch (x) { setErr(errMsg(x)); load() }
  }
  if (!slots) return <Spinner />
  const byDay = slots.reduce<Record<string, Slot[]>>((acc, s) => {
    const k = new Date(s.start_at).toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit' })
    ;(acc[k] ??= []).push(s); return acc
  }, {})
  return (
    <div className="space-y-3">
      <Alert>{err}</Alert>
      {held && (
        <Alert kind="warn">
          Đang giữ chỗ <b>{dt(held.start_at)}</b> — còn <Countdown until={held.held_until!} onEnd={load} /> để xác nhận.
          <button className="btn-success btn-sm ml-3" onClick={confirm}>Xác nhận lịch</button>
        </Alert>
      )}
      {slots.length === 0 && <Empty>Nhà tuyển dụng chưa mở khung giờ trống. Vui lòng quay lại sau.</Empty>}
      {Object.entries(byDay).map(([day, list]) => (
        <div key={day}>
          <div className="mb-1 text-sm font-semibold capitalize">{day}</div>
          <div className="flex flex-wrap gap-2">
            {list.map((s) => (
              <button key={s.id} onClick={() => hold(s)} disabled={s.mine}
                className={`rounded-lg border px-3 py-1.5 text-sm ${s.mine ? 'border-amber-500 bg-amber-50 font-semibold text-amber-800' : 'border-slate-300 hover:border-brand-500 hover:bg-brand-50'}`}>
                {new Date(s.start_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
              </button>
            ))}
          </div>
        </div>
      ))}
      <p className="text-xs text-slate-500">Chọn 1 khung giờ để giữ chỗ trong 10 phút, sau đó bấm "Xác nhận lịch". Quá thời gian, khung giờ sẽ được trả lại cho người khác.</p>
    </div>
  )
}

/** Modal xác nhận hủy / đổi lịch phỏng vấn (thay thế prompt() gốc). */
function CancelModal({ app, reschedule, onClose, onDone }: {
  app: Application; reschedule: boolean; onClose: () => void; onDone: (reschedule: boolean) => void
}) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const slot = app.booked_slot
  if (!slot) return null

  const submit = async () => {
    setLoading(true)
    setErr('')
    try {
      await api.post(`/interview-slots/${slot.id}/cancel`, { reason: reason.trim() || null })
      onDone(reschedule)
    } catch (x) {
      setErr(errMsg(x))
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={reschedule ? 'Đổi lịch phỏng vấn' : 'Hủy lịch phỏng vấn'}>
      <div className="space-y-4">
        <Alert kind="warn">
          {reschedule
            ? <>Bạn sắp hủy lịch phỏng vấn <b>{dt(slot.start_at)}</b> để chọn lịch khác.</>
            : <>Bạn sắp hủy lịch phỏng vấn <b>{dt(slot.start_at)}</b>. Khung giờ sẽ được mở lại cho người khác.</>}
        </Alert>
        <div>
          <label className="label">Lý do {reschedule ? 'đổi lịch' : 'hủy lịch'} (không bắt buộc)</label>
          <textarea
            className="input h-20"
            placeholder={reschedule ? 'Vd: Bận lịch cá nhân, muốn chọn ngày khác...' : 'Vd: Không thể tham dự...'}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            autoFocus
          />
        </div>
        <Alert>{err}</Alert>
        <div className="flex justify-end gap-2">
          <button className="btn-outline" onClick={onClose} disabled={loading}>Quay lại</button>
          <button className={reschedule ? 'btn-primary' : 'btn-danger'} onClick={submit} disabled={loading}>
            {loading ? 'Đang xử lý...' : reschedule ? 'Hủy và chọn lịch khác' : 'Xác nhận hủy lịch'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

/** Modal xác nhận rút đơn (thay thế confirm() gốc). */
function WithdrawModal({ app, onClose, onDone }: { app: Application; onClose: () => void; onDone: () => void }) {
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const submit = async () => {
    setLoading(true)
    setErr('')
    try {
      await api.post(`/applications/${app.id}/withdraw`)
      onDone()
    } catch (x) {
      setErr(errMsg(x))
      setLoading(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="Rút đơn ứng tuyển">
      <div className="space-y-4">
        <Alert kind="warn">
          Bạn có chắc muốn rút đơn ứng tuyển vị trí <b>{app.job.title}</b> tại <b>{app.job.company.name}</b>?
          Thao tác này không thể hoàn tác.
        </Alert>
        <Alert>{err}</Alert>
        <div className="flex justify-end gap-2">
          <button className="btn-outline" onClick={onClose} disabled={loading}>Quay lại</button>
          <button className="btn-danger" onClick={submit} disabled={loading}>
            {loading ? 'Đang xử lý...' : 'Xác nhận rút đơn'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default function MyApplications() {
  const [apps, setApps] = useState<Application[] | null>(null)
  const [pick, setPick] = useState<Application | null>(null)
  const [cancelTarget, setCancelTarget] = useState<{ app: Application; reschedule: boolean } | null>(null)
  const [withdrawTarget, setWithdrawTarget] = useState<Application | null>(null)
  const load = () => api.get('/applications').then((r) => setApps(r.data))
  useEffect(() => { load() }, [])

  const handleCancelDone = async (reschedule: boolean) => {
    setCancelTarget(null)
    await load()
    if (reschedule && cancelTarget) {
      // Sau khi hủy thành công, backend đã chuyển status về INTERVIEW_INVITED.
      // Mở SlotPicker với dữ liệu mới (không dùng stale state).
      const fresh = await api.get('/applications')
      const updated = fresh.data.find((a: Application) => a.id === cancelTarget.app.id)
      if (updated) setPick(updated)
    }
  }

  const handleWithdrawDone = () => {
    setWithdrawTarget(null)
    load()
  }

  return (
    <div>
      <PageTitle title="Đơn ứng tuyển" sub="Theo dõi trạng thái hồ sơ và đặt lịch phỏng vấn." />
      {!apps ? <Spinner /> : apps.length === 0 ? <Empty>Bạn chưa ứng tuyển. <Link className="text-brand-700" to="/candidate/recommendations">Xem gợi ý AI</Link></Empty> : (
        <div className="space-y-3">
          {apps.map((a) => (
            <div key={a.id} className="card p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <Link to={`/jobs/${a.job.id}`} className="font-semibold hover:text-brand-700">{a.job.title}</Link>
                  <div className="text-sm text-slate-500">{a.job.company.name} · nộp {dt(a.created_at)} · CV: {a.cv.title}</div>
                </div>
                <div className="flex items-center gap-2"><ScoreBadge score={a.match_score} /><StatusBadge status={a.status} label={a.status_vi} /></div>
              </div>
              <Timeline app={a} />
              {a.booked_slot && a.booked_slot.status === 'BOOKED' && (
                <div className="mt-3 rounded-lg bg-brand-50 p-3 text-sm text-brand-800">
                  🗓️ Lịch phỏng vấn: <b>{dt(a.booked_slot.start_at)}</b> – {new Date(a.booked_slot.end_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                  {a.booked_slot.location && <> · {a.booked_slot.location}</>}
                  {a.status === 'INTERVIEW_SCHEDULED' && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button className="btn-outline btn-sm" onClick={() => setCancelTarget({ app: a, reschedule: true })}>Đổi lịch</button>
                      <button className="btn-outline btn-sm" onClick={() => setCancelTarget({ app: a, reschedule: false })}>Hủy lịch</button>
                      <span className="self-center text-xs text-brand-700/80">Chỉ hủy/đổi được trước giờ phỏng vấn ít nhất 2 giờ.</span>
                    </div>
                  )}
                </div>
              )}
              <div className="mt-3 flex gap-2">
                {a.status === 'INTERVIEW_INVITED' && <button className="btn-primary btn-sm" onClick={() => setPick(a)}>Chọn lịch phỏng vấn</button>}
                {a.next_actions.includes('WITHDRAWN') && <button className="btn-outline btn-sm" onClick={() => setWithdrawTarget(a)}>Rút đơn</button>}
              </div>
            </div>
          ))}
        </div>
      )}
      <Modal open={!!pick} onClose={() => { setPick(null); load() }} title={`Chọn lịch phỏng vấn — ${pick?.job.title ?? ''}`}>
        {pick && <SlotPicker app={pick} onDone={() => { setPick(null); load() }} />}
      </Modal>
      {cancelTarget && (
        <CancelModal
          app={cancelTarget.app}
          reschedule={cancelTarget.reschedule}
          onClose={() => setCancelTarget(null)}
          onDone={handleCancelDone}
        />
      )}
      {withdrawTarget && (
        <WithdrawModal
          app={withdrawTarget}
          onClose={() => setWithdrawTarget(null)}
          onDone={handleWithdrawDone}
        />
      )}
    </div>
  )
}

