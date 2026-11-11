// Updates from the app (backend/multitracker/updater.py, D25): the portable Windows build follows the GitHub
// releases, a git checkout (the Pi) follows origin/main.

export interface UpdateStatus {
  mode?: string
  state: 'running' | 'restarting' | 'done' | 'error'
  step?: string
  message?: string
  from?: string | null
  to?: string | null
  /** git: the release of from / to, when that commit is exactly one */
  from_release?: string
  to_release?: string
  /** epoch seconds */
  at?: number
  progress?: { done: number; total: number }
}

export interface UpdateCommit {
  commit: string
  date: number
  subject: string
  release?: string
}

export interface UpdateInfo {
  mode: 'portable' | 'git' | 'none'
  /** git: running = the commit this app started on, when the checkout moved since */
  current: {
    version: string | null
    commit?: string
    date?: number
    running?: string
    /** git: the release tag of the commit (v0.2.23), when it is exactly one */
    release?: string
    running_release?: string
  }
  latest: null | {
    version: string
    /** portable: release page and notes */
    url?: string | null
    notes?: string
    published_at?: string | null
    /** git: commits on origin/main not here yet */
    behind?: number
    /** git: origin/main is exactly this release */
    release?: string
    commits?: UpdateCommit[]
  }
  available: boolean
  /** why the update cannot run from the app (git: local commits, other branch) */
  blocked: string | null
  checked_at: number | null
  check_error: string | null
  running: boolean
  status: UpdateStatus | null
  /** server clock (epoch seconds): the status times are compared with it, never with the browser's clock */
  now?: number
}

/** A commit with its release: « v0.2.23 (6835c3b) » when it is exactly a release, else the commit alone. */
export function withRelease(commit: string | null | undefined, release?: string | null): string {
  if (!commit) return release ?? ''
  return release ? `${release} (${commit})` : commit
}

/** The installed version: the release and its commit on the Pi when it is one, else as git describes it. */
export function currentLabel(info: UpdateInfo): string {
  const c = info.current
  if (info.mode === 'git' && c.release && c.commit) return withRelease(c.commit, c.release)
  return c.version ?? 'inconnue'
}

export function latestLabel(info: UpdateInfo): string {
  const l = info.latest
  if (!l) return ''
  if (info.mode === 'git') {
    const n = l.behind ?? 0
    const count = n === 1 ? '1 nouveau commit sur main' : `${n} nouveaux commits sur main`
    return l.release ? `${withRelease(l.version, l.release)}, ${count}` : count
  }
  return `version ${l.version}`
}

/** What the page does while an update started at `startedAt` (epoch seconds) runs. */
export type Phase = { kind: 'waiting'; text: string } | { kind: 'done' } | { kind: 'error'; text: string }

export function phaseOf(info: UpdateInfo | null, startedAt: number): Phase {
  const st = info?.status
  // a status older than the click belongs to a previous update (5 s of slack for the clocks)
  if (!info || !st || (st.at ?? 0) < startedAt - 5) return { kind: 'waiting', text: 'Redémarrage de l’app…' }
  if (st.state === 'done') return { kind: 'done' }
  if (st.state === 'error') return { kind: 'error', text: st.message || `échec à l’étape « ${st.step} »` }
  if (st.state === 'restarting') return { kind: 'waiting', text: 'Redémarrage de l’app…' }
  const p = st.progress
  const pct = p && p.total ? ` ${Math.floor((p.done * 100) / p.total)} %` : ''
  return { kind: 'waiting', text: `${st.step ?? 'Mise à jour'}…${pct}` }
}

const DISMISS_KEY = 'amt-update-dismissed'

export function loadDismissed(): string {
  try {
    return localStorage.getItem(DISMISS_KEY) ?? ''
  } catch {
    return ''
  }
}

export function saveDismissed(version: string): void {
  try {
    localStorage.setItem(DISMISS_KEY, version)
  } catch {
    /* private mode */
  }
}

export const UPDATE_ANCHOR = 'mises-a-jour'

// « Mise à jour installée » : the version this browser last saw, to say once that the app changed.
const SEEN_KEY = 'amt-seen-version'

/** What actually runs: the release (portable) or the commit the app started on (git). */
export function runningId(info: UpdateInfo): string | null {
  if (info.mode === 'git') return info.current.running ?? info.current.commit ?? null
  return info.current.version
}

export function loadSeenVersion(): string {
  try {
    return localStorage.getItem(SEEN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function saveSeenVersion(id: string): void {
  try {
    localStorage.setItem(SEEN_KEY, id)
  } catch {
    /* private mode */
  }
}

/** Release notes of the running version, when the server has them (portable: latest release = this one). */
export function installedNotes(info: UpdateInfo): { notes: string; url: string | null } | null {
  const l = info.latest
  if (info.mode !== 'portable' || !l || l.version !== info.current.version) return null
  return { notes: (l.notes ?? '').trim(), url: l.url ?? null }
}

/** Markdown of a release, as plain lines: headings and list items without their marks. */
export function noteLines(md: string): { text: string; heading: boolean }[] {
  return md
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      const heading = /^#{1,6}\s/.test(l)
      const text = l.replace(/^#{1,6}\s+/, '').replace(/^[-*]\s+/, '• ').replace(/\*\*(.+?)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1')
      return { text, heading }
    })
}
