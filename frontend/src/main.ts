import { isV2Path } from './lib/v2path'

function showLoadError(e: unknown): void {
  document.body.textContent = 'Impossible de charger l’interface : ' + String(e)
}

// Each version loads its own code and CSS: /v2 is the "Observatoire" interface, anything else the v1.
if (isV2Path(location.pathname)) void import('./v2/main').catch(showLoadError)
else void import('./v1').catch(showLoadError)
