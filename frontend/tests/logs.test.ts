import { describe, expect, it } from 'vitest'
import { LogBuffer, MAX_LINES, filterLines, levelOf } from '../src/lib/logs'

describe('log lines', () => {
  it('levels of the app, the worker, uvicorn and tracebacks', () => {
    expect(levelOf('2026-10-11 10:21:51,797 ERROR multitracker.service: logic failed for romain_mc', null)).toBe('error')
    expect(levelOf('2026-10-11 10:21:53,108 logic-worker WARNING Spicy Meatball Overdrive has more items', null)).toBe('warning')
    expect(levelOf('2026-10-11 10:21:28,117 INFO multitracker.ap.tracker: tracker romain_mc: connected', null)).toBe('info')
    expect(levelOf('INFO:     192.168.1.13:56831 - "GET /api/slots/romain_kh2 HTTP/1.1" 200 OK', null)).toBe('access')
    expect(levelOf('INFO:     Application startup complete.', null)).toBe('info')
    expect(levelOf('ERROR:root:Could not load world WorldSource(ffmq)', null)).toBe('error')
    expect(levelOf('Traceback (most recent call last):', 'info')).toBe('error')
    expect(levelOf('  File "service.py", line 201, in _logic_loop', 'error')).toBe('error')
    expect(levelOf("ModuleNotFoundError: No module named 'worlds'", 'error')).toBe('error')
    expect(levelOf('  indented after an info line', 'info')).toBe('other')
    expect(levelOf('Generating early', 'error')).toBe('other')
  })

  it('buffer keeps the newest lines and restarts on reset', () => {
    const b = new LogBuffer()
    b.reset(['2026-10-11 10:00:00,000 ERROR x: boom', '  File "a.py"'])
    expect(b.lines.map((l) => l.level)).toEqual(['error', 'error'])
    b.append(Array.from({ length: MAX_LINES }, (_, i) => `line ${i}`))
    expect(b.lines.length).toBe(MAX_LINES)
    expect(b.lines[b.lines.length - 1].text).toBe(`line ${MAX_LINES - 1}`)
    const ids = b.lines.map((l) => l.id)
    expect(new Set(ids).size).toBe(ids.length)
    b.reset(['fresh'])
    expect(b.lines.map((l) => l.text)).toEqual(['fresh'])
  })

  it('filters by level, HTTP requests and text', () => {
    const b = new LogBuffer()
    b.reset([
      '2026-10-11 10:00:00,000 ERROR x: boom',
      '2026-10-11 10:00:01,000 WARNING x: hmm',
      '2026-10-11 10:00:02,000 INFO x: Romain_MC connected',
      'INFO:     1.2.3.4:5 - "GET /api/slots HTTP/1.1" 200 OK',
    ])
    const texts = (o: Parameters<typeof filterLines>[1]) => filterLines(b.lines, o).map((l) => l.text.slice(24, 31))
    expect(texts({ level: 'all', showAccess: false, search: '' })).toEqual(['ERROR x', 'WARNING', 'INFO x:'])
    expect(filterLines(b.lines, { level: 'all', showAccess: true, search: '' }).length).toBe(4)
    expect(texts({ level: 'warning', showAccess: true, search: '' })).toEqual(['ERROR x', 'WARNING'])
    expect(texts({ level: 'error', showAccess: true, search: '' })).toEqual(['ERROR x'])
    expect(texts({ level: 'all', showAccess: false, search: ' romain_mc ' })).toEqual(['INFO x:'])
  })
})
