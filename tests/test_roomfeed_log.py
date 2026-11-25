import json
import os
import time

import pytest

from multitracker.roomfeed.log import CheckEntry, RoomLog, safe_dir_name

NAMES = {"sender_name": "Alice", "sender_game": "Tunic", "receiver_name": "Bob", "receiver_game": "Celeste",
         "item_name": "Sword", "location_name": "Chest 1"}


def local_noon(y, m, d):
    return time.mktime((y, m, d, 12, 0, 0, 0, 0, -1))


def entry(location=10, sender=1, recorded_at=1000.0, **kw):
    values = dict(recorded_at=recorded_at, at=999.0, after=None, before=None, src="live", sender=sender,
                  receiver=2, item=77, location=location, flags=1)
    values.update(kw)
    return CheckEntry(**values)


def test_add_writes_line_and_rejects_duplicate(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("123")
    day = time.strftime("%Y-%m-%d", time.localtime(1000.0))
    assert log.add(entry(), NAMES) is True
    path = tmp_path / "123" / f"checks-{day}.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["location"] == 10 and row["sender"] == 1 and row["src"] == "live" and row["at"] == 999.0
    assert row["after"] is None
    assert row["sender_name"] == "Alice" and row["item_name"] == "Sword" and row["location_name"] == "Chest 1"
    assert log.keys == {(1, 10)}
    assert log.add(entry(recorded_at=2000.0), NAMES) is False
    assert path.read_text(encoding="utf-8").splitlines() == lines
    assert len(log.entries) == 1
    assert log.write_error is None


def test_missing_names_are_null(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(), {"sender_name": "Alice"})
    row = json.loads(next((tmp_path / "s").glob("checks-*.jsonl")).read_text(encoding="utf-8"))
    assert row["sender_name"] == "Alice"
    assert row["item_name"] is None and row["receiver_game"] is None


def test_one_file_per_local_day(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1, recorded_at=local_noon(2026, 10, 22)), NAMES)
    log.add(entry(location=2, recorded_at=local_noon(2026, 10, 23)), NAMES)
    names = sorted(p.name for p in (tmp_path / "s").glob("checks-*.jsonl"))
    assert names == ["checks-2026-10-22.jsonl", "checks-2026-10-23.jsonl"]


def test_reload_in_order_and_when(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1, recorded_at=local_noon(2026, 10, 22)), NAMES)
    log.add(entry(location=2, recorded_at=local_noon(2026, 10, 23), at=None, after=None, before=123.0,
                  src="catchup"), NAMES)
    again = RoomLog(tmp_path)
    again.open_seed("s")
    assert [e.location for e in again.entries] == [1, 2]
    assert again.keys == {(1, 1), (1, 2)}
    assert again.entries[1].at is None and again.entries[1].before == 123.0
    assert again.entries[1].when == 123.0
    assert again.entries[1].src == "catchup"
    assert again.entries[0].when == 999.0
    assert entry(at=None, before=None, recorded_at=5.0).when == 5.0
    assert entry().key == (1, 10)
    # same seed again is a no-op (memory kept)
    again.open_seed("s")
    assert len(again.entries) == 2


def test_unreadable_lines_counted(tmp_path):
    d = tmp_path / "s"
    d.mkdir()
    good = {"recorded_at": 1.0, "at": 1.0, "after": None, "before": None, "src": "live", "sender": 1,
            "receiver": 2, "item": 3, "location": 4, "flags": 0}
    (d / "checks-2026-10-23.jsonl").write_text(
        json.dumps(good) + '\n{"recorded_at": 1,\n\n{"recorded_at": 1}\n', encoding="utf-8")
    log = RoomLog(tmp_path)
    log.open_seed("s")
    assert len(log.entries) == 1
    assert log.unreadable_lines == 2  # truncated line + line missing required fields


