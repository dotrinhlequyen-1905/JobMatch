import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ago, salary, SENIORITY_VI, type Job } from '../api'
import { SkillChips } from './ui'
import CompanyAvatar from './CompanyAvatar'

export function Logo({ name, url, size = 44 }: { name: string; url?: string; size?: number }) {
  return <CompanyAvatar name={name} url={url} size={size} />
}

export default function JobCard({ job, right, footer }: { job: Job; right?: ReactNode; footer?: ReactNode }) {
  return (
    <div className="card flex gap-4 p-4 transition hover:border-brand-500/50 hover:shadow">
      <Logo name={job.company.name} url={job.company.logo_url} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <Link to={`/jobs/${job.id}`} className="line-clamp-1 font-semibold text-slate-900 hover:text-brand-700">{job.title}</Link>
            <Link to={`/companies/${job.company.id}`} className="line-clamp-1 text-sm text-slate-500 hover:underline">{job.company.name}</Link>
          </div>
          {right}
        </div>
        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>💰 {salary(job.salary_min, job.salary_max)}</span>
          {job.city && <span>📍 {job.city}</span>}
          <span>🎯 {SENIORITY_VI[job.seniority] ?? job.seniority}{job.min_years ? ` · ${job.min_years}+ năm` : ''}</span>
          <span>🕒 {ago(job.created_at)}</span>
        </div>
        <div className="mt-2"><SkillChips skills={job.skills} max={8} /></div>
        {footer}
      </div>
    </div>
  )
}
