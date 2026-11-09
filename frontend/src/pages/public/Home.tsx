import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, salary, type Job } from '../../api'
import { useAuth } from '../../auth'
import HomeIcon, { type HomeIconName } from '../../components/HomeIcon'
import useSavedJobs from '../../hooks/useSavedJobs'
import CompanyAvatar from '../../components/CompanyAvatar'

interface Metadata {
  cities: string[]
  roles: { value: string; label: string }[]
  skills: string[]
}

const CITIES = ['Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ', 'Bắc Ninh', 'Bình Dương']
const CATEGORIES: { name: string; icon: HomeIconName; query: string }[] = [
  { name: 'IT - Phần mềm', icon: 'code', query: 'Phần mềm' },
  { name: 'Kinh doanh', icon: 'chart', query: 'Business' },
  { name: 'Marketing', icon: 'megaphone', query: 'Marketing' },
  { name: 'Kế toán', icon: 'calculator', query: 'Kế toán' },
  { name: 'Thiết kế', icon: 'palette', query: 'Design' },
  { name: 'Nhân sự', icon: 'users', query: 'Nhân sự' },
]
function FeaturedJob({ job, saved, onSave }: { job: Job; saved: boolean; onSave: () => void }) {
  const pay = job.salary_min && job.salary_max
    ? `${Math.round(job.salary_min / 1_000_000)} - ${Math.round(job.salary_max / 1_000_000)} triệu`
    : salary(job.salary_min, job.salary_max)
  return (
    <article className="featured-job-card">
      <button type="button" className={`job-save${saved ? ' is-saved' : ''}`} onClick={onSave}
        aria-label={`${saved ? 'Bỏ lưu' : 'Lưu'} việc làm ${job.title}`} aria-pressed={saved} title={saved ? 'Bỏ lưu việc làm' : 'Lưu việc làm'}>
        <HomeIcon name="bookmark" />
      </button>
      <div className="featured-job-main">
        <Link to={`/companies/${job.company.id}`} className="featured-company-logo" aria-label={job.company.name}>
          <CompanyAvatar name={job.company.name} url={job.company.logo_url} />
        </Link>
        <div className="featured-job-content">
          <h3><Link to={`/jobs/${job.id}`} title={job.title}>{job.title}</Link></h3>
          <Link className="featured-company-name" to={`/companies/${job.company.id}`} title={job.company.name}>{job.company.name}</Link>
          <div className="featured-skills">{job.skills.slice(0, 3).map((skill) => <Link key={skill} to={`/jobs?skill=${encodeURIComponent(skill)}`}>{skill}</Link>)}</div>
        </div>
      </div>
      <div className="featured-job-meta">
        <span title={job.city || 'Chưa cập nhật địa điểm'}><HomeIcon name="pin" />{job.city || 'Toàn quốc'}</span>
        <span title={pay}><HomeIcon name="money" />{pay}</span>
        <span title={job.min_years ? `Từ ${job.min_years} năm kinh nghiệm` : 'Không yêu cầu kinh nghiệm'}><HomeIcon name="briefcase" />{job.min_years ? `${job.min_years}+ năm` : 'Không yêu cầu'}</span>
      </div>
      <Link className="featured-job-button" to={`/jobs/${job.id}`}>Xem chi tiết<HomeIcon name="arrow" /></Link>
    </article>
  )
}

