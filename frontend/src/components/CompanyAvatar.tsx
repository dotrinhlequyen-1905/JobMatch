import { useEffect, useState } from 'react'

interface CompanyLogo {
  name: string
  aliases?: string[]
  logo_url: string
}

const PLACEHOLDER_URL = '/images/companies/company-placeholder.svg'
let companyLogos = new Map<string, string>()
let catalogRequest: Promise<Map<string, string>> | undefined

function normalizeCompanyName(name: string) {
  return name.toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '')
    .replace(/đ/g, 'd').replace(/[^\p{L}\p{N}]+/gu, ' ').trim()
}

function loadCompanyLogos() {
  catalogRequest ??= fetch('/images/companies/catalog.json')
    .then((response) => {
      if (!response.ok) throw new Error('Company logo catalog unavailable')
      return response.json() as Promise<{ companies: CompanyLogo[] }>
    })
    .then((catalog) => {
      const logos = new Map<string, string>()
      const ambiguousNames = new Set<string>()
      if (Array.isArray(catalog.companies)) {
        for (const company of catalog.companies) {
          if (typeof company.name !== 'string' || typeof company.logo_url !== 'string' || !company.logo_url.trim()) continue
          const names = [company.name, ...(Array.isArray(company.aliases) ? company.aliases : [])]
          for (const name of names) {
            if (typeof name !== 'string') continue
            const key = normalizeCompanyName(name)
            if (!key || ambiguousNames.has(key)) continue
            const logoUrl = company.logo_url.trim()
            if (logos.has(key) && logos.get(key) !== logoUrl) {
              logos.delete(key)
              ambiguousNames.add(key)
            } else logos.set(key, logoUrl)
          }
        }
      }
      companyLogos = logos
      return logos
    })
    .catch(() => companyLogos)
  return catalogRequest
}

interface AvatarProps { name: string; url?: string; size?: number }

function AvatarImage({ name, url, localUrl, size }: AvatarProps & { localUrl?: string }) {
  const [failedUrls, setFailedUrls] = useState<string[]>([])
  const customUrl = url?.trim() === PLACEHOLDER_URL ? undefined : url?.trim()
  const sources = [customUrl, localUrl, PLACEHOLDER_URL]
  const source = sources.find((candidate) => candidate && !failedUrls.includes(candidate)) ?? PLACEHOLDER_URL

  return (
    <img className="company-avatar" src={source} alt={`Logo ${name}`} loading="lazy" decoding="async"
      width={size} height={size} style={size ? { width: size, height: size } : undefined}
      onError={() => {
        if (source !== PLACEHOLDER_URL) setFailedUrls((failed) => failed.includes(source) ? failed : [...failed, source])
      }} />
  )
}

export default function CompanyAvatar({ name, url, size }: AvatarProps) {
  const [logos, setLogos] = useState(companyLogos)

  useEffect(() => {
    let active = true
    loadCompanyLogos().then((catalog) => { if (active) setLogos(catalog) })
    return () => { active = false }
  }, [])

  return <AvatarImage key={JSON.stringify([name, url])} name={name} url={url} size={size} localUrl={logos.get(normalizeCompanyName(name))} />
}
