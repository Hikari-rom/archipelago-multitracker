<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import * as api from '../../lib/api'
import { tracker } from '../../stores/tracker'

// The victory of a slot chosen by hand (D34), from the tab « But » or the page Objectifs. Only shown while
// « Choisir le but à la main » is on in the Configuration (the server sends goal_options then); saved in
// config/room.yaml like the Configuration does, and the logic is recomputed with it.
const props = defineProps<{ name: string; compact?: boolean }>()

const summary = computed(() => tracker.slots.find((s) => s.name === props.name))
const options = computed(() => summary.value?.goal_options ?? [])
const pending = ref<Record<string, string> | null>(null) // the choice being saved, shown until the server has it
const chosen = computed(() => pending.value ?? summary.value?.goal_chosen ?? {})
const saving = ref(false)
const error = ref('')
// the server's snapshot carries the saved choice: the pending one gives way to it then
watch(
  () => JSON.stringify(summary.value?.goal_chosen ?? {}),
  () => {
    if (!saving.value) pending.value = null
  },
)

async function onChange(option: string, e: Event): Promise<void> {
  const value = (e.target as HTMLSelectElement).value
  const goal = { ...chosen.value }
  if (value) goal[option] = value
  else delete goal[option]
  pending.value = goal
  saving.value = true
  error.value = ''
  try {
    await api.putSlotGoal(props.name, goal)
    if (JSON.stringify(summary.value?.goal_chosen ?? {}) === JSON.stringify(goal)) pending.value = null
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    pending.value = null
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="options.length" data-goal-chooser class="flex flex-col gap-1.5" :class="compact ? 'mt-3 border-t pt-3' : ''">
    <label v-for="o in options" :key="o.option" class="flex min-w-0 flex-wrap items-center gap-2 text-sm">
      <span class="text-muted-foreground">But choisi · {{ o.display }}</span>
      <select
        :value="chosen[o.option] ?? ''"
        :disabled="saving"
        :aria-label="`${o.display} de ${name}`"
        class="h-9 max-w-full min-w-0 rounded-lg border bg-card px-2 text-sm text-foreground max-[699px]:h-11"
        @change="onChange(o.option, $event)"
      >
        <option value="">automatique</option>
        <option v-for="c in o.choices" :key="c" :value="c">{{ c }}</option>
      </select>
      <span v-if="saving" class="text-xs text-muted-foreground" role="status">enregistrement…</span>
    </label>
    <p v-if="error" class="text-xs text-error" role="alert">{{ error }}</p>
  </div>
</template>
