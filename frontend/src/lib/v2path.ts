// The v2 interface ("Observatoire") lives at /v2, next to the v1 at /.
export function isV2Path(pathname: string): boolean {
  return pathname === '/v2' || pathname.startsWith('/v2/')
}
export function v2Href(hash: string): string {
  return '/v2' + hash
}
export function v1Href(hash: string): string {
  return '/' + hash
}
