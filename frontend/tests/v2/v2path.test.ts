import { describe, expect, it } from 'vitest'
import { isOldV2Path, isV1Path, v1Href, v2Href } from '../../src/lib/v2path'

describe('version paths', () => {
  it('serves the v1 at /v1 and below only', () => {
    expect(isV1Path('/v1')).toBe(true)
    expect(isV1Path('/v1/')).toBe(true)
    expect(isV1Path('/v1/anything')).toBe(true)
    expect(isV1Path('/')).toBe(false)
    expect(isV1Path('/v10')).toBe(false)
    expect(isV1Path('/assets/v1')).toBe(false)
  })
  it('recognises the old /v2 address', () => {
    expect(isOldV2Path('/v2')).toBe(true)
    expect(isOldV2Path('/v2/')).toBe(true)
    expect(isOldV2Path('/')).toBe(false)
    expect(isOldV2Path('/v20')).toBe(false)
  })
  it('keeps the hash when switching version', () => {
    expect(v2Href('#history')).toBe('/#history')
    expect(v2Href('')).toBe('/')
    expect(v1Href('#goals')).toBe('/v1#goals')
    expect(v1Href('')).toBe('/v1')
  })
})
