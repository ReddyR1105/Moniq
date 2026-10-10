import { useEffect, useState } from 'react'

export class ApiError extends Error {}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status}).`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((e: {loc: string[]; msg: string}) => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('; ')
    } catch { /* Keep the HTTP error when an upstream response is not JSON. */ }
    throw new ApiError(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function useResource<T>(path: string, revision: number) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    api<T>(path, { signal: controller.signal }).then(setData).catch((e: Error) => {
      if (e.name !== 'AbortError') setError(e.message || 'Could not connect to the local backend.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [path, revision])
  return { data, error, loading }
}

export const dollars = (amount: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
export const title = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)
export const prettyDate = (day: string, options: Intl.DateTimeFormatOptions = {month: 'short', day: 'numeric'}) => new Date(`${day}T12:00:00`).toLocaleDateString('en-US', options)
export const localDate = () => new Intl.DateTimeFormat('en-CA', {timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date())
export const errorText = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.'
