import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Company, type Job } from '../../api'
import JobCard, { Logo } from '../../components/JobCard'
import { Empty, Pager, PageTitle, Spinner } from '../../components/ui'
import ReportButton from '../../components/ReportButton'

export function Companies() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<{ total: number; items: Company[] } | null>(null)
  useEffect(() => { api.get('/companies', { params: { q: q || undefined, page, size: 24 } }).then((r) => setData(r.data)) }, [q, page])
  return (
    <div>
      <PageTitle title="Công ty" sub="Các nhà tuyển dụng đã được xác minh" right={
        <input className="input !w-64" placeholder="Tìm công ty..." value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />} />
      {!data ? <Spinner /> : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((c) => (
              <Link key={c.id} to={`/companies/${c.id}`} className="card flex items-center gap-3 p-4 hover:border-brand-500/50">
                <Logo name={c.name} url={c.logo_url} />
                <div className="min-w-0">
                  <div className="line-clamp-1 font-medium">{c.name}</div>
                  <div className="text-xs text-slate-500">{c.location ?? '—'} · {c.open_jobs} việc đang tuyển</div>
                </div>
              </Link>
            ))}
          </div>
          <Pager page={page} total={data.total} size={24} onChange={setPage} />
        </>
      )}
    </div>
  )
}

export function CompanyDetail() {
  const { id } = useParams()
  const [c, setC] = useState<(Company & { jobs: Job[] }) | null>(null)
  useEffect(() => { api.get(`/companies/${id}`).then((r) => setC(r.data)) }, [id])
  if (!c) return <Spinner />
  return (
    <div className="space-y-4">
      <div className="card flex gap-4 p-5">
        <Logo name={c.name} url={c.logo_url} size={72} />
        <div>
          <h1 className="text-xl font-bold">{c.name}</h1>
          <div className="text-sm text-slate-500">{c.location} {c.website && <a className="ml-2 text-brand-700" href={c.website} target="_blank">{c.website}</a>}</div>
          <p className="mt-2 text-sm text-slate-700">{c.description}</p>
          <div className="mt-2"><ReportButton type="COMPANY" id={c.id} /></div>
        </div>
      </div>
      <h2 className="text-lg font-semibold">Việc đang tuyển ({c.jobs.length})</h2>
      {c.jobs.length ? <div className="space-y-3">{c.jobs.map((j) => <JobCard key={j.id} job={{ ...j, company: c }} />)}</div> : <Empty>Chưa có tin tuyển dụng.</Empty>}
    </div>
  )
}
