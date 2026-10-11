<script setup lang="ts">
import { computed, ref } from 'vue'
import { groupLocations, hintInMyWorld, hintMineElsewhere } from '../lib/logic'
import type { Hint, ItemEntry, SlotDetail } from '../lib/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { HISTORY_PAGE, formatWhen, historyItems, type HistoryFilter } from '../lib/history'
import { tracker } from '../stores/tracker'
import { cn } from '@/lib/utils'
import Section from './Section.vue'

const props = defineProps<{ detail: SlotDetail }>()

const newItems = computed(() => props.detail.items_list.filter((i) => i.new))
const historyFilter = ref<HistoryFilter>('all')
const historyLimit = ref(HISTORY_PAGE)
const history = computed(() => historyItems(props.detail.items_list, historyFilter.value))
const shown = computed(() => history.value.slice(0, historyLimit.value))
function setFilter(v: unknown) {
  if (v === 'all' || v === 'progression' || v === 'useful') {
    historyFilter.value = v
    historyLimit.value = HISTORY_PAGE
  }
}
const sortFound = (hs: Hint[]) => [...hs].sort((a, b) => Number(a.found) - Number(b.found))
const mine = computed(() => sortFound(props.detail.hints_mine_elsewhere))
const world = computed(() => sortFound(props.detail.hints_in_my_world))
const groups = computed(() => groupLocations(props.detail.in_logic_locations))

function kind(i: { progression: boolean; useful: boolean; trap: boolean }) {
  if (i.trap) return { sym: '⚠', label: 'piège', cls: 'text-destructive' }
  if (i.progression) return { sym: '★', label: 'progression', cls: 'text-prog' }
  if (i.useful) return { sym: '◆', label: 'utile', cls: 'text-primary' }
  return null
}
const from = (i: ItemEntry) =>
  i.origin === 'start'
    ? 'inventaire de départ'
    : i.origin === 'server'
      ? 'donné par le serveur'
      : i.own
        ? 'trouvé par toi'
        : `de ${i.sender}`
const fromWhere = (i: ItemEntry) => (i.location ? `${from(i)} · ${i.location}` : from(i))
</script>

<template>
  <div class="flex flex-col gap-2">
    <Section :title="`Locations en logique (${detail.in_logic_locations.length})`">
      <p v-if="!detail.in_logic_locations.length" class="text-muted-foreground text-sm">Aucune location en logique.</p>
      <template v-else>
        <template v-for="g in groups" :key="g.title ?? '_'">
          <h4 v-if="g.title" class="text-muted-foreground mt-2.5 mb-1 text-sm font-semibold">
            {{ g.title }} <span class="font-normal">({{ g.locations.length }})</span>
          </h4>
          <ul class="divide-y">
            <li
              v-for="l in g.locations"
              :key="l.id"
              :class="cn('flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm', l.hint && 'bg-warn text-warn-foreground my-0.5 rounded-md border-none px-2')"
            >
              <span class="break-words">{{ l.name }}</span>
              <span v-if="l.hint" :class="cn('basis-full font-semibold', l.hint.progression && 'font-bold')">
                → {{ l.hint.item }} pour {{ l.hint.receiver }}
              </span>
            </li>
          </ul>
        </template>
      </template>
    </Section>

    <Section title="Nouveaux items">
      <p v-if="!newItems.length" class="text-muted-foreground text-sm">Rien de nouveau.</p>
      <ul v-else class="divide-y">
        <li v-for="i in newItems" :key="i.index" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
          <span :class="cn('break-words', i.progression && 'font-bold')">
            <span v-if="kind(i)" :class="cn('inline-block w-5 text-center', kind(i)!.cls)" :title="kind(i)!.label" :aria-label="kind(i)!.label">{{ kind(i)!.sym }}</span>
            {{ i.name }}
          </span>
          <span class="text-muted-foreground">{{ from(i) }}</span>
        </li>
      </ul>
    </Section>

    <Section :title="`Historique des items reçus (${detail.items_list.length})`" :start-open="false">
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        :spacing="1"
        class="mb-2 flex-wrap"
        :model-value="historyFilter"
        aria-label="Filtrer l'historique"
        @update:model-value="setFilter"
      >
        <ToggleGroupItem value="all" class="px-3">Tous</ToggleGroupItem>
        <ToggleGroupItem value="progression" class="px-3">★ Progression</ToggleGroupItem>
        <ToggleGroupItem value="useful" class="px-3">◆ Utiles</ToggleGroupItem>
      </ToggleGroup>
      <p v-if="!history.length" class="text-muted-foreground text-sm">Aucun item.</p>
      <ul v-else class="divide-y">
        <li v-for="i in shown" :key="i.index" class="history-item flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
          <span :class="cn('break-words', i.progression && 'font-bold', i.new && 'text-primary')">
            <span v-if="kind(i)" :class="cn('inline-block w-5 text-center', kind(i)!.cls)" :title="kind(i)!.label" :aria-label="kind(i)!.label">{{ kind(i)!.sym }}</span>
            {{ i.name }}
          </span>
          <span class="text-muted-foreground min-w-0 flex-1 break-words">{{ fromWhere(i) }}</span>
          <span class="text-muted-foreground ml-auto text-xs whitespace-nowrap tabular-nums">{{ formatWhen(i.received_at, tracker.nowMs) }}</span>
        </li>
      </ul>
      <Button v-if="history.length > shown.length" variant="ghost" size="sm" class="mt-1" @click="historyLimit += HISTORY_PAGE">
        Afficher {{ Math.min(HISTORY_PAGE, history.length - shown.length) }} de plus ({{ history.length - shown.length }} restants)
      </Button>
    </Section>

    <Section title="Hints">
      <h4 class="text-muted-foreground mt-1 mb-1 text-sm font-semibold">Tes items chez les autres</h4>
      <p v-if="!mine.length" class="text-muted-foreground text-sm">Aucun hint.</p>
      <ul v-else class="divide-y">
        <li v-for="(h, k) in mine" :key="k" :class="cn('flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm', h.found && 'line-through opacity-55')">
          <span :class="cn('break-words', h.progression && 'font-bold')">{{ hintMineElsewhere(h) }}</span>
          <Badge v-if="h.found" variant="secondary">trouvé</Badge>
        </li>
      </ul>
      <h4 class="text-muted-foreground mt-2.5 mb-1 text-sm font-semibold">Items hintés dans ton monde</h4>
      <p v-if="!world.length" class="text-muted-foreground text-sm">Aucun hint.</p>
      <ul v-else class="divide-y">
        <li
          v-for="(h, k) in world"
          :key="k"
          :class="cn('flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm', h.found && 'line-through opacity-55', h.in_logic && !h.found && 'bg-warn text-warn-foreground my-0.5 rounded-md border-none px-2')"
        >
          <span :class="cn('break-words', h.progression && 'font-bold')">{{ hintInMyWorld(h) }}</span>
          <Badge v-if="h.in_logic && !h.found" variant="good">en logique</Badge>
          <Badge v-if="h.found" variant="secondary">trouvé</Badge>
        </li>
      </ul>
    </Section>
  </div>
</template>
