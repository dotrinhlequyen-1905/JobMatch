import { dt, vnd, type Package, type User } from '../api'
import HomeIcon, { type HomeIconName } from './HomeIcon'
import { Alert, Empty, Spinner } from './ui'

const benefits = [
  'Đánh giá CV chuyên sâu',
  'Gợi ý cải thiện CV',
  'Phân tích kỹ năng',
  'Đánh giá theo vị trí tuyển dụng',
]

const freeFeatures: { icon: HomeIconName; label: string }[] = [
  { icon: 'search', label: 'Tìm kiếm việc làm' },
  { icon: 'document', label: 'Ứng tuyển' },
  { icon: 'calendar', label: 'Đặt lịch phỏng vấn' },
  { icon: 'match', label: 'Nhận gợi ý việc làm' },
  { icon: 'folder', label: 'Theo dõi hồ sơ' },
  { icon: 'bell', label: 'Nhận thông báo' },
]

function durationLabel(days: number) {
  if (days === 365 || days === 360) return '12 tháng'
  return days % 30 === 0 ? `${days / 30} tháng` : `${days} ngày`
}

export default function PremiumPlans({ packages, user, error, buying, onBuy }: {
  packages: Package[] | null
  user: User | null
  error: string
  buying: number | null
  onBuy: (pkg: Package) => void
}) {
  const plans = packages ? [...packages].sort((a, b) => a.duration_days - b.duration_days) : null
  return (
    <section className="premium-page" aria-labelledby="premium-title">
      <div className="premium-heading">
        <h1 id="premium-title"><HomeIcon name="crown" /> <span>Gói Premium dành cho ứng viên</span></h1>
        <p>Mở khóa các tính năng nâng cao để tăng cơ hội trúng tuyển</p>
      </div>
      <Alert>{error}</Alert>
      {user?.is_premium && <div className="premium-current"><Alert kind="success">Bạn đang là thành viên Premium đến {dt(user.premium_until)}. Mua thêm sẽ được cộng dồn thời gian.</Alert></div>}
      {!plans ? <Spinner /> : plans.length === 0 ? <Empty>Chưa có gói Premium khả dụng.</Empty> : (
        <div className="premium-plans">
          {plans.map((pkg) => {
            const popular = pkg.duration_days === 90
            return (
              <article key={pkg.id} className={`premium-plan${popular ? ' premium-plan-popular' : ''}`} aria-labelledby={`premium-plan-${pkg.id}`}>
                {popular && <span className="premium-popular-badge">Phổ biến</span>}
                <div className="premium-plan-heading">
                  <h2 id={`premium-plan-${pkg.id}`}>{durationLabel(pkg.duration_days)}</h2>
                  <p className="premium-price">{vnd(pkg.price)}</p>
                </div>
                <ul className="premium-benefits">
                  {benefits.map((benefit) => <li key={benefit}><HomeIcon name="check" /><span>{benefit}</span></li>)}
                </ul>
                <button className="premium-buy" disabled={buying !== null} onClick={() => onBuy(pkg)} aria-label={`Mua gói ${durationLabel(pkg.duration_days)}`}>
                  {buying === pkg.id ? 'Đang tạo đơn…' : 'Mua gói'}
                </button>
              </article>
            )
          })}
        </div>
      )}
      <section className="premium-free" aria-labelledby="premium-free-title">
        <h2 id="premium-free-title">Chức năng miễn phí</h2>
        <ul>
          {freeFeatures.map(({ icon, label }) => <li key={label}><HomeIcon name={icon} /><span>{label}</span></li>)}
        </ul>
      </section>
    </section>
  )
}
