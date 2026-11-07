# Go mode, but Fall Guys et but manuel — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** descripteur Fall Guys, go mode (calcul, API, affichage arc-en-ciel) et but imposé depuis la Configuration, livrés en v0.2.20.

**Architecture:** le worker de logique (seul process qui importe les mondes AP) calcule `goal_in_logic` et liste les
options de but ; `service.py` en dérive `go_mode` et applique les buts imposés aux objectifs ; la config porte le
réglage global et les choix par slot ; la v2 affiche le tout.

**Tech Stack:** Python 3 / FastAPI / Archipelago 0.6.7 + Universal Tracker ; Vue 3 + Tailwind (v2) ; pytest, vitest.

**Spec:** `docs/superpowers/specs/2026-11-07-go-mode-et-but-manuel-design.md`

## Global Constraints

- Zéro spoiler : `backend/` n'utilise que items reçus, checks, `slot_data`, yaml du joueur, datapackage.
- Code, commentaires, commits en anglais ; interface et docs en français ; noms d'items/options/locations non traduits.
- `goal_override` désactivé par défaut ; sans réglage, aucune carte ne change à part Fall Guys et le go mode.
- Priorité visuelle : or (but atteint) > arc-en-ciel (go mode) > rouge (BK).
- Tests backend : `scripts/test.sh -q [fichiers]` ; front : `cd frontend && npm test && npm run build`.
- Nouveaux ports de test : 38291 et plus.

## Review Focus

- Monde sans condition de victoire et sans location de but connue → `goal_in_logic` null, jamais de go mode.
- Slot dont le but est déjà atteint → pas de go mode (or seulement).
- Slot en go mode avec 0 check en logique → pas affiché BK.
- Valeur de but imposée inconnue de l'option (apworld mis à jour) → ignorée, pas d'erreur de chargement.
- Réglage `goal_override` décoché avec des choix enregistrés → choix gardés dans le fichier mais sans effet.

---

### Task 1: Descripteur Fall Guys

**Files:** Modify `backend/multitracker/goals.py` ; Test `tests/test_goals.py`

- [ ] Test `test_fall_guys_tickets` : slot_data `{"final_round_tickets_required": 30}`, 12 « Final Round Ticket » reçus,
  location « Win a Final Round » non faite → summary `"30 Final Round Tickets, puis gagner une finale"`, counter
  `{"label": "Final Round Tickets", "current": 12, "target": 30}`, dernière étape `done False`.
- [ ] `fall_guys(c) -> Goal` (ticket requis : slot_data puis yaml `final_round_tickets_required`, défaut 25), enregistré
  dans `DESCRIBERS["Fall Guys"]`. Test vert, commit.

### Task 2: `goal_in_logic` dans le worker + validation de référence

**Files:** Modify `backend/multitracker/logic/ut_worker.py`, `backend/multitracker/logic/__init__.py`,
`backend/multitracker/logic/engine.py`, `scripts/testenv/logic_reference.py`, `scripts/testenv/validate_logic.py` ;
Test `tests/test_go_mode.py`

**Interfaces:** Produces `LogicResult.goal_in_logic: bool | None` ; worker result key `"goal_in_logic"` ;
`GOAL_LOCATIONS: dict[str, str]` dans `ut_worker.py` ; `has_real_completion(mw, pid) -> bool`.

- [ ] Tests (fixtures générées existantes, cf. `tests/test_logic_e2e.py`) : Fall Guys via `Worker().handle` — tickets
  < requis → `goal_in_logic False`, = requis → `True` ; un jeu avec condition de victoire (Celeste ou SM64 de
  `tests/fixtures/`) : `False` au départ, `True` avec tous les items de progression ; `has_real_completion` faux pour
  un monde Fall Guys.
- [ ] Implémentation : la condition par défaut se reconnaît à `cond.__code__.co_filename` se terminant par
  `BaseClasses.py`. Location de but : atteignable ou absente de `missing` mais dans le slot.
