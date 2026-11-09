import { useCallback, useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api, dt, errMsg, SENIORITY_VI, type Application, type CV, type Job, type Match, type Slot } from '../../api'
import MatchPanel from '../../components/MatchPanel'
import { Alert, Empty, Modal, PageTitle, ScoreBadge, SkillChips, Spinner, StatusBadge, STATUS_VI } from '../../components/ui'

const ACTION_LABEL: Record<string, string> = {
  SCREENING: 'Chuyển sàng lọc', INTERVIEW_INVITED: 'Mời phỏng vấn', INTERVIEWED: 'Đã phỏng vấn', OFFERED: 'Gửi offer',
  REJECTED: 'Từ chối', INTERVIEW_SCHEDULED: 'Đặt lịch',
}
const PIPE = ['NEW', 'SCREENING', 'INTERVIEW_INVITED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED', 'REJECTED', 'WITHDRAWN']

function AppDetail({ id, onChanged }: { id: number; onChanged: () => void }) {
  const [a, setA] = useState<Application | null>(null)
  const [note, setNote] = useState('')
  const [err, setErr] = useState('')
  const load = useCallback(() => api.get(`/applications/${id}/manage`).then((r) => setA(r.data)), [id])
  useEffect(() => { load() }, [load])
  const move = async (to: string) => {
    setErr('')
    try { await api.patch(`/applications/${id}/status`, { to, note: note || null }); setNote(''); load(); onChanged() } catch (x) { setErr(errMsg(x)) }
  }
  const download = async () => { const r = await api.get(`/cvs/${a!.cv.id}/file`, { responseType: 'blob' }); window.open(URL.createObjectURL(r.data)) }
  if (!a) return <Spinner />
  return (
    <div className="grid gap-4 md:grid-cols-[1fr_300px]">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="text-lg font-semibold">{a.candidate.full_name}</div><StatusBadge status={a.status} />
          <span className="text-sm text-slate-500">{a.candidate.email} · {a.candidate.phone}</span>
        </div>
        {a.cover_letter && <div className="rounded-lg bg-slate-50 p-3 text-sm"><b>Thư giới thiệu:</b> {a.cover_letter}</div>}
        <div className="flex items-center justify-between"><div className="label !mb-0">CV: {a.cv.title}</div>{a.cv.has_file && <button className="btn-outline btn-sm" onClick={download}>Tải file gốc</button>}</div>
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs">{a.cv.raw_text}</pre>
        <div>
          <div className="label">Lịch sử xử lý</div>
          <ol className="space-y-1 text-sm">
            {a.history.map((h, i) => <li key={i} className="flex gap-2"><span className="w-32 shrink-0 text-xs text-slate-500">{dt(h.at)}</span><span>{STATUS_VI[h.to]}</span>{h.note && <span className="text-slate-500">— {h.note}</span>}</li>)}
          </ol>
        </div>
        {a.slots && a.slots.length > 0 && (
          <div className="text-sm"><div className="label">Lịch phỏng vấn</div>{a.slots.map((s) => <div key={s.id}>{dt(s.start_at)} · <StatusBadge status={s.status} /> {s.result && <b>{s.result}</b>}</div>)}</div>
        )}
      </div>
      <div className="space-y-3">
        {a.match && <div className="card p-3"><MatchPanel match={a.match} /></div>}
        <div className="card space-y-2 p-3">
          <div className="label">Xử lý hồ sơ</div>
          <Alert>{err}</Alert>
          {a.next_actions.length === 0 ? <div className="text-sm text-slate-500">Không còn bước nào để chuyển.</div> : <>
            <input className="input" placeholder="Ghi chú (không bắt buộc)" value={note} onChange={(e) => setNote(e.target.value)} />
            <div className="flex flex-wrap gap-2">
              {a.next_actions.map((to) => (
                <button key={to} className={to === 'REJECTED' ? 'btn-danger btn-sm' : 'btn-primary btn-sm'} onClick={() => move(to)}>{ACTION_LABEL[to] ?? to}</button>
              ))}
            </div>
            {a.status === 'INTERVIEW_SCHEDULED' && <p className="text-xs text-slate-500">Ghi kết quả phỏng vấn ở tab “Lịch phỏng vấn”.</p>}
          </>}
        </div>
      </div>
    </div>
  )
}

