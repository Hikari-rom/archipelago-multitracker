# v2 « Observatoire » de l'interface — design

Date : 2026-10-15. Demandé par Romain après les maquettes Claude Design (étape 2 du brief
`docs/design/BRIEF-claude-design.md`). Maquette de référence : `docs/design/observatoire.dc.html` (copie du fichier
`Observatoire.dc.html` du projet Claude Design ; source de vérité pour les valeurs exactes de couleurs, tailles,
espacements).

## Objectif

Tester au quotidien la direction « Observatoire » avec les vraies données, sans perdre l'interface actuelle.

- La v2 vit à **`/v2`**, la v1 reste à **`/`**, inchangée. Les deux peuvent être ouvertes côte à côte.
- La v2 couvre **tout le design** (11 écrans de la maquette). Journal et Configuration reprennent les composants v1,
  affichés dans le cadre et le thème v2.
- **Aucun changement backend** : mêmes routes `/api/*`, même SSE.
- Réussite : la v2 s'utilise à la place de la v1 sur bureau (1440) et téléphone (390), en thème Nuit et Plan, avec
  tests front et build verts.

Hors périmètre : 3e/4e thème, refonte de Journal et Configuration, suppression de la v1, tokens de l'étape 3 au-delà
de ce que la v2 utilise.

## Architecture

**Un seul point d'entrée, chargement séparé.**

- `src/main.ts` : si `location.pathname` commence par `/v2`, `import('./v2/main')` ; sinon l'app actuelle (et
  `style.css` v1) comme aujourd'hui. Vite découpe en chunks : la v1 ne charge pas le CSS v2 et inversement.
- Le backend sert déjà `index.html` pour tout chemin inconnu (`api.py`, fallback SPA) : `/v2` fonctionne tel quel.
  Les assets sont en chemin absolu (`base: '/'`), donc valides sous `/v2`.
- Mode simulé (`VITE_MOCK=1`) : même aiguillage, pour les captures.

**Partagé, non modifié** : `stores/tracker.ts` (snapshot, SSE, détails, jeu actif choisi, `nowMs`), `lib/*` (tri,
totaux, `splitFeatured`, `compactMain`, historique, objectifs, logique), `lib/api.ts`, `components/ui/*` (shadcn-vue).

**Seule modification du code partagé** :
- `stores/tracker.ts` : `restoreActivity(prev: ActivityOverrides)` pour « Annuler » après « Plus actif ».
- v1 : un lien « Essayer la v2 » (vers `/v2` + le hash courant) dans l'en-tête.

**Nouveau, `src/v2/`** (un fichier = un rôle) :

