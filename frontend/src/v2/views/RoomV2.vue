<script setup lang="ts">
import { setView, tracker } from '../../stores/tracker'
import RoomHeader from '../components/room/RoomHeader.vue'
import RoomLeaderboard from '../components/room/RoomLeaderboard.vue'
import RoomPlaying from '../components/room/RoomPlaying.vue'
import { useRoomFeed } from '../lib/roomfeed'

const { status, summary, error } = useRoomFeed()
</script>

<template>
  <section class="flex min-w-0 flex-col gap-4" aria-labelledby="room-title">
    <h2 id="room-title" class="text-lg font-semibold">Room complète</h2>
    <div v-if="!tracker.roomDashboard || (status && !status.enabled)" class="flex flex-col items-start gap-3 rounded-xl border bg-card p-4 text-sm">
      <p class="text-muted-foreground">Le tableau de bord de la room complète est désactivé.</p>
      <button type="button" class="inline-flex min-h-9 items-center rounded-lg border px-3 hover:bg-accent max-[699px]:min-h-11" @click="setView('config')">Ouvrir la configuration</button>
    </div>
    <template v-else>
      <p v-if="error" role="alert" class="rounded-xl bg-warn p-3 text-sm text-warn-foreground"><span class="text-error">! </span>{{ error }}</p>
      <template v-if="status">
        <RoomHeader :status="status" :room="summary?.room ?? null" />
        <template v-if="summary">
          <RoomPlaying :players="summary.players" />
          <div class="grid min-w-0 gap-4 min-[1100px]:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <RoomLeaderboard :players="summary.players" />
            <!-- Right column: « Activité » and « Fil des checks » (Task 11) -->
            <div data-room-side class="flex min-w-0 flex-col gap-4" />
          </div>
        </template>
      </template>
    </template>
  </section>
</template>
