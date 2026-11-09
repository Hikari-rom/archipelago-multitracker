# Infos du tableau de bord au choix — conception

Date : 2026-11-09. Interface concernée : **v2** (tableau de bord), la v1 ne change pas.

## Pourquoi

Des amis de Romain, chacun sur sa propre instance (version portable Windows ou Pi), trouvent le tableau de bord v2
trop chargé. Ils veulent choisir, dans la Configuration, les infos affichées.

Réussite :
- un ami choisit « Essentiel » et obtient un tableau sobre en un clic ;
- il peut affiner info par info ;
- l'affichage actuel de Romain reste disponible à l'identique (« Complet ») et c'est le défaut.

## Décisions

- **Par appareil**, en `localStorage`, dans la carte existante « Configuration › Affichage (sur cet appareil) ».
  Pas de backend : chaque ami a sa propre instance, un réglage serveur n'apporterait presque rien et serait le seul
  réglage d'affichage hors de l'appareil. Un téléphone peut rester en Essentiel et un PC en Complet.
- **Préréglages + détail** : densité Essentiel / Standard / Complet, puis une case par info. Toucher une case qui
  sort des préréglages fait passer en « Personnalisé ».
- **Une case = une info, partout** : « ★ Nouveaux items » décoché masque l'info dans la barre des totaux, les cartes
  actives, les tuiles et la vue Focus.
- **Complet par défaut** : une valeur absente ou illisible donne Complet, l'affichage ne change pour personne tant
  qu'on ne touche pas au réglage.
- **Jamais masqués** : le gros chiffre (checks en logique), le nom du jeu, les alertes (erreur de connexion et son
  bouton « Réessayer », BK, logique approximative, logique indisponible), les couleurs d'état (or, arc-en-ciel,
  rouge), les boutons (Activer, Détails, Plus actif) et les onglets Détails (où « Marquer comme vu » reste
  accessible).
- Hors périmètre : onglets Détails, pages Historique, Indices, Objectifs, Room, Journal, et la v1.

## Les 11 infos