| Fichier | Rôle |
|---|---|
| `main.ts` | importe `theme.css`, applique le thème v2, monte `AppV2`, démarre le store (ou le mock) |
| `theme.css` | Tailwind + tokens Nuit / Plan (mêmes noms de variables que shadcn : `--background`, `--card`, `--primary`… + tokens v2 : `--logic`, `--done`, `--hint`, `--new`, `--goal`, `--warn`, `--sky-*`), polices, keyframes `twinkle`/`drift` |
| `lib/theme.ts` | `nuit` / `plan` / `auto`, clé `amt-v2-theme` ; « Ciel animé » clé `amt-v2-sky` |
| `lib/prefs.ts` | affichage (`cards`/`focus`), tri, masquer terminés : clés `amt-v2-*` (n'affectent pas la v1) |
| `lib/sky.ts` | génération pure des étoiles (graine fixe, générateur de Park-Miller comme la maquette) |
| `lib/card.ts` | état d'une carte : `active` (auto/choisi), `expiresInMin`, statut logique, erreur, room endormie, libellés |
| `lib/historyDays.ts` | regroupement par jour (Aujourd'hui / Hier / date / « Avant le suivi ») et masquage du jeu source répété |
| `AppV2.vue` | cadre : en-tête, onglets, menus Plus et Thème, barre basse téléphone, bandeau room endormie, routage par `tracker.view` |
| `components/SkyBackground.vue` | ciel deux couches, fixe derrière la page |
| `components/ThemeMenu.vue`, `MoreMenu.vue`, `BottomNav.vue` | menus et navigation |
| `components/TotalsBar.vue`, `RecentStrip.vue` | bandeau totaux + contrôles, fil « Derniers reçus » |
| `components/ActiveCard.vue` | carte pleine largeur d'un jeu actif (Cartes) |
| `components/GameTile.vue` | carte courte de la grille « Où avancer » |
| `components/FocusPanel.vue`, `FocusList.vue` | affichage Focus |
| `components/DetailTabs.vue` | onglets En logique / Nouveaux / Reçus / Hints / But (Focus, carte ouverte, feuille téléphone) |
| `components/DetailSheet.vue` | feuille plein écran des détails (téléphone) |
| `components/UndoToast.vue` | « X n'est plus actif… Annuler », 6 s |
| `views/DashboardV2.vue`, `HistoryV2.vue`, `GoalsV2.vue` | les trois onglets |

Journal et Configuration : `components/LogsView.vue` et `ConfigView.vue` (v1) rendus dans `AppV2`. Ils utilisent les
composants `ui/` et les variables shadcn : les définir dans `theme.css` suffit à les habiller en v2.

## Écrans

Références : sections 2a à 2k de la maquette.

### Cadre
- **Bureau** : barre de 56 px translucide (`rgba(15,22,33,.66)` + flou en Nuit). Logo « AP » + « Multitracker » +
  serveur et lien de la room (cliquer le logo = tableau de bord, remplace le bouton maison). Onglets Tableau /
  Historique / Objectifs (`aria-current`). À droite : « En direct » (état SSE), « Plus ▾ » (Journal, Configuration,
  Revenir à la v1), « ◐ <Thème> ▾ ».
- **Téléphone** (< 700 px) : en-tête court (logo, « N en logique », ◐), barre basse fixe ⌂ Tableau, ↺ Historique,
  ⚑ Objectifs, ⋯ Plus ; cibles ≥ 44 px.
- **Menu Thème** : Nuit (ciel étoilé, sombre), Plan (clair, grille de dessin), Auto (suit le système : Plan ou Nuit),
  interrupteur « Ciel animé » (coupé aussi si `prefers-reduced-motion`). Feuille sur téléphone. Mémorisé par appareil.
- **Room endormie** : bandeau global sous l'en-tête (☾, texte, heure des chiffres affichés, « Réveiller maintenant »,
  même appel que la v1).
- Filtre joueur (`Joueur : tous ▾`) quand plusieurs joueurs sont suivis, comme la v1 (`lib/config`).

### Ciel (`SkyBackground`)
- Thème Nuit uniquement. Fond `radial-gradient(ellipse at 75% -5%, oklch(0.27 0.05 262), oklch(0.18 0.03 258) 50%)`.
- Deux couches d'étoiles en `<span>` positionnés (générés une fois) : lointaine 150 étoiles (bureau) / 55 (téléphone),
  0,8–1,3 px, opacité 0,25–0,6, 15 % scintillent, dérive 260 s ; proche 34 / 14 étoiles, 1,5–2,4 px, opacité 0,5–0,9,
  40 % scintillent, dérive 150 s. Chaque couche fait 200 % de haut, dupliquée, et glisse de −50 % en boucle
  (`transform`, `will-change`), donc aucune reprise visible.
- `position: fixed`, `pointer-events: none`, `aria-hidden`. Animations à `none` si réduit ou interrupteur coupé.
- Thème Plan : pas de ciel, la grille de dessin (28 px, `#C7D0DB` sur `#EAEEF3`) sert de texture.

### Tableau de bord — Cartes (défaut)
- **Bandeau** : « N en logique » (fort), « faits / total », « ★ N nouveaux », « N jeux » ; Tri (Conseillé / En logique
  / % en logique, `lib/dashboard`), Affichage (Cartes / Focus), Masquer terminés, filtre joueur.
- **Derniers reçus** : 5 items (`tracker.recent`), « item → jeu · il y a N », « Tout voir → » = Historique, onglet Reçus.
- **Actifs** (`splitFeatured`) : « ◉ Actifs · N », puis une `ActiveCard` pleine largeur par jeu actif :
  gros chiffre en logique, nom du jeu, « checks en logique · slot · faits / total », pastille d'état
  (◉ Actif · choisi / ◔ Actif · auto · il y a N min), « ● Connecté », « ★ N nouveau(x) · Marquer comme vu »,
  3 premières régions (`in_logic_locations` groupées par `region`, nombre) + « + N régions », « But · <compteur> »,
  « ✕ Plus actif », « Détails ▾ » (ouvre `DetailTabs` dans la carte).
- **Où avancer · N jeux** : grille 3 colonnes (2 entre 700 et 1100 px, 1 en dessous) de `GameTile` : chiffre en
  logique (ou « — »), nom, « slot · N restants », ★N, ◆N (hints en logique), « Logique indisponible », « ◎ Activer ».
  Une tuile ouverte prend 2 colonnes.
- Ordre stable pendant qu'une carte est ouverte ou après « Marquer comme vu » (`stableOrder`, comme la v1).

### Tableau de bord — Focus
- Gauche : carte du jeu actif (`compactMain`) avec gros chiffre, état, « ✕ Plus actif », But, `DetailTabs` ouverts
  sur « En logique » : liste des régions (nombre, ◆ si hintée) et locations de la région choisie, hintées en tête
  avec la note « hint · <item> pour <joueur> ».
- Droite : « N jeux · clic = afficher et rendre actif », tri ; une ligne par jeu (chiffre, nom, ◉ choisi / ◔ auto,
  barre faits/en logique, ◆N ★N, restants). Clic = `pinActive`. Ligne courante surlignée.

### Téléphone
- Cartes : la carte active tient en ~190 px (chiffre, nom, « en logique · faits / total », But, « Détails ↑ ») ; avec
  2 actifs, défilement horizontal à accrochage (« 1 / 2 »). Ensuite le dernier reçu (1 ligne, « › » = Historique),
  puis « Où avancer » en liste compacte.
- Focus : la liste vient juste sous la carte active ; toucher une ligne = `pinActive` et remonte en carte.
- Détails : `DetailSheet` plein écran, onglets fixes, régions repliables, locations hintées en tête.

### États d'une carte (2g)
Calculés par `lib/card.ts` à partir de `SlotSummary`, `tracker.activity`, `tracker.nowMs`, `tracker.activeMinutes`,
`tracker.roomSleeping` :
1. Repos. 2. Survol / focus clavier (anneau `--logic`). 3. Actif auto : « ◔ Actif · auto · N min » et « Expire dans
N min » (= `activeMinutes − (now − last_check_at)`). 4. Choisi : « ◉ Actif · choisi », « Mémorisé sur cet appareil ».
5. Détails ouverts. 6. But atteint : ✓, « But atteint · masquable ». 7. Logique indisponible (`logic.state =
'unavailable'`, chiffre « — »). 8. En calcul (`pending`, « ·· », « Calcul de la logique… »). 9. Avertissement
(`logic.message`, chiffre préfixé « ≈ »). 10. Erreur de connexion (`status` `error`/`disconnected`, `error`, bouton
« Réessayer » = rechargement du snapshot). 11. Room endormie (« ☾ En pause, chiffres de HH:MM »). 12. Après « Plus
actif » : `UndoToast` 6 s, « Annuler » = `restoreActivity(précédent)`.

### Historique (2h, 2f)
- Onglets « Checks envoyés · N » / « Items reçus · N », filtre « Jeu : tous (N) ▾ », « du plus récent au plus
  ancien · pages de 200 » (mêmes appels que la v1, `lib/history`).
- Gauche (bureau) : tableau par jeu (Faits / Envoyés / Reçus, total) ; clic sur une ligne = filtre.
- Liste groupée par jour (`lib/historyDays`) : en-tête « Aujourd'hui · N checks », « Hier », date, « Avant le suivi » ;
  ligne = heure, jeu source (une fois par série consécutive), location, badge PROG / UTILE / PIÈGE (rien = normal),
  item, « pour moi » ou « pour <joueur> · <jeu> » ; « contenu inconnu » si `item` est nul.
- Reçus : item, « pour <jeu> », « de <joueur> · <location> » ou « inventaire de départ ».
- Téléphone : tableau en liste repliable « Par jeu ▾ » à 3 chiffres ; chaque entrée en petite carte.

### Objectifs (2i)
- « N but(s) atteint(s) sur M », filtre joueur, « Masquer les buts atteints ».
- Une carte par jeu, triée par avancement (`lib/goals`) : nom, slot, ✓ But atteint ou pourcentage, « But · résumé »,
  compteurs avec barre, étapes ✓ faite / ○ à faire / ⊘ « invisible pour un tracker ».

## Tokens

Valeurs exactes dans la maquette ; résumé :

| Token | Nuit | Plan |
|---|---|---|
| fond | dégradé `oklch(0.18 0.03 258)` + ciel | `#EAEEF3` + grille `#C7D0DB` |
| surface carte | `rgba(22,32,46,.82)` + bord `rgba(201,211,224,.14)` | `#FFFFFF` + bord `#C7D0DB` |
| texte / secondaire | `#F4F6F9` / `#C9D3E0` | `#16202E` / `#4A5868` |
| en logique (accent) | `#8FA8FF` | `#1B4DFF` |
| fait | `oklch(0.78 0.12 160)` | `#1F7A52` |
| hint en logique ◆ | `oklch(0.80 0.11 340)` | `oklch(0.50 0.17 340)` |
| nouvel item ★ | `oklch(0.83 0.12 82)` | à dériver (même teinte, contraste AA sur blanc) |
| erreur / avertissement ! | `oklch(0.76 0.14 25)` sur fond teinté | même teinte assombrie |

- Polices : système (`system-ui`) pour le texte, JetBrains Mono (Google Fonts) pour libellés, chiffres et méta.
  Gros chiffre en logique 34 px (cartes), texte 13–15 px, méta 10,5–12 px.
- Rayons : 14 px (cartes, panneaux), 6–8 px (boutons, pastilles), 28 px (feuilles téléphone).
- Chaque sens a un **signe** en plus de la couleur (◆ ★ ✓ ! ◉ ◔) : lisible sans distinguer les teintes.
- Contraste WCAG AA vérifié pour chaque paire texte/surface dans les deux thèmes ; en Nuit, le texte est toujours sur
  une surface opaque à ≥ 0,8, jamais directement sur le ciel.

## Erreurs et cas limites
- Serveur injoignable : message d'erreur dans le cadre v2 (comme la v1). Aucune donnée : Configuration.
- 0 jeu actif : pas de section Actifs ; Focus prend le premier jeu du tri.
- Noms longs (« The Legend of Zelda - Phantom Hourglass ») : retour à la ligne sur 2 lignes max puis ellipse, nom
  complet en `title`.
- 1 à ~60 jeux : grille et listes sans limite ; liste Focus défilante.
- Zéro spoiler : la v2 n'affiche que les données déjà exposées par l'API.

## Tests
- vitest : `v2/lib/sky.ts` (nombre, bornes, déterminisme), `v2/lib/card.ts` (12 états, « expire dans »),
  `v2/lib/historyDays.ts` (jours, « Avant le suivi », jeu source masqué), `v2/lib/theme.ts` et `prefs.ts`
  (lecture/écriture, valeurs invalides), `restoreActivity`.
- Rendu (`@vue/test-utils`) : `AppV2` sur chaque vue, `ActiveCard`/`GameTile` sur les états clés, `ThemeMenu`.
- Aiguillage `main.ts` : `/v2` charge la v2, `/` la v1.
- `npm test && npm run build`.
- Captures en mode simulé (`scripts/screenshot.mjs` étendu à `/v2`) : bureau 1440 et téléphone 390, Nuit et Plan,
  tableau Cartes et Focus, Historique, Objectifs → `test-output/screenshots/v2/`.

## Suivi
- `BACKLOG.md` : nouveau jalon « M20 — v2 Observatoire (`/v2`) ». `DECISIONS.md` : D sur « v2 à côté de la v1 sous
  `/v2`, chargement séparé ». `PROGRESS.md` mis à jour à la fin.
