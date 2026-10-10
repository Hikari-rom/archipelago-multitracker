<script setup lang="ts">
import { computed } from 'vue'
import { groupLocations, hintInMyWorld, hintMineElsewhere } from '../lib/logic'
import type { Hint, ItemEntry, SlotDetail } from '../lib/types'
import Section from './Section.vue'

const props = defineProps<{ detail: SlotDetail }>()

const newItems = computed(() => props.detail.items_list.filter((i) => i.new))
const allItems = computed(() => [...props.detail.items_list].sort((a, b) => b.index - a.index))
const sortFound = (hs: Hint[]) => [...hs].sort((a, b) => Number(a.found) - Number(b.found))
const mine = computed(() => sortFound(props.detail.hints_mine_elsewhere))
const world = computed(() => sortFound(props.detail.hints_in_my_world))
const groups = computed(() => groupLocations(props.detail.in_logic_locations))

function kind(i: { progression: boolean; useful: boolean; trap: boolean }) {
  if (i.trap) return { sym: '⚠', label: 'piège', cls: 'trap' }
  if (i.progression) return { sym: '★', label: 'progression', cls: 'prog' }
  if (i.useful) return { sym: '◆', label: 'utile', cls: 'useful' }
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
  <div class="detail">
    <Section :title="`Locations en logique (${detail.in_logic_locations.length})`">
      <p v-if="!detail.in_logic_locations.length" class="muted">Aucune location en logique.</p>
      <template v-else>
        <template v-for="g in groups" :key="g.title ?? '_'">
          <h4 v-if="g.title" class="group">{{ g.title }} <span class="muted">({{ g.locations.length }})</span></h4>
          <ul class="list">
            <li v-for="l in g.locations" :key="l.id" :class="{ hl: !!l.hint }">
              <span class="main">{{ l.name }}</span>
              <span v-if="l.hint" class="hintline" :class="{ prog: l.hint.progression }">
                → {{ l.hint.item }} pour {{ l.hint.receiver }}
              </span>
            </li>
          </ul>
        </template>
      </template>
    </Section>

    <Section title="Nouveaux items">
      <p v-if="!newItems.length" class="muted">Rien de nouveau.</p>
      <ul v-else class="list">
        <li v-for="i in newItems" :key="i.index">
          <span class="main" :class="{ prog: i.progression }">
            <span v-if="kind(i)" class="mark" :class="kind(i)!.cls" :title="kind(i)!.label" :aria-label="kind(i)!.label">{{ kind(i)!.sym }}</span>
            {{ i.name }}
          </span>
          <span class="muted">{{ from(i) }}</span>
        </li>
      </ul>
    </Section>

    <Section :title="`Tous les items reçus (${allItems.length})`" :start-open="false">
      <p v-if="!allItems.length" class="muted">Aucun item reçu.</p>
      <ul v-else class="list">
        <li v-for="i in allItems" :key="i.index" :class="{ fresh: i.new }">
          <span class="main" :class="{ prog: i.progression }">
            <span v-if="kind(i)" class="mark" :class="kind(i)!.cls" :title="kind(i)!.label" :aria-label="kind(i)!.label">{{ kind(i)!.sym }}</span>
            {{ i.name }}
          </span>
          <span class="muted">{{ from(i) }}</span>
        </li>
      </ul>
    </Section>

    <Section title="Hints">
      <h4>Tes items chez les autres</h4>
      <p v-if="!mine.length" class="muted">Aucun hint.</p>
      <ul v-else class="list">
        <li v-for="(h, k) in mine" :key="k" :class="{ found: h.found }">
          <span class="main" :class="{ prog: h.progression }">{{ hintMineElsewhere(h) }}</span>
          <span v-if="h.found" class="tag">trouvé</span>
        </li>
      </ul>
      <h4>Items hintés dans ton monde</h4>
      <p v-if="!world.length" class="muted">Aucun hint.</p>
      <ul v-else class="list">
        <li v-for="(h, k) in world" :key="k" :class="{ found: h.found, hl: h.in_logic && !h.found }">
          <span class="main" :class="{ prog: h.progression }">{{ hintInMyWorld(h) }}</span>
          <span v-if="h.in_logic && !h.found" class="tag logic">en logique</span>
          <span v-if="h.found" class="tag">trouvé</span>
        </li>
      </ul>
    </Section>
  </div>
</template>
