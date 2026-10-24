<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Download, ExternalLink, RefreshCw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import * as api from '../lib/api'
import { latestLabel, phaseOf, UPDATE_ANCHOR, type Phase, type UpdateInfo } from '../lib/update'

const POLL_MS = 1500
const GIVE_UP_MS = 15 * 60 * 1000

const info = ref<UpdateInfo | null>(null)
const loadError = ref('')
const checking = ref(false)
const actionError = ref('')
const startedAt = ref(0) // epoch seconds of the click on « Mettre à jour », 0 = not updating
const phase = ref<Phase | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined

const commits = computed(() => (info.value?.latest?.commits ?? []).slice(0, 10))
const notes = computed(() => (info.value?.latest?.notes ?? '').trim())
const lastStatus = computed(() => {
  const st = info.value?.status
  if (!st || startedAt.value || (st.state !== 'done' && st.state !== 'error')) return null
  return st
})

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

function when(ts: number | null | undefined): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

async function load(): Promise<void> {
  try {
    info.value = await api.getUpdate()
    loadError.value = ''
  } catch (e) {
    loadError.value = errText(e)
  }
}

async function onCheck(): Promise<void> {
  checking.value = true
  actionError.value = ''
  try {
    info.value = await api.checkUpdate()
  } catch (e) {
    actionError.value = errText(e)
  } finally {
    checking.value = false
  }
}

async function poll(): Promise<void> {
  let next: UpdateInfo | null = null
  try {
    next = await api.getUpdate()
    info.value = next
  } catch {
    /* the app is restarting */
  }
  phase.value = phaseOf(next, startedAt.value)
  if (phase.value.kind === 'done') {
    location.reload()
    return
  }
  if (phase.value.kind === 'error') {
    startedAt.value = 0
    actionError.value = `Mise à jour échouée : ${phase.value.text}`
    return
  }
  if (Date.now() - startedAt.value * 1000 > GIVE_UP_MS) {
    startedAt.value = 0
    actionError.value = 'Pas de nouvelles de la mise à jour depuis 15 min : voir la page Journal.'
    return
  }
  timer = setTimeout(poll, POLL_MS)
}

async function onApply(): Promise<void> {
  actionError.value = ''
  startedAt.value = Date.now() / 1000
  phase.value = { kind: 'waiting', text: 'Démarrage…' }
  try {
    info.value = await api.applyUpdate()
  } catch (e) {
    startedAt.value = 0
    phase.value = null
    actionError.value = errText(e)
    return
  }
  timer = setTimeout(poll, POLL_MS)
}

onMounted(load)
onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <Card :id="UPDATE_ANCHOR" class="gap-3 py-4 scroll-mt-20" data-update-panel>
    <CardHeader class="px-5">
      <CardTitle class="flex items-center gap-2"><Download class="size-4" aria-hidden="true" /> Mises à jour</CardTitle>
      <CardDescription v-if="info?.mode === 'git'">
        Suit la branche <code>main</code> du dépôt : récupère le code, réinstalle ce qui a changé, reconstruit
        l'interface et redémarre l'app si besoin.
      </CardDescription>
      <CardDescription v-else-if="info?.mode === 'portable'">
        Télécharge la dernière version publiée sur GitHub et la remplace dans ce dossier. Ta configuration, tes yamls
        et ton historique sont gardés.
      </CardDescription>
    </CardHeader>
    <CardContent class="flex flex-col gap-3 px-5 text-sm">
      <p v-if="loadError" class="text-destructive" role="alert">Impossible de lire l'état des mises à jour : {{ loadError }}</p>
      <template v-else-if="info">
        <p v-if="info.mode === 'none'" class="text-muted-foreground">
          Cette installation ne se met pas à jour toute seule (ni dépôt git, ni version portable).
        </p>
        <template v-else>
          <p>
            Version installée : <strong data-current>{{ info.current.version ?? 'inconnue' }}</strong>
            <span v-if="info.current.date" class="text-muted-foreground"> ({{ when(info.current.date) }})</span>
            <span v-if="info.current.running" class="text-muted-foreground" data-running> · l'app tourne encore sur {{ info.current.running }}</span>
          </p>

          <div v-if="startedAt && phase" class="bg-muted flex items-center gap-2 rounded-lg px-3 py-2" role="status" data-phase>
            <RefreshCw class="size-4 shrink-0 animate-spin motion-reduce:animate-none" aria-hidden="true" />
            <span>{{ phase.kind === 'waiting' ? phase.text : 'Terminé, rechargement…' }}</span>
          </div>

          <template v-else>
            <p v-if="info.check_error" class="text-destructive" role="alert">Vérification impossible : {{ info.check_error }}</p>
            <div v-else-if="info.available && info.latest" class="flex flex-col gap-2 rounded-lg border p-3" data-available>
              <p class="font-semibold">
                Disponible : {{ latestLabel(info) }}
                <a v-if="info.latest.url" :href="info.latest.url" target="_blank" rel="noopener" class="text-primary ml-1 inline-flex items-center gap-1 font-normal underline-offset-2 hover:underline">
                  notes <ExternalLink class="size-3.5" aria-hidden="true" />
                </a>
              </p>
              <ul v-if="commits.length" class="text-muted-foreground flex flex-col gap-0.5">
                <li v-for="c in commits" :key="c.commit" class="truncate"><code>{{ c.commit }}</code> {{ c.subject }}</li>
                <li v-if="(info.latest.behind ?? 0) > commits.length">… et {{ (info.latest.behind ?? 0) - commits.length }} autre(s)</li>
              </ul>
              <p v-else-if="notes" class="text-muted-foreground max-h-40 overflow-y-auto whitespace-pre-line">{{ notes }}</p>
            </div>
            <p v-else-if="info.blocked" class="text-warn-foreground bg-warn rounded px-2 py-1">{{ info.blocked }}</p>
            <p v-else-if="info.checked_at" class="text-muted-foreground" data-uptodate>À jour.</p>

            <div class="flex flex-wrap items-center gap-2">
              <Button type="button" variant="outline" size="sm" :disabled="checking || info.running" @click="onCheck">
                <RefreshCw :class="checking ? 'animate-spin motion-reduce:animate-none' : ''" aria-hidden="true" />
                {{ checking ? 'Vérification…' : 'Vérifier maintenant' }}
              </Button>
              <Button type="button" size="sm" :disabled="!info.available || info.running" data-apply @click="onApply">
                <Download aria-hidden="true" /> Mettre à jour
              </Button>
              <span v-if="info.checked_at" class="text-muted-foreground text-xs">Dernière vérification : {{ when(info.checked_at) }}</span>
            </div>
          </template>

          <p v-if="actionError" class="text-destructive" role="alert">{{ actionError }}</p>
          <p v-if="lastStatus" class="text-muted-foreground text-xs" data-last>
            Dernière mise à jour ({{ when(lastStatus.at) }}) :
            <template v-if="lastStatus.state === 'done'">réussie<template v-if="lastStatus.from && lastStatus.to && lastStatus.from !== lastStatus.to">, {{ lastStatus.from }} → {{ lastStatus.to }}</template><template v-if="lastStatus.message"> ({{ lastStatus.message }})</template>.</template>
            <span v-else class="text-destructive">échouée : {{ lastStatus.message || lastStatus.step }}.</span>
          </p>
        </template>
      </template>
      <p v-else class="text-muted-foreground">Chargement…</p>
    </CardContent>
  </Card>
</template>
