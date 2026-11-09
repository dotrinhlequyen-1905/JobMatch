import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, d, dt, errMsg, SENIORITY_VI, type Company, type Job, type Slot } from '../../api'
import { useAuth } from '../../auth'
import { Logo } from '../../components/JobCard'
import { Alert, Empty, Modal, PageTitle, SkillChips, Spinner, Stat, StatusBadge, STATUS_VI } from '../../components/ui'

const PIPELINE = ['NEW', 'SCREENING', 'INTERVIEW_INVITED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'OFFERED', 'REJECTED', 'WITHDRAWN']

export function HRDashboard() {
  const { company } = useAuth()
  const [s, setS] = useState<{ applications_by_status: Record<string, number>; jobs_by_status: Record<string, number>; upcoming_interviews: (Slot & { job_title?: string })[]; total_cvs_in_pool: number } | null>(null)
  useEffect(() => { api.get('/jobs/stats').then((r) => setS(r.data)).catch(() => setS(null)) }, [])
  const sum = (o?: Record<string, number>) => Object.values(o ?? {}).reduce((a, b) => a + b, 0)
  return (
    <div>
      <PageTitle title={`Xin chào, ${company?.name ?? ''}`} sub="Tổng quan tuyển dụng" right={<Link to="/hr/jobs?new=1" className="btn-primary">+ Đăng tin mới</Link>} />
      {company?.status !== 'APPROVED' && (
        <div className="mb-4"><Alert kind="warn">Hồ sơ công ty đang ở trạng thái <b>{STATUS_VI[company?.status ?? ''] ?? company?.status}</b>. Hoàn thiện <Link to="/hr/company" className="underline">hồ sơ công ty</Link> và chờ quản trị viên duyệt để đăng tin.</Alert></div>
      )}
      {!s ? <Spinner /> : (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Tin đang hiển thị" value={s.jobs_by_status.PUBLISHED ?? 0} hint={`${sum(s.jobs_by_status)} tin tổng cộng`} />
            <Stat label="Hồ sơ nhận được" value={sum(s.applications_by_status)} hint={`${s.applications_by_status.NEW ?? 0} hồ sơ mới`} />
            <Stat label="Lịch phỏng vấn sắp tới" value={s.upcoming_interviews.length} />
            <Stat label="Kho CV để AI tìm kiếm" value={s.total_cvs_in_pool.toLocaleString('vi-VN')} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card p-4">
              <h3 className="mb-3 font-semibold">Hồ sơ theo trạng thái</h3>
              {PIPELINE.filter((k) => s.applications_by_status[k]).map((k) => [k, s.applications_by_status[k]] as const).map(([k, v]) => (
                <div key={k} className="mb-2 flex items-center gap-2 text-sm">
                  <div className="w-36"><StatusBadge status={k} /></div>
                  <div className="h-2 flex-1 rounded bg-slate-100"><div className="h-2 rounded bg-brand-500" style={{ width: `${(100 * v) / Math.max(1, sum(s.applications_by_status))}%` }} /></div>
                  <div className="w-8 text-right">{v}</div>
                </div>
              ))}
              {sum(s.applications_by_status) === 0 && <div className="text-sm text-slate-500">Chưa có hồ sơ.</div>}
            </div>
            <div className="card p-4">
              <h3 className="mb-3 font-semibold">Phỏng vấn sắp tới</h3>
              {s.upcoming_interviews.length === 0 ? <div className="text-sm text-slate-500">Không có lịch.</div> :
                s.upcoming_interviews.map((x) => (
                  <Link key={x.id} to={`/hr/jobs/${x.job_id}?tab=slots`} className="flex items-start justify-between gap-3 border-b border-slate-100 py-2 text-sm hover:text-brand-700">
                    <div className="min-w-0">
                      <div className="font-medium">{x.candidate_name ?? '—'}</div>
                      <div className="truncate text-xs text-slate-500">{x.job_title}</div>
                    </div>
                    <div className="shrink-0 text-right"><div>{dt(x.start_at)}</div><div className="text-xs text-slate-500">{x.location}</div></div>
                  </Link>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function HRCompany() {
  const { refresh } = useAuth()
  const [c, setC] = useState<Company | null>(null)
  const [msg, setMsg] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  useEffect(() => { api.get('/companies/me').then((r) => setC(r.data)) }, [])
  if (!c) return <Spinner />
  const set = (k: keyof Company) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setC({ ...c, [k]: e.target.value })
  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    try { const r = await api.put('/companies/me', c); setC(r.data); setMsg({ kind: 'success', text: 'Đã lưu hồ sơ công ty' }); refresh() }
    catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
  }
  const uploadLogo = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData(); form.append('file', file)
    try { const r = await api.post('/companies/me/logo', form); setC({ ...c, logo_url: r.data.logo_url }); setMsg({ kind: 'success', text: 'Đã cập nhật logo công ty' }); refresh() }
    catch (x) { setMsg({ kind: 'error', text: errMsg(x) }) }
    e.target.value = ''
  }
  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle title="Hồ sơ công ty" right={<StatusBadge status={c.status} />} />
      <form className="card space-y-3 p-5" onSubmit={save}>
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        {c.status === 'PENDING' && <Alert kind="info">Hồ sơ đang chờ quản trị viên duyệt. Sau khi duyệt bạn có thể đăng tin.</Alert>}
        <div><label className="label">Tên công ty</label><input className="input" value={c.name} onChange={set('name')} required /></div>
        <div><label className="label">Địa điểm</label><input className="input" value={c.location ?? ''} onChange={set('location')} /></div>
        <div><label className="label">Website</label><input className="input" value={c.website ?? ''} onChange={set('website')} /></div>
        <div>
          <label className="label">Logo công ty (hiển thị trên tin tuyển dụng)</label>
          <div className="flex items-center gap-4">
            <Logo name={c.name} url={c.logo_url} size={64} />
            <label className="btn-outline btn-sm cursor-pointer">Tải logo lên<input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={uploadLogo} /></label>
            <span className="text-xs text-slate-500">PNG, JPG hoặc WEBP, tối đa 2MB</span>
          </div>
        </div>
        <div><label className="label">Giới thiệu</label><textarea className="input h-32" value={c.description ?? ''} onChange={set('description')} /></div>
        <button className="btn-primary">Lưu</button>
      </form>
    </div>
  )
}

const EMPTY_JOB = { title: '', description: '', skills: '', min_years: '', seniority: '', role: '', city: '', salary_min: '', salary_max: '', expires_in_days: 30 }

export function JobForm({ job, onSaved, onCancel }: { job?: Job; onSaved: () => void; onCancel: () => void }) {
  const [meta, setMeta] = useState<{ roles: { value: string; label: string }[]; cities: string[] } | null>(null)
  const [f, setF] = useState(() => job ? {
    title: job.title, description: job.description ?? '', skills: job.skills.join(', '), min_years: String(job.min_years), seniority: job.seniority,
    role: job.role, city: job.city ?? '', salary_min: job.salary_min ? String(job.salary_min / 1e6) : '', salary_max: job.salary_max ? String(job.salary_max / 1e6) : '', expires_in_days: 30,
  } : EMPTY_JOB)
  const [err, setErr] = useState('')
  useEffect(() => { api.get('/metadata').then((r) => setMeta(r.data)) }, [])
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value })
  const save = async (e?: React.FormEvent, submit = true) => {
    e?.preventDefault(); setErr('')
    const body = {
      submit,
      title: f.title, description: f.description, city: f.city || null, role: f.role || null, seniority: f.seniority || null,
      skills: f.skills ? f.skills.split(',').map((s) => s.trim()).filter(Boolean) : null,
      min_years: f.min_years === '' ? null : Number(f.min_years),
      salary_min: f.salary_min ? Number(f.salary_min) * 1e6 : null, salary_max: f.salary_max ? Number(f.salary_max) * 1e6 : null,
      expires_in_days: Number(f.expires_in_days),
    }
    try { if (job) await api.put(`/jobs/${job.id}`, body); else await api.post('/jobs', body); onSaved() } catch (x) { setErr(errMsg(x)) }
  }
  return (
    <form className="space-y-3" onSubmit={save}>
      <Alert>{err}</Alert>
      <div><label className="label">Chức danh *</label><input className="input" value={f.title} onChange={set('title')} required /></div>
      <div><label className="label">Mô tả công việc & yêu cầu *</label><textarea className="input h-48" value={f.description} onChange={set('description')} required minLength={30} /></div>
      <div><label className="label">Kỹ năng (để trống để AI tự trích xuất từ mô tả)</label><input className="input" value={f.skills} onChange={set('skills')} placeholder="Java, Spring Boot, PostgreSQL" /></div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <div><label className="label">Nhóm nghề</label><select className="input" value={f.role} onChange={set('role')}><option value="">AI tự nhận diện</option>{meta?.roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select></div>
        <div><label className="label">Cấp bậc</label><select className="input" value={f.seniority} onChange={set('seniority')}><option value="">AI tự nhận diện</option>{Object.entries(SENIORITY_VI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
        <div><label className="label">Số năm KN tối thiểu</label><input className="input" type="number" min={0} value={f.min_years} onChange={set('min_years')} placeholder="Tự nhận diện" /></div>
        <div><label className="label">Thành phố</label><select className="input" value={f.city} onChange={set('city')}><option value="">—</option>{meta?.cities.map((c) => <option key={c}>{c}</option>)}</select></div>
        <div><label className="label">Lương từ (triệu)</label><input className="input" type="number" value={f.salary_min} onChange={set('salary_min')} /></div>
        <div><label className="label">Lương đến (triệu)</label><input className="input" type="number" value={f.salary_max} onChange={set('salary_max')} /></div>
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" className="btn-outline" onClick={onCancel}>Hủy</button>
        {!job && <button type="button" className="btn-outline" onClick={(e) => { const form = (e.target as HTMLElement).closest('form'); if (form?.reportValidity()) save(undefined, false) }}>Lưu nháp</button>}
        <button className="btn-primary">{job ? (job.status === 'DRAFT' ? 'Lưu nháp' : 'Lưu & gửi duyệt lại') : 'Đăng tin (chờ duyệt)'}</button>
      </div>
    </form>
  )
}

export function HRJobs() {
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [open, setOpen] = useState(() => new URLSearchParams(location.search).has('new'))
  const [editing, setEditing] = useState<Job | undefined>()
  const load = () => api.get('/jobs/owned').then((r) => setJobs(r.data))
  useEffect(() => { load() }, [])
  const [err, setErr] = useState('')
  const setStatus = async (j: Job, status: 'CLOSED' | 'PENDING', expires_in_days?: number) => {
    setErr('')
    try { await api.patch(`/jobs/${j.id}/status`, { status, expires_in_days }); load() } catch (x) { setErr(errMsg(x)) }
  }
  const close = (j: Job) => { if (confirm('Đóng tin này?')) setStatus(j, 'CLOSED') }
  const submit = (j: Job) => { if (confirm('Gửi bản nháp cho quản trị viên duyệt? Việc này sẽ dùng một lượt đăng tin.')) setStatus(j, 'PENDING') }
  const reopen = (j: Job) => {
    const expired = j.expires_at && new Date(j.expires_at) <= new Date()
    const days = expired ? Number(prompt('Tin đã hết hạn. Hiển thị thêm bao nhiêu ngày? (1-90)', '30')) : undefined
    if (expired && !(days && days >= 1 && days <= 90)) return
    if (confirm('Mở lại tin? Tin sẽ được gửi quản trị viên duyệt lại trước khi hiển thị.')) setStatus(j, 'PENDING', days)
  }
  const edit = async (j: Job) => { const r = await api.get(`/jobs/${j.id}/manage`); setEditing(r.data); setOpen(true) }
  return (
    <div>
      <PageTitle title="Tin tuyển dụng" right={<button className="btn-primary" onClick={() => { setEditing(undefined); setOpen(true) }}>+ Đăng tin mới</button>} />
      {err && <div className="mb-3"><Alert>{err}</Alert></div>}
      {!jobs ? <Spinner /> : jobs.length === 0 ? <Empty>Chưa có tin tuyển dụng.</Empty> : (
        <div className="card overflow-x-auto">
          <table className="table">
            <thead><tr><th>Chức danh</th><th>Kỹ năng</th><th>Trạng thái</th><th>Lượt xem</th><th>Hồ sơ</th><th>Phù hợp TB</th><th>Ngày đăng</th><th></th></tr></thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td><Link to={`/hr/jobs/${j.id}`} className="font-medium text-slate-900 hover:text-brand-700">{j.title}</Link><div className="text-xs text-slate-500">{j.role_display} · {SENIORITY_VI[j.seniority]}</div></td>
                  <td className="max-w-xs"><SkillChips skills={j.skills} max={5} /></td>
                  <td><StatusBadge status={j.status} /></td>
                  <td>{j.view_count ?? 0}</td>
                  <td>{j.applications}</td>
                  <td>{j.avg_match_score != null ? `${Math.round(j.avg_match_score * 100)}%` : '—'}</td>
                  <td className="text-xs text-slate-500">{d(j.created_at)}</td>
                  <td className="whitespace-nowrap text-right">
                    <Link className="btn-primary btn-sm" to={`/hr/jobs/${j.id}`}>Ứng viên</Link>{' '}
                    {j.status === 'DRAFT' && <><button className="btn-success btn-sm" onClick={() => submit(j)}>Gửi duyệt</button>{' '}</>}
                    {j.status !== 'CLOSED' && <><button className="btn-outline btn-sm" onClick={() => edit(j)}>Sửa</button>{' '}
                      <button className="btn-outline btn-sm" onClick={() => close(j)}>Đóng</button></>}
                    {j.status === 'CLOSED' && <button className="btn-outline btn-sm" onClick={() => reopen(j)}>Mở lại</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Sửa tin tuyển dụng' : 'Đăng tin tuyển dụng'} wide>
        {open && <JobForm job={editing} onCancel={() => setOpen(false)} onSaved={() => { setOpen(false); load() }} />}
      </Modal>
    </div>
  )
}
