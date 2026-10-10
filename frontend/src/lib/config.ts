import type { SlotSummary } from './types'

export interface ConfigSlot {
  name: string
  game: string
  owner?: string | null
  yaml?: string | null
}
export interface ConfigResponse {
  room_url: string
  server: string
  has_password: boolean
  slots: ConfigSlot[]
  player_yamls: string[]
}
export interface DiscoverResponse {
  room_url: string
  server: string
  players: { name: string; game: string }[]
}
export interface PutConfigBody {
  room_url?: string
  server?: string
  password?: string | null
  slots: { name: string; game: string; owner: string | null; yaml: string | null }[]
}

export interface SlotRow {
  name: string
  game: string
  checked: boolean
  yaml: string // '' = aucun
  owner: string
}

/** Merge discovered players with currently configured slots (configured ones are pre-checked and keep yaml/owner). */
export function mergeRows(
  configured: ConfigSlot[],
  discovered: { name: string; game: string }[] | null,
): SlotRow[] {
  const cfg = new Map(configured.map((s) => [s.name, s]))
  const rows: SlotRow[] = []
  const seen = new Set<string>()
  for (const p of discovered ?? []) {
    if (seen.has(p.name)) continue
    seen.add(p.name)
    const c = cfg.get(p.name)
    rows.push({ name: p.name, game: p.game || c?.game || '', checked: !!c, yaml: c?.yaml ?? '', owner: c?.owner ?? '' })
  }
  for (const c of configured) {
    if (seen.has(c.name)) continue
    rows.push({ name: c.name, game: c.game, checked: true, yaml: c.yaml ?? '', owner: c.owner ?? '' })
  }
  return rows
}

export interface PasswordInput {
  value: string
  clear: boolean
}
/** null = keep the current password, '' = erase it. */
export function passwordPayload(p: PasswordInput): string | null {
  if (p.clear) return ''
  return p.value === '' ? null : p.value
}

export function buildPutBody(opts: {
  roomUrl: string
  server: string
  password: PasswordInput
  rows: SlotRow[]
}): PutConfigBody {
  const body: PutConfigBody = {
    password: passwordPayload(opts.password),
    slots: opts.rows
      .filter((r) => r.checked)
      .map((r) => ({ name: r.name, game: r.game, owner: r.owner.trim() || null, yaml: r.yaml || null })),
  }
  const url = opts.roomUrl.trim()
  const server = opts.server.trim()
  if (url) body.room_url = url
  else if (server) body.server = server
  return body
}

export function checkByName(rows: SlotRow[], needle: string, value = true): SlotRow[] {
  const n = needle.trim().toLowerCase()
  if (!n) return rows
  return rows.map((r) => (r.name.toLowerCase().includes(n) ? { ...r, checked: value } : r))
}
export const setAll = (rows: SlotRow[], value: boolean): SlotRow[] => rows.map((r) => ({ ...r, checked: value }))

// ---- multi-player filter ----
export const NO_OWNER = '__none__'
export const ALL_OWNERS = '__all__'

export function distinctOwners(slots: Pick<SlotSummary, 'owner'>[]): string[] {
  return [...new Set(slots.map((s) => s.owner).filter((o): o is string => !!o))].sort((a, b) => a.localeCompare(b))
}
export function hasNoOwner(slots: Pick<SlotSummary, 'owner'>[]): boolean {
  return slots.some((s) => !s.owner)
}
/** Chips are only offered with >= 2 distinct owners. */
export function showOwnerFilter(slots: Pick<SlotSummary, 'owner'>[]): boolean {
  return distinctOwners(slots).length >= 2
}
export function filterByOwner<T extends Pick<SlotSummary, 'owner'>>(slots: T[], choice: string): T[] {
  if (choice === ALL_OWNERS || !showOwnerFilter(slots)) return slots
  if (choice === NO_OWNER) return slots.filter((s) => !s.owner)
  return slots.filter((s) => s.owner === choice)
}

const KEY = 'amt-owner'
export function loadOwnerChoice(): string {
  try {
    return localStorage.getItem(KEY) || ALL_OWNERS
  } catch {
    return ALL_OWNERS
  }
}
export function saveOwnerChoice(v: string): void {
  try {
    localStorage.setItem(KEY, v)
  } catch {
    /* ignore */
  }
}
