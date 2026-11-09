import type { Match } from '../api'
import { Bar, ScoreBadge, SkillChips } from './ui'

/** Hiển thị kết quả so khớp + phân tích kỹ năng khớp/thiếu (gap analysis). */
export default function MatchPanel({ match, compact }: { match: Match; compact?: boolean }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="text-3xl font-bold text-brand-700">{Math.round(match.score * 100)}%</div>
        <ScoreBadge score={match.score} />
      </div>
      {!compact && match.semantic != null && (
        <div className="space-y-2">
          <Bar label="Tương đồng ngữ nghĩa (AI)" value={match.semantic_norm ?? match.semantic} />
          <Bar label="Độ phủ kỹ năng yêu cầu" value={match.skill_coverage ?? 0} />
          <Bar label="Đáp ứng kinh nghiệm" value={match.experience_match ?? 0} />
          {match.required_years != null && (
            <div className="text-xs text-slate-500">Kinh nghiệm: {match.cv_years} năm / yêu cầu {match.required_years} năm</div>
          )}
        </div>
      )}
      <div>
        <div className="mb-1 text-xs font-semibold text-emerald-700">✓ Kỹ năng đáp ứng ({match.matched_skills.length})</div>
        {match.matched_skills.length ? <SkillChips skills={match.matched_skills} tone="green" /> : <span className="text-xs text-slate-400">Không có</span>}
      </div>
      <div>
        <div className="mb-1 text-xs font-semibold text-rose-700">✗ Kỹ năng còn thiếu ({match.missing_skills.length})</div>
        {match.missing_skills.length ? <SkillChips skills={match.missing_skills} tone="red" /> : <span className="text-xs text-slate-400">Đáp ứng đủ 🎉</span>}
      </div>
      {!compact && !!match.extra_skills?.length && (
        <div><div className="mb-1 text-xs font-semibold text-slate-600">+ Kỹ năng khác của ứng viên</div><SkillChips skills={match.extra_skills} /></div>
      )}
    </div>
  )
}
