<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { logicBadge, logicUnavailable, pluralize, statusLabel } from '../lib/logic'
import type { SlotSummary } from '../lib/types'
import { loadDetail, markSeen, toggleOpen, tracker } from '../stores/tracker'
import SlotDetailPanel from './SlotDetailPanel.vue'

const props = defineProps<{ summary: SlotSummary }>()

const badge = computed(() => logicBadge(props.summary))
const unavailable = computed(() => logicUnavailable(props.summary))
const open = computed(() => !!tracker.open[props.summary.name])
const detail = computed(() => tracker.details[props.summary.name])
const pct = computed(() => {
  const c = props.summary.checks
  return c.total > 0 ? Math.round((c.done / c.total) * 100) : 0
})
const busy = ref(false)
const seenError = ref('')
const panelId = 'detail-' + useId()
const detailError = computed(() => tracker.detailError[props.summary.name])
const stateMsg = computed(() =>
  props.summary.status === 'connected' ? '' : props.summary.error || '',
)

async function onSeen() {
  busy.value = true
  seenError.value = ''
  try {
    await markSeen(props.summary.name)
  } catch (e) {
    seenError.value = e instanceof Error ? e.message : 'Échec'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <article class="card" :class="{ done: summary.goal, open, 'new-primary': unavailable && summary.items.new > 0 }" :data-slot="summary.name">
    <header class="card-head">
      <div class="titles">
        <h2 class="game">{{ summary.game }}</h2>
        <p class="slotname">{{ summary.name }}</p>
      </div>
      <span class="status" :class="'st-' + summary.status" :title="stateMsg || statusLabel(summary.status)">
        <span class="dot" aria-hidden="true"></span>{{ statusLabel(summary.status) }}
      </span>
    </header>
    <p v-if="stateMsg" class="state-msg">{{ stateMsg }}</p>

    <p v-if="summary.goal" class="goal">But atteint ✓</p>

    <div class="progress">
      <div class="progress-text">
        <span><strong>{{ summary.checks.done }}</strong> / {{ summary.checks.total }} checks</span>
        <span class="muted">{{ pluralize(summary.checks.remaining, 'restant', 'restants') }}</span>
      </div>
      <div class="bar" role="progressbar" :aria-valuenow="pct" aria-valuemin="0" aria-valuemax="100" :aria-label="`Progression des checks : ${pct} %`">
        <div class="bar-fill" :style="{ width: pct + '%' }"></div>
      </div>
    </div>

    <div class="signals">
      <p class="badge" :class="'b-' + badge.variant" :title="badge.secondary">{{ badge.text }}</p>
      <p v-if="badge.secondary" class="secondary">{{ badge.secondary }}</p>

      <p v-if="summary.hints.in_my_world_in_logic > 0" class="chip hinted">
        ★ {{ summary.hints.in_my_world_in_logic }}
        {{ summary.hints.in_my_world_in_logic === 1 ? 'location hintée en logique' : 'locations hintées en logique' }}
      </p>

      <div v-if="summary.items.new > 0" class="new-row">
        <span class="badge b-new" :class="{ big: unavailable }">
          {{ summary.items.new }} {{ summary.items.new === 1 ? 'nouvel item' : 'nouveaux items' }}
        </span>
        <button type="button" class="btn" :disabled="busy" @click="onSeen">Marquer comme vu</button>
      </div>
      <p v-if="seenError" class="error-text" role="alert">{{ seenError }}</p>

      <p class="hint-counts muted">
        Hints : {{ summary.hints.mine_elsewhere }} de tes items chez les autres · {{ summary.hints.in_my_world }} dans ton monde
      </p>
    </div>

    <button
      type="button"
      class="toggle"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="toggleOpen(summary.name)"
    >
      <span class="chev" :class="{ rot: open }" aria-hidden="true">▸</span>
      {{ open ? 'Masquer les détails' : 'Voir les détails' }}
    </button>
    <div v-show="open" :id="panelId" class="panel">
      <template v-if="open">
        <SlotDetailPanel v-if="detail" :detail="detail" />
        <div v-else-if="detailError" role="alert">
          <p class="error-text">Impossible de charger les détails : {{ detailError }}</p>
          <button type="button" class="btn" @click="loadDetail(summary.name)">Réessayer</button>
        </div>
        <p v-else class="muted">Chargement…</p>
      </template>
    </div>
  </article>
</template>
