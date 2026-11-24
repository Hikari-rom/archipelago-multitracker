# Page Configuration en onglets — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer la longue page Configuration par cinq onglets (Slots, Room, Fonctions, Affichage, App), un tableau
des slots sur PC, un panneau par slot sur mobile et une barre d'enregistrement flottante, puis publier v0.2.27.

**Architecture:** L'état et les actions de la page sortent de `ConfigView.vue` dans un composable `useConfigForm()`
(aucun changement de comportement), puis `ConfigView.vue` devient une coquille (titre, résumé, onglets reka-ui,
barre d'enregistrement) qui passe le formulaire à un composant par onglet. Les helpers purs (onglet depuis l'adresse,
filtre des slots, comparaison des corps `PUT`) vont dans `src/lib/config.ts`.

**Tech Stack:** Vue 3.5, reka-ui 2 (`TabsRoot`/`TabsList`/`TabsTrigger`/`TabsContent`, `DialogRoot`), @vueuse/core
(`useMediaQuery`), Tailwind 4 avec les variables de thème shadcn/v2, vitest + happy-dom.

**Spec:** `docs/superpowers/specs/2026-11-21-config-page-design.md`

## Global Constraints

- Couleurs uniquement par les classes de thème (`bg-card`, `bg-popover`, `text-muted-foreground`, `border`,
  `text-primary`, `bg-primary`, `bg-warn`, `text-warn-foreground`, `text-destructive`, `bg-accent`…) : Nuit, Plan et la
  v1 doivent suivre. Aucune couleur en dur.
- Aucun changement backend ni API ; corps de `PUT /api/config` identique à aujourd'hui pour un même état.
- Interface en français, code et commentaires en anglais ; noms d'items/jeux/options jamais traduits.
- Point de rupture mobile/PC : 700 px (`min-[700px]:` / `max-[699px]:`, `useMediaQuery('(min-width: 700px)')`).
- Cibles tactiles mobiles ≥ 44 px (`max-[699px]:min-h-11`), comme le reste de la v2.
- Attributs gardés : `data-slot-list`, `data-goal-needs`, `data-goal-choice`, `data-goal-loading`,
  `data-active-mode`, `data-ticker-style`, `data-hints-layout`, `data-display-infos`.
- Commandes : `cd frontend && npx vitest run <fichiers>` ; avant chaque commit de fin de tâche `npm test && npm run build`.
- Commits sur `main`, messages en anglais, trailers `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` et
  `Claude-Session: https://claude.ai/code/session_01JPoKkm8MGnzEgAJEGmry5N`.

## Review Focus

- Changer d'onglet au milieu d'une saisie garde le brouillon (les `TabsContent` inactifs sont démontés) → test Task 3.
- Première installation (aucune config) : onglet Room, barre visible dès que `canSave`, pas de bouton Annuler vers un
  état vide → test Task 3.
- `#config/xyz` inconnu ou `#config?room=…` ouvert alors que la page est déjà affichée → onglet par défaut / Room → tests Task 1 et 3.
- Erreur d'enregistrement : la barre reste, avec le message → test Task 3.
- Recherche : casse ignorée, porte sur slot, jeu et joueur → test Task 1.

---

### Task 1: Helpers purs (onglet dans l'adresse, filtre des slots, comparaison des corps)

**Files:**
- Modify: `frontend/src/lib/config.ts` (près de `filterRows` et `roomFromLocation`)
- Modify: `frontend/src/stores/tracker.ts:142` (`viewFromHash`) et ajout de `setConfigTab`
- Test: `frontend/tests/config.test.ts`, `frontend/tests/tracker.test.ts`

