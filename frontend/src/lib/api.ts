import type { ConfigResponse, DiscoverResponse, PutConfigBody } from './config'
import type { SlotDetail, SlotSummary } from './types'

export interface SlotsResponse {
  server: string
  slots: SlotSummary[]
  room_url?: string | null
  room_error?: string | null
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `Erreur ${r.status}`
    try {
      const b = await r.json()
      if (b?.detail) msg = String(b.detail)
    } catch {
      /* ignore */
    }
    throw new Error(msg)
  }
  return r.json() as Promise<T>
}

export interface MockApi {
  getSlot(name: string): Promise<SlotDetail>
  markSeen(name: string): Promise<{ seen: number }>
  getConfig?(): Promise<ConfigResponse>
  discover?(url: string): Promise<DiscoverResponse>
  putConfig?(b: PutConfigBody): Promise<unknown>
}
let mock: MockApi | null = null
export function installMock(m: MockApi): void {
  mock = m
}

export const getSlots = () => fetch('/api/slots').then((r) => json<SlotsResponse>(r))

export const getSlot = (name: string) =>
  mock ? mock.getSlot(name) : fetch(`/api/slots/${encodeURIComponent(name)}`).then((r) => json<SlotDetail>(r))

export const markSeen = (name: string) =>
  mock ? mock.markSeen(name) : fetch(`/api/slots/${encodeURIComponent(name)}/seen`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  }).then((r) => json<{ seen: number }>(r))

const jsonInit = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const getConfig = () =>
  mock?.getConfig ? mock.getConfig() : fetch('/api/config').then((r) => json<ConfigResponse>(r))

export const discover = (url: string) =>
  mock?.discover ? mock.discover(url) : fetch('/api/discover', jsonInit('POST', { url })).then((r) => json<DiscoverResponse>(r))

export const putConfig = (b: PutConfigBody) =>
  mock?.putConfig ? mock.putConfig(b) : fetch('/api/config', jsonInit('PUT', b)).then((r) => json<unknown>(r))
