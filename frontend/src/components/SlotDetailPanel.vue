<script setup lang="ts">
import { computed } from 'vue'
import { groupLocations, hintInMyWorld, hintMineElsewhere } from '../lib/logic'
import type { Hint, ItemEntry, SlotDetail } from '../lib/types'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import Section from './Section.vue'

const props = defineProps<{ detail: SlotDetail }>()

const newItems = computed(() => props.detail.items_list.filter((i) => i.new))
const allItems = computed(() => [...props.detail.items_list].sort((a, b) => b.index - a.index))
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

    <Section :title="`Tous les items reçus (${allItems.length})`" :start-open="false">
      <p v-if="!allItems.length" class="text-muted-foreground text-sm">Aucun item reçu.</p>
      <ul v-else class="divide-y">
        <li v-for="i in allItems" :key="i.index" class="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5 py-1.5 text-sm">
          <span :class="cn('break-words', i.progression && 'font-bold', i.new && 'text-primary')">
            <span v-if="kind(i)" :class="cn('inline-block w-5 text-center', kind(i)!.cls)" :title="kind(i)!.label" :aria-label="kind(i)!.label">{{ kind(i)!.sym }}</span>
            {{ i.name }}
          </span>
          <span class="text-muted-foreground">{{ from(i) }}</span>
        </li>
      </ul>
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
