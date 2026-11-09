import { Link } from 'react-router-dom'
import { dt, vnd, type Package } from '../api'
import HomeIcon, { type HomeIconName } from './HomeIcon'
import { Alert, Empty, Spinner } from './ui'

export interface EmployerQuota {
  free_limit: number
  free_used: number
  subscription?: { package: string; remaining: number; ends_at: string } | null
}

const freeFeatures: { icon: HomeIconName; label: string }[] = [
  { icon: 'building', label: 'Quản lý hồ sơ công ty' },
  { icon: 'folder', label: 'Quản lý hồ sơ ứng tuyển' },
  { icon: 'calendar', label: 'Lên lịch phỏng vấn' },
  { icon: 'match', label: 'Gợi ý ứng viên bằng AI' },
  { icon: 'users', label: 'Mời ứng viên phù hợp' },
  { icon: 'bell', label: 'Nhận thông báo tuyển dụng' },
]

export default function EmployerPlans({ packages, quota, error, buying, onBuy }: {
  packages: Package[] | null
  quota: EmployerQuota | null
  error: string
  buying: number | null
  onBuy: (pkg: Package) => void
}) {
  const plans = packages ? [...packages].sort((a, b) => a.price - b.price) : null
  const freeRemaining = quota ? Math.max(0, quota.free_limit - quota.free_used) : 0
  return (
    <section className="premium-page employer-page" aria-labelledby="employer-plans-title">
      <div className="premium-heading">
        <h1 id="employer-plans-title"><HomeIcon name="crown" /><span>Gói tuyển dụng dành cho doanh nghiệp</span></h1>
        <p>Chọn gói đăng tin phù hợp để kết nối với ứng viên tiềm năng</p>
      </div>
      <Alert>{error}</Alert>
      {quota && (
        <div className="employer-quota" aria-label="Hạn mức đăng tin của bạn">
          <div className="employer-quota-item">
            <HomeIcon name="briefcase" />
            <div><span>Lượt đăng tin miễn phí</span><strong>Còn {freeRemaining}/{quota.free_limit} lượt</strong><small>Đã sử dụng {quota.free_used} lượt</small></div>
          </div>
          <div className="employer-quota-item">
            <HomeIcon name="document" />
            <div><span>Gói đang sử dụng</span>{quota.subscription ? <><strong>{quota.subscription.package}</strong><small>Còn {quota.subscription.remaining} lượt · Hết hạn {dt(quota.subscription.ends_at)}</small></> : <><strong>Chưa có gói trả phí đang hoạt động</strong><small>Mua thêm lượt khi cần đăng nhiều tin tuyển dụng</small></>}</div>
          </div>
        </div>
      )}
      {!plans ? <Spinner /> : (
        <>
          {plans.length === 0 && <Empty>Chưa có gói đăng tin trả phí khả dụng.</Empty>}
          <div className={`premium-plans employer-plans${!quota ? ' employer-plans-paid-only' : ''}`}>
            {quota && (
              <article className="premium-plan employer-free-plan" aria-labelledby="employer-free-plan-title">
                <div className="premium-plan-heading">
                  <h2 id="employer-free-plan-title">Miễn phí</h2>
                  <p className="premium-price">0 đ</p>
                  <p className="employer-plan-summary">Bắt đầu tuyển dụng trên JobMatch</p>
                </div>
                <ul className="premium-benefits">
                  <li><HomeIcon name="check" /><span>{quota.free_limit} lượt đăng tin miễn phí</span></li>
                  <li><HomeIcon name="check" /><span>Còn {freeRemaining} lượt để sử dụng</span></li>
                  <li><HomeIcon name="check" /><span>Quản lý tin và hồ sơ ứng tuyển</span></li>
                  <li><HomeIcon name="check" /><span>Kết nối với ứng viên phù hợp</span></li>
                </ul>
                <Link className="premium-buy employer-free-cta" to={freeRemaining > 0 ? '/hr/jobs?new=1' : '/hr/jobs'}>{freeRemaining > 0 ? 'Đăng tin miễn phí' : 'Quản lý tin tuyển dụng'}</Link>
              </article>
            )}
            {plans.map((pkg) => {
              const recommended = pkg.code === 'HR_BASIC'
              const name = pkg.name.replace(/^Gói đăng tin\s*/i, '')
              const benefits = [`${pkg.quota_jobs} lượt đăng tin tuyển dụng`, `Sử dụng trong ${pkg.duration_days} ngày`, 'Thanh toán bằng VietQR', 'Kích hoạt sau khi thanh toán']
              return (
                <article key={pkg.id} className={`premium-plan${recommended ? ' premium-plan-popular' : ''}`} aria-labelledby={`employer-plan-${pkg.id}`}>
                  {recommended && <span className="premium-popular-badge">Đề xuất</span>}
                  <div className="premium-plan-heading">
                    <h2 id={`employer-plan-${pkg.id}`}>{name}</h2>
                    <p className="premium-price">{vnd(pkg.price)}</p>
                    <p className="employer-plan-summary">{pkg.quota_jobs} tin tuyển dụng · {pkg.duration_days} ngày</p>
                  </div>
                  <ul className="premium-benefits">
                    {benefits.map((benefit) => <li key={benefit}><HomeIcon name="check" /><span>{benefit}</span></li>)}
                  </ul>
                  <button className="premium-buy" disabled={buying !== null} onClick={() => onBuy(pkg)} aria-label={`Mua gói ${name}`}>
                    {buying === pkg.id ? 'Đang tạo đơn…' : 'Mua gói'}
                  </button>
                </article>
              )
            })}
          </div>
        </>
      )}
      <section className="premium-free" aria-labelledby="employer-free-title">
        <h2 id="employer-free-title">Chức năng miễn phí</h2>
        <ul>{freeFeatures.map(({ icon, label }) => <li key={label}><HomeIcon name={icon} /><span>{label}</span></li>)}</ul>
      </section>
    </section>
  )
}
