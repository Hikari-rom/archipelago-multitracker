"""Diagnose a logic mismatch found by validate_logic.py (TEST CODE ONLY: uses the multidata).

  PYTHONHASHSEED=0 .venv/bin/python scripts/testenv/diag_logic.py <game_slug> <run> <sphere> 2>/dev/null

Compares, at one snapshot of test-output/logic_validation/<game_slug>/run<run>, the locations, the
collected progression items/events and the reachable regions of the reference (full generation
multiworld) and of the tool (regenerated world). Assumes player 1 is the game under test.
"""
import sys, json, glob, collections, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "backend")]
import logic_reference as lr
slug, run, sph = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
base = ROOT / f"test-output/logic_validation/{slug}/run{run}"
zp = pathlib.Path(glob.glob(str(base / "out/AP_*.zip"))[0]); md = lr.load_multidata(zp)
link = ROOT / "tests/fixtures/_diag"
if link.is_symlink(): link.unlink()
link.symlink_to(base / "players", target_is_directory=True)
try: mw = lr.regenerate("_diag", run)
finally: link.unlink()
lr.check_same_fill(mw, md)
p = 1; snap = lr.snapshots(mw, p)[sph]
from BaseClasses import CollectionState
st = CollectionState(mw)
for loc in snap.received: st.collect(loc.item, True, loc)
st.sweep_for_advancements(locations=[l for l in mw.get_locations(p) if l.address is None])
from multitracker.logic.ut_worker import SlotLogic
yaml = next((base / "players").glob("P1*.yaml"))
alls = {l.address for l in mw.get_locations(p) if l.address is not None}
lg = SlotLogic(mw.player_name[p], mw.game[p], 0, p, lr.as_sent_by_server(md["slot_data"][p]), yaml, alls)
res = lg.in_logic(lr.as_sent_by_server(snap.items), snap.missing)
ref = {l.address for l in mw.get_reachable_locations(st, p) if l.address in snap.missing}
names = mw.worlds[p].location_id_to_name
print("UNDER", sorted(names[a] for a in ref - set(res["in_logic"]))[:10])
print("OVER", sorted(names[a] for a in set(res["in_logic"]) - ref)[:10])
# tool state replicate
from BaseClasses import ItemClassification
from multitracker.logic.ut_worker import exact_classification
tmw, pid = lg.core.multiworld, lg.core.player_id
ts = CollectionState(tmw)
for net in snap.items:
    it = tmw.create_item(tmw.worlds[pid].item_id_to_name[net["item"]], pid)
    it.classification = exact_classification(it.classification, net["flags"], ItemClassification) if net["location"] >= 0 else it.classification | net["flags"]
    ts.collect(it, True)
ts.sweep_for_advancements(locations=[l for l in tmw.get_locations(pid) if not l.address])
a = collections.Counter(dict(st.prog_items[p])); b = collections.Counter(dict(ts.prog_items[pid]))
print("REFONLY", dict(a - b)); print("TOOLONLY", dict(b - a))
print("regions ref", len(st.reachable_regions[p]), "tool", len(ts.reachable_regions[pid]))
print("ref-only regions", sorted({r.name for r in st.reachable_regions[p]} - {r.name for r in ts.reachable_regions[pid]})[:15])