def test_other_seed_resets_memory(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("one")
    log.add(entry(), NAMES)
    log.open_seed("two")
    assert log.entries == [] and log.keys == set() and log.seed == "two"
    assert log.dir == tmp_path / "two"
    assert log.add(entry(), NAMES) is True
    assert (tmp_path / "one").is_dir() and (tmp_path / "two").is_dir()
    log.open_seed("one")
    assert len(log.entries) == 1
    log.open_seed("a/b c")
    assert log.dir == tmp_path / "a_b_c"
    assert safe_dir_name("") == "_"
    assert len(safe_dir_name("x" * 200)) == 80


def test_add_before_open_seed(tmp_path):
    log = RoomLog(tmp_path)
    assert log.dir is None
    assert log.add(entry(), NAMES) is False
    assert list(tmp_path.iterdir()) == []


def test_presence_and_state(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add_presence(5.0, 3, "join", ["Tracker"])
    row = json.loads((tmp_path / "s" / "presence.jsonl").read_text(encoding="utf-8"))
    assert row == {"at": 5.0, "slot": 3, "event": "join", "tags": ["Tracker"]}
    assert log.load_state() == {}
    log.save_state(last_live_at=5.0)
    log.save_state(listening_since=1.0)
    assert log.load_state() == {"last_live_at": 5.0, "listening_since": 1.0}
    (tmp_path / "s" / "state.json").write_text("{not json", encoding="utf-8")
    assert log.load_state() == {}


def test_remember_room(tmp_path):
    log = RoomLog(tmp_path)
    assert log.seed_for_room("wVAe") is None
    log.remember_room("wVAe", "123")
    assert RoomLog(tmp_path).seed_for_room("wVAe") == "123"
    assert RoomLog(tmp_path).seed_for_room("other") is None


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_write_failure_keeps_memory(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1), NAMES)
    d = tmp_path / "s"
    day_file = next(d.glob("checks-*.jsonl"))
    day_file.unlink()
    os.chmod(d, 0o500)
    try:
        assert log.add(entry(location=2), NAMES) is True
        assert isinstance(log.write_error, str) and log.write_error
        assert (1, 2) in log.keys and len(log.entries) == 2
    finally:
        os.chmod(d, 0o700)
    assert log.add(entry(location=3), NAMES) is True
    assert log.write_error is None


def test_line_separators_in_names_and_partial_last_line(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1), {**NAMES, "item_name": "Odd\u2028Name\u0085"})
    day_file = next((tmp_path / "s").glob("checks-*.jsonl"))
    with day_file.open("a", encoding="utf-8") as fh:
        fh.write('{"truncated":')  # crash mid-write
    log.add(entry(location=2), NAMES)
    again = RoomLog(tmp_path)
    again.open_seed("s")
    assert [e.location for e in again.entries] == [1, 2]
    assert again.unreadable_lines == 1


def test_add_many_opens_each_day_file_once(tmp_path, monkeypatch):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    day1, day2 = local_noon(2026, 10, 22), local_noon(2026, 10, 23)
    batch = [(entry(location=1, recorded_at=day1), NAMES), (entry(location=2, recorded_at=day2), NAMES),
             (entry(location=3, recorded_at=day1), NAMES), (entry(location=1, recorded_at=day2), NAMES),  # dup of 1
             (entry(location=4, recorded_at=day2), NAMES)]
    opened: list[str] = []
    original = type(tmp_path).open

    def counting(self, *args, **kwargs):
        opened.append(self.name)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(tmp_path), "open", counting)
    added = log.add_many(batch)
    monkeypatch.undo()
    assert [e.location for e in added] == [1, 2, 3, 4]
    assert sorted(opened) == ["checks-2026-10-22.jsonl", "checks-2026-10-23.jsonl"]
    assert log.keys == {(1, 1), (1, 2), (1, 3), (1, 4)} and len(log.entries) == 4
    again = RoomLog(tmp_path)
    again.open_seed("s")
    assert [e.location for e in again.entries] == [1, 3, 2, 4]  # files load in day order
    assert json.loads(next((tmp_path / "s").glob("checks-2026-10-22.jsonl")).read_text().splitlines()[0])["sender_name"] == "Alice"
    assert log.write_error is None
    assert log.add_many([]) == []


