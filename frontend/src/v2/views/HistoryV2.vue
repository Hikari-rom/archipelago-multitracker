<script setup lang="ts">
import { computed, ref } from 'vue'
import { tracker } from '../../stores/tracker'
import type { SlotSummary } from '../../lib/types'
import { sentText } from '../../lib/history'
import OwnerSelect from '../components/OwnerSelect.vue'
import { hhmm } from '../lib/card'
import { CATEGORY_CLASS as badgeClass, category, groupByDay, itemOrigin } from '../lib/days'
import { historyTab } from '../lib/nav'
import { useHistory } from '../lib/useHistory'

const props = defineProps<{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }>()
defineEmits<{ 'update:owner': [key: string] }>()

const slotFilter = ref('')
const { sent, received, perSlot, totals, loading, error, more } = useHistory(() => props.slots, historyTab, slotFilter)
const page = computed(() => (historyTab.value === 'sent' ? sent.value : received.value))

// groupByDay expects newest first: sort copies, entries without a time go last (stable).
const newestFirst = <T,>(items: T[], at: (e: T) => number | null): T[] =>
  [...items].sort((a, b) => (at(b) ?? -Infinity) - (at(a) ?? -Infinity))
const sentAt = (c: { checked_at: number | null }) => c.checked_at
const receivedAt = (i: { received_at?: number | null }) => i.received_at ?? null
const sentGroups = computed(() =>
  groupByDay(newestFirst(sent.value?.items ?? [], sentAt), sentAt, (c) => c.game, tracker.nowMs))
const receivedGroups = computed(() =>
  groupByDay(newestFirst(received.value?.items ?? [], receivedAt), receivedAt, (i) => i.game, tracker.nowMs))

const time = (t: number | null | undefined) => (t == null ? '—' : hhmm(t))

const tabs = computed(() => [
  { key: 'sent' as const, label: `Checks envoyés${sent.value ? ` · ${sent.value.total}` : ''}` },
  { key: 'received' as const, label: `Items reçus${received.value ? ` · ${received.value.total}` : ''}` },
])
</script>

