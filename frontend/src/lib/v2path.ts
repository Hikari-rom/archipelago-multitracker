// The v2 interface ("Observatoire") lives at /, the v1 at /v1. /v2 is the old address of the v2: still served, then
// shown as / (bookmarks made before the switch).
export function isV1Path(pathname: string): boolean {
  return pathname === '/v1' || pathname.startsWith('/v1/')
}
export function isOldV2Path(pathname: string): boolean {
  return pathname === '/v2' || pathname.startsWith('/v2/')
}
export function v2Href(hash: string): string {
  return '/' + hash
}
export function v1Href(hash: string): string {
  return '/v1' + hash
}
