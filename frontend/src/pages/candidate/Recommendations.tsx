import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errMsg, type CV, type Job, type Match } from '../../api'
import JobCard from '../../components/JobCard'
import MatchPanel from '../../components/MatchPanel'
import { Alert, Empty, PageTitle, ScoreBadge, SkillChips, Spinner } from '../../components/ui'

interface Rec { job: Job; match: Match; applied: boolean }

export default function Recommendations() {
  const [cvs, setCvs] = useState<CV[]>([])
  const [cvId, setCvId] = useState<number>()
  const [data, setData] = useState<{ items: Rec[]; premium: boolean; limit_note?: string; cv: CV } | null>(null)
  const [err, setErr] = useState('')
  const [open, setOpen] = useState<number | null>(null)

  useEffect(() => { api.get('/cvs').then((r) => setCvs(r.data)) }, [])
  useEffect(() => {
    setData(null); setErr('')
    api.get('/matching/jobs', { params: { cv_id: cvId } }).then((r) => setData(r.data)).catch((e) => setErr(errMsg(e)))
  }, [cvId])

  if (err) return <div className="space-y-3"><PageTitle title="Gợi ý việc làm bằng AI" /><Alert kind="warn">{err}</Alert><Link to="/candidate/cvs" className="btn-primary">Tải CV ngay</Link></div>
  return (
    <div>
      <PageTitle title="Gợi ý việc làm bằng AI" sub="Xếp hạng theo độ tương đồng ngữ nghĩa giữa CV và mô tả công việc, kết hợp độ phủ kỹ năng và kinh nghiệm."
        right={cvs.length > 1 && (
          <select className="input !w-64" value={cvId ?? data?.cv.id} onChange={(e) => setCvId(Number(e.target.value))}>
            {cvs.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        )} />
      {!data ? <Spinner label="AI đang so khớp..." /> : (
        <div className="space-y-3">
          <div className="card flex flex-wrap items-center gap-3 p-3 text-sm">
            <span className="text-slate-500">Dựa trên CV:</span><b>{data.cv.title}</b>
            <SkillChips skills={data.cv.skills} max={10} />
          </div>
          {data.limit_note && <Alert kind="info">{data.limit_note} <Link to="/premium" className="font-semibold underline">Nâng cấp Premium</Link></Alert>}
          {data.items.length === 0 ? <Empty>Chưa tìm thấy việc làm phù hợp.</Empty> : data.items.map((r, i) => (
            <JobCard key={r.job.id} job={r.job}
              right={<div className="flex items-center gap-2"><span className="text-xs text-slate-400">#{i + 1}</span><ScoreBadge score={r.match.score} />{r.applied && <span className="chip bg-slate-100">Đã ứng tuyển</span>}</div>}
              footer={
                <div className="mt-2">
                  <button className="text-xs font-medium text-brand-700 hover:underline" onClick={() => setOpen(open === r.job.id ? null : r.job.id)}>
                    {open === r.job.id ? 'Ẩn phân tích' : `Vì sao phù hợp? (thiếu ${r.match.missing_skills.length} kỹ năng)`}
                  </button>
                  {open === r.job.id && <div className="mt-2 rounded-lg bg-slate-50 p-3"><MatchPanel match={r.match} compact={!data.premium} /></div>}
                </div>
              } />
          ))}
        </div>
      )}
    </div>
  )
}
