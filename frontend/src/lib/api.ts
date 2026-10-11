import type { ConfigResponse, DiscoverResponse, ProbeResponse, PutConfigBody, UploadResponse } from './config'
import type { RecentItem, SlotDetail, SlotSummary } from './types'

export interface SlotsResponse {
  server: string
  slots: SlotSummary[]
  room_url?: string | null
  room_error?: string | null
  room_sleeping?: boolean
  /** server clock, epoch seconds */
  now?: number
  wake_room?: boolean
}

export class HttpError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
  }
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
    throw new HttpError(msg, r.status)
  }
  return r.json() as Promise<T>
}

export interface MockApi {
  getSlot(name: string): Promise<SlotDetail>
  markSeen(name: string): Promise<{ seen: number }>
  recentItems?(): Promise<{ items: RecentItem[] }>
  getConfig?(): Promise<ConfigResponse>
  discover?(url: string, wake?: boolean): Promise<DiscoverResponse>
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

export const getRecentItems = () =>
  mock?.recentItems ? mock.recentItems() : fetch('/api/items/recent').then((r) => json<{ items: RecentItem[] }>(r))

const jsonInit = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const getConfig = () =>
  mock?.getConfig ? mock.getConfig() : fetch('/api/config').then((r) => json<ConfigResponse>(r))

export const discover = (url: string, wake = false) =>
  mock?.discover
    ? mock.discover(url, wake)
    : fetch('/api/discover', jsonInit('POST', { url, wake })).then((r) => json<DiscoverResponse>(r))

export const testConnection = (b: { room_url?: string; server?: string; password: string | null; slot: string }) =>
  fetch('/api/config/test', jsonInit('POST', b)).then((r) => json<ProbeResponse>(r))

export const uploadYaml = (filename: string, content: string, overwrite = false) =>
  fetch('/api/yamls', jsonInit('POST', { filename, content, overwrite })).then((r) => json<UploadResponse>(r))

export const restoreConfig = () => fetch('/api/config/restore', jsonInit('POST', {})).then((r) => json<unknown>(r))

export const wakeRoom = () =>
  fetch('/api/room/wake', jsonInit('POST', {})).then((r) =>
    json<{ ok: boolean; server: string | null; room_error: string | null }>(r),
  )

export const putConfig = (b: PutConfigBody) =>
  mock?.putConfig ? mock.putConfig(b) : fetch('/api/config', jsonInit('PUT', b)).then((r) => json<unknown>(r))
