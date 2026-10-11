<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { ArrowDownToLine, Pause, Play } from '@lucide/vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { cn } from '@/lib/utils'
import { LogBuffer, filterLines, type LevelFilter, type LogLine } from '../lib/logs'
import StatusDot from './StatusDot.vue'

const FIRST_LINES = 500
const buffer = new LogBuffer()
const lines = shallowRef<LogLine[]>([])
const pending = ref<string[]>([])
const paused = ref(false)
const missing = ref(false)
const status = ref<'connecting' | 'open' | 'reconnecting'>('connecting')
const level = ref<LevelFilter>('all')
const showAccess = ref(false)
const search = ref('')
const follow = ref(true)
const box = ref<HTMLElement | null>(null)

const shown = computed(() => filterLines(lines.value, { level: level.value, showAccess: showAccess.value, search: search.value }))
const statusLabel = computed(() => ({ open: 'En direct', connecting: 'Connexion…', reconnecting: 'Reconnexion…' })[status.value])
const levelClass: Record<LogLine['level'], string> = {
  error: 'text-destructive',
  warning: 'bg-warn text-warn-foreground',
  info: '',
  access: 'text-muted-foreground',
  other: 'text-muted-foreground',
}

function publish(): void {
  lines.value = buffer.lines.slice()
}
function receive(texts: string[]): void {
  if (paused.value) pending.value.push(...texts)
  else {
    buffer.append(texts)
    publish()
  }
}
function togglePause(): void {
  paused.value = !paused.value
  if (!paused.value && pending.value.length) {
    buffer.append(pending.value)
    pending.value = []
    publish()
  }
}

function atBottom(el: HTMLElement): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight < 40
}
function onScroll(): void {
  if (box.value) follow.value = atBottom(box.value)
}
function toEnd(): void {
  follow.value = true
  if (box.value) box.value.scrollTop = box.value.scrollHeight
}
watch(shown, async () => {
  if (!follow.value) return
  await nextTick()
  if (box.value) box.value.scrollTop = box.value.scrollHeight
})

function data(e: Event): any | null {
  try {
    return JSON.parse((e as MessageEvent).data)
  } catch {
    return null
  }
}

let es: EventSource | null = null
function open(): void {
  if (import.meta.env.VITE_MOCK === '1') {
    status.value = 'open'
    buffer.reset([
      '2026-10-11 10:21:28,117 INFO multitracker.ap.tracker: tracker Romain_MC: connected',
      '2026-10-11 10:21:51,797 ERROR multitracker.service: logic failed for Romain_MC',
      'Traceback (most recent call last):',
      '  File "service.py", line 201, in _logic_loop',
      "ModuleNotFoundError: No module named 'worlds'",
      '2026-10-11 10:21:53,108 logic-worker WARNING Spicy Meatball Overdrive has more items than locations.',
      'INFO:     192.168.1.13:56831 - "GET /api/slots HTTP/1.1" 200 OK',
    ])
    publish()
    return
  }
  if (typeof EventSource === 'undefined') return
  es = new EventSource(`/api/logs/stream?lines=${FIRST_LINES}`)
  es.onopen = () => (status.value = 'open')
  es.onerror = () => (status.value = 'reconnecting') // the browser reconnects by itself ("retry" sent by the server)
  es.addEventListener('init', (e) => {
    const d = data(e)
    if (!d) return
    missing.value = !!d.missing
    pending.value = []
    buffer.reset(Array.isArray(d.lines) ? d.lines : [])
    publish()
  })
  es.addEventListener('lines', (e) => {
    const d = data(e)
    if (d && Array.isArray(d.lines)) receive(d.lines)
  })
  es.addEventListener('reset', () => receive(['— nouveau fichier de log (redémarrage de l’app) —']))
}
onMounted(open)
onBeforeUnmount(() => es?.close())
</script>

<template>
  <section class="flex flex-col gap-3" aria-labelledby="logs-title">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <h2 id="logs-title" class="text-base font-semibold">Journal de l’app</h2>
      <StatusDot :status="status" :label="statusLabel" live />
      <span class="text-muted-foreground text-xs">data/logs/app.log · {{ shown.length }} / {{ lines.length }} lignes</span>
    </div>

    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        :spacing="1"
        :model-value="level"
        aria-label="Niveau"
        @update:model-value="(v) => v && (level = v as LevelFilter)"
      >
        <ToggleGroupItem value="all" class="px-3">Tout</ToggleGroupItem>
        <ToggleGroupItem value="warning" class="px-3">Avertissements</ToggleGroupItem>
        <ToggleGroupItem value="error" class="px-3">Erreurs</ToggleGroupItem>
      </ToggleGroup>
      <div class="flex min-h-8 items-center gap-2">
        <Checkbox id="logs-access" v-model="showAccess" />
        <Label for="logs-access" class="font-normal">Requêtes HTTP</Label>
      </div>
      <Input v-model="search" type="search" placeholder="Rechercher (slot, jeu, message…)" aria-label="Rechercher dans le journal" class="h-8 max-w-72" />
      <Button size="sm" variant="outline" :aria-pressed="paused" @click="togglePause">
        <component :is="paused ? Play : Pause" aria-hidden="true" />
        {{ paused ? 'Reprendre' : 'Pause' }}
      </Button>
      <Badge v-if="paused && pending.length" variant="info">{{ pending.length }} nouvelle{{ pending.length > 1 ? 's' : '' }} ligne{{ pending.length > 1 ? 's' : '' }} en attente</Badge>
    </div>

    <Alert v-if="missing" role="status">
      <AlertDescription>Pas encore de fichier de log : l’app écrit dans data/logs/app.log quand elle est lancée par scripts/app.sh.</AlertDescription>
    </Alert>

    <div class="relative">
      <div
        ref="box"
        role="log"
        aria-live="off"
        aria-label="Lignes du journal"
        tabindex="0"
        class="bg-card h-[70dvh] min-h-72 overflow-auto rounded-md border p-2 font-mono text-xs leading-5"
        @scroll="onScroll"
      >
        <p v-if="!shown.length" class="text-muted-foreground p-2 font-sans text-sm">
          {{ lines.length ? 'Aucune ligne ne correspond aux filtres.' : 'Aucune ligne pour l’instant.' }}
        </p>
        <div v-for="l in shown" :key="l.id" :class="cn('rounded-sm px-1 break-all whitespace-pre-wrap', levelClass[l.level])">{{ l.text }}</div>
      </div>
      <Button v-if="!follow" size="sm" class="absolute right-4 bottom-3 shadow-md" @click="toEnd">
        <ArrowDownToLine aria-hidden="true" /> Aller à la fin
      </Button>
    </div>
  </section>
</template>
