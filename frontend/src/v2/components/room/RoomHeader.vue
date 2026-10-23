<script setup lang="ts">
import { computed } from 'vue'
import type { RoomFeedStatus, RoomFeedSummary } from '../../../lib/types'
import { hhmm } from '../../lib/card'
import { pct } from '../../lib/room'

const props = defineProps<{ status: RoomFeedStatus; room: RoomFeedSummary['room'] | null }>()

const stateLine = computed(() => {
  const s = props.status
  if (s.state === 'listening') return s.listening_since ? `En écoute depuis ${hhmm(s.listening_since)}` : 'En écoute'
  if (s.state === 'disconnected') return 'Déconnecté — les checks manqués seront rattrapés'
  if (s.state === 'error') return s.error || 'Erreur'
  return 'Démarrage…'
})
const isError = computed(() => props.status.state === 'error')
const pollLine = computed(() => {
  const s = props.status
  if (s.catchup_available === false) return 'Rattrapage indisponible sans lien de room'
  return s.last_poll_at ? `Dernier relevé ${hhmm(s.last_poll_at)}` : ''
})
</script>

<template>
  <div class="flex flex-col gap-3 rounded-[14px] border bg-card px-5 py-3">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
      <span
        data-state-line
        class="inline-flex min-w-0 max-w-full items-center gap-2 break-words"
        :class="isError ? 'rounded-lg bg-warn px-2 py-0.5 text-warn-foreground' : 'font-medium'"
      >
        <span v-if="!isError" class="size-2 shrink-0 rounded-full" :class="status.state === 'listening' ? 'bg-done' : 'bg-new'" aria-hidden="true" />
        <span class="min-w-0 break-words">{{ stateLine }}</span>
      </span>
      <span v-if="pollLine" class="text-muted-foreground">{{ pollLine }}</span>
      <span v-if="status.poll_error" role="alert" class="min-w-0 break-words rounded-lg bg-warn px-2 py-0.5 text-warn-foreground">Relevé : {{ status.poll_error }}</span>
      <span v-if="status.write_error" role="alert" class="min-w-0 break-words rounded-lg bg-warn px-2 py-0.5 text-warn-foreground">Écriture : {{ status.write_error }}</span>
    </div>
    <div v-if="room" class="flex flex-wrap items-baseline gap-x-6 gap-y-1 font-mono text-sm">
      <span><strong>{{ room.done }} / {{ room.total }}</strong> checks · {{ pct(room.done, room.total) }} %</span>
      <span>{{ room.goals }} / {{ room.slots }} buts</span>
      <span><strong class="text-done">{{ room.playing }}</strong> en jeu</span>
    </div>
    <p class="text-xs text-muted-foreground">
      « En jeu » : client de jeu connecté ou check il y a moins de 10 min. Les checks faits pendant une coupure sont rattrapés depuis le site, à la minute près ou sans heure.
    </p>
  </div>
</template>
