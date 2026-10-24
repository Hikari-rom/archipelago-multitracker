// Apworlds imported from the user's own Archipelago install (D27).

export type ImportStatus = 'imported' | 'shipped' | 'not_needed' | 'unreadable' | 'duplicate'
export type VersionStatus = 'room' | 'other' | 'not_loaded' | 'not_in_room' | 'unknown'

export interface ApworldFile {
  file: string
  game: string | null
  in_room?: boolean | null
  version?: VersionStatus
}
export interface ImportRow {
  file: string
  game: string | null
  status: ImportStatus
}
export interface ApworldsInfo {
  dir: string
  default_source: string | null
  files: ApworldFile[]
  report?: ImportRow[]
}

export const IMPORT_LABELS: Record<ImportStatus, string> = {
  imported: 'importé',
  shipped: 'déjà fourni par l’app',
  not_needed: 'pas utile à l’app',
  unreadable: 'illisible',
  duplicate: 'en double',
}

export const VERSION_LABELS: Record<VersionStatus, { text: string; tone: 'ok' | 'warn' | 'muted' }> = {
  room: { text: 'version de la room', tone: 'ok' },
  other: { text: 'pas la version de la room : logique refusée', tone: 'warn' },
  not_loaded: { text: 'ne se charge pas (version d’Archipelago ?)', tone: 'warn' },
  not_in_room: { text: 'pas dans la room', tone: 'muted' },
  unknown: { text: 'inconnue tant que la room n’est pas connectée', tone: 'muted' },
}

const PLURALS: Record<ImportStatus, string> = {
  imported: 'importés',
  shipped: 'déjà fournis par l’app',
  not_needed: 'pas utiles à l’app',
  unreadable: 'illisibles',
  duplicate: 'en double',
}

/** "3 importés, 40 déjà fournis par l’app, 1 pas dans la room" */
export function importSummary(rows: ImportRow[]): string {
  if (!rows.length) return 'aucun fichier .apworld dans ce dossier'
  const counts = new Map<ImportStatus, number>()
  for (const r of rows) counts.set(r.status, (counts.get(r.status) ?? 0) + 1)
  return (Object.keys(IMPORT_LABELS) as ImportStatus[])
    .filter((s) => counts.has(s))
    .map((s) => `${counts.get(s)} ${counts.get(s) === 1 ? IMPORT_LABELS[s] : PLURALS[s]}`)
    .join(', ')
}
