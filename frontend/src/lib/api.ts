import type { ConfigResponse, DiscoverResponse, ProbeResponse, PutConfigBody, UploadResponse } from './config'
import type { UpdateInfo } from './update'
import type { ApworldsInfo } from './apworlds'
import type {
  HistoryPage, ReceivedEntry, RecentItem, RoomFeedActivity, RoomFeedChecksPage, RoomFeedStatus, RoomFeedSummary,
  SentCheck, SlotDetail, SlotSummary,
} from './types'

export interface SlotsResponse {
  server: string
  slots: SlotSummary[]
  room_url?: string | null
  room_error?: string | null
  room_sleeping?: boolean
  /** server clock, epoch seconds */
  now?: number
  wake_room?: boolean
  /** the room-wide dashboard is enabled (Configuration) */
  room_dashboard?: boolean
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
  history?(kind: 'sent' | 'received', slots: string[], limit: number, offset: number): Promise<HistoryPage<any>>
  getConfig?(): Promise<ConfigResponse>
  discover?(url: string, wake?: boolean): Promise<DiscoverResponse>
  putConfig?(b: PutConfigBody): Promise<unknown>
  getRoomFeed?(): Promise<RoomFeedStatus>
  getRoomFeedSummary?(): Promise<RoomFeedSummary>
  getRoomFeedChecks?(params: RoomFeedChecksParams): Promise<RoomFeedChecksPage>
  getRoomFeedActivity?(bucket: 'hour' | 'day', player?: string): Promise<RoomFeedActivity>
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

export function getHistory(kind: 'sent', slots: string[], limit: number, offset: number): Promise<HistoryPage<SentCheck>>
export function getHistory(kind: 'received', slots: string[], limit: number, offset: number): Promise<HistoryPage<ReceivedEntry>>
export function getHistory(kind: 'sent' | 'received', slots: string[], limit = 200, offset = 0) {
  const q = new URLSearchParams({ kind, limit: String(limit), offset: String(offset) })
  for (const s of slots) q.append('slot', s)
  return mock?.history ? mock.history(kind, slots, limit, offset) : fetch(`/api/history?${q}`).then((r) => json<HistoryPage<SentCheck | ReceivedEntry>>(r))
}

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

export interface RoomFeedChecksParams {
  limit?: number
  offset?: number
  /** grouped player */
  player?: string
  /** name of the slot that did the check */
  slot?: string
  game?: string
}

export const getRoomFeed = () =>
  mock?.getRoomFeed ? mock.getRoomFeed() : fetch('/api/roomfeed').then((r) => json<RoomFeedStatus>(r))

export const getRoomFeedSummary = () =>
  mock?.getRoomFeedSummary ? mock.getRoomFeedSummary() : fetch('/api/roomfeed/summary').then((r) => json<RoomFeedSummary>(r))

export function getRoomFeedChecks(params: RoomFeedChecksParams = {}): Promise<RoomFeedChecksPage> {
  if (mock?.getRoomFeedChecks) return mock.getRoomFeedChecks(params)
  const q = new URLSearchParams()
  if (params.limit !== undefined) q.set('limit', String(params.limit))
  if (params.offset !== undefined) q.set('offset', String(params.offset))
  if (params.player) q.set('player', params.player)
  if (params.slot) q.set('slot', params.slot)
  if (params.game) q.set('game', params.game)
  return fetch(`/api/roomfeed/checks?${q}`).then((r) => json<RoomFeedChecksPage>(r))
}

export function getRoomFeedActivity(bucket: 'hour' | 'day', player?: string): Promise<RoomFeedActivity> {
  if (mock?.getRoomFeedActivity) return mock.getRoomFeedActivity(bucket, player)
  const q = new URLSearchParams({ bucket })
  if (player) q.set('player', player)
  return fetch(`/api/roomfeed/activity?${q}`).then((r) => json<RoomFeedActivity>(r))
}

export const getUpdate = () => fetch('/api/update').then((r) => json<UpdateInfo>(r))

export const checkUpdate = () => fetch('/api/update/check', jsonInit('POST', {})).then((r) => json<UpdateInfo>(r))

export const applyUpdate = () => fetch('/api/update/apply', jsonInit('POST', {})).then((r) => json<UpdateInfo>(r))

export const getApworlds = () => fetch('/api/apworlds').then((r) => json<ApworldsInfo>(r))

export const importApworlds = (path: string) =>
  fetch('/api/apworlds/import', jsonInit('POST', { path })).then((r) => json<ApworldsInfo>(r))

export const checkApworlds = () => fetch('/api/apworlds/check', jsonInit('POST', {})).then((r) => json<ApworldsInfo>(r))
