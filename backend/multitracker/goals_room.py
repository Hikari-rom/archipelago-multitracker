"""Goal describers of the other games of the room (played by Romain's friends), same rules as goals.py.

Ordered by how many slots of the room play the game. Each one is written from the world's victory rules
(`completion_condition` and the options it reads); progress only from slot_data, the yaml, the items received
and the checked locations.
"""
from __future__ import annotations

import re
from typing import Callable

from .goals import Goal, GoalContext, plural


def upper1(text: str) -> str:
    return text[:1].upper() + text[1:]


def num(c: GoalContext, sd_key: str | None, yaml_key: str | None = None, default: int = 0) -> int:
    try:
        return int(c.opt(sd_key, yaml_key, default) or 0)
    except (TypeError, ValueError):
        return default


def choice(c: GoalContext, sd_key: str | None, yaml_key: str | None, names: dict, default=0):
    """An option that the slot_data gives as a number and the yaml as a name: always the number."""
    value = c.opt(sd_key, yaml_key, default)
    if isinstance(value, str):
        value = names.get(value.lower(), value)
    return value


def checked(c: GoalContext, pred: Callable[[str], bool]) -> tuple[int, int]:
    """(checked, total) of the slot's locations matching `pred`."""
    names = [n for n in c.locations if pred(n)]
    return sum(n in c.checked for n in names), len(names)


def cap(g: Goal, label: str, current: int, target: int | None) -> Goal:
    """A counter that stops at its target (checks beyond what the goal asks do not matter)."""
    return g.counter(label, min(current, target) if target else current, target)


def checks_counter(g: Goal, label: str, pred: Callable[[str], bool], target: int | None = None) -> Goal:
    done, total = checked(g.ctx, pred)
    return cap(g, label, done, total if target is None else target)


# --- 6 slots ---------------------------------------------------------------------------------------------------------

def portal2(c: GoalContext) -> Goal:
    # "Victory" at the end of the last chapter (Chapter 9), reached by finishing its maps in order
    g = Goal(c, "Terminer le dernier niveau (Finale 4)")
    checks_counter(g, "Niveaux terminés", lambda n: n.endswith(" Completion"))
    g.final("Terminer Finale 4", "Finale 4 Completion")
    return g


# --- 4 slots ---------------------------------------------------------------------------------------------------------

def paint(c: GoalContext) -> Goal:
    # the client compares the canvas with the goal image: invisible to a tracker
    image, percent = num(c, "goal_image", "goal_image", 1), num(c, "goal_percent", "goal_percent", 80)
    g = Goal(c, f"Reproduire l'image n° {image} à {percent} % de ressemblance")
    g.final(f"Image à {percent} %")
    return g


# --- 3 slots ---------------------------------------------------------------------------------------------------------

def archipeladoku(c: GoalContext) -> Goal:
    # "Solve Everything": every block unlocked; each solved block is a location
    g = Goal(c, "Résoudre toutes les grilles")
    checks_counter(g, "Blocs résolus", lambda n: True)
    g.final("Tout résoudre (Solve Everything)")
    return g


def peak(c: GoalContext) -> Goal:
    goals = c.opt("goals", "goals", ["Reach Peak"]) or []
    goals = list(goals) if not isinstance(goals, dict) else [k for k, v in goals.items() if v]
    ascent, badges = num(c, "ascent_count", "ascent_count", 4), num(c, "badge_count", "badge_count", 0)
    parts, g = [], None
    labels = {"Reach Peak": f"atteindre le sommet en Ascent {ascent}" if ascent else "atteindre le sommet",
              "Collect Badges": f"{plural(badges, 'badge')}", "24 Karat Badge": "jeter l'Ancient Idol dans la lave du Kiln",
              "Free The Soul": "libérer l'âme du Scoutmaster"}
    parts = [labels[k] for k in ["Reach Peak", "Collect Badges", "24 Karat Badge", "Free The Soul"] if k in goals]
    g = Goal(c, upper1(", ".join(parts) or "Atteindre le sommet"))
    if "Reach Peak" in goals and ascent:
        cap(g, "Progressive Ascent", c.count("Progressive Ascent"), ascent)
    if "Collect Badges" in goals:
        checks_counter(g, "Badges", lambda n: n.endswith(" Badge"), badges)
    if "Free The Soul" in goals:
        g.item("Scoutmaster's Soul reçue", "Scoutmaster's Soul")
    g.final("Objectif atteint")
    return g


def repo(c: GoalContext) -> Goal:
    quota, pellys = num(c, "level_quota", "level_quota", 8), num(c, "pellys_required", "pellys_required", 12)
    valuables, monsters = bool(c.opt("valuable_hunt", "valuable_hunt", False)), bool(c.opt("monster_hunt", "monster_hunt", False))
    parts = [f"{plural(quota, 'niveau', 'niveaux')} dans une même partie"]
    if pellys:
        parts.append(f"{plural(pellys, 'Pelly', 'Pellys')}")
    if valuables:
        parts.append("tous les objets de valeur")
    if monsters:
        parts.append("toutes les âmes de monstres")
    g = Goal(c, upper1(", ".join(parts)))
    levels = ["Swiftbroom Academy Level", "Headman Manor Level", "McJannek Station Level", "Museum of Human Art Level"]
    cap(g, "Niveaux débloqués", sum(c.has(i) for i in levels), len(levels))
    if pellys:
        checks_counter(g, "Pellys extraits", lambda n: n.endswith(" Pelly"), pellys)
    if monsters:
        checks_counter(g, "Âmes de monstres", lambda n: n.endswith(" Soul"))
    if valuables:
        g.step("Tous les objets de valeur extraits", None)
    g.final(f"Terminer {plural(quota, 'niveau', 'niveaux')} dans une même partie")
    return g