function Pipeline({ jobId }: { jobId: number }) {
  const [apps, setApps] = useState<Application[] | null>(null)
  const [filter, setFilter] = useState('')
  const [open, setOpen] = useState<number | null>(null)
  const load = useCallback(() => api.get(`/applications/jobs/${jobId}`).then((r) => setApps(r.data.items)), [jobId])
  useEffect(() => { load() }, [load])
  if (!apps) return <Spinner />
  const counts = apps.reduce<Record<string, number>>((m, a) => ({ ...m, [a.status]: (m[a.status] ?? 0) + 1 }), {})
  const shown = filter ? apps.filter((a) => a.status === filter) : apps
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <button className={`chip px-3 py-1 ${!filter ? 'bg-brand-600 text-white' : 'bg-slate-100'}`} onClick={() => setFilter('')}>Tất cả ({apps.length})</button>
        {PIPE.filter((s) => counts[s]).map((s) => (
          <button key={s} className={`chip px-3 py-1 ${filter === s ? 'bg-brand-600 text-white' : 'bg-slate-100'}`} onClick={() => setFilter(s)}>{STATUS_VI[s]} ({counts[s]})</button>
        ))}
      </div>
      {shown.length === 0 ? <Empty>Chưa có hồ sơ ứng tuyển.</Empty> : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead><tr><th>Ứng viên</th><th>Phù hợp (AI)</th><th>Kỹ năng</th><th>Trạng thái</th><th>Nộp lúc</th><th></th></tr></thead>
            <tbody>
              {shown.map((a) => (
                <tr key={a.id}>
                  <td><div className="font-medium">{a.candidate.full_name}</div><div className="text-xs text-slate-500">{a.cv.years} năm · {SENIORITY_VI[a.cv.seniority]}</div></td>
                  <td><ScoreBadge score={a.match_score} /></td>
                  <td className="max-w-xs"><SkillChips skills={a.cv.skills} max={5} /></td>
                  <td><StatusBadge status={a.status} /></td>
                  <td className="text-xs text-slate-500">{dt(a.created_at)}</td>
                  <td className="text-right"><button className="btn-primary btn-sm" onClick={() => setOpen(a.id)}>Xem & xử lý</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={open != null} onClose={() => setOpen(null)} title="Hồ sơ ứng viên" wide>
        {open != null && <AppDetail id={open} onChanged={load} />}
      </Modal>
    </div>
  )
}

interface RecCand { cv: CV; candidate: { id: number; full_name: string }; match: Match; applied: boolean; invited?: boolean }

function AIRecommended({ jobId }: { jobId: number }) {
  const [items, setItems] = useState<RecCand[] | null>(null)
  const [open, setOpen] = useState<number | null>(null)
  useEffect(() => { api.get(`/jobs/${jobId}/candidates`, { params: { limit: 30 } }).then((r) => setItems(r.data)) }, [jobId])
  const invite = async (r: RecCand) => {
    try {
      await api.post(`/jobs/${jobId}/invite`, { candidate_id: r.candidate.id })
      setItems((xs) => xs && xs.map((x) => (x.candidate.id === r.candidate.id ? { ...x, invited: true } : x)))
    } catch (e) { alert(errMsg(e)) }
  }
  if (!items) return <Spinner label="AI đang tìm ứng viên phù hợp trong kho CV..." />
  return (
    <div className="space-y-2">
      <Alert kind="info">Danh sách xếp hạng từ toàn bộ kho CV (kể cả ứng viên chưa ứng tuyển), theo điểm tổng hợp: ngữ nghĩa + kỹ năng + kinh nghiệm. Bấm “Mời ứng tuyển” để gửi lời mời tới ứng viên.</Alert>
      {items.length === 0 && <Empty>Không tìm thấy ứng viên.</Empty>}
      {items.map((r, i) => (
        <div key={r.cv.id} className="card p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              <span className="w-6 text-center text-sm font-bold text-slate-400">{i + 1}</span>
              <div><div className="font-medium">{r.candidate.full_name} {r.applied && <span className="chip bg-emerald-100 text-emerald-800">Đã ứng tuyển</span>}</div>
                <div className="text-xs text-slate-500">{r.cv.title} · {r.cv.years} năm · {r.cv.role_display}</div></div>
            </div>
            <div className="flex items-center gap-2"><ScoreBadge score={r.match.score} />
              {!r.applied && (r.invited
                ? <span className="chip bg-brand-100 text-brand-700">Đã mời</span>
                : <button className="btn-primary btn-sm" onClick={() => invite(r)}>Mời ứng tuyển</button>)}
              <button className="btn-outline btn-sm" onClick={() => setOpen(open === r.cv.id ? null : r.cv.id)}>{open === r.cv.id ? 'Ẩn' : 'Phân tích'}</button></div>
          </div>
          <div className="ml-9 mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
            <span className="text-emerald-700">✓ {r.match.matched_skills.join(', ') || '—'}</span>
            {r.match.missing_skills.length > 0 && <span className="text-rose-700">✗ thiếu {r.match.missing_skills.join(', ')}</span>}
          </div>
          {open === r.cv.id && <div className="ml-9 mt-3 rounded-lg bg-slate-50 p-3"><MatchPanel match={r.match} /></div>}
        </div>
      ))}
    </div>
  )
}

function Slots({ jobId }: { jobId: number }) {
  const [slots, setSlots] = useState<Slot[] | null>(null)
  const [f, setF] = useState(() => {
    const t = new Date(Date.now() + 86400000); t.setHours(9, 0, 0, 0)
    const iso = (x: Date) => new Date(x.getTime() - x.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    return { start: iso(t), end: iso(new Date(t.getTime() + 3 * 3600000)), minutes: 30, location: 'Google Meet' }
  })
  const [err, setErr] = useState('')
  const [result, setResult] = useState<Slot | null>(null)
  const [fb, setFb] = useState('')
  const load = useCallback(() => api.get(`/jobs/${jobId}/interview-slots`).then((r) => setSlots(r.data)), [jobId])
  useEffect(() => { load() }, [load])
  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setErr('')
    try {
      await api.post(`/jobs/${jobId}/interview-slots`, { start_at: new Date(f.start).toISOString(), end_at: new Date(f.end).toISOString(), minutes: Number(f.minutes), location: f.location })
      load()
    } catch (x) { setErr(errMsg(x)) }
  }
  const cancel = async (s: Slot) => { if (confirm('Hủy khung giờ này?')) { await api.post(`/interview-slots/${s.id}/cancel`, { reason: 'HR hủy' }); load() } }
  const saveResult = async (r: string) => { try { await api.post(`/interview-slots/${result!.id}/result`, { result: r, feedback: fb }); setResult(null); setFb(''); load() } catch (x) { alert(errMsg(x)) } }
  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <form className="card h-fit space-y-3 p-4" onSubmit={create}>
        <div className="font-semibold">Mở khung giờ phỏng vấn</div>
        <Alert>{err}</Alert>
        <div><label className="label">Bắt đầu</label><input className="input" type="datetime-local" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} /></div>
        <div><label className="label">Kết thúc</label><input className="input" type="datetime-local" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} /></div>
        <div><label className="label">Thời lượng mỗi buổi (phút)</label><input className="input" type="number" min={10} value={f.minutes} onChange={(e) => setF({ ...f, minutes: Number(e.target.value) })} /></div>
        <div><label className="label">Địa điểm / link</label><input className="input" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} /></div>
        <button className="btn-primary w-full">Tạo khung giờ</button>
        <p className="text-xs text-slate-500">Hệ thống chặn tạo lịch chồng giờ với lịch khác của bạn.</p>
      </form>
      <div>
        {!slots ? <Spinner /> : slots.length === 0 ? <Empty>Chưa có khung giờ.</Empty> : (
          <div className="card overflow-x-auto">
            <table className="table">
              <thead><tr><th>Thời gian</th><th>Trạng thái</th><th>Ứng viên</th><th>Kết quả</th><th></th></tr></thead>
              <tbody>
                {slots.map((s) => (
                  <tr key={s.id}>
                    <td>{dt(s.start_at)}<div className="text-xs text-slate-500">{s.location}</div></td>
                    <td><StatusBadge status={s.status} /></td>
                    <td>{s.candidate_name ?? '—'}</td>
                    <td>{s.result ? <b className={s.result === 'PASS' ? 'text-emerald-700' : 'text-rose-700'}>{s.result}</b> : '—'}</td>
                    <td className="whitespace-nowrap text-right">
                      {s.status === 'BOOKED' && !s.result && <button className="btn-success btn-sm" onClick={() => setResult(s)}>Ghi kết quả</button>}{' '}
                      {s.status !== 'CANCELLED' && !s.result && <button className="btn-outline btn-sm" onClick={() => cancel(s)}>Hủy</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Modal open={!!result} onClose={() => setResult(null)} title="Kết quả phỏng vấn">
        <div className="space-y-3">
          <textarea className="input h-24" placeholder="Nhận xét" value={fb} onChange={(e) => setFb(e.target.value)} />
          <div className="flex justify-end gap-2"><button className="btn-danger" onClick={() => saveResult('FAIL')}>Không đạt</button><button className="btn-success" onClick={() => saveResult('PASS')}>Đạt</button></div>
        </div>
      </Modal>
    </div>
  )
}

export default function HRJobDetail() {
  const { id } = useParams()
  const [sp, setSp] = useSearchParams()
  const tab = sp.get('tab') ?? 'apps'
  const [job, setJob] = useState<Job | null>(null)
  useEffect(() => { api.get(`/jobs/${id}/manage`).then((r) => setJob(r.data)) }, [id])
  if (!job) return <Spinner />
  const TABS = [['apps', 'Hồ sơ ứng tuyển'], ['ai', 'Ứng viên AI gợi ý'], ['slots', 'Lịch phỏng vấn']]
  return (
    <div>
      <PageTitle title={job.title} sub={`${job.role_display} · ${SENIORITY_VI[job.seniority]} · ${job.min_years}+ năm`} right={<StatusBadge status={job.status} />} />
      <div className="mb-3"><SkillChips skills={job.skills} tone="blue" /></div>
      {job.status === 'PENDING' && <div className="mb-3"><Alert kind="warn">Tin đang chờ duyệt — chưa hiển thị công khai và chưa có trong gợi ý của ứng viên.</Alert></div>}
      <div className="mb-4 flex gap-1 border-b border-slate-200">
        {TABS.map(([k, l]) => <button key={k} className={`tab ${tab === k ? 'tab-active' : ''}`} onClick={() => setSp({ tab: k })}>{l}</button>)}
      </div>
      {tab === 'apps' && <Pipeline jobId={job.id} />}
      {tab === 'ai' && <AIRecommended jobId={job.id} />}
      {tab === 'slots' && <Slots jobId={job.id} />}
    </div>
  )
}
