// "Journal" page: lines of data/logs/app.log streamed by /api/logs/stream.

export type LogLevel = 'error' | 'warning' | 'info' | 'access' | 'other'

export interface LogLine {
  id: number
  text: string
  level: LogLevel
}

export type LevelFilter = 'all' | 'warning' | 'error'

/** Lines kept in the page (older ones are dropped). */
export const MAX_LINES = 3000

// "2026-10-11 10:21:51,797 ERROR multitracker.service: ..." (app) or "... logic-worker WARNING ..." (worker)
const STAMPED = /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d[,.]\d+ (?:[\w.-]+ )?(CRITICAL|ERROR|WARNING|INFO|DEBUG)\b/
// uvicorn's access log: 'INFO:     192.168.1.13:56831 - "GET /api/slots HTTP/1.1" 200 OK'
const ACCESS = /^INFO:\s+\S+ - "/
// uvicorn / Archipelago messages without a timestamp: "ERROR:    ...", "WARNING:root:..."
const BARE = /^(CRITICAL|ERROR|WARNING|INFO|DEBUG):/

function fromName(name: string): LogLevel {
  if (name === 'CRITICAL' || name === 'ERROR') return 'error'
  if (name === 'WARNING') return 'warning'
  return 'info'
}

/** Level of a line; traceback lines and indented continuations take the level of the line before. */
export function levelOf(text: string, previous: LogLevel | null): LogLevel {
  const stamped = STAMPED.exec(text)
  if (stamped) return fromName(stamped[1])
  if (ACCESS.test(text)) return 'access'
  const bare = BARE.exec(text)
  if (bare) return fromName(bare[1])
  if (text.startsWith('Traceback (most recent call last)')) return 'error'
  const continuation = /^\s/.test(text) || /^[\w.]*(Error|Exception|Warning)\b.*:/.test(text)
  if (continuation && (previous === 'error' || previous === 'warning')) return previous
  return 'other'
}

export class LogBuffer {
  lines: LogLine[] = []
  private nextId = 0
  private last: LogLevel | null = null

  /** Replace everything (first batch of a stream: the page reconnected or opened). */
  reset(texts: string[]): void {
    this.lines = []
    this.last = null
    this.append(texts)
  }

  append(texts: string[]): void {
    for (const text of texts) {
      const level = levelOf(text, this.last)
      this.last = level
      this.lines.push({ id: this.nextId++, text, level })
    }
    if (this.lines.length > MAX_LINES) this.lines.splice(0, this.lines.length - MAX_LINES)
  }
}

export function filterLines(
  lines: LogLine[],
  opts: { level: LevelFilter; showAccess: boolean; search: string },
): LogLine[] {
  const q = opts.search.trim().toLowerCase()
  return lines.filter((l) => {
    if (opts.level === 'error' && l.level !== 'error') return false
    if (opts.level === 'warning' && l.level !== 'error' && l.level !== 'warning') return false
    if (!opts.showAccess && l.level === 'access') return false
    return !q || l.text.toLowerCase().includes(q)
  })
}
