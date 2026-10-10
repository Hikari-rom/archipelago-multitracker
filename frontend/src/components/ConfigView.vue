<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  AlarmClock, CircleAlert, CircleCheck, FileUp, Info, Link2, PlugZap, RotateCcw, Search, TriangleAlert, Wand2,
} from '@lucide/vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import * as api from '../lib/api'
import {
  autoAssociate,
  buildPutBody,
  diagnose,
  distinctGames,
  filterRows,
  mergeDiscovered,
  mergeRows,
  probeMessage,
  setChecked,
  type ConfigResponse,
  type Diag,
  type DiscoverResponse,
  type SlotRow,
  type YamlEntry,
} from '../lib/config'
import { refreshMeta, setView, tracker } from '../stores/tracker'

const emit = defineEmits<{ saved: [] }>()

const cfg = ref<ConfigResponse | null>(null)
const roomUrl = ref('')
const server = ref('')
const advanced = ref(false)
const password = ref('')
const clearPassword = ref(false)
const wakeRoom = ref(false)
const rows = ref<SlotRow[]>([])
const loading = ref(true)
const loadError = ref('')

const room = ref<DiscoverResponse | null>(null)
const discovering = ref(false)
const discoverError = ref('')
const waking = ref(false)

const probing = ref(false)
const probeResult = ref<{ ok: boolean; text: string } | null>(null)

