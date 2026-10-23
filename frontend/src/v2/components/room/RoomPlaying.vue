<script setup lang="ts">
import { computed } from 'vue'
import type { RoomFeedPlayer, RoomPresence } from '../../../lib/types'

const props = defineProps<{ players: RoomFeedPlayer[] }>()

interface Chip { key: string; player: string; game: string; presence: RoomPresence }
const chips = computed<Chip[]>(() => {
  const all = props.players.flatMap((p) =>
    p.slots
      .filter((s) => s.presence === 'playing' || s.presence === 'connected')
      .map((s, i) => ({ key: `${p.player}:${s.name ?? i}`, player: p.player, game: s.game ?? '?', presence: s.presence })))
  const rank = (c: Chip) => (c.presence === 'playing' ? 0 : 1)
  return all.sort((a, b) => rank(a) - rank(b) || a.player.localeCompare(b.player) || a.game.localeCompare(b.game))
})
</script>

<template>
  <section class="flex flex-col gap-2" aria-labelledby="room-playing-title">
    <h3 id="room-playing-title" class="text-base font-semibold">En jeu maintenant</h3>
    <ul v-if="chips.length" class="flex min-w-0 flex-wrap gap-1.5">
      <li
        v-for="c in chips" :key="c.key" :data-chip="c.presence"
        class="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs"
        :class="c.presence === 'playing' ? 'border-transparent bg-done/15 text-done' : 'text-muted-foreground'"
        :title="`${c.player} · ${c.game}`"
      >
        <span class="size-1.5 shrink-0 rounded-full" :class="c.presence === 'playing' ? 'bg-done' : 'bg-muted-foreground'" aria-hidden="true" />
        <span class="truncate">{{ c.player }} · {{ c.game }}</span>
      </li>
    </ul>
    <p v-else class="text-sm text-muted-foreground">Personne pour l'instant.</p>
  </section>
</template>
