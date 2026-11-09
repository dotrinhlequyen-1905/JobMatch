import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, errMsg, SENIORITY_VI, type Job } from '../../api'
import HomeIcon from '../../components/HomeIcon'
import JobListingCard from '../../components/JobListingCard'
import { Pager } from '../../components/ui'

interface Meta { roles: { value: string; label: string }[]; cities: string[]; seniorities: string[]; skills: string[] }
interface SearchResult { total: number; items: Job[] }
interface SearchResponse { key: string; data?: SearchResult; error?: string }

const PRIMARY_CITIES = ['Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng', 'Remote']
const SALARIES = [
  ['', 'Tất cả'], ['under_10', 'Dưới 10 triệu'], ['10_15', '10 - 15 triệu'],
  ['15_25', '15 - 25 triệu'], ['over_25', 'Trên 25 triệu'],
] as const
const EXPERIENCES = [
  ['none', 'Không yêu cầu'], ['under_1', 'Dưới 1 năm'], ['1_3', '1 - 3 năm'],
  ['3_5', '3 - 5 năm'], ['over_5', 'Trên 5 năm'],
] as const
const PAGE_SIZE = 20

export default function Jobs() {
  const [sp, setSp] = useSearchParams()
  const [meta, setMeta] = useState<Meta | null>(null)
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [showFilter, setShowFilter] = useState(false)
  const [retry, setRetry] = useState(0)
  const searchForm = useRef<HTMLFormElement>(null)
  const keyword = sp.get('q') ?? ''
  const query = sp.toString()
  const requestKey = `${query}|${retry}`
  const current = response?.key === requestKey ? response : null
  const data = current?.data
  const error = current?.error
  const loading = !current
  const rawPage = Number(sp.get('page') ?? 1)
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1
  const cities = [...new Set([...sp.getAll('cities'), sp.get('city') ?? ''].filter(Boolean))]
  const experience = sp.getAll('experience')
  const activeCount = [...sp.entries()].filter(([key, value]) => value && !['page', 'size', 'sort'].includes(key)).length
  const extraCities = [...new Set([...(meta?.cities ?? []), ...cities])].filter((city) => !PRIMARY_CITIES.includes(city))

  useEffect(() => {
    let active = true
    api.get('/metadata').then((r) => { if (active) setMeta(r.data) }).catch(() => {})
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    const params = new URLSearchParams(query)
    const requestedPage = Number(params.get('page') ?? 1)
    params.set('page', String(Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1))
    params.set('size', String(PAGE_SIZE))
    api.get('/jobs', { params }).then((r) => {
      if (active) setResponse({ key: requestKey, data: r.data })
    }).catch((e: unknown) => {
      if (active) setResponse({ key: requestKey, error: errMsg(e) })
    })
    return () => { active = false }
  }, [query, requestKey])

  useEffect(() => {
    if (!showFilter) return
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') setShowFilter(false) }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [showFilter])

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(sp)
    if (value) next.set(key, value); else next.delete(key)
    next.delete('page')
    setSp(next)
  }
  const toggleMulti = (key: 'cities' | 'experience', value: string) => {
    const selected = key === 'cities' ? cities : experience
    const nextValues = selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]
    const next = new URLSearchParams(sp)
    next.delete(key)
    if (key === 'cities') next.delete('city')
    nextValues.forEach((item) => next.append(key, item))
    next.delete('page')
    setSp(next)
  }
  const clearFilters = () => {
    searchForm.current?.reset()
    setSp(new URLSearchParams())
  }
  const cityOption = (city: string) => <label className="jobs-filter-option" key={city}>
    <input type="checkbox" name="cities" value={city} checked={cities.includes(city)} onChange={() => toggleMulti('cities', city)} />
    <span>{city === 'Remote' ? 'Làm việc từ xa' : city}</span>
  </label>

  return (
    <div className="jobs-page">
      <button type="button" className="jobs-mobile-filter-toggle" onClick={() => setShowFilter(!showFilter)} aria-expanded={showFilter} aria-controls="jobs-filters">
        <HomeIcon name="filter" />{showFilter ? 'Ẩn bộ lọc' : 'Bộ lọc tìm kiếm'}{activeCount > 0 && <span>{activeCount}</span>}<HomeIcon name="chevron" />
      </button>
      <aside id="jobs-filters" className={`jobs-filters${showFilter ? ' is-open' : ''}`} aria-labelledby="filters-title">
        <div className="jobs-filters-heading"><h2 id="filters-title">Bộ lọc</h2>{activeCount > 0 && <button type="button" onClick={clearFilters}>Xóa tất cả</button>}</div>
        <fieldset className="jobs-filter-group"><legend>Địa điểm</legend>{PRIMARY_CITIES.map(cityOption)}
          {extraCities.length > 0 && <details className="jobs-more-cities" open={extraCities.some((city) => cities.includes(city)) || undefined}><summary>Địa điểm khác<HomeIcon name="chevron" /></summary><div>{extraCities.map(cityOption)}</div></details>}
        </fieldset>
        <fieldset className="jobs-filter-group"><legend>Mức lương</legend>{SALARIES.map(([value, label]) => <label className="jobs-filter-option" key={value}>
          <input type="radio" name="salary" value={value} checked={(sp.get('salary_range') ?? '') === value} onChange={() => set('salary_range', value)} /><span>{label}</span>
        </label>)}</fieldset>
        <fieldset className="jobs-filter-group"><legend>Kinh nghiệm</legend>
          <label className="jobs-filter-option"><input type="checkbox" name="experience" value="" checked={experience.length === 0} onChange={() => set('experience', '')} /><span>Tất cả</span></label>
          {EXPERIENCES.map(([value, label]) => <label className="jobs-filter-option" key={value}>
            <input type="checkbox" name="experience" value={value} checked={experience.includes(value)} onChange={() => toggleMulti('experience', value)} /><span>{label}</span>
          </label>)}
        </fieldset>
        <details className="jobs-advanced-filters" open={!!(sp.get('role') || sp.get('seniority') || sp.get('skill')) || undefined}>
          <summary>Bộ lọc nâng cao<HomeIcon name="chevron" /></summary>
          <div className="jobs-advanced-fields">
            <label>Nhóm nghề<select value={sp.get('role') ?? ''} onChange={(e) => set('role', e.target.value)}><option value="">Tất cả nhóm nghề</option>{meta?.roles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}</select></label>
            <label>Cấp bậc<select value={sp.get('seniority') ?? ''} onChange={(e) => set('seniority', e.target.value)}><option value="">Tất cả cấp bậc</option>{(meta?.seniorities ?? Object.keys(SENIORITY_VI)).map((value) => <option key={value} value={value}>{SENIORITY_VI[value] ?? value}</option>)}</select></label>
            <label>Kỹ năng<input key={sp.get('skill') ?? ''} defaultValue={sp.get('skill') ?? ''} list="job-search-skills" placeholder="VD: React, Docker..." onBlur={(e) => { if (e.target.value.trim() !== (sp.get('skill') ?? '')) set('skill', e.target.value.trim()) }} onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }} /></label>
            <datalist id="job-search-skills">{meta?.skills.slice(0, 300).map((skill) => <option key={skill} value={skill} />)}</datalist>
          </div>
        </details>
      </aside>

      <section className="jobs-results" aria-labelledby="jobs-result-title" aria-busy={loading}>
        <form ref={searchForm} className="jobs-search" role="search" onSubmit={(e) => { e.preventDefault(); set('q', String(new FormData(e.currentTarget).get('q') ?? '').trim()) }}>
          <label><HomeIcon name="search" /><span className="sr-only">Vị trí, kỹ năng hoặc tên công ty</span><input key={keyword} name="q" defaultValue={keyword} placeholder="Nhập vị trí, kỹ năng hoặc tên công ty..." /></label>
          <button type="submit">Tìm kiếm<HomeIcon name="arrow" /></button>
        </form>
        <div className="jobs-results-toolbar">
          <h1 id="jobs-result-title" aria-live="polite">{loading ? 'Đang tìm việc làm...' : data ? <>Tìm thấy <span>{data.total.toLocaleString('vi-VN')}</span> việc làm phù hợp</> : 'Tìm việc làm phù hợp'}</h1>
          <label className="jobs-sort"><span>Sắp xếp:</span><select aria-label="Sắp xếp việc làm" value={sp.get('sort') ?? 'newest'} onChange={(e) => set('sort', e.target.value)}><option value="newest">Mới nhất</option><option value="oldest">Cũ nhất</option><option value="salary_desc">Lương cao nhất</option></select><HomeIcon name="chevron" /></label>
        </div>
        {error ? <div className="jobs-message jobs-error" role="alert"><HomeIcon name="briefcase" /><h2>Chưa thể tải danh sách việc làm</h2><p>{error}</p><button type="button" onClick={() => setRetry((value) => value + 1)}>Thử lại<HomeIcon name="arrow" /></button></div>
          : loading ? <div className="jobs-list" aria-label="Đang tải việc làm">{[0, 1, 2].map((i) => <div key={i} className="job-listing-card jobs-skeleton"><div /><div /><div /><div /></div>)}</div>
            : data?.items.length ? <div className="jobs-list">{data.items.map((job, index) => <JobListingCard key={job.id} job={job} index={index} />)}</div>
              : <div className="jobs-message"><HomeIcon name="search" /><h2>Chưa có việc làm phù hợp</h2><p>Thử từ khóa khác hoặc điều chỉnh bộ lọc để khám phá thêm cơ hội.</p>{activeCount > 0 && <button type="button" onClick={clearFilters}>Xóa bộ lọc<HomeIcon name="arrow" /></button>}</div>}
        {data && <div className="jobs-pagination"><Pager page={page} total={data.total} size={PAGE_SIZE} onChange={(value) => {
          const next = new URLSearchParams(sp)
          next.set('page', String(value))
          setSp(next)
          window.scrollTo({ top: 0, behavior: 'instant' })
        }} /></div>}
      </section>
    </div>
  )
}