export default function Home() {
  const [q, setQ] = useState('')
  const [city, setCity] = useState('')
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [total, setTotal] = useState<number | null>(null)
  const [companyTotal, setCompanyTotal] = useState<number | null>(null)
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  const { savedJobs, toggleSaved } = useSavedJobs()
  const { user } = useAuth()
  const nav = useNavigate()
  const { hash } = useLocation()

  useEffect(() => {
    let active = true
    api.get('/jobs', { params: { size: 4 } }).then((r) => {
      if (active) { setJobs(r.data.items); setTotal(r.data.total) }
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [retry])

  useEffect(() => {
    let active = true
    api.get('/metadata').then((r) => { if (active) setMetadata(r.data) }).catch(() => {})
    api.get('/companies', { params: { size: 1 } }).then((r) => { if (active) setCompanyTotal(r.data.total) }).catch(() => {})
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (hash === '#about') document.getElementById('about')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  }, [hash])

  const count = (value: number | null | undefined) => value == null ? '—' : value.toLocaleString('vi-VN')
  const featureTarget = (path: string) => !user || user.role === 'CANDIDATE' ? path : '/jobs'

  return (
    <div className="home-page">
      <section className="home-hero" aria-labelledby="hero-title">
        <div className="home-container hero-inner">
          <div className="hero-art" aria-hidden="true">
            <div className="hero-blob hero-blob-one" /><div className="hero-blob hero-blob-two" />
            <div className="hero-document"><span /><span /><span /><span /><i /><i /></div>
            <div className="hero-growth-arrow"><HomeIcon name="arrow" /></div>
            <div className="hero-chart"><div className="chart-lines"><span /><span /><span /></div><div className="chart-bars"><i /><i /><i /><i /></div></div>
            <img className="hero-person" src="/images/career-professional.png" alt="" fetchPriority="high" width="1024" height="1536" />
          </div>
          <div className="hero-copy">
            <div className="hero-eyebrow"><HomeIcon name="sparkles" /><span>Nền tảng tuyển dụng thông minh với AI</span></div>
            <h1 id="hero-title">Tìm đúng việc<br /><span>Phát triển đúng hướng</span></h1>
            <p className="hero-description">Kết nối ứng viên và nhà tuyển dụng với công nghệ AI.<br className="hero-copy-break" /> Tìm việc nhanh hơn, tuyển đúng người phù hợp hơn.</p>
            <form className="home-search" role="search" onSubmit={(e) => {
              e.preventDefault()
              const params = new URLSearchParams()
              if (q.trim()) params.set('q', q.trim())
              if (city) params.set('city', city)
              nav(`/jobs${params.size ? `?${params}` : ''}`)
            }}>
              <div className="home-search-fields">
                <label className="home-keyword"><HomeIcon name="search" /><span className="sr-only">Từ khóa tìm việc</span><input placeholder="Nhập vị trí, kỹ năng hoặc tên công ty..." value={q} onChange={(e) => setQ(e.target.value)} /></label>
                <label className="home-location"><HomeIcon name="pin" /><span className="sr-only">Địa điểm</span><select value={city} onChange={(e) => setCity(e.target.value)}><option value="">Tất cả địa điểm</option>{(metadata?.cities ?? CITIES).map((name) => <option key={name}>{name}</option>)}</select><HomeIcon name="chevron" /></label>
              </div>
              <button type="submit">Tìm kiếm<HomeIcon name="arrow" /></button>
            </form>
            <nav className="home-categories" aria-label="Khám phá theo lĩnh vực">
              {CATEGORIES.map((category) => <Link key={category.name} to={`/jobs?q=${encodeURIComponent(category.query)}`}><HomeIcon name={category.icon} />{category.name}</Link>)}
              <Link className="home-category-more" to="/jobs" aria-label="Tất cả lĩnh vực"><HomeIcon name="more" /></Link>
            </nav>
          </div>
          <div className="hero-features">
            <Link className="hero-feature" to={featureTarget('/candidate/recommendations')}><span className="hero-feature-icon"><HomeIcon name="match" /></span><span><strong>Gợi ý việc làm phù hợp</strong><small>Dựa trên CV và kỹ năng của bạn</small></span></Link>
            <Link className="hero-feature" to={featureTarget('/candidate/evaluation')}><span className="hero-feature-icon"><HomeIcon name="document" /></span><span><strong>Đánh giá CV bằng AI</strong><small>Phân tích điểm mạnh, gợi ý cải thiện</small></span></Link>
            <a className="hero-feature" href="#about"><span className="hero-feature-icon"><HomeIcon name="shield" /></span><span><strong>An toàn &amp; bảo mật</strong><small>Kiểm tra liên kết độc hại trong CV</small></span></a>
          </div>
        </div>
      </section>

      <div className="home-container home-content">
        <section className="featured-jobs" aria-labelledby="featured-title">
          <div className="featured-heading">
            <div className="featured-heading-copy"><HomeIcon name="star" /><div><h2 id="featured-title">Việc làm nổi bật</h2><p>Những cơ hội tốt nhất từ các doanh nghiệp uy tín</p></div></div>
            <Link className="home-view-all" to="/jobs">Xem tất cả<HomeIcon name="arrow" /></Link>
          </div>
          {error ? <div className="home-jobs-message" role="alert"><p>Chưa thể tải việc làm. Vui lòng thử lại.</p><button className="btn-primary" onClick={() => { setError(false); setRetry((value) => value + 1) }}>Thử lại</button></div>
            : !jobs ? <div className="featured-job-grid" aria-busy="true" aria-label="Đang tải việc làm">{[0, 1, 2, 3].map((i) => <div key={i} className="featured-job-card job-skeleton"><div /><div /><div /><div /></div>)}</div>
              : jobs.length ? <div className="featured-job-grid">{jobs.map((job) => <FeaturedJob key={job.id} job={job} saved={savedJobs.includes(job.id)} onSave={() => toggleSaved(job.id)} />)}</div>
                : <div className="home-jobs-message"><HomeIcon name="briefcase" /><p>Chưa có việc làm đang tuyển. Hãy quay lại sau để khám phá cơ hội mới.</p></div>}
        </section>
        <section className="home-stats" aria-label="JobMatch qua những con số">
          <div className="home-stat"><span className="stat-icon"><HomeIcon name="document" /></span><span><strong>{count(total)}</strong><small>Việc làm đang tuyển</small></span></div>
          <div className="home-stat"><span className="stat-icon"><HomeIcon name="building" /></span><span><strong>{count(companyTotal)}</strong><small>Doanh nghiệp trên nền tảng</small></span></div>
          <div className="home-stat"><span className="stat-icon stat-icon-purple"><HomeIcon name="users" /></span><span><strong>{count(metadata?.skills.length)}</strong><small>Kỹ năng trong hệ thống</small></span></div>
          <div className="home-stat"><span className="stat-icon stat-icon-green"><HomeIcon name="shield" /></span><span><strong>{count(metadata?.roles.length)}</strong><small>Nhóm nghề nghiệp</small></span></div>
        </section>
        <section className="home-about" id="about" aria-labelledby="about-title">
          <div><div className="about-eyebrow">CÙNG BẠN TRÊN HÀNH TRÌNH SỰ NGHIỆP</div><h2 id="about-title">Kết nối đúng người. Mở lối tương lai.</h2><p>JobMatch kết nối ứng viên và doanh nghiệp bằng công nghệ AI: tìm việc theo kỹ năng, đánh giá CV và khám phá những cơ hội phù hợp với bạn.</p></div>
          <Link className="about-cta" to={user ? '/jobs' : '/register'}>{user ? 'Khám phá việc làm' : 'Bắt đầu cùng JobMatch'}<HomeIcon name="arrow" /></Link>
        </section>
      </div>
    </div>
  )
}