<template>
  <section class="flex flex-col gap-4" aria-labelledby="history-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h2 id="history-title" class="text-lg font-semibold">Historique</h2>
      <div role="tablist" aria-label="Type d'historique" class="flex gap-1 border-b">
        <button
          v-for="t in tabs" :key="t.key" type="button" role="tab" :aria-selected="historyTab === t.key"
          class="border-b-2 px-3 py-1.5 text-sm max-[699px]:min-h-11"
          :class="historyTab === t.key ? 'border-logic font-semibold' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="historyTab = t.key"
        >{{ t.label }}</button>
      </div>
      <label class="flex items-center gap-2 text-sm text-muted-foreground">
        Jeu
        <select v-model="slotFilter" class="h-9 rounded-lg border bg-card px-2 text-sm text-foreground max-[699px]:h-11">
          <option value="">tous ({{ slots.length }})</option>
          <option v-for="s in slots" :key="s.name" :value="s.name">{{ s.game }}</option>
        </select>
      </label>
      <OwnerSelect :model-value="owner" :chips="chips" @update:model-value="(k: string) => $emit('update:owner', k)" />
      <span class="font-mono text-xs text-muted-foreground">du plus récent au plus ancien · pages de 200</span>
    </div>

    <p v-if="error" role="alert" class="rounded-xl bg-warn p-3 text-sm text-warn-foreground"><span class="text-error">! </span>{{ error }}</p>
    <p v-if="historyTab === 'sent' && page && page.scout_checked === false" class="text-sm text-muted-foreground">
      Le contenu des checks faits n'est pas demandé au serveur (Configuration).
    </p>

    <div class="grid gap-4 min-[1100px]:grid-cols-[400px_1fr]">
      <div>
        <table data-history-table class="hidden w-full rounded-xl border bg-card text-sm min-[700px]:table">
          <thead class="text-left text-xs text-muted-foreground">
            <tr class="border-b">
              <th scope="col" class="px-3 py-2 font-medium">Jeu · clic = filtrer</th>
              <th scope="col" class="px-2 py-2 text-right font-medium">Faits</th>
              <th scope="col" class="px-2 py-2 text-right font-medium">Envoyés</th>
              <th scope="col" class="px-2 py-2 text-right font-medium">Reçus</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="s in perSlot" :key="s.name" :class="slotFilter === s.name && 'bg-accent'">
              <th scope="row" class="px-3 py-1.5 text-left font-normal">
                <button type="button" class="text-left hover:underline" :aria-pressed="slotFilter === s.name" @click="slotFilter = slotFilter === s.name ? '' : s.name">{{ s.game }}</button>
              </th>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ s.checks.done }} / {{ s.checks.total }}</td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">
                {{ s.sent.to_others }}<span v-if="s.checks.done - s.sent.known > 0" class="text-muted-foreground" :title="sentText(s)"> +{{ s.checks.done - s.sent.known }} ?</span>
              </td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ s.received }}</td>
            </tr>
          </tbody>
          <tfoot class="border-t font-semibold">
            <tr>
              <th scope="row" class="px-3 py-1.5 text-left">Total</th>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ totals.done }}</td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ totals.toOthers }}</td>
              <td class="whitespace-nowrap px-2 py-1.5 text-right font-mono tabular-nums">{{ totals.received }}</td>
            </tr>
          </tfoot>
        </table>
        <p class="hidden px-3 py-2 text-xs text-muted-foreground min-[700px]:block">« +N ? » : checks au contenu inconnu</p>
        <details class="rounded-xl border bg-card p-3 text-sm min-[700px]:hidden">
          <summary class="flex min-h-11 cursor-pointer items-center">Par jeu ▾</summary>
          <ul class="mt-2 divide-y">
            <li v-for="s in perSlot" :key="s.name" class="flex flex-wrap justify-between gap-x-3 py-1.5">
              <span>{{ s.game }}</span>
              <span class="font-mono text-xs text-muted-foreground">{{ s.checks.done }} / {{ s.checks.total }} · {{ sentText(s) }} · {{ s.received }}</span>
            </li>
          </ul>
        </details>
      </div>

      <div class="rounded-xl border bg-card px-4 py-3">
        <p class="mb-2 flex flex-wrap gap-x-4 font-mono text-xs text-muted-foreground">
          <span><span class="rounded px-1" :class="badgeClass.PROG">PROG</span> progression</span>
          <span><span class="rounded px-1" :class="badgeClass.UTILE">UTILE</span> utile</span>
          <span><span class="rounded px-1" :class="badgeClass.PIÈGE">PIÈGE</span> piège</span>
          <span>sans étiquette = normal</span>
        </p>
        <p v-if="!page && loading" class="text-sm text-muted-foreground">Chargement…</p>
        <p v-else-if="page && !page.total" class="text-sm text-muted-foreground">{{ historyTab === 'sent' ? 'Aucun check fait.' : 'Aucun item reçu.' }}</p>

        <template v-if="historyTab === 'sent'">
          <section v-for="g in sentGroups" :key="g.key" :data-day="g.label" class="mb-3">
            <h3 class="border-b py-1 text-sm font-semibold">{{ g.label }} · {{ g.rows.length }} check{{ g.rows.length > 1 ? 's' : '' }}</h3>
            <ul class="divide-y">
              <li v-for="r in g.rows" :key="`${r.entry.slot}:${r.entry.location_id}`" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
                <span class="w-12 font-mono text-xs text-muted-foreground tabular-nums">{{ time(r.entry.checked_at) }}</span>
                <span v-if="r.showSource" class="font-semibold">{{ r.entry.game }}</span>
                <span class="font-mono text-xs">{{ r.entry.location }}</span>
                <span v-if="r.entry.item == null" class="italic text-muted-foreground">contenu inconnu</span>
                <template v-else>
                  <span v-if="category(r.entry)" class="rounded px-1 font-mono text-[11px]" :class="badgeClass[category(r.entry)!]">{{ category(r.entry) }}</span>
                  <span>{{ r.entry.item }}</span>
                  <span class="text-muted-foreground">{{ r.entry.to_self ? 'pour moi' : `pour ${r.entry.receiver} · ${r.entry.receiver_game}` }}</span>
                </template>
              </li>
            </ul>
          </section>
        </template>

        <template v-else>
          <section v-for="g in receivedGroups" :key="g.key" :data-day="g.label" class="mb-3">
            <h3 class="border-b py-1 text-sm font-semibold">{{ g.label }} · {{ g.rows.length }} item{{ g.rows.length > 1 ? 's' : '' }}</h3>
            <ul class="divide-y">
              <li v-for="r in g.rows" :key="`${r.entry.slot}:${r.entry.index}`" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
                <span class="w-12 font-mono text-xs text-muted-foreground tabular-nums">{{ time(r.entry.received_at) }}</span>
                <span v-if="category(r.entry)" class="rounded px-1 font-mono text-[11px]" :class="badgeClass[category(r.entry)!]">{{ category(r.entry) }}</span>
                <span>{{ r.entry.name }}</span>
                <span v-if="r.showSource" class="text-muted-foreground">pour <span class="font-semibold text-foreground">{{ r.entry.game }}</span></span>
                <span class="text-muted-foreground">{{ itemOrigin(r.entry) }}</span>
              </li>
            </ul>
          </section>
        </template>

        <button v-if="page && page.items.length < page.total" type="button" class="mt-1 rounded-lg border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50 max-[699px]:min-h-11" :disabled="loading" @click="more">Afficher plus</button>
      </div>
    </div>
  </section>
</template>
