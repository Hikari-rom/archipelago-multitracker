// State and actions of the Configuration page, shared by its tabs. Nothing is saved before save().
import { computed, ref, watch } from 'vue'
import * as api from '../../lib/api'
import {
  autoAssociate,
  buildPutBody,
  diagnose,
  mergeRows,
  probeMessage,
  sameBody,
  withDiscovered,
  withGoal,
  withGoalOptions,
  type ConfigResponse,
  type Diag,
  type DiscoverResponse,
  type PutConfigBody,
  type SlotRow,
  type YamlEntry,
} from '../../lib/config'
import { refreshMeta, tracker } from '../../stores/tracker'

export const shortYaml = (p: string) => p.replace(/^config\/players\//, '')

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

export function useConfigForm() {
  const cfg = ref<ConfigResponse | null>(null)
  const roomUrl = ref('')
  const server = ref('')
  const advanced = ref(false)
  const password = ref('')
  const clearPassword = ref(false)
  const wakeRoom = ref(false)
  const scoutChecked = ref(true)
  const roomDashboard = ref(false)
  const hintsForeignLogic = ref(true)
  const goalOverride = ref(false)
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
  const assocInfo = ref('')

  const saving = ref(false)
  const saveError = ref('')
  const restoring = ref(false)
  /** What is saved on the server, as a PUT body: the page has changes when its own body differs. */
  const baseline = ref<PutConfigBody | null>(null)

  const yamls = computed<YamlEntry[]>(() => cfg.value?.yamls ?? [])
  const games = computed(() => cfg.value?.games ?? {})
  const goalOptions = (game: string) => games.value[game]?.goal_options ?? []
  // Victory conditions the server did not know when the page loaded (its logic worker may be busy): asked apart, so
  // that the page never waits for them.
  const goalLoading = ref(new Set<string>())
  const goalAsked = new Set<string>()
  async function fetchGoalOptions(list: string[]): Promise<void> {
    const todo = [...new Set(list)].filter((g) => g && !goalAsked.has(g) && !games.value[g]?.goal_options)
    if (!todo.length) return
    todo.forEach((g) => goalAsked.add(g))
    goalLoading.value = new Set([...goalLoading.value, ...todo])
    try {
      const res = await api.getGoalOptions(todo)
      if (cfg.value) cfg.value = { ...cfg.value, games: withGoalOptions(cfg.value.games ?? {}, res.games) }
    } catch {
      todo.forEach((g) => goalAsked.delete(g)) // asked again on the next change
    } finally {
      goalLoading.value = new Set([...goalLoading.value].filter((g) => !todo.includes(g)))
    }
  }
  function onGoal(r: SlotRow, option: string, e: Event): void {
    r.goal = withGoal(r.goal ?? {}, option, (e.target as HTMLSelectElement).value)
  }
  const yamlPaths = computed(() => yamls.value.map((y) => y.path))
  const owners = computed(() => [...new Set(rows.value.map((r) => r.owner.trim()).filter(Boolean))].sort())
  const checkedRows = computed(() => rows.value.filter((r) => r.checked))
  const diags = computed(() => {
    const out: Record<string, Diag[]> = {}
    const roomSlots = room.value ? new Set(room.value.players.map((p) => p.name)) : undefined
    for (const r of rows.value) out[r.name] = diagnose(r, yamls.value, games.value, roomSlots)
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
  const firstSetup = computed(() => !cfg.value?.slots.length)

  function currentBody(): PutConfigBody {
    return buildPutBody({
      roomUrl: roomUrl.value,
      server: server.value,
      password: { value: password.value, clear: clearPassword.value },
      rows: rows.value,
      wakeRoom: wakeRoom.value,
      scoutChecked: scoutChecked.value,
      roomDashboard: roomDashboard.value,
      hintsForeignLogic: hintsForeignLogic.value,
      goalOverride: goalOverride.value,
    })
  }
  const dirty = computed(() => !!baseline.value && !sameBody(currentBody(), baseline.value))

  watch(
    () => (goalOverride.value ? checkedRows.value.map((r) => r.game).join('\n') : ''),
    (list) => {
      if (list) void fetchGoalOptions(list.split('\n'))
    },
  )

  /** Puts every field back as saved on the server (rows without the automatic yaml matches). */
  function applySaved(c: ConfigResponse): void {
    roomUrl.value = c.room_url ?? ''
    server.value = c.room_url ? '' : (c.server ?? '')
    advanced.value = !c.room_url && !!c.server
    wakeRoom.value = !!c.wake_room
    scoutChecked.value = c.scout_checked !== false
    roomDashboard.value = !!c.room_dashboard
    hintsForeignLogic.value = c.hints_foreign_logic !== false
    goalOverride.value = !!c.goal_override
    password.value = ''
    clearPassword.value = false
    rows.value = mergeRows(c.slots, null)
  }

  async function loadConfig(): Promise<void> {
    cfg.value = await api.getConfig()
  }

  async function load(): Promise<void> {
    try {
      await loadConfig()
      const c = cfg.value!
      applySaved(c)
      baseline.value = currentBody()
      rows.value = autoAssociate(rows.value, yamls.value).rows
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
    if (roomUrl.value.trim()) await onDiscover()
  }

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

  function reset(): void {
    if (!cfg.value) return
    applySaved(cfg.value)
    if (room.value) rows.value = withDiscovered(rows.value, room.value.players, yamls.value, false)
    saveError.value = ''
  }

  async function onDiscover(wake = false): Promise<void> {
    if (!roomUrl.value.trim()) return
    discovering.value = !wake
    waking.value = wake
    discoverError.value = ''
    try {
      const d = await api.discover(roomUrl.value.trim(), wake)
      room.value = d
      if (d.room_url) roomUrl.value = d.room_url
      rows.value = withDiscovered(rows.value, d.players, yamls.value, firstSetup.value)
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

  async function uploadFiles(files: File[]): Promise<void> {
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

  function checkWithYaml(): void {
    rows.value = rows.value.map((r) => (r.yaml ? { ...r, checked: true } : r))
  }

  /** true when saved. */
  async function save(): Promise<boolean> {
    saving.value = true
    saveError.value = ''
    try {
      const body = currentBody()
      await api.putConfig(body)
      password.value = ''
      clearPassword.value = false
      baseline.value = currentBody()
      await refreshMeta()
      return true
    } catch (e) {
      saveError.value = errText(e)
      return false
    } finally {
      saving.value = false
    }
  }

  /** true when restored. */
  async function onRestore(): Promise<boolean> {
    if (!window.confirm('Revenir à la configuration enregistrée avant la dernière ? (Elle-même reste récupérable.)')) return false
    restoring.value = true
    saveError.value = ''
    try {
      await api.restoreConfig()
      await refreshMeta()
      return true
    } catch (e) {
      saveError.value = errText(e)
      return false
    } finally {
      restoring.value = false
    }
  }

  return {
    cfg, roomUrl, server, advanced, password, clearPassword, wakeRoom, scoutChecked, roomDashboard, hintsForeignLogic,
    goalOverride, rows, loading, loadError, room, discovering, discoverError, waking, probing, probeResult, uploading,
    uploadLog, assocInfo, saving, saveError, restoring, yamls, games, goalOptions, goalLoading, yamlPaths, owners,
    checkedRows, diags, summary, canSave, roomGames, firstSetup, dirty,
    load, loadConfig, reset, onDiscover, onProbe, uploadFiles, onAssociate, checkWithYaml, onGoal, save, onRestore,
  }
}

export type ConfigForm = ReturnType<typeof useConfigForm>
