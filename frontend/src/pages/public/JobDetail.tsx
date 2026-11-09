import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, d, errMsg, salary, SENIORITY_VI, type CV, type Job, type Match } from '../../api'
import { useAuth } from '../../auth'
import { Logo } from '../../components/JobCard'
import MatchPanel from '../../components/MatchPanel'
import ReportButton from '../../components/ReportButton'
import { Alert, Modal, SkillChips, Spinner } from '../../components/ui'

export default function JobDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const nav = useNavigate()
  const [job, setJob] = useState<Job | null>(null)
  const [err, setErr] = useState('')
  const [match, setMatch] = useState<Match | null>(null)
  const [cvs, setCvs] = useState<CV[]>([])
  const [applyOpen, setApplyOpen] = useState(false)
  const [cvId, setCvId] = useState<number>()
  const [letter, setLetter] = useState('')
  const [msg, setMsg] = useState('')
  const isCand = user?.role === 'CANDIDATE'

  useEffect(() => { api.get(`/jobs/${id}`).then((r) => setJob(r.data)).catch((e) => setErr(errMsg(e))) }, [id])
  useEffect(() => {
    if (!isCand) return
    api.get('/cvs').then((r) => {
      setCvs(r.data)
      const def = r.data.find((c: CV) => c.is_default) ?? r.data[0]
      if (def) setCvId(def.id)
    })
  }, [isCand])
  useEffect(() => {
    if (!isCand || !cvId) return
    api.get(`/matching/jobs/${id}/match`, { params: { cv_id: cvId } }).then((r) => setMatch(r.data.match)).catch(() => setMatch(null))
  }, [isCand, cvId, id])

  const apply = async () => {
    try {
      await api.post('/applications', { job_id: Number(id), cv_id: cvId, cover_letter: letter || null })
      setApplyOpen(false); setMsg('Ứng tuyển thành công! Theo dõi trạng thái ở mục Đơn ứng tuyển.')
    } catch (e) { setMsg(errMsg(e)); setApplyOpen(false) }
  }

  if (err) return <Alert>{err}</Alert>
  if (!job) return <Spinner />
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="space-y-4">
        <div className="card p-5">
          <div className="flex gap-4">
            <Logo name={job.company.name} url={job.company.logo_url} size={64} />
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-bold text-slate-900">{job.title}</h1>
              <Link to={`/companies/${job.company.id}`} className="text-brand-700 hover:underline">{job.company.name}</Link>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600">
                <span>💰 {salary(job.salary_min, job.salary_max)}</span>
                {job.city && <span>📍 {job.city}</span>}
                <span>🎯 {SENIORITY_VI[job.seniority]} · {job.min_years}+ năm</span>
                <span>🏷️ {job.role_display}</span>
                {job.expires_at && <span>⏳ Hạn nộp {d(job.expires_at)}</span>}
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {isCand && cvId && <Link className="btn-outline" to={`/candidate/evaluation?cv_id=${cvId}&job_id=${id}`}>Đánh giá CV trước khi ứng tuyển</Link>}
            {msg && <div className="w-full"><Alert kind={msg.startsWith('Ứng tuyển thành công') ? 'success' : 'error'}>{msg}</Alert></div>}
            {!user && <button className="btn-primary" onClick={() => nav(`/login?next=/jobs/${id}`)}>Đăng nhập để ứng tuyển</button>}
            {isCand && (cvs.length ? <button className="btn-primary" onClick={() => setApplyOpen(true)}>Ứng tuyển ngay</button>
              : <Link className="btn-primary" to="/candidate/cvs">Tải CV để ứng tuyển</Link>)}
            <span className="ml-auto"><ReportButton type="JOB" id={job.id} /></span>
          </div>
        </div>
        <div className="card p-5">
          <h2 className="mb-2 font-semibold">Kỹ năng yêu cầu (AI trích xuất)</h2>
          <SkillChips skills={job.skills} tone="blue" />
          <h2 className="mb-2 mt-5 font-semibold">Mô tả công việc</h2>
          <div className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{job.description}</div>
        </div>
      </div>
      <aside className="space-y-4">
        {isCand && (
          <div className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">Mức độ phù hợp với bạn</h3>
              {cvs.length > 1 && (
                <select className="input !w-auto !py-1 text-xs" value={cvId} onChange={(e) => setCvId(Number(e.target.value))}>
                  {cvs.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
                </select>
              )}
            </div>
            {match ? <MatchPanel match={match} /> : <div className="text-sm text-slate-500">{cvs.length ? 'Đang phân tích...' : 'Tải CV lên để xem phân tích.'}</div>}
            {match && match.semantic == null && (
              <div className="mt-3 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">
                Xem điểm ngữ nghĩa, độ phủ kỹ năng và kinh nghiệm chi tiết với <Link to="/premium" className="font-semibold underline">Premium</Link>.
              </div>
            )}
          </div>
        )}
        <div className="card p-4 text-sm">
          <h3 className="mb-2 font-semibold">Về công ty</h3>
          <div className="text-slate-600">{job.company.description || 'Chưa có mô tả.'}</div>
          {job.company.location && <div className="mt-2 text-slate-500">📍 {job.company.location}</div>}
          <Link to={`/companies/${job.company.id}`} className="mt-3 inline-block text-brand-700 hover:underline">Xem các vị trí khác →</Link>
        </div>
      </aside>

      <Modal open={applyOpen} onClose={() => setApplyOpen(false)} title="Ứng tuyển">
        <div className="space-y-3">
          <div><label className="label">Chọn CV</label>
            <select className="input" value={cvId} onChange={(e) => setCvId(Number(e.target.value))}>
              {cvs.map((c) => <option key={c.id} value={c.id}>{c.title}{c.is_default ? ' (mặc định)' : ''}</option>)}
            </select></div>
          <div><label className="label">Thư giới thiệu (không bắt buộc)</label>
            <textarea className="input h-28" value={letter} onChange={(e) => setLetter(e.target.value)} /></div>
          <div className="flex justify-end gap-2">
            <button className="btn-outline" onClick={() => setApplyOpen(false)}>Hủy</button>
            <button className="btn-primary" onClick={apply}>Gửi hồ sơ</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
