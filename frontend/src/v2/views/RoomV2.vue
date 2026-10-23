<script setup lang="ts">
import { useRoomFeed } from '../lib/roomfeed'

const { status, error } = useRoomFeed()
</script>

<template>
  <section class="flex flex-col gap-4" aria-labelledby="room-title">
    <h2 id="room-title" class="text-lg font-semibold">Room complète</h2>
    <p v-if="error" role="alert" class="rounded-xl bg-warn p-3 text-sm text-warn-foreground"><span class="text-error">! </span>{{ error }}</p>
    <p v-else-if="status && !status.enabled" class="rounded-xl border bg-card p-4 text-sm text-muted-foreground">
      Le tableau de bord de la room est désactivé. Active-le dans la Configuration.
    </p>
  </section>
</template>
