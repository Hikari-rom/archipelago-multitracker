<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { goalProgress, sortByGoal } from '../../lib/goals'
import type { SlotSummary } from '../../lib/types'
import GoalBlock from '../components/GoalBlock.vue'
import OwnerSelect from '../components/OwnerSelect.vue'
import { loadHideReached, saveHideReached } from '../lib/prefs'

const props = defineProps<{ slots: SlotSummary[]; owner: string; chips: { key: string; label: string }[] }>()
const emit = defineEmits<{ 'update:owner': [key: string] }>()

const hideReached = ref(loadHideReached())
watch(hideReached, saveHideReached)

const reached = computed(() => props.slots.filter((s) => s.goal).length)
const shown = computed(() => sortByGoal(props.slots).filter((s) => !(hideReached.value && s.goal)))
</script>

<template>
  <section class="flex flex-col gap-4" aria-labelledby="goals-title">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <h2 id="goals-title" class="text-lg font-semibold">Objectifs</h2>
      <p class="text-sm text-muted-foreground">{{ reached }} but{{ reached > 1 ? 's' : '' }} atteint{{ reached > 1 ? 's' : '' }} sur {{ slots.length }}</p>
      <div class="ml-auto flex flex-wrap items-center gap-x-4 gap-y-2">
        <OwnerSelect :model-value="owner" :chips="chips" @update:model-value="(k: string) => emit('update:owner', k)" />
        <label class="flex items-center gap-2 text-sm text-muted-foreground max-[699px]:min-h-11">
          <input v-model="hideReached" type="checkbox" class="size-4" />
          Masquer les buts atteints
        </label>
      </div>
    </div>
    <div class="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2 min-[1100px]:grid-cols-3">
      <article v-for="s in shown" :key="s.name" :data-goal="s.name" class="rounded-[14px] border bg-card p-5">
        <header class="mb-3 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="line-clamp-2 font-semibold" :title="s.game">{{ s.game }}</h3>
            <p class="font-mono text-xs text-muted-foreground">{{ s.name }}<template v-if="s.owner"> · {{ s.owner }}</template></p>
          </div>
          <span v-if="s.goal" class="shrink-0 text-sm text-done">✓ But atteint</span>
          <span v-else class="shrink-0 font-mono text-sm tabular-nums">{{ Math.round(goalProgress(s) * 100) }} %</span>
        </header>
        <GoalBlock v-if="s.objective" :objective="s.objective" :goal="s.goal" />
        <p v-else class="text-sm text-muted-foreground">Pas encore de description du but pour ce jeu.</p>
      </article>
    </div>
  </section>
</template>