const uploading = ref(false)
const uploadLog = ref<{ ok: boolean; text: string }[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const assocInfo = ref('')

const filterText = ref('')
const filterGame = ref('')
const checkedOnly = ref(false)

const saving = ref(false)
const saveError = ref('')
const restoring = ref(false)

const yamls = computed<YamlEntry[]>(() => cfg.value?.yamls ?? [])
const games = computed(() => cfg.value?.games ?? {})
const yamlPaths = computed(() => yamls.value.map((y) => y.path))
const owners = computed(() => [...new Set(rows.value.map((r) => r.owner.trim()).filter(Boolean))].sort())
const checkedRows = computed(() => rows.value.filter((r) => r.checked))
const visible = computed(() =>
  filterRows(rows.value, { text: filterText.value, game: filterGame.value, checkedOnly: checkedOnly.value }),
)
const gameOptions = computed(() => distinctGames(rows.value))
const diags = computed(() => {
  const out: Record<string, Diag[]> = {}
  for (const r of rows.value) out[r.name] = diagnose(r, yamls.value, games.value)
  return out
})
const summary = computed(() => {
  const list = checkedRows.value
  const withLogic = list.filter((r) => {
    const g = games.value[r.game]
    return g?.logic && !diags.value[r.name].some((d) => d.level !== 'info')
  }).length
  const warnings = list.filter((r) => diags.value[r.name].some((d) => d.level === 'warn')).length
  const errors = list.filter((r) => diags.value[r.name].some((d) => d.level === 'error')).length
  return { count: list.length, withLogic, warnings, errors }
})
const canSave = computed(
  () => !saving.value && !!(roomUrl.value.trim() || server.value.trim()) && checkedRows.value.length > 0,
)
const roomGames = computed(() => (room.value ? new Set(room.value.players.map((p) => p.game)).size : 0))
const shortYaml = (p: string) => p.replace(/^config\/players\//, '')

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

async function loadConfig(): Promise<void> {
  cfg.value = await api.getConfig()
}

onMounted(async () => {
  try {
    await loadConfig()
    const c = cfg.value!
    roomUrl.value = c.room_url ?? ''
    server.value = c.room_url ? '' : (c.server ?? '')
    advanced.value = !c.room_url && !!c.server
    wakeRoom.value = !!c.wake_room
    rows.value = autoAssociate(mergeRows(c.slots, null), yamls.value).rows
  } catch (e) {
    loadError.value = errText(e)
  } finally {
    loading.value = false
  }
  const prefill = tracker.prefillRoom
  if (prefill) {
    roomUrl.value = prefill
    tracker.prefillRoom = ''
    advanced.value = false
  }
  if (roomUrl.value.trim()) void onDiscover()
})

// "#config?room=..." opened while the page is already displayed
watch(
  () => tracker.prefillRoom,
  (v) => {
    if (!v || loading.value) return
    roomUrl.value = v
    tracker.prefillRoom = ''
    void onDiscover()
  },
)

async function onDiscover(wake = false): Promise<void> {
  if (!roomUrl.value.trim()) return
  discovering.value = !wake
  waking.value = wake
  discoverError.value = ''
  try {
    const d = await api.discover(roomUrl.value.trim(), wake)
    room.value = d
    if (d.room_url) roomUrl.value = d.room_url
    const known = new Set(rows.value.map((r) => r.name))
    const merged = mergeDiscovered(rows.value, d.players)
    // newly found slots that have exactly one matching yaml are pre-selected
    const fresh = merged.filter((r) => !known.has(r.name))
    const assoc = autoAssociate(fresh, yamls.value, true).rows
    const byName = new Map(assoc.map((r) => [r.name, r]))
    rows.value = merged.map((r) => byName.get(r.name) ?? r)
  } catch (e) {
    discoverError.value = errText(e)
  } finally {
    discovering.value = false
    waking.value = false
  }
}

async function onProbe(): Promise<void> {
  const slot = checkedRows.value[0]?.name ?? rows.value[0]?.name
  if (!slot) {
    probeResult.value = { ok: false, text: 'Choisis au moins un slot pour tester la connexion.' }
    return
  }
  probing.value = true
  probeResult.value = null
  try {
    const url = roomUrl.value.trim()
    const r = await api.testConnection({
      ...(url ? { room_url: url } : { server: server.value.trim() }),
      password: clearPassword.value ? '' : password.value === '' ? null : password.value,
      slot,
    })
    probeResult.value = { ok: r.ok, text: probeMessage(r, slot) }
    if (r.sleeping && room.value) room.value = { ...room.value, sleeping: true }
  } catch (e) {
    probeResult.value = { ok: false, text: errText(e) }
  } finally {
    probing.value = false
  }
}

async function onFiles(ev: Event): Promise<void> {
  const input = ev.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  if (!files.length) return
  uploading.value = true
  uploadLog.value = []
  for (const f of files) {
    try {
      const content = await f.text()
      let r
      try {
        r = await api.uploadYaml(f.name, content)
      } catch (e) {
        if (!(e instanceof api.HttpError) || e.status !== 409) throw e
        if (!window.confirm(`${f.name} existe déjà avec un autre contenu. Le remplacer ?`)) {
          uploadLog.value.push({ ok: false, text: `${f.name} : non remplacé` })
          continue
        }
        r = await api.uploadYaml(f.name, content, true)
      }
      const who = r.players.map((p) => `${p.name} (${p.game})`).join(', ')
      const verb = r.status === 'unchanged' ? 'déjà présent' : r.status === 'replaced' ? 'remplacé' : 'ajouté'
      uploadLog.value.push({ ok: true, text: `${shortYaml(r.path)} ${verb} : ${who}` })
    } catch (e) {
      uploadLog.value.push({ ok: false, text: `${f.name} : ${errText(e)}` })
    }
  }
  input.value = ''
  try {
    await loadConfig()
    onAssociate()
  } finally {
    uploading.value = false
  }
}

function onAssociate(): void {
  const r = autoAssociate(rows.value, yamls.value)
  rows.value = r.rows
  assocInfo.value = r.matched
    ? `${r.matched} slot(s) associé(s) à leur yaml.`
    : 'Aucune nouvelle association (même nom et même jeu requis).'
}

function setVisible(value: boolean): void {
  rows.value = setChecked(rows.value, new Set(visible.value.map((r) => r.name)), value)
}
function checkWithYaml(): void {
  rows.value = rows.value.map((r) => (r.yaml ? { ...r, checked: true } : r))
}

async function onSave(): Promise<void> {
  saving.value = true
  saveError.value = ''
  try {
    await api.putConfig(
      buildPutBody({
        roomUrl: roomUrl.value,
        server: server.value,
        password: { value: password.value, clear: clearPassword.value },
        rows: rows.value,
        wakeRoom: wakeRoom.value,
      }),
    )
    password.value = ''
    clearPassword.value = false
    await refreshMeta()
    emit('saved')
    setView('dashboard')
  } catch (e) {
    saveError.value = errText(e)
  } finally {
    saving.value = false
  }
}

async function onRestore(): Promise<void> {
  if (!window.confirm('Revenir à la configuration enregistrée avant la dernière ? (Elle-même reste récupérable.)')) return
  restoring.value = true
  saveError.value = ''
  try {
    await api.restoreConfig()
    await refreshMeta()
    setView('dashboard')
  } catch (e) {
    saveError.value = errText(e)
  } finally {
    restoring.value = false
  }
}

const diagIcon = { info: Info, warn: TriangleAlert, error: CircleAlert } as const
const diagClass = { info: 'text-muted-foreground', warn: 'text-warn-foreground bg-warn', error: 'text-destructive' } as const
const selectClass =
  'border-input bg-background h-9 w-full min-w-0 rounded-md border px-2 text-sm shadow-xs focus-visible:ring-ring/50 focus-visible:ring-3'
</script>

<template>
  <section class="mx-auto flex max-w-[900px] flex-col gap-4" aria-labelledby="cfg-title">
    <h2 id="cfg-title" class="text-xl font-semibold">Configuration</h2>
    <p v-if="loading" class="text-muted-foreground">Chargement…</p>
    <Alert v-else-if="loadError" variant="destructive" role="alert">
      <AlertDescription>Impossible de lire la configuration : {{ loadError }}</AlertDescription>
    </Alert>
    <form v-else class="flex flex-col gap-4" @submit.prevent="onSave">
      <!-- 1. Room -->
      <Card class="gap-4 py-5">
        <CardHeader class="px-5">
          <CardTitle class="flex items-center gap-2"><Link2 class="size-4" aria-hidden="true" /> Room</CardTitle>
          <CardDescription>Colle le lien de la room archipelago.gg : l'app y lit les slots et le port.</CardDescription>
        </CardHeader>
        <CardContent class="flex flex-col gap-4 px-5">
          <div class="flex flex-col gap-1.5">
            <Label for="cfg-room">Lien de la room</Label>
            <div class="flex flex-wrap gap-2">
              <Input
                id="cfg-room"
                v-model="roomUrl"
                type="url"
                inputmode="url"
                placeholder="https://archipelago.gg/room/…"
                autocomplete="off"
                class="min-w-0 flex-[1_1_240px]"
              />
              <Button type="button" variant="secondary" :disabled="discovering || !roomUrl.trim()" @click="onDiscover()">
                <Search aria-hidden="true" /> {{ discovering ? 'Recherche…' : 'Découvrir les slots' }}
              </Button>
            </div>
            <p v-if="discoverError" class="text-destructive text-sm" role="alert">{{ discoverError }}</p>
          </div>

          <div v-if="room" class="bg-muted/60 flex flex-wrap items-center gap-2 rounded-lg p-3 text-sm" role="status">
            <Badge variant="outline">{{ room.players.length }} slots</Badge>
            <Badge variant="outline">{{ roomGames }} jeux</Badge>
            <Badge v-if="room.server" variant="outline">{{ room.server }}</Badge>
            <template v-if="room.sleeping">
              <Badge variant="warn"><AlarmClock aria-hidden="true" /> Room endormie</Badge>
              <Button type="button" size="sm" variant="outline" :disabled="waking" @click="onDiscover(true)">
                {{ waking ? 'Réveil…' : 'Réveiller la room' }}
              </Button>
              <span class="text-muted-foreground basis-full text-xs">
                Elle redémarre quand quelqu'un ouvre son lien. Réveille-la pour tester la connexion.
              </span>
            </template>
            <Badge v-else variant="good"><CircleCheck aria-hidden="true" /> Room éveillée</Badge>
          </div>

          <details class="text-sm" :open="advanced" @toggle="advanced = ($event.target as HTMLDetailsElement).open">
            <summary class="text-primary min-h-8 cursor-pointer">Avancé : serveur hors archipelago.gg</summary>
            <div class="mt-2 flex flex-col gap-1.5">
              <Label for="cfg-server">Adresse du serveur (host:port)</Label>
              <Input id="cfg-server" v-model="server" type="text" placeholder="192.168.1.10:38281" autocomplete="off" />
              <p class="text-muted-foreground text-xs">Utilisée seulement si le lien de room est vide.</p>
            </div>
          </details>

          <div class="flex flex-col gap-1.5">
            <Label for="cfg-pw">Mot de passe de la room</Label>
            <Input
              id="cfg-pw"
              v-model="password"
              type="password"
              autocomplete="new-password"
              :placeholder="cfg?.has_password ? 'inchangé' : 'aucun'"
              :disabled="clearPassword"
            />
            <div class="flex min-h-8 items-center gap-2">
              <Checkbox id="cfg-pw-clear" v-model="clearPassword" />
              <Label for="cfg-pw-clear" class="font-normal">effacer le mot de passe</Label>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" :disabled="probing || (!roomUrl.trim() && !server.trim())" @click="onProbe">
              <PlugZap aria-hidden="true" /> {{ probing ? 'Test en cours…' : 'Tester la connexion' }}
            </Button>
            <p
              v-if="probeResult"
              :class="cn('text-sm', probeResult.ok ? 'text-good-foreground' : 'text-destructive')"
              role="status"
            >
              {{ probeResult.text }}
            </p>
          </div>

          <div class="flex items-start gap-2">
            <Checkbox id="cfg-wake" v-model="wakeRoom" class="mt-0.5" />
            <div class="flex flex-col gap-0.5">
              <Label for="cfg-wake" class="font-normal">Réveiller automatiquement la room quand elle dort</Label>
              <p class="text-muted-foreground text-xs">
                Désactivé : l'app attend que quelqu'un ouvre la room (elle ne la garde pas allumée).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- 2. Yamls -->
      <Card class="gap-4 py-5">
        <CardHeader class="px-5">
          <CardTitle class="flex items-center gap-2"><FileUp class="size-4" aria-hidden="true" /> Yamls</CardTitle>
          <CardDescription>
            {{ yamls.length }} yaml(s) dans <code class="bg-muted rounded px-1">config/players/</code>. Certains jeux en
            ont besoin pour calculer la logique.
          </CardDescription>
        </CardHeader>
        <CardContent class="flex flex-col gap-3 px-5">
          <div class="flex flex-wrap gap-2">
            <input ref="fileInput" type="file" accept=".yaml,.yml" multiple class="sr-only" aria-label="Importer des yamls" @change="onFiles" />
            <Button type="button" variant="secondary" :disabled="uploading" @click="fileInput?.click()">
              <FileUp aria-hidden="true" /> {{ uploading ? 'Import…' : 'Importer des yamls' }}
            </Button>
            <Button type="button" variant="outline" :disabled="!yamls.length" @click="onAssociate">
              <Wand2 aria-hidden="true" /> Associer automatiquement
            </Button>
          </div>
          <p v-if="assocInfo" class="text-muted-foreground text-sm" role="status">{{ assocInfo }}</p>
          <ul v-if="uploadLog.length" class="flex flex-col gap-1 text-sm" role="status">
            <li v-for="(l, k) in uploadLog" :key="k" :class="l.ok ? 'text-good-foreground' : 'text-destructive'">{{ l.text }}</li>
          </ul>
        </CardContent>
      </Card>

      <!-- 3. Slots -->
      <Card class="gap-4 py-5">
        <CardHeader class="px-5">
          <CardTitle>
            Slots à suivre <span class="text-muted-foreground text-sm font-normal">({{ checkedRows.length }} / {{ rows.length }})</span>
          </CardTitle>
          <CardDescription>Coche tes slots ; le yaml et le joueur se règlent sur les slots cochés.</CardDescription>
        </CardHeader>
        <CardContent class="flex flex-col gap-3 px-5">
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_minmax(0,14rem)]">
            <Input v-model="filterText" type="search" placeholder="Rechercher un slot ou un jeu…" aria-label="Rechercher un slot ou un jeu" />
            <select v-model="filterGame" :class="selectClass" aria-label="Filtrer par jeu">
              <option value="">Tous les jeux</option>
              <option v-for="g in gameOptions" :key="g" :value="g">{{ g }}</option>
            </select>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <div class="flex min-h-8 items-center gap-2 pr-2">
              <Checkbox id="cfg-checked-only" v-model="checkedOnly" />
              <Label for="cfg-checked-only" class="font-normal">Cochés seulement</Label>
            </div>
            <Button type="button" size="sm" variant="outline" :disabled="!visible.length" @click="setVisible(true)">
              Cocher les {{ visible.length }} affichés
            </Button>
            <Button type="button" size="sm" variant="outline" :disabled="!visible.length" @click="setVisible(false)">
              Décocher les affichés
            </Button>
            <Button type="button" size="sm" variant="outline" @click="checkWithYaml">Cocher ceux qui ont un yaml</Button>
          </div>

          <p v-if="!rows.length" class="text-muted-foreground text-sm">Aucun slot. Utilise « Découvrir les slots ».</p>
          <p v-else-if="!visible.length" class="text-muted-foreground text-sm">Aucun slot ne correspond au filtre.</p>
          <ul v-else class="divide-y rounded-lg border">
            <li
              v-for="(r, i) in visible"
              :key="r.name"
              :class="cn('flex flex-col gap-2 px-3 py-2.5', !r.checked && 'opacity-75')"
            >
              <div class="flex items-start gap-2.5">
                <Checkbox :id="`cfg-row-${i}`" v-model="r.checked" class="mt-0.5" :aria-label="`suivre ${r.name}`" />
                <label :for="`cfg-row-${i}`" class="flex min-w-0 flex-1 cursor-pointer flex-col">
                  <span class="font-medium break-words">{{ r.name }}</span>
                  <span class="text-muted-foreground text-xs break-words">{{ r.game || 'jeu inconnu' }}</span>
                </label>
              </div>
              <template v-if="r.checked">
                <div class="grid grid-cols-1 gap-2 pl-6.5 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
                  <label class="text-muted-foreground flex flex-col gap-1 text-xs font-medium">
                    yaml
                    <select v-model="r.yaml" :class="selectClass" :aria-label="`yaml de ${r.name}`">
                      <option value="">aucun</option>
                      <option v-for="y in yamlPaths" :key="y" :value="y">{{ shortYaml(y) }}</option>
                      <option v-if="r.yaml && !yamlPaths.includes(r.yaml)" :value="r.yaml">{{ r.yaml }}</option>
                    </select>
                  </label>
                  <label class="text-muted-foreground flex flex-col gap-1 text-xs font-medium">
                    joueur
                    <Input v-model="r.owner" type="text" list="cfg-owners" placeholder="optionnel" class="h-9" :aria-label="`joueur de ${r.name}`" />
                  </label>
                </div>
                <ul v-if="diags[r.name].length" class="flex flex-col gap-1 pl-6.5">
                  <li
                    v-for="(d, k) in diags[r.name]"
                    :key="k"
                    :class="cn('flex items-start gap-1.5 rounded px-1.5 py-0.5 text-xs', diagClass[d.level])"
                  >
                    <component :is="diagIcon[d.level]" class="mt-px size-3.5 shrink-0" aria-hidden="true" />{{ d.text }}
                  </li>
                </ul>
              </template>
            </li>
          </ul>
          <datalist id="cfg-owners"><option v-for="o in owners" :key="o" :value="o" /></datalist>
        </CardContent>
      </Card>

      <!-- 4. Save -->
      <Card class="gap-3 py-4">
        <CardContent class="flex flex-col gap-3 px-5">
          <p class="text-sm" role="status">
            <strong>{{ summary.count }}</strong> slot(s) suivi(s) · {{ summary.withLogic }} avec logique
            <template v-if="summary.warnings"> · <span class="text-warn-foreground bg-warn rounded px-1">{{ summary.warnings }} avertissement(s)</span></template>
            <template v-if="summary.errors"> · <span class="text-destructive">{{ summary.errors }} erreur(s)</span></template>
          </p>
          <p v-if="saveError" class="text-destructive text-sm" role="alert">{{ saveError }}</p>
          <div class="flex flex-wrap gap-2">
            <Button type="submit" :disabled="!canSave">{{ saving ? 'Enregistrement…' : 'Enregistrer' }}</Button>
            <Button v-if="tracker.slots.length" type="button" variant="outline" @click="setView('dashboard')">Annuler</Button>
            <Button v-if="cfg?.has_backup" type="button" variant="ghost" :disabled="restoring" class="sm:ml-auto" @click="onRestore">
              <RotateCcw aria-hidden="true" /> Restaurer la configuration précédente
            </Button>
          </div>
        </CardContent>
      </Card>
    </form>
  </section>
</template>
