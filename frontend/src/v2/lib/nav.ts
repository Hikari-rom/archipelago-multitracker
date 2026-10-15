import { ref } from 'vue'
import { setView } from '../../stores/tracker'

/** Tab of the History page, set from the dashboard ("Tout voir →" opens "Items reçus"). */
export const historyTab = ref<'sent' | 'received'>('sent')
export function openHistory(tab: 'sent' | 'received'): void {
  historyTab.value = tab
  setView('history')
}
