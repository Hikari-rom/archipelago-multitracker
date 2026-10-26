// "Plus actif" with a 6 s "Annuler".
import { reactive } from 'vue'
import type { ActivityOverrides } from '../../lib/logic'
import { cloneActivity, restoreActivity, setInactive, tracker } from '../../stores/tracker'

export const UNDO_MS = 6000
export const undo = reactive({ message: '', prev: null as ActivityOverrides | null })
let timer: ReturnType<typeof setTimeout> | undefined

export function clearUndo(): void {
  clearTimeout(timer)
  undo.message = ''
  undo.prev = null
}

export function dismissWithUndo(name: string, game: string): void {
  const prev = cloneActivity(tracker.activity)
  const manual = tracker.activity.mode === 'manual'
  setInactive(name)
  clearTimeout(timer)
  undo.prev = prev
  undo.message = manual ? `${game} n'est plus actif.` : `${game} n'est plus actif jusqu'à son prochain check.`
  timer = setTimeout(clearUndo, UNDO_MS)
}

export function undoLast(): void {
  if (undo.prev) restoreActivity(undo.prev)
  clearUndo()
}