| Clé | Libellé | Où elle disparaît |
|---|---|---|
| `slot` | Nom du slot | sous le nom du jeu : carte active, tuile, panneau Focus |
| `done` | Faits / total | barre des totaux, carte active, panneau Focus |
| `remaining` | Restants | tuile, panneau Focus, liste Focus |
| `newItems` | ★ Nouveaux items | barre des totaux, carte active (avec « Marquer comme vu »), tuile, liste Focus |
| `hints` | ◆ Hints en logique | tuile, liste Focus |
| `regions` | Régions en logique | puces de régions de la carte active |
| `goal` | But et go mode | bloc But (carte active, panneau Focus), puce GO MODE (tuile, puces d'état), total GO |
| `activity` | Activité | puce « Actif · auto / choisi », « Expire dans », « Mémorisé sur cet appareil », « dernier check », « ◉ choisi / ◔ auto » de la liste Focus |
| `connection` | État de connexion | puces « ● Connecté », « Connexion… », « ☾ En pause » (jamais l'erreur) |
| `progress` | Barre de progression | liste Focus |
| `recent` | Bandeau Derniers reçus | haut du tableau de bord (statique ou défilant) |

Dans la barre des totaux, « en logique », le nombre de jeux et le total BK restent toujours affichés.

## Préréglages

| Clé | Essentiel | Standard | Complet |
|---|:-:|:-:|:-:|
| `slot` | | | ✓ |
| `done` | | ✓ | ✓ |
| `remaining` | | | ✓ |
| `newItems` | ✓ | ✓ | ✓ |
| `hints` | ✓ | ✓ | ✓ |
| `regions` | | ✓ | ✓ |
| `goal` | ✓ | ✓ | ✓ |
| `activity` | | | ✓ |
| `connection` | | | ✓ |
| `progress` | | ✓ | ✓ |
| `recent` | | ✓ | ✓ |

Complet = l'affichage d'avant cette fonctionnalité, au pixel près.

## Modèle de données

Nouveau module pur `frontend/src/v2/lib/display.ts` (ni Vue ni stockage) :

- `type InfoKey = 'slot' | 'done' | 'remaining' | 'newItems' | 'hints' | 'regions' | 'goal' | 'activity' | 'connection' | 'progress' | 'recent'`
- `INFO_KEYS: readonly InfoKey[]` dans l'ordre d'affichage de la Configuration, `INFO_LABELS: Record<InfoKey, string>`.
- `type Density = 'essentiel' | 'standard' | 'complet'`, `DENSITY_LABELS`, `PRESETS: Record<Density, readonly InfoKey[]>`
  (table ci-dessus).
- `interface DisplayPrefs { preset: Density | 'custom'; shown: InfoKey[] }`
- `applyPreset(d: Density): DisplayPrefs`
- `toggleInfo(p: DisplayPrefs, key: InfoKey, on: boolean): DisplayPrefs` : si l'ensemble obtenu est exactement celui
  d'un préréglage, `preset` prend ce nom, sinon `'custom'`.
- `presetOf(shown: readonly InfoKey[]): Density | 'custom'` (utilisée par `toggleInfo`).

Stockage dans `frontend/src/v2/lib/prefs.ts`, sur le modèle de `loadHintsSort` :

- clé `amt-v2-display`, JSON `{ preset, shown }` ;
- `loadDisplay()` : absent ou JSON invalide → `applyPreset('complet')` ; préréglage nommé stocké → `applyPreset(nom)`
  (une info ajoutée plus tard suit le préréglage sans migration) ; `custom` → `shown` filtré sur les clés connues ;
- `saveDisplay(p)`.

État partagé : `tracker.display: DisplayPrefs` dans `frontend/src/stores/tracker.ts` (comme `tracker.ticker`), et un
helper `shows(key: InfoKey): boolean` exporté par le store. Les composants le lisent dans leurs `v-if` ; le changement
s'applique tout de suite, sans « Enregistrer », comme les autres réglages de la carte Affichage.

## Composants

Seulement des `v-if` ; aucune mise en page ne change.

- `TotalsBar.vue` : `done`, `newItems`, `goal` (total GO).
- `RecentStrip.vue` : rien n'est rendu si `!shows('recent')`, quel que soit le style choisi.
- `ActiveCard.vue` : `slot`, `done` (le texte de la ligne sous le titre se recompose sans séparateurs orphelins),
  `newItems`, `regions`, `goal`.
- `GameTile.vue` : `slot`, `remaining`, `newItems`, `hints`, `goal` (puce GO MODE).
- `FocusPanel.vue` : `slot`, `done`, `remaining`, `activity` (« dernier check »), `goal`.
- `FocusList.vue` : `activity`, `progress`, `hints`, `newItems`, `remaining`.
- `StateChips.vue` : `activity` ; `connection` pour les états ok, connexion en cours et en pause, la branche erreur
  reste affichée ; `goal` pour les puces GO MODE et « But atteint ». BK, logique approximative et logique
  indisponible restent affichés.

La ligne « checks en logique · slot · x / y faits · n restants » est construite à partir des parties affichées,
jointes par « · », pour ne laisser ni point isolé ni ligne vide.

## Configuration

Dans `frontend/src/components/ConfigView.vue`, carte « Affichage (sur cet appareil) », un nouveau bloc en tête :

```
Infos du tableau de bord
  Densité  [Essentiel] [Standard] [Complet]   · Personnalisé
  ☑ Nom du slot          ☑ ★ Nouveaux items    ☑ Activité
  ☑ Faits / total        ☑ ◆ Hints en logique  ☑ État de connexion
  ☑ Restants             ☑ Régions en logique  ☑ Barre de progression
                         ☑ But et go mode      ☑ Bandeau Derniers reçus
  Le gros chiffre, le nom du jeu et les alertes (erreur, BK, logique
  approximative) restent toujours affichés. Interface v2 seulement.
```

- Densité : sélecteur segmenté au style de Tri / Affichage de `TotalsBar` (`aria-pressed`). Aucun bouton actif et
  étiquette « · Personnalisé » en `custom`.
- Cases : 3 colonnes à partir de 700 px, une seule en dessous ; cibles de 44 px de haut sur téléphone.
- Le menu « Bandeau Derniers reçus » existant est désactivé (`disabled`) quand `recent` est décoché.
- Attributs de test : `data-density="<d>"` sur les boutons, `data-info="<clé>"` sur les cases.

## Tests

Front (`cd frontend && npm test`, vitest + happy-dom) :

- `tests/v2/display.test.ts` : contenu des préréglages ; `toggleInfo` passe en `custom` puis retrouve le nom du
  préréglage quand l'ensemble y revient ; `applyPreset`.
- `tests/v2/prefs.test.ts` : valeur absente et JSON invalide → Complet ; clé inconnue ignorée ; préréglage nommé
  recalculé au chargement ; aller-retour `saveDisplay` / `loadDisplay` en `custom`.
- Composants, avec les fixtures existantes :
  - Essentiel : `GameTile` sans slot ni restants, avec ★ et ◆ ;
  - `StateChips` en erreur de connexion : erreur et « Réessayer » affichés avec `connection` décoché ;
  - `RecentStrip` absent avec `recent` décoché, en statique comme en défilant ;
  - Complet : `TotalsBar` et `ActiveCard` rendent le même HTML qu'avant la fonctionnalité.
- Configuration : « Essentiel » coche les bonnes cases ; décocher une case affiche « Personnalisé » ; recocher la
  revient au préréglage.

Vérifications finales : `npm run build`, puis captures (`node scripts/screenshot.mjs`) en Essentiel, Standard et
Complet, sur PC et téléphone.

## Docs du repo

- `DECISIONS.md` : **D36**, réglage par appareil, Complet par défaut, alertes jamais masquées.
- `BACKLOG.md`, `PROGRESS.md` : entrée de la fonctionnalité.
- `README.md` : une ligne sur les infos au choix dans Configuration › Affichage.