**Interfaces:**
- Produces:
  - `export type ConfigTab = 'slots' | 'room' | 'fonctions' | 'affichage' | 'app'`
  - `export const CONFIG_TABS: readonly ConfigTab[]` (dans cet ordre)
  - `export function configTabFromHash(hash: string): ConfigTab | null` — `#config/room` → `'room'`,
    `#config/room?room=x` → `'room'`, `#config`, `#config?room=x`, `#config/xyz`, `#hints` → `null`
  - `export function initialConfigTab(o: { hashTab: ConfigTab | null; hasSlots: boolean; prefillRoom: boolean }): ConfigTab`
    — ordre : `hashTab`, puis `'room'` si `prefillRoom || !hasSlots`, sinon `'slots'`
  - `export type SlotMode = 'tracked' | 'all' | 'fix'`
  - `export function slotView(rows: SlotRow[], diags: Record<string, Diag[]>, o: { text: string; mode: SlotMode }): SlotRow[]`
    — `tracked` = cochés ; `fix` = cochés avec un diag `warn`/`error` ; texte sans casse sur `name`, `game`, `owner`
  - `export function sameBody(a: PutConfigBody, b: PutConfigBody): boolean` — égalité profonde, ordre des `slots` ignoré (tri par `name`)
  - `roomFromLocation` accepte aussi `#config/<onglet>?room=…`
  - `viewFromHash` : `/^#config(\/[a-z]+)?(\?|$)/` → `'config'`
  - `export function setConfigTab(tab: ConfigTab): void` (tracker) — `history.replaceState` vers `#config/<tab>`
    (garde `pathname + search`), sans toucher `tracker.view`

- [ ] **Step 1: Tests qui échouent** dans `config.test.ts` :
  - `configTabFromHash` : les six cas ci-dessus.
  - `initialConfigTab` : `{hashTab:'app',hasSlots:false,prefillRoom:true}` → `'app'` ; `{null,false,false}` → `'room'` ;
    `{null,true,true}` → `'room'` ; `{null,true,false}` → `'slots'`.
  - `slotView` : rows A (KH2, coché, owner `kuro`), B (Hades, non coché), C (Jak 3, coché, diag warn) →
    `tracked` = [A, C] ; `all` = [A, B, C] ; `fix` = [C] ; `{text:'KURO', mode:'all'}` = [A] ; `{text:'hades', mode:'tracked'}` = [].
  - `sameBody` : mêmes slots dans un autre ordre → `true` ; `goal_needs` différent → `false` ; `password: 'x'` vs absent → `false`.
  - `roomFromLocation('#config/room?room=https://a', '')` → `'https://a'`.
  Dans `tracker.test.ts` : `location.hash = '#config/fonctions'` puis événement `hashchange` → `tracker.view === 'config'`.
- [ ] **Step 2:** `npx vitest run tests/config.test.ts tests/tracker.test.ts` → FAIL (exports manquants).
- [ ] **Step 3:** Implémenter les signatures ci-dessus.
- [ ] **Step 4:** Mêmes tests → PASS.
- [ ] **Step 5:** `npm test && npm run build`, commit « Add the helpers of the tabbed Configuration page ».

### Task 2: `useConfigForm()` — sortir l'état de la page, avec « changé ? » et « annuler »

