<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { History } from '@lucide/vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { cn } from '@/lib/utils'
import * as api from '../lib/api'
import { checkedTitle, formatChecked, formatReceived, itemKind, receivedTitle, sentText } from '../lib/history'
import type { HistoryPage, HistorySlot, ReceivedEntry, SentCheck, SlotSummary } from '../lib/types'
import { tracker } from '../stores/tracker'

/** Every check made by the selected slots (what it held and for whom) and every item they received. */
const props = defineProps<{ slots: SlotSummary[] }>()

type Kind = 'sent' | 'received'
const PAGE = 200
const kind = ref<Kind>('sent')
const slotFilter = ref('')
const sent = ref<HistoryPage<SentCheck> | null>(null)
const received = ref<HistoryPage<ReceivedEntry> | null>(null)
const limit = ref(PAGE)
const error = ref('')
const loading = ref(false)

const names = computed(() => props.slots.map((s) => s.name))
const wanted = computed(() => (slotFilter.value && names.value.includes(slotFilter.value) ? [slotFilter.value] : names.value))
const page = computed(() => (kind.value === 'sent' ? sent.value : received.value))
const perSlot = computed<HistorySlot[]>(() => {
  const keep = new Set(names.value)
  return (page.value?.slots ?? []).filter((s) => keep.has(s.name))
})
const totals = computed(() =>
  perSlot.value.reduce(
    (t, s) => ({ done: t.done + s.checks.done, toOthers: t.toOthers + s.sent.to_others, received: t.received + s.received }),
    { done: 0, toOthers: 0, received: 0 },
  ),
)

let seq = 0
async function load(): Promise<void> {
  const mine = ++seq
  loading.value = true
  try {
    const k = kind.value
    const r = await (k === 'sent'
      ? api.getHistory('sent', wanted.value, limit.value, 0)
      : api.getHistory('received', wanted.value, limit.value, 0))
    if (mine !== seq) return
    if (k === 'sent') sent.value = r as HistoryPage<SentCheck>
    else received.value = r as HistoryPage<ReceivedEntry>
    error.value = ''
  } catch (e) {
    if (mine === seq) error.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (mine === seq) loading.value = false
  }
}

function more(): void {
  limit.value += PAGE
  void load()
}

// the slot list is rebuilt on every live update: compare its names, not the array
watch([kind, () => wanted.value.join('\n')], () => {
  limit.value = PAGE
  void load()
}, { immediate: true })

// New checks or items on the selected slots: reload (grouped, they come in bursts).
const signature = computed(() => props.slots.map((s) => `${s.checks.done}/${s.items.received}/${s.sent?.known ?? 0}`).join(','))
let timer: ReturnType<typeof setTimeout> | undefined
watch(signature, () => {
  clearTimeout(timer)
  timer = setTimeout(() => void load(), 1500)
})
onBeforeUnmount(() => clearTimeout(timer))

const sentRows = computed(() => (kind.value === 'sent' ? (sent.value?.items ?? []) : []))
const receivedRows = computed(() => (kind.value === 'received' ? (received.value?.items ?? []) : []))
const from = (i: ReceivedEntry) => (i.origin === 'server' ? 'donné par le serveur' : i.origin === 'start' ? 'inventaire de départ' : `de ${i.sender}`)
const selectClass =
  'border-input bg-background h-9 min-w-0 rounded-md border px-2 text-sm shadow-xs focus-visible:ring-ring/50 focus-visible:ring-3'
</script>

