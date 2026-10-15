<script setup lang="ts">
import { computed, ref } from 'vue'
import { wakeRoom } from '../../lib/api'
import { refreshMeta, tracker } from '../../stores/tracker'
import { hhmm } from '../lib/card'

const waking = ref(false)
const wakeError = ref('')
const since = computed(() => {
  const t = Math.max(0, ...tracker.slots.map((s) => s.updated_at ?? 0))
  return t ? hhmm(t) : ''
})
async function onWake() {
  waking.value = true
  wakeError.value = ''
  try {
    const r = await wakeRoom()
    if (!r.ok && r.room_error) wakeError.value = r.room_error
  } catch (e) {
    wakeError.value = e instanceof Error ? e.message : String(e)
  } finally {
    await refreshMeta()
    waking.value = false
  }
}
</script>

<template>
  <div v-if="tracker.roomError" role="alert" class="mx-auto mt-3 flex max-w-[1440px] flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-3 text-sm">
    <span aria-hidden="true" class="text-xl text-logic">☾</span>
    <p v-if="tracker.roomSleeping" class="min-w-0 flex-1">
      <strong>La room est endormie</strong>
      <span class="text-muted-foreground"> archipelago.gg l'a arrêtée faute d'activité.<template v-if="since"> Les chiffres affichés datent de {{ since }}.</template></span>
    </p>
    <p v-else class="min-w-0 flex-1"><span class="text-error" aria-hidden="true">! </span>Room : {{ tracker.roomError }}</p>
    <button v-if="tracker.roomSleeping" type="button" class="min-h-9 rounded-lg bg-primary max-[699px]:min-h-11 px-4 font-semibold text-primary-foreground disabled:opacity-60" :disabled="waking" @click="onWake">
      {{ waking ? 'Réveil…' : 'Réveiller maintenant' }}
    </button>
    <span v-if="wakeError" class="text-error">{{ wakeError }}</span>
  </div>
</template>
