<script setup lang="ts">
import { computed, ref } from 'vue'
import { Inbox } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { FEED_LONG, FEED_PHONE, FEED_SHORT, feedItems } from '../lib/dashboard'
import { formatReceived, itemKind, receivedTitle } from '../lib/history'
import type { SlotSummary } from '../lib/types'
import { tracker } from '../stores/tracker'

/** Latest items received by the slots shown on the dashboard (owner filter applied). */
const props = defineProps<{ slots: SlotSummary[] }>()
const long = ref(false)
const names = computed(() => new Set(props.slots.map((s) => s.name)))
const all = computed(() => feedItems(tracker.recent, names.value, FEED_LONG))
const shown = computed(() => (long.value ? all.value : all.value.slice(0, FEED_SHORT)))
const from = (sender: string, origin?: string) => (origin === 'server' ? 'donné par le serveur' : `de ${sender}`)
</script>

<template>
  <section class="bg-card mb-3 rounded-xl border px-4 py-3" aria-labelledby="feed-title">
    <h2 id="feed-title" class="mb-1 flex items-center gap-2 text-sm font-semibold">
      <Inbox class="size-4" aria-hidden="true" /> Derniers items reçus
    </h2>
    <p v-if="!all.length" class="text-muted-foreground text-sm">Aucun item reçu depuis que l’app suit ces slots.</p>
    <ul v-else class="divide-y">
      <li
        v-for="(i, k) in shown"
        :key="`${i.slot}:${i.index}`"
        :class="cn('flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm', !long && k >= FEED_PHONE && 'max-[699px]:hidden')"
      >
        <span :class="cn('break-words', i.progression && 'font-bold', i.new && 'text-primary')">
          <span v-if="itemKind(i)" :class="cn('inline-block w-5 text-center', itemKind(i)!.cls)" :title="itemKind(i)!.label" :aria-label="itemKind(i)!.label">{{ itemKind(i)!.sym }}</span>
          {{ i.name }}
        </span>
        <span class="text-muted-foreground min-w-48 flex-1 break-words">
          pour <span class="text-foreground">{{ i.game }}</span> ({{ i.slot }}) · {{ from(i.sender, i.origin) }}
        </span>
        <span class="text-muted-foreground ml-auto text-xs whitespace-nowrap tabular-nums" :title="receivedTitle(i) || undefined">{{ formatReceived(i, tracker.nowMs) }}</span>
      </li>
    </ul>
    <Button v-if="all.length > FEED_SHORT" variant="ghost" size="sm" class="mt-1" :aria-expanded="long" @click="long = !long">
      {{ long ? 'Afficher moins' : `Afficher les ${all.length} derniers` }}
    </Button>
  </section>
</template>
