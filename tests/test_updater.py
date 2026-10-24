"""Updates from the app (D25): portable build (GitHub release zip, staged for Multitracker.exe) and git checkout
(scripts/update.sh). No network: releases are file:// URLs, origin is a local bare repository."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import pytest

from multitracker import updater as up

ROOT = Path(__file__).resolve().parents[1]


def test_versions():
    assert up.parse_version("v0.1.0") == (0, 1, 0, 0)
    assert up.parse_version("1.2.10") == (1, 2, 10, 0)
    assert up.parse_version("v0.1.0-3-g7075bd0") == (0, 1, 0, 3)  # build of a workflow run, after the tag
    assert not up.is_newer("v0.1.0", "v0.1.0-3-g7075bd0") and up.is_newer("v0.1.1", "v0.1.0-3-g7075bd0")
    assert up.is_newer("v0.1.0-5-gabc", "v0.0.1")
    assert up.parse_version("dev-abc123") is None
    assert up.is_newer("v0.2.0", "v0.1.0")
    assert up.is_newer("v0.10.0", "v0.9.9")
    assert not up.is_newer("v0.1.0", "v0.1.0")
    assert not up.is_newer("v0.1.0", "v0.2.0")
    assert up.is_newer("v0.1.0", None) and up.is_newer("v0.1.0", "dev-abc")
    assert not up.is_newer("nightly", "v0.1.0")


def test_mode(tmp_path):
    assert up.detect_mode(tmp_path) == "none"
    (tmp_path / "VERSION").write_text("v0.1.0\n")
    assert up.detect_mode(tmp_path) == "portable"
    (tmp_path / ".git").mkdir()
    assert up.detect_mode(tmp_path) == "git"
    assert up.detect_mode(ROOT) == "git"


# --- portable ---------------------------------------------------------------------------------------------------

def make_zip(path: Path, version: str, extra: dict[str, str] | None = None) -> Path:
    files = {"VERSION": version + "\n", "Multitracker.exe": "exe", "python/python.exe": "py",
             "backend/multitracker/__init__.py": "", "config/apworlds.yaml": "new"}
    with zipfile.ZipFile(path, "w") as zf:
        for rel, text in files.items():
            zf.writestr(f"{up.PORTABLE_DIR}/{rel}", text)
        for rel, text in (extra or {}).items():
            zf.writestr(rel, text)
    return path


def make_release(tmp_path: Path, version: str, zip_path: Path, digest: str | None = "auto") -> str:
    data = zip_path.read_bytes()
    if digest == "auto":
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
    asset = {"name": up.ASSET, "browser_download_url": zip_path.as_uri(), "size": len(data)}
    if digest:
        asset["digest"] = digest
    rel = tmp_path / "release.json"
    rel.write_text(json.dumps({"tag_name": version, "html_url": "https://example.invalid/r", "body": "notes",
                               "assets": [{"name": "other.zip"}, asset]}))
    return rel.as_uri()


def portable_root(tmp_path: Path, version: str = "v0.1.0") -> Path:
    root = tmp_path / "app"
    (root / "config").mkdir(parents=True)
    (root / "VERSION").write_text(version + "\n")
    (root / "config" / "room.yaml").write_text("mine")
    return root


def test_fetch_release_reads_the_windows_asset(tmp_path):
    url = make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0"))
    rel = up.fetch_release(url)
    assert rel["version"] == "v0.2.0" and rel["notes"] == "notes"
    assert rel["asset"]["sha256"] and rel["asset"]["url"].startswith("file:")
    (tmp_path / "bad.json").write_text(json.dumps({"tag_name": "v1.0.0", "assets": []}))
    with pytest.raises(up.UpdateError, match="n'a pas de"):
        up.fetch_release((tmp_path / "bad.json").as_uri())


def test_stage_portable_extracts_the_new_version(tmp_path):
    root = portable_root(tmp_path)
    rel = up.fetch_release(make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0")))
    seen = []
    top = up.stage_portable(root, rel, lambda d, t: seen.append((d, t)))
    assert top == root / "update" / "new" / up.PORTABLE_DIR
    assert (top / "VERSION").read_text().strip() == "v0.2.0"
    assert seen and seen[-1][0] == seen[-1][1]
    assert not (root / "update" / up.ASSET).exists()
    assert (root / "config" / "room.yaml").read_text() == "mine"  # staging never touches the app


@pytest.mark.parametrize("case,match", [
    ("digest", "empreinte"),
    ("version", "pas v0.2.0"),
    ("slip", "chemin refusé"),
    ("incomplete", "ne contient pas"),
])
def test_stage_portable_refuses_bad_downloads(tmp_path, case, match):
    root = portable_root(tmp_path)
    z = tmp_path / "z.zip"
    if case == "slip":
        make_zip(z, "v0.2.0", {"../evil.txt": "x"})
    elif case == "version":
        make_zip(z, "v0.3.0")
    elif case == "incomplete":
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr(f"{up.PORTABLE_DIR}/VERSION", "v0.2.0")
    else:
        make_zip(z, "v0.2.0")
    rel = up.fetch_release(make_release(tmp_path, "v0.2.0", z, "sha256:" + "0" * 64 if case == "digest" else "auto"))
    with pytest.raises(up.UpdateError, match=match):
        up.stage_portable(root, rel)
    assert not (tmp_path / "evil.txt").exists() and not (root / "update" / "evil.txt").exists()


def test_long_paths_and_zip_entries():
    assert up.long_path(r"C:\Users\x\ArchipelagoMultitracker") == r"\\?\C:\Users\x\ArchipelagoMultitracker"
    assert up.long_path(r"\\nas\share\app") == r"\\?\UNC\nas\share\app"
    assert up.long_path(r"\\?\C:\app") == r"\\?\C:\app"
    assert up.member_parts("ArchipelagoMultitracker/python/") == ["ArchipelagoMultitracker", "python"]
    assert up.member_parts("a/./b//c.txt") == ["a", "b", "c.txt"]
    for name in ("../evil.txt", "a/../../evil.txt", "/etc/evil", "C:/evil", "a\\..\\evil", "./"):
        with pytest.raises(up.UpdateError, match="chemin refusé"):
            up.member_parts(name)


@pytest.mark.parametrize("error,match", [
    (FileNotFoundError(2, "No such file or directory"), "écriture impossible"),  # a path over 260 characters
    (RuntimeError("boom"), "boom"),
])
async def test_portable_apply_ends_in_error_whatever_fails(tmp_path, monkeypatch, error, match):
    root = portable_root(tmp_path)
    url = make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0"))

    def fail(zip_path, dest):
        raise error

    monkeypatch.setattr(up, "extract", fail)
    u = up.Updater(root, release_url=url, on_exit=lambda c: pytest.fail("must not exit"))
    await u.apply()
    for _ in range(100):
        if (up.read_status(root) or {}).get("state") == "error":
            break
        await asyncio.sleep(0.05)
    st = up.read_status(root)
    assert st["state"] == "error" and match in st["message"] and not u.running()


async def test_portable_apply_stages_then_asks_to_exit(tmp_path):
    root = portable_root(tmp_path)
    url = make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0"))
    exits = []
    u = up.Updater(root, release_url=url, on_exit=exits.append)
    assert u.mode == "portable"
    info = await u.check()
    assert info["available"] and info["latest"]["version"] == "v0.2.0" and info["current"]["version"] == "v0.1.0"
    await u.apply()
    for _ in range(100):
        if exits:
            break
        await asyncio.sleep(0.05)
    assert exits == [up.EXIT_UPDATE]
    st = up.read_status(root)
    assert st["state"] == "restarting" and st["from"] == "v0.1.0" and st["to"] == "v0.2.0"
    assert (root / "update" / "new" / up.PORTABLE_DIR / "VERSION").exists()


async def test_portable_apply_when_up_to_date_or_failing(tmp_path):
    root = portable_root(tmp_path, "v0.2.0")
    url = make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0"))
    u = up.Updater(root, release_url=url, on_exit=lambda c: None)
    with pytest.raises(up.UpdateError, match="déjà à jour"):
        await u.apply()
    u = up.Updater(root, release_url=(tmp_path / "missing.json").as_uri())
    info = await u.check()
    assert info["check_error"] and not info["available"]
    # a broken download ends in an error status, the app keeps running
    root2 = portable_root(tmp_path / "b")
    url2 = make_release(tmp_path / "b", "v0.3.0", make_zip(tmp_path / "b" / "z.zip", "v0.3.0"), "sha256:" + "1" * 64)
    u = up.Updater(root2, release_url=url2, on_exit=lambda c: pytest.fail("must not exit"))
    await u.apply()
    for _ in range(100):
        if (up.read_status(root2) or {}).get("state") == "error":
            break
        await asyncio.sleep(0.05)
    st = up.read_status(root2)
    assert st["state"] == "error" and "empreinte" in st["message"] and not u.running()


def test_status_after_restart(tmp_path):
    root = portable_root(tmp_path, "v0.2.0")
    up.write_status(root, mode="portable", state="restarting", step="x", message="", **{"from": "v0.1.0", "to": "v0.2.0"})
    assert up.Updater(root).info()["status"]["state"] == "done"
    up.write_status(root, mode="portable", state="restarting", step="x", message="", **{"from": "v0.2.0", "to": "v0.3.0"})
    st = up.Updater(root).info()["status"]
    assert st["state"] == "error" and "ancienne" in st["message"]
    up.write_status(root, mode="portable", state="running", step="x", message="", at=1.0)
    u = up.Updater(root)
    assert u.info()["status"]["state"] == "error" and not u.running()


def test_stage_from_cli(tmp_path, monkeypatch):
    root = portable_root(tmp_path)
    monkeypatch.setenv("MT_UPDATE_RELEASE_URL", make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0")))
    said = []
    assert up.stage_from_cli(root, said.append)
    assert up.read_status(root)["state"] == "restarting"
    (root / "VERSION").write_text("v0.2.0")
    assert not up.stage_from_cli(root, said.append)
    assert "Déjà à jour (v0.2.0)." in said


# --- git checkout (the Pi) --------------------------------------------------------------------------------------

def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo: Path, rel: str, text: str, msg: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    if rel.endswith(".sh"):
        (repo / rel).chmod(0o755)
    git(repo, "add", rel)
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)


@pytest.fixture
def repos(tmp_path):
    """origin (bare), dev (pushes to it) and pi (the app's checkout), with scripts/update.sh and a stub app.sh."""
    origin, dev, pi = tmp_path / "origin.git", tmp_path / "dev", tmp_path / "pi"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(dev)], check=True, capture_output=True)
    git(dev, "checkout", "-q", "-b", "main")
    (dev / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "update.sh", dev / "scripts" / "update.sh")
    git(dev, "add", "scripts/update.sh")
    commit(dev, "scripts/app.sh", "#!/bin/sh\necho \"$1\" >> app.calls\nif [ \"$1\" = status ]; then [ -f running ]; fi\n", "app.sh")
    commit(dev, "README.md", "v1", "first")
    commit(dev, "config/players/a.yaml", "name: a", "yaml")
    git(dev, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", "-b", "main", str(origin), str(pi)], check=True, capture_output=True)
    (pi / ".gitignore").write_text("data/\n.run/\napp.calls\nrunning\n")
    git(pi, "add", ".gitignore")
    git(pi, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "ignore")
    git(pi, "push", "-q", "origin", "main")
    git(dev, "pull", "-q", "origin", "main")
    return dev, pi


def run_update(pi: Path, since: str = "") -> subprocess.CompletedProcess:
    env = {**os.environ, "MT_UPDATE_SINCE": since}
    return subprocess.run(["bash", "scripts/update.sh"], cwd=pi, capture_output=True, text=True, timeout=120, env=env)


def test_git_check_lists_the_new_commits(repos):
    dev, pi = repos
    commit(dev, "README.md", "v2", "second")
    commit(dev, "README.md", "v3", "third")
    git(dev, "push", "-q", "origin", "main")
    u = up.Updater(pi)
    assert u.mode == "git"
    info = asyncio.run(u.check())
    assert info["available"] and info["latest"]["behind"] == 2
    assert [c["subject"] for c in info["latest"]["commits"]] == ["third", "second"]
    assert info["current"]["commit"] == git(pi, "rev-parse", "--short", "HEAD")
    # a local commit not pushed: the update is for a human
    commit(pi, "notes.txt", "x", "local")
    info = asyncio.run(u.check())
    assert not info["available"] and "pas encore poussé" in info["blocked"]


def test_update_script_fast_forwards_and_keeps_local_changes(repos):
    dev, pi = repos
    commit(dev, "README.md", "v2", "second")
    git(dev, "push", "-q", "origin", "main")
    (pi / "config" / "players" / "a.yaml").write_text("name: a\nmine: 1\n")  # Romain's edit, not committed
    r = run_update(pi)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (pi / "README.md").read_text() == "v2"
    assert (pi / "config" / "players" / "a.yaml").read_text() == "name: a\nmine: 1\n"
    st = up.read_status(pi)
    assert st["state"] == "done" and st["to"] == git(pi, "rev-parse", "--short", "HEAD")
    assert not (pi / "app.calls").exists()  # only docs changed: no restart
    r = run_update(pi)
    assert r.returncode == 0 and up.read_status(pi)["message"] == "déjà à jour"


def test_update_script_restarts_a_running_app_when_the_backend_changes(repos):
    dev, pi = repos
    commit(dev, "backend/x.py", "x = 1", "backend")
    git(dev, "push", "-q", "origin", "main")
    (pi / "running").write_text("")
    r = run_update(pi)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (pi / "app.calls").read_text().split() == ["status", "restart"]
    assert up.read_status(pi)["state"] == "done"


def test_commits_made_in_the_checkout_since_the_app_started(repos):
    """A dev session commits and pushes on the Pi itself: main has nothing new, but the running app is behind."""
    dev, pi = repos
    u = up.Updater(pi)
    started = u.started_commit
    commit(pi, "backend/x.py", "x = 2", "made on the Pi")
    git(pi, "push", "-q", "origin", "main")
    info = asyncio.run(u.check())
    assert info["available"] and info["latest"]["behind"] == 1 and info["current"]["running"] == started[:7]
    (pi / "running").write_text("")
    r = run_update(pi, started)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (pi / "app.calls").read_text().split() == ["status", "restart"]
    st = up.read_status(pi)
    assert st["state"] == "done" and st["from"] == started[:7]
    # docs only, no restart: this process counts as up to date once the script is done
    commit(pi, "README.md", "doc", "doc on the Pi")
    git(pi, "push", "-q", "origin", "main")
    u = up.Updater(pi)
    started = u.started_commit
    commit(pi, "README.md", "doc 2", "doc again")
    git(pi, "push", "-q", "origin", "main")
    assert asyncio.run(u.check())["available"]
    assert run_update(pi, started).returncode == 0
    assert (pi / "app.calls").read_text().split() == ["status", "restart"]
    assert not asyncio.run(u.check())["available"]


def test_update_script_stops_on_local_commits(repos):
    dev, pi = repos
    commit(dev, "README.md", "v2", "second")
    git(dev, "push", "-q", "origin", "main")
    commit(pi, "notes.txt", "x", "local")
    head = git(pi, "rev-parse", "HEAD")
    r = run_update(pi)
    assert r.returncode == 1
    st = up.read_status(pi)
    assert st["state"] == "error" and "pas encore poussé" in st["message"]
    assert git(pi, "rev-parse", "HEAD") == head


def test_update_api(tmp_path):
    from fastapi.testclient import TestClient

    from multitracker import api
    from multitracker.config import RoomConfig
    from multitracker.service import Service
    from multitracker.store import Store

    root = portable_root(tmp_path)
    url = make_release(tmp_path, "v0.2.0", make_zip(tmp_path / "z.zip", "v0.2.0"))
    exits = []
    u = up.Updater(root, release_url=url, on_exit=exits.append)
    cfg = RoomConfig(server="ws://127.0.0.1:9")
    app = api.create_app(lambda: Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(30.0,)),
                         frontend_dist=None, log_file=None, updater=u)
    with TestClient(app) as client:
        info = client.get("/api/update").json()
        assert info["mode"] == "portable" and info["current"]["version"] == "v0.1.0" and info["latest"] is None
        assert client.post("/api/update/check", content="{}").status_code == 415  # no JSON: refused
        info = client.post("/api/update/check", json={}).json()
        assert info["available"] and info["latest"]["version"] == "v0.2.0"
        assert client.post("/api/update/apply", json={}).status_code == 200
        for _ in range(100):
            if exits:
                break
            time.sleep(0.05)
        assert exits == [up.EXIT_UPDATE]
        assert client.post("/api/update/apply", json={}).status_code == 409  # already running
    noupd = api.create_app(lambda: Service(cfg, Store(tmp_path / "db2.sqlite3"), reconnect_delays=(30.0,)),
                           frontend_dist=None, log_file=None)
    with TestClient(noupd) as client:
        assert client.get("/api/update").json()["mode"] == "none"
        assert client.post("/api/update/apply", json={}).status_code == 409
