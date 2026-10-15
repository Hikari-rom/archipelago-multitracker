// "Plus actif" with a 6 s "Annuler".
import { reactive } from 'vue'
import type { ActivityOverrides } from '../../lib/logic'
import { restoreActivity, setInactive, tracker } from '../../stores/tracker'

export const UNDO_MS = 6000
export const undo = reactive({ message: '', prev: null as ActivityOverrides | null })
let timer: ReturnType<typeof setTimeout> | undefined

export function clearUndo(): void {
  clearTimeout(timer)
  undo.message = ''
  undo.prev = null
}

export function dismissWithUndo(name: string, game: string): void {
  const prev = { pinned: tracker.activity.pinned ? { ...tracker.activity.pinned } : null, dismissed: { ...tracker.activity.dismissed } }
  setInactive(name)
  clearTimeout(timer)
  undo.prev = prev
  undo.message = `${game} n'est plus actif jusqu'à son prochain check.`
  timer = setTimeout(clearUndo, UNDO_MS)
}

export function undoLast(): void {
  if (undo.prev) restoreActivity(undo.prev)
  clearUndo()
}