**Files:**
- Create: `frontend/src/components/config/form.ts`
- Modify: `frontend/src/components/ConfigView.vue` (script : tout l'état et les actions passent par le composable ; template inchangé)
- Test: `frontend/tests/configform.test.ts`

**Interfaces:**
- Consumes: `sameBody`, `buildPutBody`, `mergeRows`, `autoAssociate`, `withDiscovered` (Task 1 / existant).
- Produces: `export function useConfigForm(): ConfigForm` et `export type ConfigForm = ReturnType<typeof useConfigForm>`.
  Le composable reprend tels quels les refs, computed et fonctions actuels de `ConfigView.vue` (lignes 42–342), avec
  les mêmes noms (`roomUrl`, `rows`, `diags`, `summary`, `canSave`, `onDiscover`, `onProbe`, `onAssociate`,
  `checkWithYaml`, `onGoal`, `onRestore`…), plus :
  - `load(): Promise<void>` — le contenu actuel de `onMounted` (le composant l'appelle dans son `onMounted`)
  - `uploadFiles(files: File[]): Promise<void>` — le cœur de `onFiles` (le composant garde l'`<input type=file>`)
  - `firstSetup: ComputedRef<boolean>` — `!cfg.value?.slots.length`
  - `dirty: ComputedRef<boolean>` — `!sameBody(currentBody(), baseline)` où `baseline` = corps construit depuis la
    config chargée **sans** `autoAssociate` (`mergeRows(c.slots, null)`), mot de passe vide
  - `reset(): void` — remet tous les champs comme après le chargement, `rows` = `mergeRows(c.slots, null)` puis
    `withDiscovered(…, room.players, …)` si la room est découverte ; vide mot de passe, `clearPassword`, `saveError`
  - `save(): Promise<boolean>` — l'actuel `onSave` sans le `setView` (renvoie `true` si enregistré) ; le composant fait
    `emit('saved')` + `setView('dashboard')`

- [ ] **Step 1: Tests qui échouent** dans `configform.test.ts` (fetch simulé comme dans `configview.test.ts`, le
  composable monté dans un petit composant de test) :
  - après `load()`, `dirty === false` quand les yamls n'associent rien ;
  - `rows[0].goalNeeds = false` → `dirty === true` ; `reset()` → `false` et `rows[0].goalNeeds === true` ;
  - `password.value = 'x'` → `dirty === true` ;
  - un yaml `config/players/a.yaml` déclarant le slot `A` du même jeu, slot sans yaml en config → `dirty === true`
    dès le chargement (association automatique à enregistrer) ;
  - un slot découvert non coché ajouté par `onDiscover()` → `dirty === false`.
- [ ] **Step 2:** `npx vitest run tests/configform.test.ts` → FAIL.
- [ ] **Step 3:** Créer `form.ts`, brancher `ConfigView.vue` dessus (rendu identique).
- [ ] **Step 4:** `npx vitest run tests/configform.test.ts tests/configview.test.ts` → PASS.
- [ ] **Step 5:** `npm test && npm run build`, commit « Move the Configuration page state into a composable ».

### Task 3: Coquille en onglets, onglets Room / Fonctions / Affichage / App, barre d'enregistrement

**Files:**
- Modify: `frontend/src/components/ConfigView.vue` (template réécrit), `frontend/src/v2/AppV2.vue:106` (`bottom-nav`)
- Create: `frontend/src/components/config/RoomTab.vue`, `FeaturesTab.vue`, `DisplayTab.vue`, `AppTab.vue`, `SaveBar.vue`
- Create: `frontend/src/components/config/SlotsTab.vue` (pour l'instant : le bloc Yamls + la liste actuelle, déplacés tels quels)
- Test: `frontend/tests/configview.test.ts`

**Interfaces:**
- Consumes: `ConfigForm` (Task 2) en prop `form` pour chaque onglet ; `CONFIG_TABS`, `configTabFromHash`,
  `initialConfigTab`, `setConfigTab` (Task 1) ; `getUpdate()` de `lib/api` pour le point de l'onglet App.
- Produces: `data-config-tab="<onglet>"` sur chaque `TabsTrigger`, `data-tab-dot` sur le point d'attention,
  `data-save-bar` sur la barre, `data-config-summary` sur la ligne de résumé.

Contenu exact (voir la spec, « Ce que la page devient ») :
- Résumé : `{n} suivis · {withLogic} avec logique` + ` · {warnings+errors} à corriger` si > 0 + ` · room éveillée` /
  ` · room endormie` si la room est découverte.
- Libellés d'onglets : `Slots {n}`, `Room`, `Fonctions`, `Affichage` + `(cet appareil)` en `text-muted-foreground`
  masqué sous 700 px, `App`. Points : Slots si à corriger > 0, Room si `room.sleeping` ou `discoverError`, App si
  `getUpdate().available && !running`.
- Fonctions : les quatre cases actuelles (`scoutChecked`, `hintsForeignLogic`, `goalOverride`, `roomDashboard`), titre,
  description actuelle et pastille `Historique` / `Indices` / `Objectifs` / `Plus › Room complète`.
- Affichage : le contenu actuel de la carte Affichage, plus la ligne « Appliqué tout de suite sur cet appareil, rien à enregistrer. »
- App : `UserApworldsPanel` (même `@imported`), `UpdatePanel`, le bouton « Restaurer la configuration précédente » (si `cfg.has_backup`).
- Barre : `fixed inset-x-3 bottom-3 z-30` centrée, `max-w-xl`, `bg-popover border rounded-xl shadow-lg` ; sous 700 px
  en v2, au-dessus de `BottomNav` : nouvelle prop `bottomNav?: boolean` de `ConfigView`, passée à `true` par
  `AppV2.vue`, qui ajoute `max-[699px]:bottom-[76px]` (la v1 n'a pas de barre en bas). Le contenu garde une marge basse
  (`pb-24`) pour que la barre ne cache pas la dernière ligne. La `TabsList` défile horizontalement (`overflow-x-auto`). Visible si `form.dirty || (form.firstSetup && form.canSave)`.
  Texte « Changements non enregistrés » (ou « Nouvelle configuration » en première installation), bouton Annuler
  (`form.reset()`, absent en première installation), bouton Enregistrer (`disabled` si `!canSave`, « Enregistrement… »),
  `saveError` en `text-destructive role="alert"` dans la barre.
- Onglet actif : `initialConfigTab({ hashTab: configTabFromHash(location.hash), hasSlots: !firstSetup, prefillRoom: !!tracker.prefillRoom })`
  au montage ; à chaque changement `setConfigTab(tab)` ; quand `tracker.prefillRoom` change pendant l'affichage → `'room'` ;
  sur `hashchange` avec un onglet reconnu → cet onglet.

- [ ] **Step 1: Tests qui échouent** dans `configview.test.ts` (garder les deux tests existants, ils doivent passer
  sur l'onglet Slots par défaut) :
  - cinq `[role="tab"]` dans l'ordre Slots, Room, Fonctions, Affichage, App ; Slots sélectionné quand il y a des slots ;
  - config sans slots → Room sélectionné, `[data-save-bar]` présent dès que le serveur est rempli, sans bouton « Annuler » ;
  - décocher « fin » du slot A → `[data-save-bar]` présent ; aller sur Room puis revenir sur Slots → la case est toujours décochée ;
    « Annuler » → barre absente, case cochée ;
  - « Enregistrer » → le `PUT /api/config` reçu a le même corps que `buildPutBody` pour cet état (comparer à la main
    `slots[0].goal_needs === false`) ; réponse 500 → barre toujours là avec le message d'erreur ;
  - onglet Fonctions : quatre cases et les pastilles `Historique`, `Indices`, `Objectifs`, `Plus › Room complète` ;
  - `location.hash = '#config/app'` avant le montage → App sélectionné ; `/api/update` `available: true` → `[data-config-tab="app"] [data-tab-dot]`.
- [ ] **Step 2:** `npx vitest run tests/configview.test.ts` → FAIL.
- [ ] **Step 3:** Écrire la coquille et les composants d'onglets.
- [ ] **Step 4:** `npx vitest run tests/configview.test.ts tests/configform.test.ts` → PASS.
- [ ] **Step 5:** `npm test && npm run build`, commit « Split the Configuration page into tabs with a floating save bar ».

### Task 4: Onglet Slots — pastilles, tableau PC, liste et panneau mobile

**Files:**
- Modify: `frontend/src/components/config/SlotsTab.vue`
- Create: `frontend/src/components/config/SlotRowFields.vue` (yaml, joueur, but, fin, diagnostics d'un slot — partagé par la ligne PC et le panneau)
- Create: `frontend/src/components/config/SlotSheet.vue` (panneau mobile, `DialogRoot` de reka-ui comme `v2/components/DetailSheet.vue`)
- Test: `frontend/tests/configslots.test.ts`

**Interfaces:**
- Consumes: `ConfigForm`, `slotView`, `SlotMode` (Task 1).
- Produces: `data-slot-mode="tracked|all|fix"` sur les pastilles, `data-slot-row="<nom>"` sur chaque ligne/rangée,
  `data-slot-sheet` sur le panneau, `data-slot-list` sur le conteneur qui défile (comme aujourd'hui).

Contenu exact :
- Barre d'outils : pastilles `Suivis {n}` (défaut), `Toute la room {rows.length}`, `À corriger {k}` ; recherche
  « Chercher un slot, un jeu, un joueur… » ; boutons « Importer des yamls », « Associer automatiquement »,
  « Cocher ceux qui ont un yaml » ; messages `assocInfo` et `uploadLog` dessous. Le sélecteur « Tous les jeux » et les
  boutons « Cocher/Décocher les affichés » disparaissent.
- PC (`useMediaQuery('(min-width: 700px)')`) : `<table>` dans `data-slot-list` (`max-h-[min(60vh,36rem)] overflow-y-auto`,
  `thead` collé) ; colonnes : case (en-tête = cocher/décocher les affichés, `aria-label="cocher les slots affichés"`) |
  `Slot` (nom en `text-primary`, jeu dessous en `text-muted-foreground text-xs`, diagnostics dessous) | `Yaml` |
  `Joueur` | `But` (seulement si `goalOverride`) | `Fin`. Champs seulement pour un slot coché.
- Mobile : liste dans `data-slot-list` ; une ligne = case, nom, jeu, puis yaml court (`shortYaml`) + ` · fin ✓` si
  `goalNeeds` et jeu avec logique, ou le premier diagnostic `warn`/`error` en `text-warn-foreground`/`text-destructive` ;
  `›` à droite. Toucher la ligne hors case → `SlotSheet` avec titre = nom, jeu, case « Suivi », `SlotRowFields`, bouton OK.
- Aucun résultat : « Aucun slot. Utilise « Découvrir les slots » dans l'onglet Room. » / « Aucun slot ne correspond au filtre. »

- [ ] **Step 1: Tests qui échouent** dans `configslots.test.ts` (fetch simulé ; `window.matchMedia` simulé pour 1280 puis 390) :
  - PC : pastille `tracked` active, seuls les slots cochés en `[data-slot-row]` ; clic `all` → tous ; clic `fix` → le slot
    sans yaml dont le jeu en demande un ; recherche `KURO` → le slot dont le joueur est `kuro` ;
  - PC : la case d'en-tête décoche les slots affichés (et seulement eux) ;
  - PC : colonne `But` absente si `goal_override: false`, présente (avec `[data-goal-choice]`) sinon ;
  - mobile : pas de `<table>` ; clic sur la ligne de A → `[data-slot-sheet]` avec le sélecteur yaml de A ; changer le
    joueur dans le panneau → `form.rows` modifié et barre d'enregistrement visible.
- [ ] **Step 2:** `npx vitest run tests/configslots.test.ts` → FAIL.
- [ ] **Step 3:** Implémenter.
- [ ] **Step 4:** `npx vitest run tests/configslots.test.ts tests/configview.test.ts` → PASS.
- [ ] **Step 5:** `npm test && npm run build`, commit « Show the slots as a table on PC and a list with a sheet on mobile ».

### Task 5: Liens entrants, vérification dans l'app, documentation

**Files:**
- Modify: `frontend/src/components/UpdateBanner.vue` (`onOpen` : `location.hash = '#config/app'` au lieu de `setView('config')` + recherche d'ancre ; l'ancre `UPDATE_ANCHOR` reste pour le défilement)
- Modify: `frontend/scripts/screenshot-v2.mjs` (ajouter `['config-fonctions', '/#config/fonctions', {}]`)
- Modify: `PROGRESS.md`, `DECISIONS.md` (D42), `docs/API.md` rien (pas d'API)
- Test: `frontend/tests/update.test.ts`

- [ ] **Step 1: Test qui échoue** : clic sur « Voir » du bandeau → `location.hash === '#config/app'`.
- [ ] **Step 2:** `npx vitest run tests/update.test.ts` → FAIL. **Step 3:** implémenter. **Step 4:** PASS.
- [ ] **Step 5:** `npm run build`, puis captures de l'app qui tourne (PC 1280 et mobile 390, Nuit et Plan) des
  onglets Slots, Fonctions et du panneau mobile ; vérifier : aucune couleur illisible en Plan, la barre ne cache ni la
  BottomNav ni la dernière ligne (marge basse du contenu), la v1 `/v1#config` s'affiche.
- [ ] **Step 6:** `PROGRESS.md` (une ligne dans l'état), `DECISIONS.md` « D42 — Configuration en onglets » (choix de
  Romain : piste A ; mes choix listés dans la spec), commit « Open the App tab from the update banner and document the tabbed Configuration ».

### Task 6: Release v0.2.27

- [ ] **Step 1:** `cd frontend && npm test && npm run build` → tout passe ; `scripts/test.sh -q tests/test_goal_needs.py tests/test_goal_override.py` → passe (aucun changement backend, contrôle rapide).
- [ ] **Step 2:** `git push`, puis tag annoté `v0.2.27` (message en anglais résumant : tabbed Configuration page,
  hinted item colours in the Hints tab, per-slot victory needs switch) et `git push origin v0.2.27`.
- [ ] **Step 3:** Attendre la fin du workflow `windows.yml` (`gh run watch`), puis `gh release edit v0.2.27 --notes-file`
  avec des notes en français (Configuration en onglets ; couleurs des objets dans l'onglet Hints ; case « fin » par slot).
- [ ] **Step 4:** `bash scripts/overnight/notify.sh "Release v0.2.27" "<résumé>"`.
