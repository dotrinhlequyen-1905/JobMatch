import type { ReactNode } from 'react'

export type HomeIconName = 'search' | 'pin' | 'chevron' | 'arrow' | 'code' | 'chart' | 'megaphone' | 'calculator' | 'palette' | 'users' | 'more' | 'sparkles' | 'briefcase' | 'match' | 'document' | 'shield' | 'star' | 'bookmark' | 'money' | 'building' | 'clock' | 'filter' | 'crown' | 'check' | 'calendar' | 'folder' | 'bell'

const paths: Record<HomeIconName, ReactNode> = {
  crown: <><path d="m3 7 4 4 5-8 5 8 4-4-2 13H5L3 7Z" fill="currentColor" stroke="none" /><path d="M5 22h14" /><circle cx="3" cy="6" r="1.5" fill="currentColor" stroke="none" /><circle cx="12" cy="2" r="1.5" fill="currentColor" stroke="none" /><circle cx="21" cy="6" r="1.5" fill="currentColor" stroke="none" /></>,
  check: <path d="m5 12 4 4L19 6" strokeWidth="3" />,
  calendar: <><rect x="3" y="5" width="18" height="17" rx="2" /><path d="M7 2v6m10-6v6M3 11h18m-9 3v5m-3-2h6" /></>,
  folder: <path d="M3 7V4h6l3 3h9v4M3 7h7l2 3h9l-3 11H2L3 7Z" />,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M10 21h4" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5h4" /></>,
  filter: <><path d="M3 6h18M3 12h18M3 18h18" /><circle cx="8" cy="6" r="2" fill="white" /><circle cx="16" cy="12" r="2" fill="white" /><circle cx="10" cy="18" r="2" fill="white" /></>,
  pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  chevron: <path d="m7 10 5 5 5-5" />,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  code: <path d="m7 6-5 6 5 6m10-12 5 6-5 6M14 3l-4 18" />,
  chart: <><rect x="3" y="14" width="3" height="7" rx=".5" fill="currentColor" /><rect x="10" y="8" width="3" height="13" rx=".5" fill="currentColor" /><rect x="17" y="3" width="3" height="18" rx=".5" fill="currentColor" /></>,
  megaphone: <><path d="m4 9 15-5v16L4 15H2V9h2Zm4 7 2 6H6l-2-7M22 9v6" /></>,
  calculator: <><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M8 6h8M8 11h1m6 0h1m-8 4h1m6 0h1m-8 4h1m6 0h1" /></>,
  palette: <><path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-3.7 1.5 1.5 0 0 1 1-2.8h2a4 4 0 0 0 4-4C21 6.4 17 3 12 3Z" /><circle cx="7.5" cy="10" r="1" fill="currentColor" /><circle cx="11" cy="7" r="1" fill="currentColor" /><circle cx="16" cy="8" r="1" fill="currentColor" /><circle cx="6.5" cy="15" r="1" fill="currentColor" /></>,
  users: <><circle cx="9" cy="7" r="3.5" /><path d="M2 21v-2a7 7 0 0 1 14 0v2H2Zm14-17a3.5 3.5 0 0 1 0 7m2 4a6 6 0 0 1 4 6" /></>,
  more: <><circle cx="5" cy="12" r="1.4" fill="currentColor" /><circle cx="12" cy="12" r="1.4" fill="currentColor" /><circle cx="19" cy="12" r="1.4" fill="currentColor" /></>,
  sparkles: <><path d="m10 3 2.5 6.5L19 12l-6.5 2.5L10 21l-2.5-6.5L1 12l6.5-2.5L10 3Z" fill="currentColor" stroke="none" /><path d="m20 1 .9 3.1L24 5l-3.1.9L20 9l-.9-3.1L16 5l3.1-.9L20 1Z" fill="currentColor" stroke="none" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="14" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12a25 25 0 0 0 18 0M12 11v4" /></>,
  match: <><rect x="3" y="7" width="17" height="14" rx="3" /><path d="M9 7V5h6v2M17 2v6m-3-3h6M12 12l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Z" /></>,
  document: <><path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" /><path d="M14 2v6h6M8 12h8m-8 4h6" /></>,
  shield: <><path d="m12 2 9 4v6c0 5-6 8.5-9 10-3-1.5-9-5-9-10V6l9-4Z" /><path d="m8 12 3 3 5-6" /></>,
  star: <path d="m12 2 3.1 6.3L22 9.4l-5 4.9 1.2 6.9-6.2-3.3-6.2 3.3L7 14.3 2 9.4l6.9-1.1L12 2Z" fill="currentColor" />,
  bookmark: <path d="M6 3h12v19l-6-4-6 4V3Z" />,
  money: <><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M15 8h-4a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9m3-10v12" /></>,
  building: <><path d="M4 22V8h7m0 14V2h9v20M2 22h20M7 12v1m0 4v1m8-12h1m-1 4h1m-1 4h1m-2 8v-4h3v4" /></>,
}

export default function HomeIcon({ name, className = '' }: { name: HomeIconName; className?: string }) {
  return <svg className={`home-icon ${className}`} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}
