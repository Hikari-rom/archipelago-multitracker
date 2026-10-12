"""Goal of each slot and how far it is ("Objectifs" page and the goal line of the dashboard cards).

No spoiler: only the slot_data, the player's yaml, the items the slot received, its checked locations and the
names of its locations are used. Each game has its own describer (written from the world's victory rules); a game
without one only gets the "goal reached" status sent by the server.

Result of `describe()`:
    {"summary": "40 Lucky Emblems, puis Final Xemnas",       # one line for the dashboard card
     "counters": [{"label": "Lucky Emblems", "current": 23, "target": 40}],
     "steps": [{"label": "Vaincre Final Xemnas", "done": False}],  # done None: not visible to a tracker
     "source": "slot_data"}                                       # where the options came from
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

MISSING = object()


@dataclass
class GoalContext:
    game: str
    slot_data: dict[str, Any]
    yaml: dict[str, Any]  # options of the player's yaml for this game (only values that are not random)
    received: Counter  # item name -> copies received
    checked: set[str]  # names of the slot's checked locations
    locations: set[str]  # names of all the slot's locations (checked or not)
    goal: bool  # the server says the slot reached its goal
    checked_ids: set[int] = field(default_factory=set)  # ids of the checked locations
    sources: set[str] = field(default_factory=set)

    def opt(self, sd_key: str | None, yaml_key: str | None = None, default: Any = None) -> Any:
        """Option value: slot_data first (what the generator really used), then the yaml, then `default`."""
        if sd_key and sd_key in self.slot_data:
            self.sources.add("slot_data")
            return self.slot_data[sd_key]
        if yaml_key and yaml_key in self.yaml:
            self.sources.add("yaml")
            return self.yaml[yaml_key]
        return default

    def has(self, item: str, count: int = 1) -> bool:
        return self.received[item] >= count

    def count(self, *items: str) -> int:
        return sum(self.received[i] for i in items)

    def count_where(self, pred: Callable[[str], bool]) -> int:
        return sum(n for name, n in self.received.items() if pred(name))


class Goal:
    def __init__(self, ctx: GoalContext, summary: str) -> None:
        self.ctx = ctx
        self.summary = summary
        self.counters: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []
        self.note: str | None = None  # explanation shown once under the summary

    def counter(self, label: str, current: int, target: int | None, detail: str | None = None) -> Goal:
        if target is not None and target > 0:
            entry = {"label": label, "current": int(current), "target": int(target)}
            if detail:
                entry["detail"] = detail
            self.counters.append(entry)
        return self

    def step(self, label: str, done: bool | None) -> Goal:
        self.steps.append({"label": label, "done": True if self.ctx.goal else done})
        return self

    def location(self, label: str, location: str) -> Goal:
        """Step done when the location is checked (unknown when it is not a real location of the slot)."""
        known = location in self.ctx.locations
        return self.step(label, (location in self.ctx.checked) if known else None)

    def item(self, label: str, item: str, count: int = 1) -> Goal:
        return self.step(label, self.ctx.has(item, count))

    def final(self, label: str, location: str | None = None) -> Goal:
        """Last step: the goal itself (from the server), or its location when it is a real one of the slot."""
        done = self.ctx.goal or (location in self.ctx.checked if location in self.ctx.locations else False)
        self.steps.append({"label": label, "done": done})
        return self

    def to_json(self) -> dict[str, Any]:
        source = " + ".join(sorted(self.ctx.sources)) or None
        out = {"summary": self.summary, "counters": self.counters, "steps": self.steps, "source": source}
        if self.note:
            out["note"] = self.note
        return out


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


# --- describers, one per game (keyed by the exact game name) ------------------------------------------------------

def kh2(c: GoalContext) -> Goal:
    goal = c.opt("Goal", "Goal", 0)
    goal = {"three_proofs": 0, "lucky_emblem_hunt": 1, "hitlist": 2, "hitlist_and_lucky_emblem": 3}.get(goal, goal)
    emblems = int(c.opt("LuckyEmblemsRequired", "LuckyEmblemsRequired", 0) or 0)
    bounties = int(c.opt("BountyRequired", "BountyRequired", 0) or 0)
    xemnas = bool(c.opt("FinalXemnas", "FinalXemnas", True))
    proofs = ["Proof of Connection", "Proof of Nonexistence", "Proof of Peace"]
    parts = {0: "les 3 Proofs", 1: f"{emblems} Lucky Emblems", 2: plural(bounties, "Bounty", "Bounties"),
             3: f"{emblems} Lucky Emblems et {plural(bounties, 'Bounty', 'Bounties')}"}
    g = Goal(c, parts.get(goal, "?") + (", puis Final Xemnas" if xemnas else ""))
    if goal == 0:
        g.counter("Proofs", sum(c.has(p) for p in proofs), 3)
        for p in proofs:
            g.item(p, p)
    if goal in (1, 3):
        g.counter("Lucky Emblems", c.count("Lucky Emblem"), emblems)
    if goal in (2, 3):
        g.counter("Bounties", c.count("Bounty"), bounties)
    if xemnas:
        g.final("Vaincre Final Xemnas")
    else:
        g.final("Objectif atteint")
    return g


def sm64(c: GoalContext) -> Goal:
    stars = int(c.opt("StarsToFinish", None, 0) or 0)
    all_bowsers = c.opt("CompletionType", "completion_type", 0) in (1, "all_bowser_stages")
    g = Goal(c, f"{stars} Power Stars, puis " + ("les 3 niveaux de Bowser" if all_bowsers else "Bowser in the Sky"))
    g.counter("Power Stars", c.count("Power Star"), stars)
    prog = c.count("Progressive Key")
    g.step("Basement Key", c.has("Basement Key") or prog >= 1)
    g.step("Second Floor Key", c.has("Second Floor Key") or prog >= 2)
    if all_bowsers:
        g.step("Bowser in the Dark World", None).step("Bowser in the Fire Sea", None)
    g.final("Vaincre Bowser in the Sky")
    return g


CELESTE_GOAL_AREAS = {
    "7a": "The Summit A - Level Clear", "7b": "The Summit B - Level Clear", "7c": "The Summit C - Level Clear",
    "9a": "Core A - Level Clear", "9b": "Core B - Level Clear", "9c": "Core C - Level Clear",
    "10a": "Farewell - Crystal Heart?", "10b": "Farewell - Level Clear", "10c": "Farewell - Golden Strawberry",
}


def celeste(c: GoalContext) -> Goal:
    required = int(c.opt("strawberries_required", None, 0) or 0)
    area = str(c.opt("goal_area", None, "7a"))
    location = CELESTE_GOAL_AREAS.get(area, "")
    area_name = location.split(" - ")[0] if location else area
    g = Goal(c, f"{required} fraises, puis {area_name}" if required else f"Finir {area_name}")
    g.counter("Strawberry", c.count("Strawberry"), required)
    if location:
        g.location(f"Finir {area_name} ({location})", location)
    g.final("Épilogue (Granny's House Keys)")
    return g


JAK_GOALS = {69: "Traverser Fire Canyon", 87: "Traverser Mountain Pass", 89: "Traverser Lava Tube",
             86: "Vaincre Klaww", 112: "Vaincre Gol et Maia", 116: "Ouvrir la porte des 100 Power Cells"}
JAK_GOAL_NAMES = {"cross_fire_canyon": 69, "cross_mountain_pass": 87, "cross_lava_tube": 89, "defeat_klaww": 86,
                  "defeat_gol_and_maia": 112, "open_100_cell_door": 116}


def jak(c: GoalContext) -> Goal:
    goal = c.opt("jak_completion_condition", "jak_completion_condition", 112)
    goal = JAK_GOAL_NAMES.get(goal, goal)
    gates = [("Fire Canyon", int(c.opt("fire_canyon_cell_count", "fire_canyon_cell_count", 20))),
             ("Mountain Pass", int(c.opt("mountain_pass_cell_count", "mountain_pass_cell_count", 45))),
             ("Lava Tube", int(c.opt("lava_tube_cell_count", "lava_tube_cell_count", 72)))]
    cells = c.count("Power Cell")
    upto = {69: 1, 86: 1, 87: 2, 89: 3, 112: 3, 116: 3}.get(goal, 3)
    target = 100 if goal == 116 else gates[upto - 1][1]
    g = Goal(c, JAK_GOALS.get(goal, "Objectif du jeu"))
    g.counter("Power Cells", cells, target)
    for name, need in gates[:upto]:
        g.step(f"{need} Power Cells pour traverser {name}", cells >= need)
    if goal in (86, 87, 89, 112, 116):
        g.location("Vaincre Klaww", "MP: Defeat Klaww")
    g.final(JAK_GOALS.get(goal, "Objectif atteint"))
    return g


BALATRO_STAKES = ["White Stake", "Red Stake", "Green Stake", "Black Stake", "Blue Stake", "Purple Stake",
                  "Orange Stake", "Gold Stake"]
BALATRO_WIN = re.compile(r"^(.+) Ante 8 (\w+ Stake)$")


def balatro(c: GoalContext) -> Goal:
    goal = c.opt("goal", "goal", 0)
    goal = {"beat_decks": 0, "unlock_jokers": 1, "beat_ante": 2, "beat_decks_on_stake": 3,
            "win_with_jokers_on_stake": 4, "beat_unique_decks": 5}.get(goal, goal)
    stake_n = int(c.opt("required_stake", None, 1) or 1)
    stake = BALATRO_STAKES[stake_n - 1] if 1 <= stake_n <= 8 else "White Stake"
    wins = [m.groups() for m in (BALATRO_WIN.match(n) for n in c.checked) if m]
    decks = int(c.opt("decks_win_goal", "decks_win_goal", 0) or 0)
    if goal in (0, 3):
        ok = [d for d, s in wins if goal == 0 or BALATRO_STAKES.index(s) >= BALATRO_STAKES.index(stake)]
        g = Goal(c, f"Gagner avec {plural(decks, 'deck')}" + (f" en {stake} ou plus" if goal == 3 else ""))
        g.counter("Decks gagnants", len(set(ok)), decks)
    elif goal == 5:
        unique = int(c.opt("unique_deck_win_goal", "unique_deck_win_goal", 0) or 0)
        g = Goal(c, f"{unique} victoires différentes (deck + stake)")
        g.counter("Victoires différentes", len(set(wins)), unique)
    elif goal == 2:
        g = Goal(c, f"Battre l'ante {c.opt('ante_win_goal', 'ante_win_goal', 8)}")
    else:
        jokers = int(c.opt("jokers_unlock_goal", "jokers_unlock_goal", 0) or 0)
        g = Goal(c, f"Débloquer {jokers} jokers" + (f", puis gagner en {stake}" if goal == 4 else ""))
    g.final("Objectif atteint")
    return g


def pokemon_bw(c: GoalContext) -> Goal:
    options = c.slot_data.get("options") or {}
    if options:
        c.sources.add("slot_data")
    goal = options.get("goal", c.yaml.get("goal", "ghetsis"))
    labels = {"ghetsis": "Vaincre Ghetsis", "champion": "Devenir Champion (vaincre Alder)",
              "cynthia": "Vaincre Cynthia (Undella Town)", "cobalion": "Vaincre ou capturer Cobalion",
              "tmhm_hunt": "Montrer toutes les CT/CS au scientifique de Castelia City",
              "seven_sages_hunt": "Trouver les sept Sages", "legendary_hunt": "Vaincre ou capturer les légendaires",
              "pokemon_master": "Remplir tous les autres objectifs"}
    label = labels.get(goal, str(goal))
    g = Goal(c, label)
    badges = ["Trio Badge", "Basic Badge", "Insect Badge", "Bolt Badge", "Quake Badge", "Jet Badge",
              "Freeze Badge", "Legend Badge"]
    if goal in ("ghetsis", "champion", "pokemon_master"):
        g.counter("Badges", sum(c.has(b) for b in badges), 8)
    g.final(label)
    return g


def pokemon_platinum(c: GoalContext) -> Goal:
    badges = ["Coal Badge", "Forest Badge", "Cobble Badge", "Fen Badge", "Relic Badge", "Mine Badge",
              "Icicle Badge", "Beacon Badge"]
    c.opt("goal", "goal", 0)
    g = Goal(c, "Devenir Champion (Conseil 4 et Cynthia)")
    g.counter("Badges", sum(c.has(b) for b in badges), 8)
    g.final("Entrer au Panthéon (Hall of Fame)")
    return g


def pokepark(c: GoalContext) -> Goal:
    options = c.slot_data.get("options") or {}
    if options:
        c.sources.add("slot_data")
    goal = options.get("goal", {"mew": 0, "postgame": 1}.get(c.yaml.get("goal"), 0))
    prisma = c.count_where(lambda n: n.endswith(" Prisma"))
    if goal == 1:
        g = Goal(c, "Compléter tous les Prismas (après-jeu)")
        g.counter("Prismas", prisma, 14)
        g.final("Compléter les Prismas")
        return g
    need = int(options.get("num_required_prisma_count_skygarden", c.yaml.get("num_required_prisma_count_skygarden", 14)))
    g = Goal(c, f"{need} Prismas pour le Skygarden, puis gagner l'amitié de Mew")
    g.counter("Prismas", prisma, need)
    g.final("Mew Power Competition (Skygarden)")
    return g


def phantom_hourglass(c: GoalContext) -> Goal:
    goal = c.opt("goal_requirements", "goal_requirements", 1)
    goal = {"triforce_door": 0, "defeat_bosses": 1, "metal_hunt": 2}.get(goal, goal)
    metals = list(c.slot_data.get("boss_reward_items_pool") or [])
    need_metals = int(c.opt("required_metals", None, 0) or 0)
    if goal == 1:
        dungeons = list(c.slot_data.get("required_dungeons") or [])
        g = Goal(c, f"Vaincre les boss de {plural(len(dungeons) or int(c.opt('dungeons_required', 'dungeons_required', 3)), 'donjon')}, puis Bellum")
        for dungeon, location in zip(dungeons, c.slot_data.get("required_dungeon_locations") or []):
            g.location(f"{dungeon} ({location})", location)
    elif goal == 2:
        total = int(c.opt("metal_hunt_required", "metal_hunt_required", 0) or 0)
        g = Goal(c, f"Trouver {total} métaux rares, puis Bellum")
    else:
        g = Goal(c, "Ouvrir la porte de la Triforce")
    if metals and need_metals:
        g.counter("Métaux rares (pour Zauz)", sum(c.received[m] for m in metals), need_metals)
    g.final("Vaincre Bellum" if goal in (1, 2) else "Ouvrir la porte de la Triforce")
    return g


ORI_BF_TREES = ["WallJumpSkillTree", "ChargeFlameSkillTree", "DashSkillTree", "GrenadeSkillTree",
                "DoubleJumpSkillTree", "BashSkillTree", "StompSkillTree", "GlideSkillFeather", "ChargeJumpSkillTree",
                "ClimbSkillTree"]


def ori_bf(c: GoalContext) -> Goal:
    goals = c.opt("goal", "goal", ["AllSkillTrees"])
    goals = [goals] if isinstance(goals, str) else list(goals or [])
    labels = {"AllSkillTrees": "les 10 arbres de compétence", "AllMaps": "toutes les cartes",
              "WarmthFragments": "les fragments de chaleur", "WorldTour": "les reliques"}
    escape = bool(c.opt("require_final_escape", "require_final_escape", True))
    g = Goal(c, "Trouver " + " et ".join(labels.get(x, x) for x in goals) + (", puis la fuite du mont Horu" if escape else ""))
    if "AllSkillTrees" in goals:
        g.counter("Arbres de compétence", sum(t in c.checked for t in ORI_BF_TREES), len(ORI_BF_TREES))
    if "WarmthFragments" in goals:
        g.counter("Warmth Fragments", c.count("WarmthFragment"), int(c.opt("warmth_fragments_required", "warmth_fragments_required", 0) or 0))
    if "WorldTour" in goals:
        g.counter("Relics", c.count("Relic"), int(c.opt("relic_count", "relic_count", 0) or 0))
    if "AllMaps" in goals:
        g.step("Toutes les cartes", None)
    g.final("Fuir le mont Horu" if escape else "Objectif atteint")
    return g


ORI_WOTW_TREES = ["MarshSpawn.RegenTree", "MarshSpawn.DamageTree", "HowlsDen.SwordTree", "HowlsDen.DoubleJumpTree",
                  "MarshPastOpher.BowTree", "WestHollow.DashTree", "EastHollow.BashTree", "GladesTown.DamageTree",
                  "InnerWellspring.GrappleTree", "UpperPools.SwimDashTree", "UpperReach.LightBurstTree",
                  "LowerDepths.FlashTree", "LowerWastes.BurrowTree", "WeepingRidge.LaunchTree"]
ORI_WOTW_FINAL = ["Double Jump", "Dash", "Bash", "Grapple", "Glide", "Burrow", "Launch"]


def ori_wotw(c: GoalContext) -> Goal:
    goals = [k for k in ("trees", "wisps", "quests", "relics") if c.opt(f"goal_{k}", None, False)]
    if not goals:
        y = c.yaml.get("goal") or ["trees"]
        goals = [y] if isinstance(y, str) else list(y)
    labels = {"trees": "les 14 arbres", "wisps": "les 5 Wisps", "quests": "les quêtes", "relics": "les reliques"}
    g = Goal(c, "Trouver " + " et ".join(labels.get(x, x) for x in goals) + ", puis vaincre Shriek")
    if "trees" in goals:
        g.counter("Arbres", sum(t in c.checked for t in ORI_WOTW_TREES), len(ORI_WOTW_TREES))
    owned = sum(c.has(a) for a in ORI_WOTW_FINAL) + (1 if c.has("Sword") or c.has("Hammer") else 0)
    g.counter("Capacités pour Shriek", owned, len(ORI_WOTW_FINAL) + 1,
              "Sword ou Hammer, Double Jump, Dash, Bash, Grapple, Glide, Burrow, Launch")
    if "wisps" in goals:
        g.step("Les 5 Wisps", None)
    g.final("Vaincre Shriek")
    return g


def jak3(c: GoalContext) -> Goal:
    mode = c.opt("jak_3_completion_condition", "jak_3_completion_condition", 1)
    mode = {"complete_specific_mission": 1, "complete_number_of_missions": 2}.get(mode, mode)
    if mode == 2:
        n = int(c.opt("number_of_missions_for_completion", "number_of_missions_for_completion", 0) or 0)
        g = Goal(c, f"Finir {n} missions")
        g.final(f"{n} missions finies")
        return g
    mission = c.opt("specific_mission_for_completion", "specific_mission_for_completion", 71)
    mission = {"defeat_robot_in_mines": 25, "defeat_errol_in_factory": 60, "defeat_final_boss": 71}.get(mission, mission)
    label = {25: "Vaincre le robot des mines", 60: "Vaincre Errol dans l'usine", 71: "Vaincre le boss final"}.get(mission, "Finir la mission demandée")
    g = Goal(c, label)
    if mission == 71:
        g.final(label, "Destroy final boss")
    else:
        g.final(label)
    return g


KH_BBS_WORLDS = ["Dwarf Woodlands", "Castle of Dreams", "Enchanted Dominion", "The Mysterious Tower", "Radiant Garden",
                 "Mirage Arena", "Olympus Coliseum", "Deep Space", "Realm of Darkness", "Never Land", "Disney Town"]


def kh_bbs(c: GoalContext) -> Goal:
    char = c.opt("character", "character", 2)
    char = {"ventus": 0, "aqua": 1, "terra": 2}.get(str(char).lower(), char)
    final_terra = bool(c.opt("final_terranort", "final_terra_xehanort_ii", False))
    finals = {0: ("Ventus", "(V) The Keyblade Graveyard Defeat Final Vanitas", "Vaincre Vanitas (forme finale)"),
              1: ("Aqua", "(A) The Keyblade Graveyard Defeat Ventus-Vanitas", "Vaincre Ventus-Vanitas"),
              2: ("Terra", "(T) The Keyblade Graveyard Defeat Terra-Xehanort", "Vaincre Terra-Xehanort")}
    name, location, label = finals.get(char, finals[2])
    if char == 1 and final_terra:
        location, label = "(A) Radiant Garden Defeat Final Terra-Xehanort II", "Vaincre Final Terra-Xehanort II"
    g = Goal(c, f"{name} : 3 Wayfinders et 8 mondes pour la Keyblade Graveyard, puis {label[0].lower() + label[1:]}")
    for w in ("Wayfinder Ventus", "Wayfinder Aqua", "Wayfinder Terra"):
        g.item(w, w)
    g.counter("Mondes débloqués", sum(c.has(w) for w in KH_BBS_WORLDS), 8)
    g.final(label, location)
    return g


def minecraft(c: GoalContext) -> Goal:
    required = int(c.opt("advancements_required", "advancements_required", 0) or 0)
    bosses = c.opt("boss_list", "boss_list", []) or []
    bosses = [str(b).split(":")[-1].replace("_", " ").title() for b in bosses]
    ids = set((c.slot_data.get("locations") or {}).values())
    done = len(ids & c.checked_ids)
    g = Goal(c, (f"{required} advancements" if required else "") + (" et " if required and bosses else "")
             + (("vaincre " + ", ".join(bosses)) if bosses else ""))
    g.counter("Advancements", done, required)
    g.final(("Vaincre " + ", ".join(bosses)) if bosses else "Objectif atteint")
    return g


def mkwii(c: GoalContext) -> Goal:
    cups = int(c.opt("cups_required_for_goal", "cups_required_for_goal", 8) or 0)
    cc = c.opt("goal_cc", "goal_cc", 2)
    cc = ["50cc", "100cc", "150cc", "Mirror"][cc] if isinstance(cc, int) and 0 <= cc < 4 else str(cc)
    diff = c.opt("goal_difficulty", "goal_difficulty", 2)
    diffs = ["3e place", "2e place", "1re place", "1 étoile", "2 étoiles", "3 étoiles"]
    diff = diffs[diff] if isinstance(diff, int) and 0 <= diff < 6 else str(diff).replace("_", " ")
    g = Goal(c, f"{plural(cups, 'coupe')} en {cc} ({diff} ou mieux)")
    g.counter("Victory Trophy", c.count("Victory Trophy"), cups)
    g.final("Objectif atteint")
    return g


SMO_GATES = [("Cascade", 5, "Sand"), ("Sand", 16, "Lake"), ("Lake", 8, "Wooded"), ("Wooded", 16, "Lost"),
             ("Lost", 10, "Metro"), ("Metro", 20, "Snow"), ("Snow", 10, "Seaside"), ("Seaside", 10, "Luncheon"),
             ("Luncheon", 18, "Ruined"), ("Ruined", 3, "Bowser's"), ("Bowser's", 8, "Moon")]


def odyssey(c: GoalContext) -> Goal:
    goal = c.opt("goal", "goal", 0)
    goal = {"mushroom_kingdom": 0, "festival": 1}.get(goal, goal)
    gates = SMO_GATES[:5] if goal == 1 else SMO_GATES
    g = Goal(c, "Festival de New Donk City" if goal == 1 else "Vaincre Bowser et arriver au royaume Champignon")
    g.note = "Pour quitter un royaume, il faut assez de Power Moons de ce royaume (une Multi-Moon compte 3)."
    for kingdom, need, to in gates:
        moons = c.count(f"{kingdom} Kingdom Power Moon") + 3 * c.count(f"{kingdom} Kingdom Multi-Moon")
        g.counter(f"{kingdom} → {to}", min(moons, need), need)
    if goal == 1:
        g.final("A Traditional Festival!", "Metro: A Traditional Festival!")
    else:
        g.final("Arrive in the Mushroom Kingdom", "Arrive in the Mushroom Kingdom")
    return g


OOT_BRIDGE = {0: "ouvert", 1: "vanilla (médaillons Shadow et Spirit)", 2: "{stones} Spiritual Stones",
              3: "{medallions} médaillons", 4: "{rewards} récompenses de donjon", 5: "{tokens} Gold Skulltula Tokens",
              6: "{hearts} cœurs"}
OOT_GANON_BK = {0: "pas de Boss Key de Ganon", 8: "Boss Key de Ganon à la Light Arrow Cutscene",
                9: "Boss Key de Ganon : {stones} Spiritual Stones", 10: "Boss Key de Ganon : {medallions} médaillons",
                11: "Boss Key de Ganon : {rewards} récompenses", 12: "Boss Key de Ganon : {tokens} Gold Skulltula Tokens",
                13: "Boss Key de Ganon : {hearts} cœurs"}


def oot(c: GoalContext) -> Goal:
    sd = c.slot_data
    if sd:
        c.sources.add("slot_data")
    if sd.get("triforce_hunt"):
        g = Goal(c, f"Triforce Hunt : {sd.get('triforce_goal')} Triforce Pieces")
        g.counter("Triforce Pieces", c.count("Triforce Piece"), int(sd.get("triforce_goal") or 0))
        g.final("Objectif atteint")
        return g
    vals = {k: sd.get(f"bridge_{k}") for k in ("stones", "medallions", "rewards", "tokens", "hearts")}
    bridge = OOT_BRIDGE.get(sd.get("bridge"), "?").format(**vals)
    bk_vals = {k: sd.get(f"ganon_bosskey_{k}") for k in ("stones", "medallions", "rewards", "tokens", "hearts")}
    bk = OOT_GANON_BK.get(sd.get("shuffle_ganon_bosskey"), "Boss Key de Ganon dans le monde").format(**bk_vals)
    g = Goal(c, f"Vaincre Ganon (pont : {bridge} ; {bk})")
    if sd.get("bridge") == 5:
        g.counter("Gold Skulltula Tokens", c.count("Gold Skulltula Token"), int(sd.get("bridge_tokens") or 0))
    g.step("Pont du château de Ganon (récompenses de donjon invisibles pour un tracker)", None)
    g.final("Vaincre Ganon")
    return g


def rac2(c: GoalContext) -> Goal:
    return Goal(c, "Vaincre le Protopet muté (Yeedil)").final("Vaincre le Protopet muté")


def rac3(c: GoalContext) -> Goal:
    g = Goal(c, "Vaincre le Dr. Nefarious")
    g.location("Command Center: Biobliterator Defeated!", "Command Center: Biobliterator Defeated!")
    g.final("Command Center: Dr. Nefarious Defeated!", "Command Center: Dr. Nefarious Defeated!")
    return g


def slay_the_spire(c: GoalContext) -> Goal:
    chars = [x.get("name") for x in c.slot_data.get("characters") or [] if isinstance(x, dict)]
    if chars:
        c.sources.add("slot_data")
    n = int(c.opt("num_chars_goal", "num_chars_goal", 0) or 0)
    act = "l'acte 4 (Heart)" if c.opt("final_act", "final_act", False) else "l'acte 3"
    who = (", ".join(chars) if chars else "les personnages") if n == 0 else plural(n, "personnage")
    g = Goal(c, f"Vaincre le boss de {act} avec {who}")
    for name in chars:
        locked = next((x.get("locked") for x in c.slot_data["characters"] if x.get("name") == name), False)
        if locked:
            g.item(f"{name} Unlock", f"{name} Unlock")
    g.final(f"Victoire avec {who}")
    return g


def tboi(c: GoalContext) -> Goal:
    options = c.slot_data.get("options") or {}
    if options:
        c.sources.add("slot_data")
    bosses = list(options.get("goals") or c.yaml.get("goals") or [])
    amount = options.get("goal_amount", c.yaml.get("goal_amount", 0))
    need = len(bosses) if amount in (0, "all", None) else int(amount)
    g = Goal(c, f"Vaincre {'tous ces boss' if need == len(bosses) else f'{need} de ces boss'} : " + ", ".join(bosses))
    done = 0
    for b in bosses:
        candidates = [f"{b} Reward #1", f"{b} - Boss Room"]
        real = [x for x in candidates if x in c.locations]
        hit = any(x in c.checked for x in real)
        done += hit
        g.step(b, hit if real else None)
    if bosses:
        g.counter("Boss vaincus", done, need)
    return g


def wwhd(c: GoalContext) -> Goal:
    shards = [f"Triforce Shard {i}" for i in range(1, 9)]
    bosses = bool(c.opt("required_bosses", "required_bosses", False))
    g = Goal(c, "Les 8 Triforce Shards, puis Ganondorf" + (" (et les boss requis)" if bosses else ""))
    g.counter("Triforce Shards", sum(c.has(s) for s in shards), 8)
    if bosses:
        g.step(f"{c.opt('num_required_bosses', 'num_required_bosses', '?')} boss requis", None)
    g.final("Vaincre Ganondorf")
    return g


DESCRIBERS: dict[str, Callable[[GoalContext], Goal]] = {
    "Kingdom Hearts 2": kh2,
    "Super Mario 64": sm64,
    "Celeste (Open World)": celeste,
    "Jak and Daxter: The Precursor Legacy": jak,
    "Balatro": balatro,
    "Pokemon Black and White": pokemon_bw,
    "Pokemon Platinum": pokemon_platinum,
    "PokePark": pokepark,
    "The Legend of Zelda - Phantom Hourglass": phantom_hourglass,
    "Ori and the Blind Forest": ori_bf,
    "Ori and the Will of the Wisps": ori_wotw,
    "Jak 3": jak3,
    "Kingdom Hearts Birth by Sleep": kh_bbs,
    "AEMinecraft": minecraft,
    "Mario Kart Wii": mkwii,
    "Spicy Meatball Overdrive": odyssey,
    "Ocarina of Time": oot,
    "Ratchet & Clank 2": rac2,
    "Ratchet and Clank 3": rac3,
    "Slay the Spire": slay_the_spire,
    "The Binding of Isaac Repentance": tboi,
    "The Wind Waker HD": wwhd,
}


def describe(ctx: GoalContext) -> dict[str, Any] | None:
    """The goal of the slot, or None when the game has no describer."""
    fn = DESCRIBERS.get(ctx.game)
    if fn is None:
        return None
    return fn(ctx).to_json()


# --- player yamls ----------------------------------------------------------------------------------------------------

_yaml_cache: dict[Path, tuple[float, dict[str, Any]]] = {}


def _fixed(value: Any) -> Any:
    """A yaml option value, or MISSING when it is random ("random…", or weights on several values)."""
    if isinstance(value, dict) and value and all(isinstance(w, (int, float)) for w in value.values()):
        chosen = [k for k, w in value.items() if w > 0]  # {value: weight}
        value = chosen[0] if len(chosen) == 1 else MISSING
    if isinstance(value, str) and value.startswith("random"):
        return MISSING
    return value


def yaml_options(path: Path | None, game: str | None) -> dict[str, Any]:
    """Options of `game` in the player's yaml (random values left out). Empty when there is no yaml."""
    if not path or not game:
        return {}
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    cached = _yaml_cache.get(path)
    if cached and cached[0] == mtime:
        raw = cached[1]
    else:
        try:
            docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(d, dict)]
        except (OSError, yaml.YAMLError):
            docs = []
        raw = next((d for d in docs if d.get("game") == game), docs[0] if docs else {})
        _yaml_cache[path] = (mtime, raw)
    section = raw.get(game) if isinstance(raw.get(game), dict) else {}
    out = {}
    for key, value in section.items():
        v = _fixed(value)
        if v is not MISSING:
            out[key] = v
    return out
