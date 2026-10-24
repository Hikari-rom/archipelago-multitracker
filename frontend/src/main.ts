import { isOldV2Path, isV1Path } from './lib/v2path'

function showLoadError(e: unknown): void {
  document.body.textContent = 'Impossible de charger l’interface : ' + String(e)
}

// Each version loads its own code and CSS: /v1 is the original interface, anything else the v2 « Observatoire ».
if (isV1Path(location.pathname)) void import('./v1').catch(showLoadError)
else {
  if (isOldV2Path(location.pathname)) history.replaceState(null, '', '/' + location.search + location.hash)
  void import('./v2/main').catch(showLoadError)
}
