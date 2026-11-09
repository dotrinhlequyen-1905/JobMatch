import { Link } from 'react-router-dom'
import { salary, type Job } from '../api'
import useSavedJobs from '../hooks/useSavedJobs'
import HomeIcon from './HomeIcon'
import CompanyAvatar from './CompanyAvatar'

export default function JobListingCard({ job }: { job: Job; index?: number }) {
  const { savedJobs, toggleSaved } = useSavedJobs()
  const saved = savedJobs.includes(job.id)
  const pay = job.salary_min && job.salary_max
    ? `${Math.round(job.salary_min / 1_000_000)} - ${Math.round(job.salary_max / 1_000_000)} triệu`
    : salary(job.salary_min, job.salary_max)
  const experience = job.min_years ? `${job.min_years}+ năm` : 'Không yêu cầu'
  const skills = [...new Set(job.skills)].slice(0, 4)

  return (
    <article className="job-listing-card" aria-labelledby={`job-listing-title-${job.id}`}>
      <Link to={`/companies/${job.company.id}`} className="job-listing-logo" aria-label={`Xem doanh nghiệp ${job.company.name}`}>
        <CompanyAvatar name={job.company.name} url={job.company.logo_url} />
      </Link>
      <div className="job-listing-body">
        <h3 className="job-listing-title" id={`job-listing-title-${job.id}`}>
          <Link to={`/jobs/${job.id}`} title={job.title}>{job.title}</Link>
        </h3>
        <Link className="job-listing-company" to={`/companies/${job.company.id}`} title={job.company.name}>{job.company.name}</Link>
        <div className="job-listing-meta">
          <span title={job.city || 'Chưa cập nhật địa điểm'}><HomeIcon name="pin" />{job.city || 'Chưa cập nhật'}</span>
          <span title={pay}><HomeIcon name="money" />{pay}</span>
          <span title={job.min_years ? `Từ ${job.min_years} năm kinh nghiệm` : 'Không yêu cầu kinh nghiệm'}><HomeIcon name="clock" />{experience}</span>
        </div>
        <div className="job-listing-skills">
          {skills.map(skill => <Link key={skill} to={`/jobs?skill=${encodeURIComponent(skill)}`}>{skill}</Link>)}
        </div>
      </div>
      <button type="button" className={`job-listing-save${saved ? ' is-saved' : ''}`} onClick={() => toggleSaved(job.id)}
        aria-label={`${saved ? 'Bỏ lưu' : 'Lưu'} việc làm ${job.title}`} aria-pressed={saved} title={saved ? 'Bỏ lưu việc làm' : 'Lưu việc làm'}>
        <HomeIcon name="bookmark" />
      </button>
      <Link className="job-listing-detail" to={`/jobs/${job.id}`} aria-label={`Xem chi tiết việc làm ${job.title}`}>Xem chi tiết<HomeIcon name="arrow" /></Link>
    </article>
  )
}
