import { useEffect, useState } from 'react'
import { api, type Organization } from '../api'

let cached: Organization | null = null

export function useOrg() {
  const [org, setOrg] = useState<Organization | null>(cached)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!cached)

  useEffect(() => {
    if (cached) return
    let alive = true
    api
      .ensureDemoOrg()
      .then((o) => {
        cached = o
        if (alive) setOrg(o)
      })
      .catch((e: Error) => {
        if (alive) setError(e.message)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  return { org, error, loading }
}
