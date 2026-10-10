<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as api from '../lib/api'
import {
  buildPutBody,
  checkByName,
  mergeDiscovered,
  mergeRows,
  setAll,
  type ConfigResponse,
  type SlotRow,
} from '../lib/config'
import { refreshMeta, setView, tracker } from '../stores/tracker'

const emit = defineEmits<{ saved: [] }>()

const cfg = ref<ConfigResponse | null>(null)
const roomUrl = ref('')
const server = ref('')
const advanced = ref(false)
const password = ref('')
const clearPassword = ref(false)
const rows = ref<SlotRow[]>([])
const filterText = ref('')
const loading = ref(true)
const loadError = ref('')
const discovering = ref(false)
const discoverError = ref('')
const discoverInfo = ref('')
const saving = ref(false)
const saveError = ref('')

const yamls = computed(() => cfg.value?.player_yamls ?? [])
const owners = computed(() => [...new Set(rows.value.map((r) => r.owner.trim()).filter(Boolean))].sort())
const checkedCount = computed(() => rows.value.filter((r) => r.checked).length)
const canSave = computed(() => !saving.value && (roomUrl.value.trim() || server.value.trim()) && checkedCount.value > 0)

onMounted(async () => {
  try {
    cfg.value = await api.getConfig()
    roomUrl.value = cfg.value.room_url ?? ''
    server.value = cfg.value.room_url ? '' : (cfg.value.server ?? '')
    advanced.value = !cfg.value.room_url && !!cfg.value.server
    rows.value = mergeRows(cfg.value.slots, null)
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
})

async function onDiscover() {
  discovering.value = true
  discoverError.value = ''
  discoverInfo.value = ''
  try {
    const d = await api.discover(roomUrl.value.trim())
    if (d.room_url) roomUrl.value = d.room_url
    rows.value = mergeDiscovered(rows.value, d.players)
    discoverInfo.value = `${d.players.length} slot(s) trouvé(s) sur ${d.server}`
  } catch (e) {
    discoverError.value = e instanceof Error ? e.message : String(e)
  } finally {
    discovering.value = false
  }
}

async function onSave() {
  saving.value = true
  saveError.value = ''
  try {
    await api.putConfig(
      buildPutBody({
        roomUrl: roomUrl.value,
        server: server.value,
        password: { value: password.value, clear: clearPassword.value },
        rows: rows.value,
      }),
    )
    password.value = ''
    clearPassword.value = false
    await refreshMeta()
    emit('saved')
    setView('dashboard')
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="config" aria-labelledby="cfg-title">
    <h2 id="cfg-title">Configuration</h2>
    <p v-if="loading" class="muted">Chargement…</p>
    <p v-else-if="loadError" class="error-text" role="alert">Impossible de lire la configuration : {{ loadError }}</p>
    <form v-else class="cfg-form" @submit.prevent="onSave">
      <div class="field">
        <label for="cfg-room">Lien de la room archipelago.gg</label>
        <div class="row">
          <input id="cfg-room" v-model="roomUrl" type="url" inputmode="url" placeholder="https://archipelago.gg/room/…" autocomplete="off" />
          <button type="button" class="btn" :disabled="discovering || !roomUrl.trim()" @click="onDiscover">
            {{ discovering ? 'Recherche…' : 'Découvrir les slots' }}
          </button>
        </div>
        <p v-if="discoverError" class="error-text" role="alert">{{ discoverError }}</p>
        <p v-else-if="discoverInfo" class="muted small" role="status">{{ discoverInfo }}</p>
      </div>

      <details class="field" :open="advanced" @toggle="advanced = ($event.target as HTMLDetailsElement).open">
        <summary>Avancé : serveur hors archipelago.gg</summary>
        <label for="cfg-server">Adresse du serveur (host:port)</label>
        <input id="cfg-server" v-model="server" type="text" placeholder="192.168.1.10:38281" autocomplete="off" />
      </details>

      <div class="field">
        <label for="cfg-pw">Mot de passe de la room</label>
        <input
          id="cfg-pw"
          v-model="password"
          type="password"
          autocomplete="new-password"
          :placeholder="cfg?.has_password ? 'inchangé' : ''"
          :disabled="clearPassword"
        />
        <label class="check"><input v-model="clearPassword" type="checkbox" /> effacer le mot de passe</label>
      </div>

      <div class="field">
        <h3>Slots à suivre <span class="muted small">({{ checkedCount }} / {{ rows.length }})</span></h3>
        <p class="muted small">
          Les jeux dont la logique est calculée ont besoin d'un yaml : choisis-en un dans la liste (les yamls se
          déposent dans <code>config/players/</code> sur le Pi).
        </p>
        <div class="quick">
          <button type="button" class="btn" @click="rows = setAll(rows, true)">Tout cocher</button>
          <button type="button" class="btn" @click="rows = setAll(rows, false)">Tout décocher</button>
          <input v-model="filterText" type="text" placeholder="Nom contenant…" aria-label="Filtre sur le nom du slot" />
          <button type="button" class="btn" :disabled="!filterText.trim()" @click="rows = checkByName(rows, filterText)">
            Cocher les slots de {{ filterText.trim() || '…' }}
          </button>
        </div>
        <p v-if="!rows.length" class="muted">Aucun slot. Utilise « Découvrir les slots ».</p>
        <ul v-else class="rows">
          <li v-for="(r, i) in rows" :key="r.name" class="srow" :class="{ off: !r.checked }">
            <label class="check pick">
              <input v-model="r.checked" type="checkbox" :aria-label="`suivre ${r.name}`" />
              <span class="who"><strong>{{ r.name }}</strong><span class="muted small">{{ r.game }}</span></span>
            </label>
            <label class="mini">yaml
              <select v-model="r.yaml" :aria-label="`yaml de ${r.name}`">
                <option value="">aucun</option>
                <option v-for="y in yamls" :key="y" :value="y">{{ y.replace(/^config\/players\//, '') }}</option>
                <option v-if="r.yaml && !yamls.includes(r.yaml)" :value="r.yaml">{{ r.yaml }}</option>
              </select>
            </label>
            <label class="mini">joueur
              <input v-model="r.owner" type="text" list="cfg-owners" placeholder="optionnel" :aria-label="`joueur de ${r.name}`" :data-i="i" />
            </label>
          </li>
        </ul>
        <datalist id="cfg-owners"><option v-for="o in owners" :key="o" :value="o" /></datalist>
      </div>

      <p v-if="saveError" class="error-text" role="alert">{{ saveError }}</p>
      <div class="row">
        <button type="submit" class="btn primary" :disabled="!canSave">{{ saving ? 'Enregistrement…' : 'Enregistrer' }}</button>
        <button v-if="tracker.slots.length" type="button" class="btn" @click="setView('dashboard')">Annuler</button>
      </div>
    </form>
  </section>
</template>
