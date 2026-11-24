<script setup lang="ts">
import { AlarmClock, CircleCheck, PlugZap, Search } from '@lucide/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import type { ConfigForm } from './form'

const props = defineProps<{ form: ConfigForm }>()
const { cfg, roomUrl, server, advanced, password, clearPassword, wakeRoom, room, roomGames, discovering, discoverError, waking, probing, probeResult } = props.form
const { onDiscover, onProbe } = props.form
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-muted-foreground text-sm">Colle le lien de la room archipelago.gg : l'app y lit les slots et le port.</p>
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

    <div v-if="room" class="bg-muted/60 flex flex-wrap items-center gap-2 rounded-lg p-3 text-sm">
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
      <p v-if="probeResult" :class="cn('text-sm', probeResult.ok ? 'text-good-foreground' : 'text-destructive')" role="status">
        {{ probeResult.text }}
      </p>
    </div>

    <div class="flex items-start gap-2">
      <Checkbox id="cfg-wake" v-model="wakeRoom" class="mt-0.5" />
      <div class="flex flex-col gap-0.5">
        <Label for="cfg-wake" class="font-normal">Réveiller automatiquement la room quand elle dort</Label>
        <p class="text-muted-foreground text-xs">Désactivé : l'app attend que quelqu'un ouvre la room (elle ne la garde pas allumée).</p>
      </div>
    </div>
  </div>
</template>