# --- 2 slots ---------------------------------------------------------------------------------------------------------

def sub(c: GoalContext, group: str, key: str, yaml_key: str | None = None, default=None):
    """An option kept in a nested dict of the slot_data (e.g. slot_data["options"]["goal"]), then the yaml."""
    nested = c.slot_data.get(group)
    if isinstance(nested, dict) and key in nested:
        c.sources.add("slot_data")
        return nested[key]
    return c.opt(None, yaml_key or key, default)


def adofai(c: GoalContext) -> Goal:
    percent = num(c, "percentage_goal_completion", "percentage_goal_completion", 80)
    levels = [n for n in str(c.slot_data.get("goal_levels") or "").split() if n in c.locations]
    mode = choice(c, "completion_goal", "completion_goal", {"allx": 0, "goallevels": 1}, 0)
    what = "des niveaux X" if mode == 0 else "des niveaux choisis"
    g = Goal(c, f"Finir {percent} % {what}")
    if levels:
        need = max(1, -(-len(levels) * percent // 100))
        cap(g, "Niveaux du but finis", sum(n in c.checked for n in levels), need)
    g.final("Objectif atteint")
    return g


def archipelacode(c: GoalContext) -> Goal:
    meta = c.slot_data.get("metadata") or {}
    need = int(meta.get("EndGoal") or 0)
    if need:
        c.sources.add("slot_data")
    g = Goal(c, f"Résoudre {plural(need, 'problème')}" if need else "Résoudre assez de problèmes")
    cap(g, "Problèmes résolus", len(c.checked & c.locations), need)
    g.final("Objectif atteint")
    return g


def bloons(c: GoalContext) -> Goal:
    medals = num(c, "medalsNeeded", None, 0)
    goal = choice(c, "goal", "goal", {"default": 0, "boss": 1, "elite_boss": 2}, 0)
    where = c.slot_data.get("victoryLocation") or "la carte de victoire"
    how = {0: f"gagner {where} dans la difficulté la plus haute", 1: f"vaincre le boss de {where}",
           2: f"vaincre le boss Elite de {where}"}.get(goal, f"gagner {where}")
    g = Goal(c, f"{plural(medals, 'Medal')}, puis {how}")
    cap(g, "Medals", c.count("Medal"), medals)
    g.final(how[0].upper() + how[1:])
    return g


def blue_prince(c: GoalContext) -> Goal:
    goal = choice(c, "goal_type", "goal_type", {"antechamber": 0, "room46": 1, "sanctum": 2, "ascend": 3, "blueprints": 4}, 0)
    keys = num(c, "goal_sanctum_solves", "goal_sanctum_solves", 8)
    label = {0: "Atteindre l'Antechamber", 1: "Atteindre la Room 46", 2: f"Ouvrir {keys} portes du Sanctum",
             3: "Monter sur le trône (Ascend)", 4: "Trouver les Blue Prints"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal == 2:
        cap(g, "Sanctum Keys", c.count_where(lambda n: n.startswith("SANCTUM KEY")), keys)
    g.final(label)
    return g


BURNOUT_LICENSES = {0: ("Class C", 9), 1: ("Class B", 24), 2: ("Class A", 50), 3: ("Burnout", 90), 4: ("Burnout Elite", 210)}


def burnout(c: GoalContext) -> Goal:
    lic = choice(c, "license_goal", "license_goal",
                 {"c_class": 0, "b_class": 1, "a_class": 2, "burnout": 3, "burnout_elite": 4}, 1)
    name, wins = BURNOUT_LICENSES.get(lic, ("?", 0))
    g = Goal(c, f"Obtenir la licence {name} ({wins} victoires d'épreuves)")
    checks_counter(g, "Épreuves gagnées", lambda n: n.startswith("Win the "), wins)
    g.final(f"Licence {name}", f"License Acquired - {name}")
    return g


def clair_obscur(c: GoalContext) -> Goal:
    goal = sub(c, "options", "goal", "goal", 1)
    if isinstance(goal, str):
        goal = {"paintress": 0, "curator": 1, "painted_love": 2, "simon": 3, "clea": 4}.get(goal, 1)
    label = {0: "Vaincre la Paintress (The Monolith)", 1: "Vaincre le Curator (Lumière)",
             2: "Vaincre Painted Love (Endless Tower, étage 11)", 3: "Vaincre Simon (Renoir's Drafts)",
             4: "Vaincre Clea (Flying Manor)"}.get(goal, "Objectif")
    return Goal(c, label).final(label)


def cookie_clicker(c: GoalContext) -> Goal:
    need = num(c, "advancement_goal", "advancement_goal", 100)
    g = Goal(c, f"{need} succès (achievements, ombres comprises)")
    checks_counter(g, "Succès (checks)", lambda n: n != "Victory Location", need)
    g.final("Objectif atteint", "Victory Location")
    g.note = "Le jeu compte aussi les succès qui ne sont pas des checks : le compteur peut être en retard."
    return g


def geometry_dash(c: GoalContext) -> Goal:
    goal = choice(c, "goal", "goal", {"all_levels": 0, "levels_and_platformers": 1, "platformers": 2, "star": 3,
                                      "moon": 4, "star_and_moon": 5, "demon": 6, "completionist": 7}, 0)
    stars, moons = num(c, "star_goal_amount", None, 0), num(c, "moon_goal_amount", None, 0)
    both, demons = num(c, "star_and_moon_goal_amount", None, 0), num(c, "demon_goal", "demon_goal_amount", 0)
    level = lambda n: n.startswith("Complete ") and not re.match(r"Complete \d+ demons?$", n)  # noqa: E731
    label = {0: "Finir tous les niveaux", 1: "Finir tous les niveaux et les platformers", 2: "Finir tous les platformers",
             3: f"{stars} étoiles", 4: f"{moons} lunes", 5: f"{both} étoiles et lunes",
             6: plural(demons, "demon"), 7: f"Tout finir, {stars} étoiles et {moons} lunes"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal in (0, 1, 2, 7):
        checks_counter(g, "Niveaux finis", level)
    if goal in (3, 7) and stars:
        g.location(f"{stars} étoiles", f"Reach {stars} stars")
    if goal in (4, 7) and moons:
        g.location(f"{moons} lunes", f"Reach {moons} moons")
    if goal == 5 and both:
        g.location(f"{both} étoiles et lunes", f"Reach {both} stars and moons")
    if goal == 6 and demons:
        g.location(plural(demons, "demon"), f"Complete {demons} {'demons' if demons > 1 else 'demon'}")
    g.final("Objectif atteint")
    return g


def haste(c: GoalContext) -> Goal:
    # "A New Future" is locked on the boss of the goal shard (shards 11-14 are the Disaster Shards 1-4)
    shard = num(c, "Shard Goal", "shard_goal", 10)
    name = f"Disaster Shard {shard - 10}" if shard > 10 else f"Shard {shard}"
    g = Goal(c, f"Vaincre le boss du {name}")
    cap(g, "Progressive Shards", c.count("Progressive Shard"), shard - 1)
    g.final(f"Boss du {name}", f"{name} Boss")
    return g


def outer_wilds(c: GoalContext) -> Goal:
    goal = choice(c, "goal", "goal", {"song_of_five": 0, "song_of_the_nomai": 1, "song_of_the_stranger": 2,
                                      "song_of_six": 3, "song_of_seven": 4, "echoes_of_the_eye": 5,
                                      "song_of_the_universe": 6}, 0)
    friends = num(c, "required_friends", "required_friends", 1)
    label = {0: "Atteindre l'Œil", 1: "Atteindre l'Œil après avoir rencontré Solanum",
             2: "Atteindre l'Œil après avoir rencontré le Prisonnier",
             3: "Atteindre l'Œil après avoir rencontré Solanum ou le Prisonnier",
             4: "Atteindre l'Œil après avoir rencontré Solanum et le Prisonnier",
             5: "Rencontrer le Prisonnier et finir Echoes of the Eye",
             6: f"Atteindre l'Œil après avoir rencontré {plural(friends, 'ami')}"}.get(goal, "Objectif")
    return Goal(c, label).final(label)


def satisfactory(c: GoalContext) -> Goal:
    opts = (c.slot_data.get("Data") or {}).get("Options") or {}
    if opts:
        c.sources.add("slot_data")
    goals = opts.get("GoalSelection") or c.yaml.get("goal_selection") or ["Space Elevator Phase"]
    goals = [k for k, v in goals.items() if v] if isinstance(goals, dict) else list(goals)
    every = int(opts.get("GoalRequirement", 0) or 0) == 1 or c.yaml.get("goal_requirement") == "require_all_goals"
    phase = int(opts.get("FinalElevatorPhase") or c.yaml.get("final_elevator_phase") or 0)
    total = int(opts.get("FinalResourceSinkPointsTotal") or 0)
    per_min = int(opts.get("FinalResourceSinkPointsPerMinute") or 0)
    labels = {"Space Elevator Phase": f"Space Elevator, phase {phase}" if phase else "Space Elevator",
              "AWESOME Sink Points (total)": f"{total:,} points d'AWESOME Sink".replace(",", " ") if total else "points d'AWESOME Sink",
              "AWESOME Sink Points (per minute)": f"{per_min:,} points d'AWESOME Sink par minute".replace(",", " ") if per_min else "points d'AWESOME Sink par minute",
              "Exploration Collectables": "les objets d'exploration demandés"}
    parts = [labels.get(k, k) for k in goals]
    g = Goal(c, (" et " if every else " ou ").join(parts) or "Space Elevator")
    for part in parts if len(parts) > 1 else []:
        g.step(part[0].upper() + part[1:], None)
    g.final("Objectif atteint")
    return g


def slime_rancher(c: GoalContext) -> Goal:
    goal = choice(c, "goal_type", "goal_type", {"notes": 0, "7zee": 1, "credits": 2, "mail": 3}, 0)
    mail = num(c, "mail_count", "mail_count", 0)
    label = {0: "Lire les 30 notes", 1: "Acheter tous les rangs 7Zee", 2: "Voir les crédits de fin",
             3: f"{mail} lettres de Casey"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal == 1:
        checks_counter(g, "Achats 7Zee", lambda n: n.startswith("7Zee lv."))
    elif goal == 2:
        regions = ["Dry Reef", "Indigo Quarry", "Moss Blanket", "Glass Desert", "Ancient Ruins"]
        cap(g, "Régions débloquées", sum(c.has(f"Region Unlock: {r}") for r in regions), len(regions))
    elif goal == 3:
        cap(g, "Casey's Letters", c.count("Casey's Letter"), mail)
    g.final(label)
    return g


def subnautica(c: GoalContext) -> Goal:
    goal = c.opt("goal", "goal", "launch")
    goal = {0: "launch", 1: "free", 2: "infected", 3: "drive"}.get(goal, goal)
    label = {"launch": "Quitter la planète (Neptune)", "free": "Désactiver la quarantaine",
             "infected": "Atteindre l'infection maximale", "drive": "Réparer le moteur de l'Aurora"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal == "drive":
        g.final(label, "Repair Aurora Drive")
    else:
        g.final(label)
    return g


def tunic(c: GoalContext) -> Goal:
    if c.opt("hexagon_quest", "hexagon_quest", False):
        need = num(c, "Hexagon Quest Goal", "hexagon_goal", 20)
        g = Goal(c, f"{need} Gold Questagons (Hexagon Quest)")
        cap(g, "Gold Questagons", c.count("Gold Questagon"), need)
        g.final("Objectif atteint")
        return g
    g = Goal(c, "Les 3 Questagons, puis vaincre The Heir")
    hexes = ["Red Questagon", "Green Questagon", "Blue Questagon"]
    cap(g, "Questagons", sum(c.has(h) for h in hexes), 3)
    g.final("Vaincre The Heir")
    return g


def undertale(c: GoalContext) -> Goal:
    route = c.opt("route", "route_required", "neutral")
    route = {0: "neutral", 1: "pacifist", 2: "genocide", 3: "all_routes"}.get(route, route)
    label = {"neutral": "Finir la route neutre", "pacifist": "Finir la route pacifiste",
             "genocide": "Finir la route génocide", "all_routes": "Finir les trois routes"}.get(route, "Objectif")
    g = Goal(c, label)
    if c.opt("key_hunt", "key_hunt", False):
        pieces = num(c, "key_pieces", "key_pieces", 5)
        cap(g, "Key Pieces", c.count("Key Piece"), pieces)
    g.final(label)
    return g



# --- 1 slot ----------------------------------------------------------------------------------------------------------

def g2048(c: GoalContext) -> Goal:
    g = Goal(c, "Faire la tuile 2048")
    merges = [f"Merge {2 ** i}s" for i in range(1, 11)]
    cap(g, "Fusions débloquées", sum(c.has(m) for m in merges), len(merges))
    g.final("Tuile 2048")
    return g


def short_hike(c: GoalContext) -> Goal:
    goal = sub(c, "settings", "goal", "goal", 3)
    goal = {"nap": 0, "photo": 1, "races": 2, "help_everyone": 3, "fishmonger": 4}.get(goal, goal)
    label = {0: "Grimper au sommet de Hawk Peak et faire la sieste", 1: "Se faire photographier au sommet de Hawk Peak",
             2: "Gagner les trois courses d'Avery", 3: "Aider tout le monde", 4: "Pêcher tous les poissons"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal in (0, 1, 3):
        cap(g, "Golden Feathers", c.count("Golden Feather"), 7 if goal == 0 else 12)
    if goal == 2:
        g.final(label, "Hawk Peak Race Reward")
    elif goal == 4:
        g.final(label, "Catch All Fish Reward")
    else:
        g.final(label)
    return g


def bg3(c: GoalContext) -> Goal:
    goal = choice(c, "goal", "goal", {"rescue_halsin": 0, "kill_inquisitor_wwargaz": 1, "act1_user_defined_fights": 2,
                                      "kill_myrkul": 3, "act2_user_defined_fights": 4, "kill_nether_brain": 5,
                                      "act3_user_defined_fights": 6}, 0)
    fights = c.opt("user_defined_fights", "user_defined_fights", []) or []
    label = {0: "Sauver Halsin et le ramener au Bosquet", 1: "Tuer l'Inquisiteur W'wargaz", 3: "Tuer Myrkul",
             5: "Tuer le Cerveau Suprême (Netherbrain)"}.get(goal)
    if label is None:
        act = {2: 1, 4: 2, 6: 3}.get(goal, "?")
        label = f"Gagner les combats choisis de l'acte {act}"
    g = Goal(c, label)
    if goal in (2, 4, 6) and fights:
        g.note = "Combats choisis : " + ", ".join(map(str, fights))
    g.final(label)
    return g


def big_walk(c: GoalContext) -> Goal:
    goal = c.opt("goal", "goal", "big_goodbye")
    goal = {"ending": "big_wall", "gauntlet": "big_goodbye", "second_ending": "big_game", "secret_ending": "big_game",
            "deposits": "big_collection", 0: "big_wall", 1: "big_goodbye", 2: "big_game", 3: "big_collection"}.get(goal, goal)
    gourds = num(c, "gourds_required", "gourds_required", 0)
    label = {"big_wall": "Casser la cloche dans le Big Wall", "big_goodbye": "Finir le Silent Gauntlet (derrière le Big Wall)",
             "big_game": "Atteindre la fin secrète (Spawn Secret Door)",
             "big_collection": f"Placer {gourds} gourdes dans les tours"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal in ("big_wall", "big_goodbye"):
        g.item("Big Wall Door reçue", "Big Wall Door")
    elif goal == "big_game":
        g.item("Spawn Secret Door reçue", "Spawn Secret Door")
    objectives = c.slot_data.get("objectives") or []
    if objectives and c.slot_data.get("lock_endings_until_objectives"):
        g.note = f"La fin est verrouillée tant que les {plural(len(objectives), 'objectif')} du slot ne sont pas faits."
    g.final(label)
    return g


def civ6(c: GoalContext) -> Goal:
    g = Goal(c, "Atteindre l'ère du Futur")
    g.final("Ère du Futur")
    return g


def cloverpit(c: GoalContext) -> Goal:
    goal = choice(c, "goal_type", "goal_type", {"key": 0, "deadline": 1, "memory_packs": 2}, 0)
    if goal == 1:
        dl, times = num(c, "deadline_goal", "deadline_goal", 12), num(c, "deadline_amount", "deadline_amount", 5)
        g = Goal(c, f"Passer la deadline {dl}, {plural(times, 'fois', 'fois')}")
    elif goal == 2:
        packs = num(c, "memory_goal", "memory_goal", 3)
        g = Goal(c, f"Battre {plural(packs, 'memory pack')} différents")
        checks_counter(g, "Memory packs battus", lambda n: n.endswith(" Beat"), packs)
    else:
        good = choice(c, "ending_type", "ending_type", {"skeleton_key_bad_ending": 0, "sacred_key_good_ending": 1}, 0)
        g = Goal(c, "Sortir par la porte avec la clé sacrée (bonne fin)" if good == 1
                 else "Sortir par la porte avec la clé squelette")
        cap(g, "Progressive Skeleton", c.count("Progressive Skeleton"), 5)
        cap(g, "Progressive Drawer", c.count("Progressive Drawer"), 4)
        if good == 1:
            g.item("Charm: Possessed Cell Phone", "Charm: Possessed Cell Phone")
    g.final("Objectif atteint", "Goal Completed")
    return g


LEVEL = re.compile(r"^[1-9hc]-(10|[1-9])$")


def clustertruck(c: GoalContext) -> Goal:
    goal_level = str(c.opt("goal", None, "") or c.yaml.get("goal_level", "")).replace("_", "-")
    start = str(c.slot_data.get("start") or "")
    need = num(c, "goal_requirement", "goal_requirement", 40)
    g = Goal(c, f"{plural(need, 'niveau', 'niveaux')} débloqués, puis finir le niveau {goal_level or '?'}")
    cap(g, "Niveaux débloqués", c.count_where(lambda n: bool(LEVEL.match(n)) and n not in (goal_level, start)), need)
    g.final(f"Finir le niveau {goal_level}" if goal_level else "Objectif atteint")
    return g


def cuphead(c: GoalContext) -> Goal:
    mode = num(c, "mode", "mode", 1) & ~(32 | 64)
    contracts = num(c, "contract_goal_requirements", "contract_goal_requirements", 17)
    ingredients = num(c, "dlc_ingredient_goal_requirements", "dlc_ingredient_goal_requirements", 5)
    label = {1: "Vaincre le Diable", 2: f"{contracts} Soul Contracts", 4: "Vider la boutique de Porkrind",
             8: "Vaincre Chef Saltbaker", 9: "Vaincre le Diable et Chef Saltbaker", 16: f"{ingredients} Ingredients",
             18: f"{contracts} Soul Contracts et {ingredients} Ingredients"}.get(mode, "Vaincre le Diable")
    g = Goal(c, label)
    if mode in (2, 18):
        cap(g, "Soul Contracts", c.count("Soul Contract"), contracts)
    if mode in (16, 18):
        cap(g, "Ingredients", c.count("Ingredient"), ingredients)
    g.final(label)
    return g


def cyberpunk(c: GoalContext) -> Goal:
    goal = choice(c, "completion_goal", "completion_goal", {"complete_any_ending": 0,
                  "complete_any_ending_w_all_side_quests": 1, "complete_only_phantom_liberty_questline": 2}, 0)
    label = {0: "Atteindre une fin", 1: "Atteindre une fin, toutes les quêtes secondaires faites",
             2: "Finir la quête principale de Phantom Liberty"}.get(goal, "Atteindre une fin")
    g = Goal(c, label)
    g.final(label, "Ending Reached" if goal == 0 else None)
    return g


def dredge(c: GoalContext) -> Goal:
    return Goal(c, "Apporter les reliques au Collecteur (fin du jeu)").final("Fin du jeu (The Collector)")


def dead_rising(c: GoalContext) -> Goal:
    goal = sub(c, "options", "goal", "goal", None)
    if goal is None:
        goal = c.opt("goal", "goal", 0)
    goal = {"ending_s": 0, "ending_a": 1, "savior": 2}.get(goal, goal)
    survivors = num(c, "number_of_survivors", "number_of_survivors", 0)
    if goal == 1:
        g = Goal(c, "Fin A : résoudre toutes les affaires et être sur l'héliport à 12h le jour 4")
        g.final("Fin A", "Ending A: Solve all of the cases and be on the helipad at 12pm")
    elif goal == 2:
        g = Goal(c, f"Sauver {survivors} survivants")
        g.final(f"{survivors} survivants sauvés")
    else:
        g = Goal(c, "Fin S : finir l'Overtime et vaincre Brock sur le tank")
        g.final("Fin S", "Ending S: Beat up Brock with your bare fists!")
    return g



def deep_rock(c: GoalContext) -> Goal:
    goal = choice(c, "goal_mode", "goal_mode", {"kill_caretaker": 1, "goldrush": 2, "hunter": 3, "gauntlet": 4}, 1)
    gold, bosses = num(c, "gold_rush_val", "gold_rush_val", 0), num(c, "hunter_bosses", "hunter_bosses", 3)
    stages = num(c, "gauntlet_stages", "gauntlet_stages", 0)
    label = {1: "Vaincre le Caretaker", 2: f"Ramasser {gold} d'or (Gold Rush)" if gold else "Gold Rush",
             3: f"Trophées de {plural(bosses, 'boss', 'boss')} (Hunter)",
             4: f"Finir les {stages} étapes du Gauntlet" if stages else "Finir le Gauntlet"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal == 3:
        done = {n.split(":")[1] for n in c.checked if n.startswith("Hunting Boss Trophy:")}
        cap(g, "Boss chassés", len(done), bosses)
    g.final(label)
    return g


def dome_keeper(c: GoalContext) -> Goal:
    kind = choice(c, "progressionType", "progression_type", {"relic_hunt_no_progression": 0,
                  "relic_hunt_progression_layers": 1, "guild_assignments": 2}, 1)
    if kind == 2:
        n = num(c, "assignmentsAmount", "assignment_amount", 16)
        g = Goal(c, f"Réussir {n} missions de la guilde")
    else:
        g = Goal(c, "Trouver la relique et la ramener au dôme")
    g.final("Objectif atteint")
    return g


def dont_starve(c: GoalContext) -> Goal:
    goal = c.opt("goal", "goal", "survival")
    goal = {0: "survival", 1: "bosses_any", 2: "bosses_all"}.get(goal, goal)
    if goal == "survival":
        days = num(c, "days_to_survive", "days_to_survive", 70)
        g = Goal(c, f"Survivre {days} jours")
    else:
        bosses = c.opt("required_bosses", "required_bosses", []) or []
        bosses = [k for k, v in bosses.items() if v] if isinstance(bosses, dict) else list(bosses)
        word = "un de ces boss" if goal == "bosses_any" else "ces boss"
        g = Goal(c, f"Vaincre {word} : {', '.join(bosses)}" if bosses else "Vaincre les boss demandés")
    g.final("Objectif atteint")
    return g


def donut_county(c: GoalContext) -> Goal:
    need = max([int(n or 0) for n in c.slot_data.get("required_pieces") or []] or [0])
    total = num(c, "total_pieces", None, 0)
    goal = choice(c, "goal_area", "goal_area", {"bossfight": 0, "aftermath": 1}, 0)
    g = Goal(c, f"{need} Quadcopter Pieces, puis " + ("le Boss Fight et l'Aftermath" if goal == 0 else "l'Aftermath"))
    cap(g, "Quadcopter Pieces", c.count("Quadcopter Piece"), need or total)
    if goal == 0:
        g.location("Boss Fight", "Boss Fight")
    g.final("Entrer dans l'Aftermath")
    return g


def gungeon(c: GoalContext) -> Goal:
    sd = c.slot_data
    parts = []
    if sd.get("Dragun", 1):
        parts.append("vaincre le High Dragun")
    if sd.get("Lich", 1):
        parts.append("vaincre la Liche")
    pasts = {1: 4, 2: 6}.get(int(sd.get("Pasts", 1) or 0), 0)
    if pasts:
        parts.append(f"tuer {pasts} passés")
    if sd.get("BaseSecret"):
        parts.append("vaincre Blobulord et le Old King")
    if sd.get("AdvancedGungeon"):
        parts.append("vaincre le Resourceful Rat et l'Advanced Dragun")
    if sd.get("FarewellArms") == 0 and "FarewellArms" in sd:
        parts.append("vaincre Agunim")
    if sd:
        c.sources.add("slot_data")
    g = Goal(c, upper1(", ".join(parts) or "Objectif"))
    if pasts:
        checks_counter(g, "Passés tués", lambda n: n.startswith("Past Clears "), pasts)
    g.final("Objectif atteint")
    return g


def factorio(c: GoalContext) -> Goal:
    goal = c.opt("goal", "goal", "rocket")
    label = "Lancer une fusée avec un satellite" if goal in ("satellite", 1) else "Lancer une fusée"
    return Goal(c, label).final(label)


def fez(c: GoalContext) -> Goal:
    need = num(c, "goal", "goal", 32)
    g = Goal(c, f"{need} cubes, puis finir le jeu")
    cubes = c.count("Golden Cube") + c.count("Anti-Cube") + c.count("Cube Bit") // 8
    cap(g, "Cubes (dorés, anti-cubes, 8 morceaux = 1)", cubes, need)
    g.final("Reconstruire l'hexaèdre (Hex Rebuild)")
    return g


def hades(c: GoalContext) -> Goal:
    defeats = num(c, "hades_defeats_needed", "hades_defeats_needed", 1)
    parts = [f"vaincre Hadès {defeats} fois" if defeats > 1 else "vaincre Hadès"]
    keepsakes = num(c, "keepsakes_needed", "keepsakes_needed", 0) if c.opt("keepsakesanity", "keepsakesanity", 0) else 0
    weapons = num(c, "weapons_clears_needed", "weapons_clears_needed", 0) if c.opt("weaponsanity", "weaponsanity", 0) else 0
    fates = num(c, "fates_needed", "fates_needed", 0) if c.opt("fatesanity", "fatesanity", 0) else 0
    if weapons:
        parts.append(f"avec {plural(weapons, 'arme')}")
    if keepsakes:
        parts.append(f"{keepsakes} keepsakes")
    if fates:
        parts.append(f"{fates} prophéties (Fated List)")
    g = Goal(c, upper1(", ".join(parts)))
    if keepsakes:
        cap(g, "Keepsakes", c.count_where(lambda n: n.endswith(" Keepsake")), keepsakes)
    g.final("Objectif atteint")
    return g



def hades2(c: GoalContext) -> Goal:
    routes = c.opt("goals_required", "goals_required", ["Underworld", "Surface"]) or []
    routes = [k for k, v in routes.items() if v] if isinstance(routes, dict) else list(routes)
    any_mode = choice(c, "goal_mode", "goal_mode", {"all_selected": 0, "any_selected": 1}, 0) == 1
    boss = {"Underworld": "Chronos (Underworld)", "Surface": "Typhon (Surface)", "Nightmare": "Hadès (Nightmare)",
            "Dream": "le boss du Dream Dive"}
    parts = []
    for r in routes:
        wins = num(c, f"{r.lower()}_wins_needed", f"{r.lower()}_wins_needed", 1)
        parts.append(f"vaincre {boss.get(r, r)}" + (f" {wins} fois" if wins > 1 else ""))
    text = (" ou " if any_mode else " et ").join(parts) or "vaincre Chronos"
    if c.opt("goal_requires_zagreus", "goal_requires_zagreus", False):
        text += ", et vaincre Zagreus"
    return Goal(c, upper1(text)).final("Objectif atteint")


def hollow_knight(c: GoalContext) -> Goal:
    goal = sub(c, "options", "Goal", "Goal", 0)
    goal = {"any": 0, "hollowknight": 1, "siblings": 2, "radiance": 3, "godhome": 4, "godhome_flower": 5,
            "grub_hunt": 6}.get(goal, goal)
    grubs = int(c.slot_data.get("grub_count") or sub(c, "options", "GrubHuntGoal", "GrubHuntGoal", 46) or 0)
    label = {0: "Vaincre le Hollow Knight (n'importe quelle fin)", 1: "Vaincre le Hollow Knight",
             2: "Fin Sealed Siblings (vaincre le Hollow Knight avec le Void Heart)", 3: "Vaincre la Radiance",
             4: "Finir le Panthéon de Hallownest (Godhome)",
             5: "Finir le Panthéon de Hallownest avec la Delicate Flower", 6: f"Libérer {grubs} larves (Grub Hunt)"}.get(goal, "Objectif")
    g = Goal(c, label)
    if goal == 6:
        cap(g, "Grubs", c.count("Grub"), grubs)
    g.final(label)
    return g


def inscryption(c: GoalContext) -> Goal:
    goal = choice(c, "goal", "goal", {"full_story_in_order": 0, "full_story_any_order": 1, "first_act": 2}, 0)
    if goal == 2:
        g = Goal(c, "Finir l'acte 1 (vaincre Leshy)")
        g.final("Vaincre Leshy", "Act 1 - Boss Leshy")
        return g
    label = "Finir l'histoire (actes 1 à 3" + (" dans l'ordre" if goal == 0 else ", dans n'importe quel ordre") + ")"
    return Goal(c, label).final("Finir l'épilogue")


def ktane(c: GoalContext) -> Goal:
    g = Goal(c, "Finir toutes les sections, puis désamorcer la bombe finale")
    checks_counter(g, "Sections terminées", lambda n: bool(re.match(r"Section \d+ Completed$", n)))
    g.final("Désamorcer la bombe finale")
    return g



def lego_sw(c: GoalContext) -> Goal:
    minikits, bosses = num(c, "minikit_goal_amount", None, 0), num(c, "defeat_bosses_goal_amount", None, 0)
    levels, kyber = num(c, "goal_area_completion_count", None, 0), bool(c.opt("goal_requires_kyber_bricks", None, False))
    chapter = c.opt("goal_chapter", None, None)
    parts = []
    if minikits > 0:
        parts.append(f"{minikits} Minikits")
    if bosses:
        parts.append(f"vaincre {plural(bosses, 'boss', 'boss')}")
    if levels:
        parts.append(f"finir {plural(levels, 'niveau', 'niveaux')}")
    if kyber:
        parts.append("7 Kyber Bricks")
    text = ", ".join(parts)
    if chapter and chapter != "no_goal_chapter":
        text = f"{text}, puis finir le chapitre {chapter}" if text else f"Finir le chapitre {chapter}"
    g = Goal(c, upper1(text or "Objectif"))
    if minikits > 0:
        have = c.count("Minikit") + 2 * c.count("2 Minikits") + 5 * c.count("5 Minikits") + 10 * c.count("10 Minikits")
        cap(g, "Minikits", have, minikits)
    if kyber:
        cap(g, "Kyber Bricks", c.count("Kyber Brick"), 7)
    if bosses:
        g.step(f"{plural(bosses, 'boss vaincu', 'boss vaincus')}", None)
    if levels:
        g.step(f"{plural(levels, 'niveau fini', 'niveaux finis')}", None)
    g.final(f"Finir le chapitre {chapter}" if chapter and chapter != "no_goal_chapter" else "Objectif atteint")
    return g


def lethal_company(c: GoalContext) -> Goal:
    goal = choice(c, "goal", "goal", {"trophy": 0, "collectathon": 1, "credit_hunt": 2}, 0)
    if goal == 1:
        need = num(c, "collectathonGoal", "collectathon_scrap_goal", 10)
        g = Goal(c, f"Ramasser {need} scraps de collection (Collectathon)")
    elif goal == 2:
        pct = num(c, None, "required_credits", 75)
        g = Goal(c, f"Recevoir {pct} % des Company Credits")
        g.step(f"Company Credits reçus : {c.count('Company Credit')}", None)
    else:
        g = Goal(c, "Ramasser le trophée de chaque lune")
    g.final("Objectif atteint")
    return g


def librarian(c: GoalContext) -> Goal:
    goal = choice(c, "goal", "goal", {"full": 0, "custom": 1, "floor_1": 2, "floor_2": 3}, 0)
    rows = num(c, "goal_row_threshold", "custom_goal_row_count", 0)
    label = {0: "Ranger toute la bibliothèque (les deux étages)", 2: "Ranger l'étage 1",
             3: "Ranger l'étage 2", 1: f"Ranger {rows} rangées" if rows else "Ranger assez de livres"}.get(goal, "Objectif")
    g = Goal(c, label)
    checks_counter(g, "Sections rangées", lambda n: n.startswith("Section Complete: "))
    if goal == 2:
        g.final(label, "Floor 1 Complete")
    elif goal == 3:
        g.final(label, "Floor 2 Complete")
    else:
        g.final(label)
    return g


ROOM_DESCRIBERS: dict[str, Callable[[GoalContext], Goal]] = {
    "Portal 2": portal2,
    "Paint": paint,
    "Archipeladoku": archipeladoku,
    "PEAK": peak,
    "R.E.P.O": repo,
    "A Dance of Fire and Ice": adofai,
    "ArchipelaCode": archipelacode,
    "Bloons TD6": bloons,
    "Blue Prince": blue_prince,
    "Burnout Paradise Remastered": burnout,
    "Clair Obscur Expedition 33": clair_obscur,
    "Cookie Clicker": cookie_clicker,
    "Geometry Dash": geometry_dash,
    "Haste": haste,
    "Outer Wilds": outer_wilds,
    "Satisfactory": satisfactory,
    "Slime Rancher": slime_rancher,
    "Subnautica": subnautica,
    "TUNIC": tunic,
    "Undertale": undertale,
    "2048": g2048,
    "A Short Hike": short_hike,
    "Baldur's Gate 3": bg3,
    "Big Walk": big_walk,
    "Civilization VI": civ6,
    "CloverPit": cloverpit,
    "ClusterTruck": clustertruck,
    "Cuphead": cuphead,
    "Cyberpunk 2077": cyberpunk,
    "DREDGE": dredge,
    "Dead Rising Deluxe Remaster": dead_rising,
    "Deep Rock Galactic": deep_rock,
    "Dome Keeper": dome_keeper,
    "Don't Starve Together": dont_starve,
    "Donut County": donut_county,
    "Enter The Gungeon": gungeon,
    "Factorio": factorio,
    "Fez": fez,
    "Hades": hades,
    "Hades2Rogue": hades2,
    "Hollow Knight": hollow_knight,
    "Inscryption": inscryption,
    "Keep Talking and Nobody Explodes": ktane,
    "Lego Star Wars: The Complete Saga": lego_sw,
    "Lethal Company": lethal_company,
    "Librarian Tidy Up the Arcane Library": librarian,
}
_ = re
