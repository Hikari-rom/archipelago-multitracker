import { describe, expect, it } from 'vitest'
import { isV2Path, v1Href, v2Href } from '../../src/lib/v2path'

describe('v2 path', () => {
  it('matches /v2 and below only', () => {
    expect(isV2Path('/v2')).toBe(true)
    expect(isV2Path('/v2/')).toBe(true)
    expect(isV2Path('/v2/anything')).toBe(true)
    expect(isV2Path('/')).toBe(false)
    expect(isV2Path('/v20')).toBe(false)
    expect(isV2Path('/assets/v2')).toBe(false)
  })
  it('keeps the hash when switching version', () => {
    expect(v2Href('#history')).toBe('/v2#history')
    expect(v2Href('')).toBe('/v2')
    expect(v1Href('#goals')).toBe('/#goals')
    expect(v1Href('')).toBe('/')
  })
})
