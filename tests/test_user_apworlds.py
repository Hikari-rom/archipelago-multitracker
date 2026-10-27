"""Apworlds imported from the user's own Archipelago install (D27): reading, import filtering, sync, API."""
from __future__ import annotations

import asyncio
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from multitracker import user_apworlds as ua
from multitracker.api import create_app


def make_apworld(path: Path, game: str | None, manifest: bool = False, module: str | None = None) -> Path:
    module = module or path.stem
    with zipfile.ZipFile(path, "w") as zf:
        if manifest:
            zf.writestr(f"{module}/archipelago.json", json.dumps({"game": game, "version": 7}))
            zf.writestr(f"{module}/__init__.py", "")
        elif game is not None:
            zf.writestr(f"{module}/__init__.py", f'from x import y\n\nclass W(World):\n    game: str = "{game}"\n')
        else:
            zf.writestr(f"{module}/__init__.py", "class W:\n    pass\n")
    return path


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A fake app layout: catalog shipping "Shipped Game", custom_worlds with its apworld, an empty data dir."""
    custom, user, source = tmp_path / "custom_worlds", tmp_path / "data_apworlds", tmp_path / "src"
    custom.mkdir()
    source.mkdir()
    catalog = tmp_path / "apworlds.yaml"
    catalog.write_text('apworlds:\n  shipped: {game: "Shipped Game", source: github}\n'
                       '  mine: {game: "User Game", source: user}\n  old: {game: "Old Game", source: user}\n'
                       '  new: {game: "New Game", source: user}\n  other: {game: "Other Version", source: user}\n'
                       '  absent: {game: "Not Loaded", source: user}\n', encoding="utf-8")
    make_apworld(custom / "shipped.apworld", "Shipped Game")
    monkeypatch.setattr(ua, "CUSTOM_DIR", custom)
    monkeypatch.setattr(ua, "USER_DIR", user)
    monkeypatch.setattr(ua, "CATALOG", catalog)
    return SimpleNamespace(custom=custom, user=user, source=source, catalog=catalog)


def test_apworld_game_reads_manifest_or_class_attribute(tmp_path):
    assert ua.apworld_game(make_apworld(tmp_path / "a.apworld", "Game A", manifest=True)) == "Game A"
    assert ua.apworld_game(make_apworld(tmp_path / "b.apworld", "Majora's Mask Recompiled")) == "Majora's Mask Recompiled"
    assert ua.apworld_game(make_apworld(tmp_path / "c.apworld", None)) is None
    with zipfile.ZipFile(tmp_path / "e.apworld", "w") as zf:  # manifest at the root (newer apworlds)
        zf.writestr("archipelago.json", json.dumps({"game": "Cuphead", "version": 7}))
        zf.writestr("e/__init__.py", "game = GAME_NAME\n")
    assert ua.apworld_game(tmp_path / "e.apworld") == "Cuphead"
    (tmp_path / "d.apworld").write_bytes(b"not a zip")
    assert ua.apworld_game(tmp_path / "d.apworld") is None


def test_import_keeps_only_the_user_games_of_the_catalog(env):
    (env.source / "shipped.apworld").write_bytes(b"same name as the app's file: not even read")
    make_apworld(env.source / "other_name.apworld", "Shipped Game")  # the app's version wins
    make_apworld(env.source / "mine.apworld", "User Game")
    make_apworld(env.source / "rich_presence.apworld", "Discord Rich Presence")  # not in the catalog
    make_apworld(env.source / "mine_copy.apworld", "User Game")
    make_apworld(env.source / "broken.apworld", None)
    rows = ua.import_dir(env.source)
    assert {r["file"]: r["status"] for r in rows} == {
        "broken.apworld": "unreadable", "rich_presence.apworld": "not_needed", "mine.apworld": "imported",
        "mine_copy.apworld": "duplicate", "other_name.apworld": "shipped", "shipped.apworld": "shipped"}
    assert [p.name for p in env.user.iterdir()] == ["mine.apworld"]
    assert ua.imported() == [{"file": "mine.apworld", "game": "User Game"}]


def test_import_replaces_the_previous_import(env):
    make_apworld(env.source / "old.apworld", "Old Game")
    ua.import_dir(env.source)
    (env.source / "old.apworld").unlink()
    make_apworld(env.source / "new.apworld", "New Game")
    ua.import_dir(env.source)
    assert sorted(p.name for p in env.user.iterdir()) == ["new.apworld"]


def test_import_of_a_missing_folder_fails(env, tmp_path):
    with pytest.raises(FileNotFoundError):
        ua.import_dir(tmp_path / "nope")


def test_sync_copies_records_and_cleans_up(env):
    env.user.mkdir()
    make_apworld(env.user / "mine.apworld", "User Game")
    make_apworld(env.user / "shipped.apworld", "Not the shipped one")  # name taken by the app's file
    make_apworld(env.user / "dup.apworld", "Shipped Game")  # game shipped by the app
    make_apworld(env.user / "tool.apworld", "Discord Rich Presence")  # put there by hand: not a user game
    assert ua.sync() == ["mine.apworld"]
    assert json.loads((env.custom / ua.RECORD).read_text()) == ["mine.apworld"]
    assert ua.apworld_game(env.custom / "shipped.apworld") == "Shipped Game"
    assert sorted(p.name for p in env.custom.glob("*.apworld")) == ["mine.apworld", "shipped.apworld"]
    mtime = (env.custom / "mine.apworld").stat().st_mtime_ns
    assert ua.sync() == ["mine.apworld"]
    assert (env.custom / "mine.apworld").stat().st_mtime_ns == mtime  # unchanged copy left in place
    (env.user / "mine.apworld").unlink()
    assert ua.sync() == []
    assert sorted(p.name for p in env.custom.glob("*.apworld")) == ["shipped.apworld"]
    assert not (env.custom / ua.RECORD).exists()


def test_synced_files_are_not_taken_for_shipped_ones(env):
    env.user.mkdir()
    make_apworld(env.user / "mine.apworld", "User Game")
    ua.sync()
    assert ua.shipped_files() == {"shipped.apworld"}
    make_apworld(env.source / "mine.apworld", "User Game")
    assert [r["status"] for r in ua.import_dir(env.source)] == ["imported"]


def test_shipped_games_ignore_user_entries(env):
    assert ua.shipped_games() == {"Shipped Game"}
    assert "User Game" in ua.user_games() and "Shipped Game" not in ua.user_games()


# -- API ----------------------------------------------------------------------------------------
class FakeEngine:
    def __init__(self, checksums):
        self._checksums = checksums
        self.restarts = 0

    async def checksums(self, games):
        return None if self._checksums is None else {g: self._checksums.get(g) for g in games}


class FakeService:
    def __init__(self, room, local):
        self.trackers = {"p1": SimpleNamespace(state=SimpleNamespace(datapackage_checksums=room))}
        self.logic_engine = FakeEngine(local)
        self.config = SimpleNamespace(password="")
        self.restarts = 0

    def room_checksums(self):
        return dict(self.trackers["p1"].state.datapackage_checksums)

    async def restart_logic(self):
        self.restarts += 1


def call(service, method, path, **kw):
    app = create_app(lambda: None, frontend_dist=None, log_file=None)
    app.state.service = service

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def test_api_import_then_check_versions(env):
    for name, game in [("mine", "User Game"), ("other", "Other Version"), ("absent", "Not Loaded"),
                       ("away", "Not Wanted")]:
        make_apworld(env.source / f"{name}.apworld", game)
    room = {"User Game": "aaa", "Other Version": "bbb", "Not Loaded": "ccc", "Shipped Game": "ddd"}
    service = FakeService(room, {"User Game": "aaa", "Other Version": "zzz"})
    r = call(service, "POST", "/api/apworlds/import", json={"path": str(env.source)})
    assert r.status_code == 200, r.text
    assert service.restarts == 1
    assert {row["file"]: row["status"] for row in r.json()["report"]}["away.apworld"] == "not_needed"
    assert [f["file"] for f in r.json()["files"]] == ["absent.apworld", "mine.apworld", "other.apworld"]
    r = call(service, "POST", "/api/apworlds/check", json={})
    assert {f["game"]: f["version"] for f in r.json()["files"]} == {
        "User Game": "room", "Other Version": "other", "Not Loaded": "not_loaded"}


def test_api_check_without_worker_is_unknown(env):
    env.user.mkdir()
    make_apworld(env.user / "mine.apworld", "User Game")
    r = call(FakeService({"User Game": "aaa"}, None), "POST", "/api/apworlds/check", json={})
    assert [f["version"] for f in r.json()["files"]] == ["unknown"]


def test_api_import_refuses_relative_path_cross_site_and_form_posts(env):
    service = FakeService({}, {})
    assert call(service, "POST", "/api/apworlds/import", json={"path": "custom_worlds"}).status_code == 400
    assert call(service, "POST", "/api/apworlds/import", json={"path": str(env.source / "nope")}).status_code == 400
    r = call(service, "POST", "/api/apworlds/import", json={"path": str(env.source)},
             headers={"origin": "http://evil.example"})
    assert r.status_code == 403
    r = call(service, "POST", "/api/apworlds/import", content=f'{{"path": "{env.source}"}}',
             headers={"content-type": "text/plain"})
    assert r.status_code in (415, 422)
    assert service.restarts == 0


def test_api_config_flags_imported_games(env, tmp_path, monkeypatch):
    from multitracker.logic import engine
    catalog = engine.game_catalog
    monkeypatch.setattr(engine, "game_catalog", lambda: catalog(env.catalog))
    env.user.mkdir()
    make_apworld(env.user / "mine.apworld", "User Game")
    service = FakeService({}, {})
    service.config = SimpleNamespace(room_url=None, server="", password="", wake_room=False, scout_checked=False,
                                     room_dashboard=False, hints_foreign_logic=True, path=tmp_path / "room.yaml", slots=[])
    games = call(service, "GET", "/api/config").json()["games"]
    assert games["User Game"] == {"logic": False, "needs_yaml": False, "user": True, "imported": True}
    assert games["Shipped Game"]["imported"] is False and games["Shipped Game"]["user"] is False
