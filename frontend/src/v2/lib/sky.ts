// Star field of the "Nuit" theme: two layers drifting upwards, generated once from a fixed seed.
export interface Star { x: number; y: number; size: number; opacity: number; twinkle: boolean; dur: number; delay: number }
export interface SkyLayer { stars: Star[]; duration: number }

function rng(seed: number) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return s / 2147483647
  }
}

function layer(rnd: () => number, count: number, size: [number, number], op: [number, number], twinkleShare: number, duration: number): SkyLayer {
  const stars = Array.from({ length: count }, () => ({
    x: rnd() * 100,
    y: rnd() * 50,
    size: size[0] + rnd() * (size[1] - size[0]),
    opacity: op[0] + rnd() * (op[1] - op[0]),
    twinkle: rnd() < twinkleShare,
    dur: 3 + rnd() * 5,
    delay: -rnd() * 8,
  }))
  return { stars, duration }
}

export function skyLayers(phone: boolean): SkyLayer[] {
  const rnd = rng(phone ? 29 : 11)
  return [
    layer(rnd, phone ? 55 : 150, [0.8, 1.3], [0.25, 0.6], 0.15, 260),
    layer(rnd, phone ? 14 : 34, [1.5, 2.4], [0.5, 0.9], 0.4, 150),
  ]
}
