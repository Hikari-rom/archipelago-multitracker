"""Diagnose a slot of an e2e run that got stuck (TEST CODE ONLY: uses the multidata).

  PYTHONHASHSEED=0 .venv/bin/python scripts/testenv/diag_e2e_stuck.py <fixture> <seed> <slot name> 2>/dev/null

Reads test-output/e2e_stuck_<fixture>.json (written by tests/test_logic_e2e.py) and compares the reference
(full generation) with a fresh regeneration on that state. Stardew-specific lines at the end are skipped for
other games.
"""
import sys, json, glob, collections, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "backend")]
import logic_reference as lr
from testenv_helpers import generated_seed
fixture, seed, name = sys.argv[1], int(sys.argv[2]), sys.argv[3]
zp = generated_seed(fixture, seed, spoiler=1); md = lr.load_multidata(zp)
mw = lr.regenerate(fixture, seed)
dump = json.load(open(ROOT / f"test-output/e2e_stuck_{fixture}.json"))[name]
p = {mw.player_name[i]: i for i in mw.player_ids}[name]
from BaseClasses import CollectionState
st = CollectionState(mw)
for net in dump["items"]:
    if net["location"] < 0 or net["player"] == 0: continue
    loc = mw.get_location(mw.worlds[net["player"]].location_id_to_name[net["location"]], net["player"])
    st.collect(loc.item, True, loc)
st.sweep_for_advancements(locations=[l for l in mw.get_locations(p) if l.address is None])
from multitracker.logic.ut_worker import SlotLogic
yaml = ROOT / f"tests/fixtures/{fixture}" / next(f.name for f in (ROOT/f"tests/fixtures/{fixture}").glob("*.yaml") if f"name: {name}\n" in f.read_text())
alls = {l.address for l in mw.get_locations(p) if l.address is not None}
missing = set(dump["missing"])
lg = SlotLogic(name, mw.game[p], 0, p, lr.as_sent_by_server(md["slot_data"][p]), yaml, alls)
res = lg.in_logic(dump["items"], missing)
ref = {l.address for l in mw.get_reachable_locations(st, p) if l.address in missing}
names = mw.worlds[p].location_id_to_name
print("UNDER", sorted(names[a] for a in ref - set(res["in_logic"]))[:10])
print("OVER", sorted(names[a] for a in set(res["in_logic"]) - ref)[:10])
if "_mt_prefill_progress" not in vars(lg.core.multiworld.worlds[lg.core.player_id]): sys.exit()
EV = "Received Progression Item"
ra = collections.Counter()
for net in dump["items"]:
    if net["location"] < 0: continue
    it = mw.get_location(mw.worlds[net["player"]].location_id_to_name[net["location"]], net["player"]).item
    if it.advancement: ra[it.name] += it.events_to_collect.get(EV, 0)
w = lg.core.multiworld.worlds[lg.core.player_id]
cnt = w._mt_prefill_progress
rec = collections.Counter(w.item_id_to_name[n["item"]] for n in dump["items"] if n["location"] >= 0 and n["flags"] & 1)
mixed = {k: (v, rec.get(k), ra.get(k)) for k, v in cnt.items() if len(set(v)) > 1}
print("MIXED (pool values, received prog copies, ref count)", mixed)
print("percent ref", st.prog_items[p]["Received Progression Percent"], "total", mw.worlds[p].total_progression_items, w.total_progression_items)
