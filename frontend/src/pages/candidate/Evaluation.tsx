import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, errMsg, type CV, type Job } from '../../api'
import { useAuth } from '../../auth'
import { Alert, Empty, PageTitle, SkillChips, Spinner } from '../../components/ui'

interface Assessment {
  cv_score: number
  match_score: number | null
  strengths: string[]
  matched_skills: string[]
  missing_skills: string[]
  components: { name: string; score: number; comment: string }[]
  suggestions: { priority: string; section: string; issue: string; suggestion: string }[]
  method: string
}

export default function Evaluation() {
  const { user } = useAuth()
  const [params] = useSearchParams()
  const [cvs, setCvs] = useState<CV[] | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [cvId, setCvId] = useState(params.get('cv_id') ?? '')
  const [jobId, setJobId] = useState(params.get('job_id') ?? '')
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<Assessment | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.get('/cvs').then(({ data }: { data: CV[] }) => {
      if (!active) return
      setCvs(data)
      setCvId((current) => current || String(data.find((cv) => cv.is_default)?.id ?? data[0]?.id ?? ''))
    }).catch((err) => { if (active) setError(errMsg(err)) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    const timer = setTimeout(() => {
      api.get('/jobs', { params: { q: query || undefined, size: 30 } }).then(({ data }: { data: { items: Job[] } }) => {
        if (active) setJobs(data.items)
      }).catch((err) => { if (active) setError(errMsg(err)) })
    }, 250)
    return () => { active = false; clearTimeout(timer) }
  }, [query])

  const assess = async () => {
    setBusy(true); setError(''); setResult(null)
    try {
      const { data } = await api.get('/matching/cv-evaluation', { params: { cv_id: Number(cvId), job_id: jobId ? Number(jobId) : undefined } })
      setResult(data)
    } catch (err) { setError(errMsg(err)) }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <PageTitle title="Đánh giá CV và gợi ý cải thiện" sub="Kiểm tra mức độ đầy đủ của CV hoặc đối chiếu với một vị trí trước khi ứng tuyển." />
      {error && <Alert kind="error">{error}</Alert>}
      {!user?.is_premium ? (
        <div className="card space-y-3 p-5">
          <Alert kind="info">Đánh giá CV chuyên sâu là tính năng dành cho gói Premium còn hiệu lực.</Alert>
          <p className="text-sm text-slate-600">Nhận đánh giá từng phần của CV, điểm mạnh, kỹ năng còn thiếu và gợi ý cải thiện. Bạn vẫn có thể tìm việc, xem gợi ý cơ bản và ứng tuyển miễn phí.</p>
          <Link className="btn-primary" to="/premium">Xem gói Premium</Link>
        </div>
      ) : !cvs ? <Spinner /> : cvs.length === 0 ? <Empty>Bạn cần <Link to="/candidate/cvs" className="text-brand-700">tải CV</Link> trước khi đánh giá.</Empty> : (
        <>
          <div className="card grid gap-4 p-4 md:grid-cols-2">
            <div><label className="label" htmlFor="evaluation-cv">CV cần đánh giá</label><select id="evaluation-cv" className="input" value={cvId} onChange={(event) => { setCvId(event.target.value); setResult(null) }}>{cvs.map((cv) => <option value={cv.id} key={cv.id}>{cv.title}</option>)}</select></div>
            <div><label className="label" htmlFor="evaluation-search">Tìm vị trí tuyển dụng</label><input id="evaluation-search" className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tên vị trí hoặc công ty" /></div>
            <div><label className="label" htmlFor="evaluation-job">Đối chiếu vị trí (tuỳ chọn)</label><select id="evaluation-job" className="input" value={jobId} onChange={(event) => { setJobId(event.target.value); setResult(null) }}><option value="">Đánh giá CV tổng quát</option>{jobId && !jobs.some((job) => String(job.id) === jobId) && <option value={jobId}>Vị trí #{jobId}</option>}{jobs.map((job) => <option value={job.id} key={job.id}>{job.title} — {job.company.name}</option>)}</select></div>
            <button className="btn-primary self-end" disabled={!cvId || busy} onClick={assess}>{busy ? 'Đang đánh giá...' : 'Đánh giá CV'}</button>
          </div>
          {result && (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="card p-5"><div className="text-sm text-slate-500">Điểm CV (mức độ đầy đủ)</div><div className="text-3xl font-bold text-brand-700">{result.cv_score}/100</div></div>
                {result.match_score != null && <div className="card p-5"><div className="text-sm text-slate-500">Điểm phù hợp với vị trí</div><div className="text-3xl font-bold text-brand-700">{Math.round(result.match_score * 100)}%</div></div>}
              </div>
              <Alert kind="info">{result.method} Các điểm đánh giá chỉ hỗ trợ bạn chuẩn bị hồ sơ; bạn có thể tiếp tục ứng tuyển với mọi mức điểm.</Alert>
              <div className="card space-y-3 p-4"><h2 className="font-semibold">Nội dung đã nhận diện</h2>{result.components.map((part) => <div key={part.name} className="flex flex-wrap justify-between gap-2 text-sm"><b>{part.name}</b><span className="text-slate-500">{part.comment}</span></div>)}</div>
              <div className="card space-y-2 p-4"><h2 className="font-semibold">Điểm mạnh</h2>{result.strengths.map((strength) => <p key={strength} className="text-sm">{strength}</p>)}</div>
              {jobId && <div className="card space-y-3 p-4"><h2 className="font-semibold">Kỹ năng phù hợp</h2><SkillChips skills={result.matched_skills} tone="green" /><h2 className="font-semibold">Kỹ năng còn thiếu</h2><SkillChips skills={result.missing_skills} /></div>}
              <div className="card space-y-3 p-4"><h2 className="font-semibold">Gợi ý cải thiện</h2>{result.suggestions.map((suggestion, index) => <div key={index} className="border-b border-slate-100 pb-3 text-sm"><b>{suggestion.section} · {suggestion.priority}</b><p>{suggestion.issue}</p><p className="mt-1 text-slate-600">{suggestion.suggestion}</p></div>)}</div>
              <div className="flex flex-wrap gap-2"><Link className="btn-outline" to="/candidate/cvs">Cải thiện CV</Link><Link className="btn-primary" to={jobId ? `/jobs/${jobId}` : '/jobs'}>Tiếp tục ứng tuyển</Link></div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