- [ ] `compare_slot` : référence `multiworld.completion_condition[player](state)` sur l'état de `reference_in_logic`
  (le refactorer pour rendre aussi l'état) ; snapshot gagne `goal_ref`, `goal_tool` ; `goal_over` = outil vrai et
  référence fausse (compté dans `bad`) ; `goal_under` toléré mais rapporté. `validate_logic.py` imprime les deux.
- [ ] Tests verts, commit.

### Task 3: `go_mode` dans l'API

**Files:** Modify `backend/multitracker/service.py`, `backend/multitracker/logic/engine.py` (catalogue `go_mode`),
`config/apworlds.yaml` (au besoin), `docs/API.md` ; Test `tests/test_go_mode.py`

- [ ] Test service (moteur de logique factice comme dans les tests existants de `service.py`) : `go_mode` vrai si
  logique ok + `goal_in_logic` + pas de but ; faux si but atteint, si logique indisponible, si
  `go_mode: false` dans le catalogue.
- [ ] Champ `go_mode` du résumé de slot ; `logic.goal_in_logic` dans `logic.to_json()`. Commit.

### Task 4: But imposé (backend)

**Files:** Modify `backend/multitracker/config.py`, `backend/multitracker/api.py`, `backend/multitracker/goals.py`,
`backend/multitracker/service.py`, `backend/multitracker/logic/ut_worker.py`, `engine.py`, `docs/API.md` ;
Test `tests/test_goal_override.py`

**Interfaces:** `RoomConfig.goal_override: bool = False` ; `SlotConfig.goal: dict[str, str] | None` ;
`LogicRequest.goal: dict[str, str]` ; worker op `{"op": "goal_options", "games": [...]}` →
`{"state": "ok", "options": {game: [{"option", "display", "choices": [str]}]}}` ;
`GoalContext.overrides: dict[str, str]` ; `goals.generic(ctx, option, display, value) -> Goal`.

- [ ] Tests : aller-retour `load/save` de `goal_override` et `goal` ; `goal_options` pour Kingdom Hearts 2 contient
  l'option `Goal` avec `three_proofs` ; `PUT /api/config` refuse une valeur hors choix (400) ; `GoalContext.opt`
  rend l'override avant slot_data ; objectif générique pour un jeu sans descripteur, `source == "manuel"` ; worker :
  `goal` imposé change `request_key` et se retrouve dans le yaml préparé.
- [ ] Implémentation ; override ignoré si `goal_override` faux ou valeur hors choix. Commit.

### Task 5: Front v2

**Files:** Modify `frontend/src/lib/types.ts`, `frontend/src/v2/theme.css`, `frontend/src/v2/lib/tokens.ts`,
`frontend/src/v2/lib/card.ts`, `GoalBlock.vue`, `GoalsV2.vue`, bandeau des totaux, page Configuration ;
Test `frontend/tests/v2/*.test.ts`

- [ ] Tests : `stateClass` → `v2-gold` > `v2-go` > `v2-bk` ; GoalBlock affiche la pastille « GO MODE » ; message
  « But non décrit » + mention de la Configuration quand `goal_options` existe ; sélecteur de but visible seulement
  avec la case cochée.
- [ ] Implémentation d'après la maquette ; `npm test && npm run build`. Commit.

### Task 6: Fall Guys de bout en bout avec le yaml de natazox

**Files:** `tests/test_logic_e2e.py` (ou nouveau test), fixture dans `tests/fixtures/`

- [ ] Génération locale avec `config/players/room/natazox_fall.yaml`, `validate_logic.py "Fall Guys" --yaml …` OK ;
  test e2e : go mode au 30e ticket. Commit.

### Task 7: Campagne go mode, docs, release v0.2.20

- [ ] Campagne `validate_logic.py` (2 runs) sur tous les jeux avec logique ; `go_mode: false` pour un faux positif
  non corrigé. `docs/COMPAT.md`, `DECISIONS.md` (D34), `PROGRESS.md`, `BACKLOG.md`.
- [ ] Tests complets, captures, redémarrage de l'app, commit, tag `v0.2.20`, push, notes de release.
