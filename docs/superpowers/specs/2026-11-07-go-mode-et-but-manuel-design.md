# Go mode, but de Fall Guys et but choisi à la main — conception

Date : 2026-11-07. Release visée : **v0.2.20** (avec la correction Super Mario Odyssey D33, déjà sur `main`).
Maquette du go mode : https://claude.ai/artifact/5GJkE37M2mAJTQLMfGePVu

## Pourquoi

- **Fall Guys** : un joueur de la room (natazox) ne voyait pas où il en était de ses Final Round Tickets. L'app n'a
  pas de descripteur d'objectif pour Fall Guys : sa carte affiche « But non décrit pour ce jeu », alors que le but est
  connu (`slot_data.final_round_tickets_required` tickets, puis gagner une finale : location « Win a Final Round »,
  que le client n'envoie qu'avec assez de tickets).
- **But choisi à la main** : quand l'app se trompe de but ou ne le trouve pas, l'utilisateur doit pouvoir le
  choisir. L'automatique reste prioritaire ; le manuel n'existe que par un réglage de la Configuration, désactivé par
  défaut.
- **Go mode** : signaler qu'un jeu peut être terminé avec ce qu'on a déjà, et qu'il « n'y a plus qu'à y aller ».

## Objectifs

1. Descripteur Fall Guys : compteur « Final Round Tickets x / N », étape finale « Gagner une finale (Win a Final
   Round) ». Testé avec le yaml de natazox (`config/players/room/natazox_fall.yaml`), sur le serveur de test local.