def test_add_many_before_open_seed_and_after_partial_line(tmp_path):
    assert RoomLog(tmp_path).add_many([(entry(), NAMES)]) == []
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1), NAMES)
    day_file = next((tmp_path / "s").glob("checks-*.jsonl"))
    with day_file.open("a", encoding="utf-8") as fh:
        fh.write('{"truncated":')
    log.add_many([(entry(location=2), NAMES), (entry(location=3), NAMES)])
    again = RoomLog(tmp_path)
    again.open_seed("s")
    assert [e.location for e in again.entries] == [1, 2, 3] and again.unreadable_lines == 1


def test_stored_slot_names_are_kept_from_disk_and_adds(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1, sender=1), NAMES)
    log.add(entry(location=2, sender=5), {"sender_name": None})
    assert log.slot_names == {1: ("Alice", "Tunic"), 2: ("Bob", "Celeste")}
    again = RoomLog(tmp_path)
    again.open_seed("s")
    assert again.slot_names == {1: ("Alice", "Tunic"), 2: ("Bob", "Celeste")}


def test_via_is_kept_across_a_reload(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    log.add(entry(location=1, via="collect"), NAMES)
    log.add(entry(location=2), NAMES)
    again = RoomLog(tmp_path)
    again.open_seed("s")
    assert [e.via for e in again.entries] == ["collect", None]


def test_bulk_locations_from_the_tags_and_from_the_bursts_before_them(tmp_path):
    log = RoomLog(tmp_path)
    log.open_seed("s")
    # before the tags: a burst of 3 worlds sending to slot 9 within a second is a collect by slot 9
    for sender, loc in ((1, 10), (2, 20), (3, 30)):
        log.add(entry(location=loc, sender=sender, receiver=9, at=100.0 + sender * 0.3, recorded_at=100.0), NAMES)
    log.add(entry(location=11, sender=1, receiver=9, at=500.0, recorded_at=500.0), NAMES)  # alone: played
    log.add(entry(location=12, sender=1, receiver=8, at=100.5, recorded_at=100.5), NAMES)  # other receiver
    log.add(entry(location=13, sender=1, receiver=9, at=None, before=100.2, src="catchup",
                  recorded_at=900.0), NAMES)  # dated by a poll: never a burst
    log.start_tags(1000.0)
    # after: only the tags count
    log.add(entry(location=14, sender=1, receiver=7, at=2000.0, recorded_at=2000.0, via="collect"), NAMES)
    for sender, loc in ((1, 15), (2, 25), (3, 35)):
        log.add(entry(location=loc, sender=sender, receiver=6, at=3000.0, recorded_at=3000.0), NAMES)
    assert log.bulk_locations(1) == {10, 14}
    assert log.bulk_locations(2) == {20}
    again = RoomLog(tmp_path)
    again.open_seed("s")
    again.start_tags(5000.0)  # already started: kept
    assert again.bulk_locations(1) == {10, 14}


def test_a_collect_missed_while_not_listening_is_found_in_the_catchup(tmp_path):
    # A catch-up poll that finds many worlds' checks for one receiver in a short gap: a collect heard by nobody.
    log = RoomLog(tmp_path)
    log.open_seed("s")
    def catchup(sender, receiver, location, after, before):
        log.add(entry(location=location, sender=sender, receiver=receiver, at=None, after=after, before=before,
                      src="catchup", recorded_at=before), NAMES)
    for sender in range(1, 11):
        catchup(sender, 9, 100 + sender, 1000.0, 1500.0)  # 10 worlds in 8 minutes: collect
    for sender in range(1, 11):
        catchup(sender, 8, 200 + sender, 1000.0, 9000.0)  # 10 worlds in a night: played
    for sender in range(1, 10):
        catchup(sender, 7, 300 + sender, 1000.0, 1500.0)  # 9 worlds: played
    assert log.bulk_locations(1) == {101}
    assert log.bulk_locations(10) == {110}
