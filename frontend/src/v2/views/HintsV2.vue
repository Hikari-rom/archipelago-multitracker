<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getHints } from '../../lib/api'
import { FILTER_LABEL, doneBy, filterHints, groupBySlot, type HintColumn, type HintsFilter } from '../../lib/hints'
import type { HintsResponse, SlotSummary } from '../../lib/types'
import { hintsListeners, tracker } from '../../stores/tracker'
import HintsTable from '../components/HintsTable.vue'
import OwnerSelect from '../components/OwnerSelect.vue'
import { loadHideFoundHints, loadHintsSort, saveHideFoundHints, saveHintsSort } from '../lib/prefs'

const props = defineProps<{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }>()
const emit = defineEmits<{ 'update:owner': [key: string] }>()

const data = ref<HintsResponse | null>(null)
const error = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
let alive = true

async function load() {
  try {
    const res = await getHints()
    if (!alive) return
    data.value = res
    error.value = ''
  } catch (e) {
    if (alive) error.value = e instanceof Error ? e.message : String(e)
  }
}
function loadSoon() {
  clearTimeout(timer)
  timer = setTimeout(load, 400)
}
onMounted(() => {
  load()
  hintsListeners.add(loadSoon)
})
onBeforeUnmount(() => {
  alive = false
  clearTimeout(timer)
  hintsListeners.delete(loadSoon)
})

const hideFound = ref(loadHideFoundHints())
watch(hideFound, saveHideFoundHints)
const sort = ref(loadHintsSort())
watch(sort, saveHintsSort)
const filter = ref<HintsFilter>('all')
const query = ref('')

const mine = computed(() => new Set(props.slots.map((s) => s.name)))
const all = computed(() => (data.value?.hints ?? []).filter((h) => h.slots.some((n) => mine.value.has(n))))
const rows = computed(() => filterHints(all.value, mine.value, { filter: filter.value, query: query.value, hideFound: hideFound.value }))
const count = (state: string) => all.value.filter((h) => h.access.state === state).length
const counts = computed(() => ({ open: all.value.filter((h) => !h.found).length, ok: count('ok'), blocked: count('blocked') }))

const layout = computed(() => tracker.hintsLayout)
const REGISTRE: HintColumn[] = ['access', 'item', 'receiver', 'finder', 'location', 'status']
const MY_ITEMS: HintColumn[] = ['access', 'item', 'receiver', 'finder', 'location', 'status']
const MY_WORLDS: HintColumn[] = ['access', 'item', 'finder', 'location', 'receiver', 'status']
const BY_SLOT: HintColumn[] = ['dir', 'access', 'item', 'other', 'location', 'status']

const myItems = computed(() => rows.value.filter((h) => h.receiver_slot && mine.value.has(h.receiver_slot) && doneBy(h, mine.value) === 'other'))
const myWorlds = computed(() => rows.value.filter((h) => doneBy(h, mine.value) === 'me'))
const groups = computed(() => groupBySlot(rows.value, props.slots))

const foreign = computed(() => data.value?.foreign)
const foreignText = computed(() => {
  const f = foreign.value
  if (!f) return ''
  if (!f.enabled) return 'Accessibilité chez les autres joueurs désactivée (page Configuration).'
  const n = f.followed.length
  let t = n ? `Accessibilité suivie aussi chez ${n} autre${n > 1 ? 's' : ''} slot${n > 1 ? 's' : ''}` : ''
  if (f.capped.length) t += `${t ? ' ; ' : ''}${f.capped.length} non suivi${f.capped.length > 1 ? 's' : ''} (maximum ${f.max})`
  return t ? `${t}.` : ''
})
const FILTERS = Object.keys(FILTER_LABEL) as HintsFilter[]
</script>