2. Go mode calculé par le worker de logique pour chaque slot suivi dont la logique est active, exposé par l'API,
   affiché en arc-en-ciel (même structure que l'or du but atteint : bord, filet intérieur, halo qui respire).
3. But manuel : réglage global « Choisir le but à la main » (désactivé par défaut) ; une fois activé, la
   Configuration permet, slot par slot, d'imposer une des conditions de victoire possibles du jeu.

## Non-objectifs

- Pas de go mode pour les jeux sans logique (OoT, jeux non validés), ni pour les slots des autres joueurs (tableau de
  bord de la room complète, page Indices).
- Pas de notification ntfy ni d'événement dans le fil « Derniers reçus » au passage en go mode (idée pour plus tard).
- Pas de saisie libre d'un but (item + nombre, location au choix) : seulement les valeurs de l'option de but du jeu.

## Anti-objectifs (ce qui serait un échec même si « ça marche »)

- Un go mode affiché alors que la victoire n'est pas atteignable (faux positif). Un go mode en retard est acceptable
  (même règle que la logique minorée, D32).
- Un spoiler : le go mode n'utilise que ce que la logique utilise déjà (items reçus, checks, `slot_data`, yaml).
- Un but manuel qui s'active tout seul, ou qui change la carte d'un utilisateur qui n'a rien réglé.

## Go mode

### Calcul (worker, `SlotLogic.in_logic`)

Avec l'état déjà calculé (items reçus collectés, adaptateurs appliqués, événements balayés) :

1. Si le monde a une vraie condition de victoire (`multiworld.completion_condition[pid]` n'est pas le
   `lambda state: True` posé par défaut par `BaseClasses.MultiWorld`), `goal_in_logic = condition(state)`.
2. Sinon, si le jeu a une location de but connue (table `GOAL_LOCATIONS`, ex. `"Fall Guys": "Win a Final Round"`),
   `goal_in_logic` = cette location est atteignable (ou déjà faite).
3. Sinon `goal_in_logic = None` (inconnu : pas de go mode).

Le résultat du worker gagne `goal_in_logic: true | false | null`. `LogicResult` et `logic.to_json()` le portent.

### Exposition (API)

`SlotSummary.go_mode: bool` = logique `ok` **et** `goal_in_logic is True` **et** but pas encore atteint
(`goal: false`) **et** le jeu n'a pas `go_mode: false` dans `config/apworlds.yaml`. Documenté dans `docs/API.md`.

### Validation

`scripts/testenv/logic_reference.py` compare aussi le go mode à chaque sphère : la référence évalue la condition de
victoire du multiworld complet sur le même état que `reference_in_logic`. Un go mode de l'outil sans go mode de la
référence est une erreur (`over`) ; l'inverse est un retard (`under`, toléré avec `--lower-bound`). Une campagne
sur tous les jeux avec logique (2 runs chacun au moins) ; un jeu qui donne un faux positif non corrigeable reçoit
`go_mode: false` dans `config/apworlds.yaml` et une ligne dans `docs/COMPAT.md`.

### Affichage (v2)

D'après la maquette :

- Carte (Cartes, Focus, carte active) : classe `v2-go` — bord arc-en-ciel qui défile lentement, filet intérieur,
  halo flou qui respire ; pastille « GO MODE » à côté du nom du jeu. Couleurs arc-en-ciel tirées des jetons du
  thème (pastel en Nuit, soutenues en Plan). `prefers-reduced-motion` : tout est figé.
- Priorités : but atteint (or) > go mode (arc-en-ciel) > BK (rouge). Un jeu en go mode sans check en logique n'est
  pas « bloqué » : il ne s'affiche pas en BK.
- Ligne « But » de la carte et page Objectifs : barre arc-en-ciel et pastille « GO MODE ».
- Bandeau des totaux : « N jeux en go mode » quand N > 0.
- La v1 (`/v1`) n'est pas modifiée.

## But choisi à la main

### Conditions de victoire possibles

Le worker (seul à importer les mondes) répond à une nouvelle requête `{"op": "goal_options", "games": [...]}` : pour
chaque jeu, les options `Choice` de son `options_dataclass` dont le nom évoque le but (`goal`, `victory`,
`completion`, `win_condition`, `ending`…, insensible à la casse), avec leur `display_name` et leurs valeurs
(clé de l'option, non traduite). Un jeu sans telle option n'a pas de but à choisir. Le serveur garde la réponse en
cache par jeu (elle ne change qu'avec l'apworld).

### Configuration

- `config/room.yaml` : `goal_override: false` (global) et, par slot, `goal: {<option>: <valeur>}` (facultatif).
- `GET /api/config` : `goal_override`, `slots[].goal`, et `games[<jeu>].goal_options` (liste ci-dessus).
- `PUT /api/config` : mêmes champs ; une valeur hors des choix de l'option est refusée (400). Changer le but d'un
  slot relance seulement le calcul de sa logique (comme un changement de yaml, D29).
- Page Configuration : une case « Choisir le but à la main » (désactivée par défaut). Cochée, chaque slot dont le jeu
  a des conditions de victoire possibles montre un sélecteur « But : automatique | <valeurs> ». Décochée, les choix
  enregistrés sont gardés mais ignorés.

### Effet d'un but imposé (réglage actif et valeur choisie)

- **Objectifs** : la valeur imposée passe avant `slot_data` et yaml dans `GoalContext.opt()` pour cette option ; la
  source affichée devient « manuel ». Un jeu sans descripteur obtient un objectif générique
  (« <display_name> : <valeur> », étape finale « Objectif atteint »).
- **Logique et go mode** : le monde est régénéré avec cette valeur (dans le yaml préparé, ou dans le yaml vide que
  Universal Tracker écrit en mode `slot_data`). Si le `slot_data` du monde fixe déjà l'option, c'est lui qui
  gagne pour la logique (il dit ce que la seed a vraiment) ; l'objectif affiché suit le choix manuel.

### Quand le but reste introuvable

La carte garde son affichage actuel (« But non décrit pour ce jeu »). Si le jeu a des conditions de victoire
possibles, le message ajoute qu'on peut le choisir dans la Configuration (réglage « Choisir le but à la main »).

## Tests

- `tests/test_goals.py` : Fall Guys (compteur, étape, slot_data de natazox) ; override dans `opt()` ; objectif
  générique.
- Worker : `goal_in_logic` sur un monde avec condition de victoire, sur Fall Guys (location de but), `None` sinon ;
  `goal_options`.
- Config : lecture/écriture de `goal_override` et `goal`, refus d'une valeur invalide.
- Bout en bout Fall Guys avec le yaml de natazox (serveur de test, port ≥ 38291) : tickets reçus un à un, go mode
  dès le 30e.
- Front : classes de carte (or > go > BK), pastille, bandeau, sélecteur de la Configuration ; `npm test && npm run
  build`.

## Laissé au constructeur

Noms exacts des classes et composants, découpage des commits, liste exacte des motifs du nom d'option de but,
texte précis des messages (en français, « tu » comme le reste de l'interface).
