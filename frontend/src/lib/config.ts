import type { SlotSummary } from './types'

export interface ConfigSlot {
  name: string
  game: string
  owner?: string | null
  yaml?: string | null
}
export interface YamlPlayer {
  name: string
  game: string
}
export interface YamlEntry {
  path: string
  players: YamlPlayer[]
  error: string | null
}
export interface GameInfo {
  logic: boolean
  needs_yaml: boolean
}
export interface ConfigResponse {
  room_url: string | null
  server: string | null
  has_password: boolean
  wake_room?: boolean
  has_backup?: boolean
  slots: ConfigSlot[]
  player_yamls: string[]
  yamls?: YamlEntry[]
  games?: Record<string, GameInfo>
}
export interface DiscoverResponse {
  room_url: string
  server: string | null
  sleeping?: boolean
  players: { name: string; game: string }[]
}
export interface ProbeResponse {
  ok: boolean
  errors: string[]
  game?: string | null
  server?: string
  sleeping?: boolean
}
export interface UploadResponse {
  path: string
  players: YamlPlayer[]
  status: 'created' | 'replaced' | 'unchanged'
}
export interface PutConfigBody {
  room_url?: string
  server?: string
  password?: string | null
  wake_room?: boolean
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

/** After a discover: keep the user's current rows (edits included), add newly found players unchecked. */
export function mergeDiscovered(rows: SlotRow[], players: { name: string; game: string }[]): SlotRow[] {
  const have = new Set(rows.map((r) => r.name))
  const out = rows.map((r) => ({ ...r }))
  for (const p of players) {
    if (have.has(p.name)) continue
    have.add(p.name)
    out.push({ name: p.name, game: p.game, checked: false, yaml: '', owner: '' })
  }
  return out
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
  wakeRoom?: boolean
}): PutConfigBody {
  const body: PutConfigBody = {
    password: passwordPayload(opts.password),
    ...(opts.wakeRoom === undefined ? {} : { wake_room: opts.wakeRoom }),
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

// ---- yamls: slot <-> yaml association and per-slot diagnosis ----

/** Does a yaml `name` (which may use Archipelago's {player}/{PLAYER}/{number}/{NUMBER} placeholders) give this slot name? */
export function nameMatches(pattern: string, slot: string): boolean {
  if (!/\{(player|PLAYER|number|NUMBER)\}/.test(pattern)) return pattern === slot
  const parts = pattern.split(/\{(?:player|PLAYER|number|NUMBER)\}/)
  const re = parts.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\d*')
  return new RegExp(`^${re}$`).test(slot)
}

/** Yamls (no read error) holding a player document for this slot: same game and matching name. */
export function yamlCandidates(row: Pick<SlotRow, 'name' | 'game'>, yamls: YamlEntry[]): string[] {
  return yamls
    .filter((y) => !y.error && y.players.some((p) => p.game === row.game && nameMatches(p.name, row.name)))
    .map((y) => y.path)
}

/** Give a yaml to every row without one when exactly one yaml matches it. `check` also ticks those rows. */
export function autoAssociate(rows: SlotRow[], yamls: YamlEntry[], check = false): { rows: SlotRow[]; matched: number } {
  let matched = 0
  const out = rows.map((r) => {
    if (r.yaml) return r
    const c = yamlCandidates(r, yamls)
    if (c.length !== 1) return r
    matched++
    return { ...r, yaml: c[0], checked: check ? true : r.checked }
  })
  return { rows: out, matched }
}

export type DiagLevel = 'info' | 'warn' | 'error'
export interface Diag {
  level: DiagLevel
  text: string
}

export function diagnose(row: SlotRow, yamls: YamlEntry[], games: Record<string, GameInfo>): Diag[] {
  const out: Diag[] = []
  const info = games[row.game]
  if (!row.game) out.push({ level: 'info', text: 'jeu inconnu tant que la room n\'est pas découverte' })
  else if (!info) out.push({ level: 'info', text: 'pas d\'apworld : suivi des checks seulement' })
  else if (!info.logic) out.push({ level: 'info', text: 'logique pas encore validée pour ce jeu' })
  if (row.yaml) {
    const y = yamls.find((e) => e.path === row.yaml)
    if (!y) out.push({ level: 'warn', text: 'yaml introuvable dans config/players/' })
    else if (y.error) out.push({ level: 'error', text: `yaml illisible : ${y.error}` })
    else if (row.game && !y.players.some((p) => p.game === row.game)) {
      const other = [...new Set(y.players.map((p) => p.game))].join(', ')
      out.push({ level: 'error', text: `ce yaml est pour ${other}` })
    } else if (!y.players.some((p) => nameMatches(p.name, row.name))) {
      const names = y.players.map((p) => p.name).join(', ')
      out.push({ level: 'warn', text: `nom différent dans le yaml (${names})` })
    }
  } else if (info?.logic && info.needs_yaml) {
    out.push({ level: 'warn', text: 'yaml nécessaire pour la logique' })
  }
  return out
}

export interface RowFilter {
  text: string
  game: string // '' = all
  checkedOnly: boolean
}
export function filterRows(rows: SlotRow[], f: RowFilter): SlotRow[] {
  const n = f.text.trim().toLowerCase()
  return rows.filter(
    (r) =>
      (!n || r.name.toLowerCase().includes(n) || r.game.toLowerCase().includes(n)) &&
      (!f.game || r.game === f.game) &&
      (!f.checkedOnly || r.checked),
  )
}
/** Check/uncheck only the given (visible) rows. */
export function setChecked(rows: SlotRow[], names: Set<string>, value: boolean): SlotRow[] {
  return rows.map((r) => (names.has(r.name) ? { ...r, checked: value } : r))
}
export function distinctGames(rows: SlotRow[]): string[] {
  return [...new Set(rows.map((r) => r.game).filter(Boolean))].sort((a, b) => a.localeCompare(b))
}

/** "#config?room=https://..." or "?room=..." -> the room link to pre-fill, if any. */
export function roomFromLocation(hash: string, search: string): string {
  const q = hash.includes('?') ? hash.slice(hash.indexOf('?') + 1) : search.replace(/^\?/, '')
  try {
    return new URLSearchParams(q).get('room')?.trim() ?? ''
  } catch {
    return ''
  }
}

const PROBE_ERRORS: Record<string, string> = {
  InvalidPassword: 'mot de passe refusé',
  InvalidSlot: 'slot inconnu dans cette room',
  InvalidGame: 'jeu refusé par le serveur',
  IncompatibleVersion: 'version d\'Archipelago incompatible',
}
export function probeMessage(r: ProbeResponse, slot: string): string {
  if (r.ok) return `Connexion réussie (slot ${slot}${r.game ? `, ${r.game}` : ''}).`
  return `Échec : ${r.errors.map((e) => PROBE_ERRORS[e] ?? e).join(', ')}`
}

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