<template>
  <section class="flex flex-col gap-4" aria-labelledby="hints-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h2 id="hints-title" class="text-lg font-semibold">Indices</h2>
      <p v-if="data" class="text-sm text-muted-foreground" data-hints-counts>
        {{ counts.open }} à trouver · <span class="text-done">{{ counts.ok }} accessible{{ counts.ok > 1 ? 's' : '' }}</span> ·
        <span class="text-error">{{ counts.blocked }} bloqué{{ counts.blocked > 1 ? 's' : '' }}</span>
      </p>
      <div class="ml-auto flex flex-wrap items-center gap-x-4 gap-y-2">
        <OwnerSelect :model-value="owner" :chips="chips" @update:model-value="(k: string) => emit('update:owner', k)" />
        <label class="flex items-center gap-2 text-sm text-muted-foreground max-[699px]:min-h-11">
          <input v-model="hideFound" type="checkbox" class="size-4" />
          Masquer les trouvés
        </label>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="Filtrer les indices" class="flex flex-wrap gap-1.5">
        <button
          v-for="f in FILTERS" :key="f" type="button" :aria-pressed="filter === f" :data-filter="f"
          class="min-h-9 rounded-full border px-3 text-sm max-[699px]:min-h-11"
          :class="filter === f ? 'border-logic bg-logic/15 text-foreground' : 'text-muted-foreground hover:text-foreground'"
          @click="filter = f"
        >
          {{ FILTER_LABEL[f] }}
        </button>
      </div>
      <input
        v-model="query" type="search" placeholder="Chercher un item, une location, un joueur…" aria-label="Chercher dans les indices"
        class="h-9 min-w-0 flex-1 rounded-lg border bg-card px-3 text-sm max-[699px]:h-11 min-[700px]:max-w-80 min-[700px]:ml-auto"
      />
    </div>
    <p v-if="foreignText" class="text-xs text-muted-foreground">{{ foreignText }}</p>

    <p v-if="error && !data" class="text-sm text-error">Impossible de charger les indices : {{ error }}</p>
    <p v-else-if="!data" class="text-sm text-muted-foreground">Chargement…</p>
    <p v-else-if="!all.length" class="rounded-[14px] border bg-card p-5 text-sm text-muted-foreground">
      Aucun indice pour {{ slots.length > 1 ? 'ces slots' : 'ce slot' }} pour l’instant.
    </p>
    <p v-else-if="!rows.length" class="rounded-[14px] border bg-card p-5 text-sm text-muted-foreground">Aucun indice ne correspond à ces filtres.</p>

    <template v-else-if="layout === 'sens'">
      <section class="flex flex-col gap-2" aria-labelledby="hints-mine">
        <h3 id="hints-mine" class="font-semibold">Tes items chez les autres <span class="font-mono text-xs text-muted-foreground">{{ myItems.length }}</span></h3>
        <p class="text-xs text-muted-foreground">Quelqu’un d’autre doit faire le check.</p>
        <HintsTable v-if="myItems.length" v-model:sort="sort" :rows="myItems" :columns="MY_ITEMS" label="Tes items chez les autres" />
        <p v-else class="text-sm text-muted-foreground">Rien ici.</p>
      </section>
      <section class="flex flex-col gap-2" aria-labelledby="hints-worlds">
        <h3 id="hints-worlds" class="font-semibold">Dans tes mondes <span class="font-mono text-xs text-muted-foreground">{{ myWorlds.length }}</span></h3>
        <p class="text-xs text-muted-foreground">C’est à toi de faire le check.</p>
        <HintsTable v-if="myWorlds.length" v-model:sort="sort" :rows="myWorlds" :columns="MY_WORLDS" label="Dans tes mondes" />
        <p v-else class="text-sm text-muted-foreground">Rien ici.</p>
      </section>
    </template>

    <template v-else-if="layout === 'slots'">
      <details v-for="g in groups" :key="g.name" open class="group flex flex-col gap-2" :data-hints-slot="g.name">
        <summary class="flex cursor-pointer list-none flex-wrap items-baseline gap-x-3 gap-y-1 py-1">
          <span aria-hidden="true" class="text-muted-foreground transition-transform group-open:rotate-90">▸</span>
          <span class="font-semibold">{{ g.game }}</span>
          <span class="font-mono text-xs text-muted-foreground">{{ g.name }}</span>
          <span class="ml-auto text-xs text-muted-foreground">
            {{ g.rows.length }} · <span class="text-done">{{ g.ok }} accessible{{ g.ok > 1 ? 's' : '' }}</span> ·
            <span class="text-error">{{ g.blocked }} bloqué{{ g.blocked > 1 ? 's' : '' }}</span>
          </span>
        </summary>
        <HintsTable v-model:sort="sort" :rows="g.rows" :columns="BY_SLOT" :context="g.name" :label="`Indices de ${g.name}`" class="mt-2" />
      </details>
    </template>

    <HintsTable v-else v-model:sort="sort" :rows="rows" :columns="REGISTRE" label="Indices" />
  </section>
</template>
