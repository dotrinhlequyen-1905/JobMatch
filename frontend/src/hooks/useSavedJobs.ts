import { useEffect, useState } from 'react'

const SAVED_JOBS_KEY = 'jobmatch:saved-jobs'
const SAVED_JOBS_EVENT = 'jobmatch:saved-jobs-changed'

function readSavedJobs(fallback: number[] = []): number[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(SAVED_JOBS_KEY) ?? '[]')
    return Array.isArray(saved) ? saved.filter((id): id is number => typeof id === 'number' && Number.isSafeInteger(id) && id > 0) : []
  } catch { return fallback }
}

export default function useSavedJobs() {
  const [savedJobs, setSavedJobs] = useState(() => readSavedJobs())

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === SAVED_JOBS_KEY || event.key === null) setSavedJobs(readSavedJobs())
    }
    const onChange = (event: Event) => setSavedJobs((event as CustomEvent<number[]>).detail)
    window.addEventListener('storage', onStorage)
    window.addEventListener(SAVED_JOBS_EVENT, onChange)
    return () => {
      window.removeEventListener('storage', onStorage)
      window.removeEventListener(SAVED_JOBS_EVENT, onChange)
    }
  }, [])

  const toggleSaved = (id: number) => {
    const current = readSavedJobs(savedJobs)
    const next = current.includes(id) ? current.filter(savedId => savedId !== id) : [...current, id]
    setSavedJobs(next)
    try { localStorage.setItem(SAVED_JOBS_KEY, JSON.stringify(next)) } catch { /* Saving stays usable when browser storage is unavailable. */ }
    window.dispatchEvent(new CustomEvent<number[]>(SAVED_JOBS_EVENT, { detail: next }))
  }

  return { savedJobs, toggleSaved }
}