<template>
  <section class="flex flex-col gap-3" aria-labelledby="history-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h2 id="history-title" class="flex items-center gap-2 text-base font-semibold"><History class="size-4" aria-hidden="true" /> Historique</h2>
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        :spacing="1"
        :model-value="kind"
        aria-label="Checks envoyés ou items reçus"
        @update:model-value="(v) => v && (kind = v as Kind)"
      >
        <ToggleGroupItem value="sent" class="px-3">Checks envoyés</ToggleGroupItem>
        <ToggleGroupItem value="received" class="px-3">Items reçus</ToggleGroupItem>
      </ToggleGroup>
      <select v-model="slotFilter" :class="selectClass" aria-label="Filtrer par jeu">
        <option value="">Tous les jeux ({{ slots.length }})</option>
        <option v-for="s in slots" :key="s.name" :value="s.name">{{ s.game }} ({{ s.name }})</option>
      </select>
    </div>

    <Alert v-if="error" variant="destructive" role="alert"><AlertDescription>Impossible de charger l’historique : {{ error }}</AlertDescription></Alert>
    <p v-if="kind === 'sent' && page && !page.scout_checked" class="text-muted-foreground text-sm">
      Le contenu des checks n’est demandé au serveur que si l’option est activée (Configuration) : ici, il n’est connu que
      pour les items partis vers un slot suivi par l’app.
    </p>

    <div v-if="perSlot.length > 1" class="bg-card overflow-x-auto rounded-xl border">
      <table class="w-full text-sm">
        <caption class="sr-only">Par jeu</caption>
        <thead class="text-muted-foreground text-left text-xs">
          <tr class="border-b">
            <th scope="col" class="px-3 py-2 font-medium">Jeu</th>
            <th scope="col" class="px-3 py-2 text-right font-medium">Checks faits</th>
            <th scope="col" class="px-3 py-2 text-right font-medium">Envoyés aux autres</th>
            <th scope="col" class="px-3 py-2 text-right font-medium">Items reçus</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="s in perSlot" :key="s.name" :class="cn(slotFilter === s.name && 'bg-accent')">
            <th scope="row" class="px-3 py-1.5 text-left font-normal">
              <button type="button" class="hover:underline text-left" :aria-pressed="slotFilter === s.name" @click="slotFilter = slotFilter === s.name ? '' : s.name">
                <span class="font-medium">{{ s.game }}</span> <span class="text-muted-foreground text-xs">{{ s.name }}</span>
              </button>
            </th>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ s.checks.done }} <span class="text-muted-foreground">/ {{ s.checks.total }}</span></td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ sentText(s) }}</td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ s.received }}</td>
          </tr>
        </tbody>
        <tfoot class="border-t font-semibold">
          <tr>
            <th scope="row" class="px-3 py-1.5 text-left">Total</th>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ totals.done }}</td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ totals.toOthers }}</td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ totals.received }}</td>
          </tr>
        </tfoot>
      </table>
    </div>

    <div class="bg-card rounded-xl border px-4 py-3">
      <p v-if="!page && loading" class="text-muted-foreground text-sm">Chargement…</p>
      <template v-else-if="page">
        <p class="text-muted-foreground mb-1 text-xs">
          {{ page.total }} {{ kind === 'sent' ? (page.total === 1 ? 'check' : 'checks') : page.total === 1 ? 'item' : 'items' }}, du plus récent au plus ancien
        </p>
        <p v-if="!page.total" class="text-muted-foreground text-sm">{{ kind === 'sent' ? 'Aucun check fait.' : 'Aucun item reçu.' }}</p>

        <!-- Bounded height: the page does not grow with « Afficher de plus ». -->
        <ul v-if="kind === 'sent'" class="divide-y max-h-[min(70vh,48rem)] overflow-y-auto overscroll-contain">
          <li v-for="c in sentRows" :key="`${c.slot}:${c.location_id}`" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
            <span class="min-w-0 break-words">{{ c.location }}</span>
            <span class="text-muted-foreground min-w-48 flex-1 break-words">
              <template v-if="c.item">
                →
                <span :class="cn('text-foreground', c.progression && 'font-bold')">
                  <span v-if="itemKind(c)" :class="cn('inline-block w-5 text-center', itemKind(c)!.cls)" :title="itemKind(c)!.label" :aria-label="itemKind(c)!.label">{{ itemKind(c)!.sym }}</span>{{ c.item }}
                </span>
                <template v-if="c.to_self"> pour toi</template>
                <template v-else> pour <span class="text-foreground">{{ c.receiver }}</span> ({{ c.receiver_game }})</template>
              </template>
              <template v-else>contenu inconnu</template>
              <template v-if="!slotFilter"> · {{ c.game }} ({{ c.slot }})</template>
            </span>
            <span class="text-muted-foreground ml-auto text-xs whitespace-nowrap tabular-nums" :title="checkedTitle(c) || undefined">{{ formatChecked(c, tracker.nowMs) }}</span>
          </li>
        </ul>

        <ul v-else class="divide-y max-h-[min(70vh,48rem)] overflow-y-auto overscroll-contain">
          <li v-for="i in receivedRows" :key="`${i.slot}:${i.index}`" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
            <span :class="cn('break-words', i.progression && 'font-bold')">
              <span v-if="itemKind(i)" :class="cn('inline-block w-5 text-center', itemKind(i)!.cls)" :title="itemKind(i)!.label" :aria-label="itemKind(i)!.label">{{ itemKind(i)!.sym }}</span>{{ i.name }}
            </span>
            <span class="text-muted-foreground min-w-48 flex-1 break-words">
              <template v-if="!slotFilter">pour <span class="text-foreground">{{ i.game }}</span> ({{ i.slot }}) · </template>{{ from(i) }}<template v-if="i.location"> ({{ i.location }})</template>
            </span>
            <span class="text-muted-foreground ml-auto text-xs whitespace-nowrap tabular-nums" :title="receivedTitle(i) || undefined">{{ formatReceived(i, tracker.nowMs) }}</span>
          </li>
        </ul>

        <Button v-if="page.items.length < page.total" variant="ghost" size="sm" class="mt-1" :disabled="loading" @click="more">
          Afficher {{ Math.min(PAGE, page.total - page.items.length) }} de plus
        </Button>
      </template>
    </div>
  </section>
</template>
