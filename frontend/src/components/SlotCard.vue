<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { Activity, ChevronRight, Star, TriangleAlert, Trophy } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { formatWhen } from '../lib/history'
import { connectionMessage, isActive, logicBadge, logicUnavailable, pluralize, statusLabel } from '../lib/logic'
import type { SlotSummary } from '../lib/types'
import { loadDetail, markSeen, toggleOpen, tracker } from '../stores/tracker'
import SlotDetailPanel from './SlotDetailPanel.vue'
import StatusDot from './StatusDot.vue'

const props = defineProps<{ summary: SlotSummary }>()

const badge = computed(() => logicBadge(props.summary))
const active = computed(() => isActive(props.summary, tracker.nowMs, tracker.activeMinutes))
const badgeVariant = computed(() =>
  badge.value.variant === 'good' ? 'good' : badge.value.variant === 'muted' ? 'muted' : 'secondary',
)
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
const stateMsg = computed(() => connectionMessage(props.summary, tracker.roomSleeping))
const rawError = computed(() => (props.summary.status === 'connected' ? '' : props.summary.error || ''))

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
  <Card
    as="article"
    :class="cn('min-w-0 gap-3 px-4 py-4', open && 'col-span-full', summary.goal && 'opacity-70')"
    :data-slot-name="summary.name"
  >
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h2 class="text-lg leading-tight font-semibold break-words">{{ summary.game }}</h2>
        <p class="text-muted-foreground text-sm break-words">
          {{ summary.name }}<span v-if="summary.owner" class="italic"> · {{ summary.owner }}</span>
        </p>
        <Badge v-if="active" variant="good" class="active mt-1" :title="`Dernier check : ${formatWhen(summary.last_check_at, tracker.nowMs)}`">
          <Activity aria-hidden="true" /> Actif · {{ formatWhen(summary.last_check_at, tracker.nowMs) }}
        </Badge>
      </div>
      <StatusDot :status="summary.status" :label="statusLabel(summary.status)" :title="rawError || statusLabel(summary.status)" />
    </header>
    <p v-if="stateMsg" :class="cn('text-sm', tracker.roomSleeping ? 'text-muted-foreground' : 'text-destructive')" :title="rawError">{{ stateMsg }}</p>

    <p v-if="summary.goal" class="text-good-foreground flex items-center gap-1.5 font-semibold">
      <Trophy class="size-4" aria-hidden="true" /> But atteint
    </p>

    <div>
      <div class="mb-1.5 flex justify-between gap-2 text-sm">
        <span><strong>{{ summary.checks.done }}</strong> / {{ summary.checks.total }} checks</span>
        <span class="text-muted-foreground">{{ pluralize(summary.checks.remaining, 'restant', 'restants') }}</span>
      </div>
      <Progress :model-value="pct" class="h-1.5" :aria-label="`Progression des checks : ${pct} %`" />
    </div>

    <div class="flex flex-col items-start gap-2">
      <Badge :variant="badgeVariant" :class="cn('rounded-lg px-3 py-1.5 text-sm whitespace-normal', badge.variant === 'good' && 'font-semibold')" :title="badge.secondary">
        {{ badge.text }}
      </Badge>
      <p
        v-if="badge.secondary"
        :class="cn('text-xs', summary.logic.state === 'ok' ? 'logic-warning bg-warn text-warn-foreground flex items-start gap-1 rounded px-1.5 py-0.5' : 'text-muted-foreground')"
      >
        <TriangleAlert v-if="summary.logic.state === 'ok'" class="mt-px size-3.5 shrink-0" aria-hidden="true" />{{ badge.secondary }}
      </p>

      <Badge v-if="summary.hints.in_my_world_in_logic > 0" variant="warn" class="hinted px-3 py-1 text-sm font-semibold">
        <Star aria-hidden="true" />
        {{ summary.hints.in_my_world_in_logic }}
        {{ summary.hints.in_my_world_in_logic === 1 ? 'location hintée en logique' : 'locations hintées en logique' }}
      </Badge>

      <div v-if="summary.items.new > 0" class="flex flex-wrap items-center gap-2">
        <Badge variant="info" :class="cn('rounded-lg px-3 py-1.5 font-semibold', unavailable ? 'text-base' : 'text-sm')">
          {{ summary.items.new }} {{ summary.items.new === 1 ? 'nouvel item' : 'nouveaux items' }}
        </Badge>
        <Button variant="outline" size="sm" class="seen" :disabled="busy" @click="onSeen">Marquer comme vu</Button>
      </div>
      <p v-if="seenError" class="text-destructive text-sm" role="alert">{{ seenError }}</p>

      <p class="text-muted-foreground text-xs">
        Hints : {{ summary.hints.mine_elsewhere }} de tes items chez les autres · {{ summary.hints.in_my_world }} dans ton monde
      </p>
    </div>

    <button
      type="button"
      class="toggle text-primary flex min-h-11 items-center gap-1.5 border-t pt-2.5 text-left text-sm hover:underline"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="toggleOpen(summary.name)"
    >
      <ChevronRight :class="cn('size-4 transition-transform motion-reduce:transition-none', open && 'rotate-90')" aria-hidden="true" />
      {{ open ? 'Masquer les détails' : 'Voir les détails' }}
    </button>
    <div v-show="open" :id="panelId">
      <template v-if="open">
        <SlotDetailPanel v-if="detail" :detail="detail" />
        <div v-else-if="detailError" role="alert" class="flex flex-col items-start gap-2">
          <p class="text-destructive text-sm">Impossible de charger les détails : {{ detailError }}</p>
          <Button variant="outline" size="sm" @click="loadDetail(summary.name)">Réessayer</Button>
        </div>
        <p v-else class="text-muted-foreground">Chargement…</p>
      </template>
    </div>
  </Card>
</template>
