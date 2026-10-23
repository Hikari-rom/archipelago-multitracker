<script setup lang="ts">
import { start } from '../../stores/tracker'
import type { CardState } from '../lib/card'

defineProps<{ state: CardState }>()
const pill = 'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs'
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <span v-if="state.activity?.kind === 'chosen'" :class="pill" class="border-transparent bg-logic/15 text-logic">◉ Actif · choisi</span>
    <span v-else-if="state.activity?.kind === 'auto'" :class="pill" class="border-transparent bg-logic/15 text-logic">◔ Actif · auto · il y a {{ state.activity.agoMin }} min</span>
    <span v-if="state.activity?.kind === 'auto'" class="text-xs text-muted-foreground">Expire dans {{ state.activity.expiresInMin }} min</span>
    <span v-else-if="state.activity?.kind === 'chosen'" class="text-xs text-muted-foreground">Mémorisé sur cet appareil</span>

    <span v-if="state.connection.kind === 'ok'" :class="pill" class="text-done">● Connecté</span>
    <span v-else-if="state.connection.kind === 'sleeping'" :class="pill" class="text-muted-foreground">☾ En pause<template v-if="state.connection.since">, chiffres de {{ state.connection.since }}</template></span>
    <template v-else-if="state.connection.kind === 'error'">
      <span :class="pill" class="border-transparent bg-warn text-error">! {{ state.connection.message }}</span>
      <button type="button" data-retry class="inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs hover:bg-accent max-[699px]:min-h-11" @click="start()">Réessayer</button>
    </template>
    <span v-else :class="pill" class="text-muted-foreground">Connexion…</span>

    <span v-if="state.logic.kind === 'unavailable'" :class="pill" class="text-muted-foreground">Logique indisponible pour ce jeu</span>
    <span v-else-if="state.logic.kind === 'pending'" :class="pill" class="text-muted-foreground">{{ state.logic.waiting ? 'En attente de connexion' : 'Calcul de la logique…' }}</span>
    <span v-else-if="state.logic.approx && state.logic.message" :class="pill" class="border-transparent bg-warn text-error">! {{ state.logic.message }}</span>

    <span v-if="state.bk" :class="pill" class="border-transparent bg-warn text-warn-foreground">BK · rien en logique, en attente d'items</span>
    <span v-if="state.goalReached" :class="pill" class="text-done">✓ But atteint</span>
  </div>
</template>
