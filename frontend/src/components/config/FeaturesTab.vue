<script setup lang="ts">
import type { Ref } from 'vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import type { ConfigForm } from './form'

const props = defineProps<{ form: ConfigForm }>()
const f = props.form

const features: { id: string; model: Ref<boolean>; title: string; text: string; page: string }[] = [
  {
    id: 'cfg-scout',
    model: f.scoutChecked,
    title: 'Contenu des checks déjà faits',
    text: "Demande au serveur quel item était dans chacun de tes checks faits, et pour qui. Seulement des checks déjà faits, sans créer de hint : rien n'est dévoilé. Désactivé : l'item n'est connu que s'il est parti vers un slot suivi par l'app.",
    page: 'Historique',
  },
  {
    id: 'cfg-hints-foreign',
    model: f.hintsForeignLogic,
    title: "Accessibilité chez les autres joueurs",
    text: "Quand un de tes items est chez un joueur que l'app ne suit pas, elle suit aussi ce slot (en lecture seule, au plus 12) pour savoir s'il peut faire le check et ce qui lui manque. Une connexion et un monde recalculé de plus par slot. Désactivé : « Inconnu » pour ces indices.",
    page: 'Indices',
  },
  {
    id: 'cfg-goal-override',
    model: f.goalOverride,
    title: 'Choisir le but à la main',
    text: "L'app trouve le but de chaque slot toute seule. Activé : dans l'onglet Slots, une colonne « But » permet d'imposer la condition de victoire des jeux qui en proposent plusieurs (objectif, logique et go mode la suivent). Tes choix restent enregistrés.",
    page: 'Objectifs',
  },
  {
    id: 'cfg-roomdash',
    model: f.roomDashboard,
    title: 'Tableau de bord de la room complète',
    text: "Classement, fil des checks et activité de toute la room. Une connexion d'écoute en plus, en lecture seule ; les checks sont écrits dans data/room_feed/. Désactivé par défaut.",
    page: 'Plus › Room complète',
  },
]
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-muted-foreground text-sm">Chaque fonction dit quelle page elle change. Tout reste en lecture seule vers le serveur.</p>
    <ul class="divide-y rounded-lg border">
      <li v-for="x in features" :key="x.id" class="flex items-start gap-3 p-4">
        <Checkbox :id="x.id" v-model="x.model.value" class="mt-0.5" />
        <div class="flex min-w-0 flex-1 flex-col gap-0.5">
          <Label :for="x.id" class="font-medium">{{ x.title }}</Label>
          <p class="text-muted-foreground text-xs">{{ x.text }}</p>
        </div>
        <span class="text-primary border-primary/40 shrink-0 rounded-full border px-2 py-0.5 font-mono text-[11px]">{{ x.page }}</span>
      </li>
    </ul>
  </div>
</template>
