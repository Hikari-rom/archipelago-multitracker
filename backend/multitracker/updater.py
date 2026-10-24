"""Updates started from the app (Configuration > Mises à jour, D25). Standard library only: the Windows launcher
(scripts/windows/launcher.py) imports it for `Multitracker.exe --update`.

- Portable Windows build (a VERSION file, no .git): follows the GitHub releases. The app downloads the zip of the
  latest release, checks its sha256, extracts it into update/new/ and exits with EXIT_UPDATE; Multitracker.exe
  (scripts/windows/update.go) then swaps the folders, keeping config/ and data/, and starts the new version. If the
  new version does not start, the old one is put back.
- Git checkout (the Pi): follows origin/main. scripts/update.sh, started detached, fast-forwards main, reinstalls
  what changed, rebuilds the interface and restarts the app.

The state of the running or last update is in data/update/status.json: written before the restart, read after it.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
REPO = "Hikari-rom/archipelago-multitracker"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET = "ArchipelagoMultitracker-windows-x64.zip"
PORTABLE_DIR = "ArchipelagoMultitracker"  # top folder of the zip
EXIT_UPDATE = 75  # the app exits with it once the new version is staged: Multitracker.exe swaps the folders
FIRST_CHECK_DELAY = 60.0
CHECK_EVERY = 24 * 3600.0
STALE_RUNNING = 3600.0  # a "running" status older than this was interrupted
USER_AGENT = "archipelago-multitracker-updater"


class UpdateError(Exception):
    pass


def detect_mode(root: Path) -> str:
    if (root / ".git").exists():
        return "git"
    if (root / "VERSION").is_file():
        return "portable"
    return "none"


def parse_version(text: str | None) -> tuple[int, ...] | None:
    """v1.2.3, or v1.2.3-N-gSHA (git describe: a build N commits after the tag, newer than v1.2.3)."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-(\d+)-g[0-9a-f]+)?", (text or "").strip())
    return tuple(int(x or 0) for x in m.groups()) if m else None


def is_newer(latest: str, current: str | None) -> bool:
    """A development build (no x.y.z version) is offered any release."""
    new, cur = parse_version(latest), parse_version(current)
    if new is None:
        return False
    return cur is None or new > cur


def read_status(root: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((root / "data" / "update" / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_status(root: Path, **status: Any) -> dict[str, Any]:
    path = root / "data" / "update" / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    status.setdefault("at", time.time())
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return status


# --- portable build ---------------------------------------------------------------------------------------------

def portable_version(root: Path) -> str | None:
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _get(url: str, timeout: float) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def fetch_release(url: str | None = None, timeout: float = 20.0) -> dict[str, Any]:
    """The latest release and its Windows zip. MT_UPDATE_RELEASE_URL replaces the GitHub API (tests, CI)."""
    url = url or os.environ.get("MT_UPDATE_RELEASE_URL") or RELEASE_API
    try:
        with _get(url, timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("aucune release publiée") from exc
        raise UpdateError(f"GitHub a répondu {exc.code}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise UpdateError(f"impossible de joindre GitHub : {exc}") from exc
    asset = next((a for a in data.get("assets", []) if a.get("name") == ASSET), None)
    if asset is None:
        raise UpdateError(f"la release {data.get('tag_name')} n'a pas de {ASSET}")
    digest = asset.get("digest") or ""
    return {"version": str(data.get("tag_name", "")), "url": data.get("html_url"), "notes": data.get("body") or "",
            "published_at": data.get("published_at"),
            "asset": {"url": asset["browser_download_url"], "size": int(asset.get("size") or 0),
                      "sha256": digest.removeprefix("sha256:") if digest.startswith("sha256:") else None}}


def download(asset: dict[str, Any], dest: Path, progress: Callable[[int, int], None] | None = None,
             timeout: float = 60.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    sha, size, done = hashlib.sha256(), int(asset.get("size") or 0), 0
    try:
        with _get(asset["url"], timeout) as resp, open(dest, "wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
                sha.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, size)
    except (urllib.error.URLError, OSError) as exc:
        raise UpdateError(f"téléchargement interrompu : {exc}") from exc
    if size and done != size:
        raise UpdateError(f"téléchargement incomplet ({done} octets sur {size})")
    if asset.get("sha256") and sha.hexdigest() != asset["sha256"]:
        raise UpdateError("le fichier téléchargé ne correspond pas à l'empreinte de la release")


def extract(zip_path: Path, dest: Path) -> Path:
    """Extract the zip into dest (emptied first) and return its top folder."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    base = dest.resolve()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                target = (dest / name).resolve()
                if target != base and base not in target.parents:
                    raise UpdateError(f"chemin refusé dans le zip : {name}")
            zf.extractall(dest)
    except zipfile.BadZipFile as exc:
        raise UpdateError("le zip téléchargé est illisible") from exc
    top = dest / PORTABLE_DIR
    for need in ("VERSION", "Multitracker.exe", "python", "backend"):
        if not (top / need).exists():
            raise UpdateError(f"le zip ne contient pas {PORTABLE_DIR}/{need}")
    return top


def stage_portable(root: Path, release: dict[str, Any],
                   progress: Callable[[int, int], None] | None = None) -> Path:
    """Download and extract the release into update/new/; Multitracker.exe does the rest after the app exits."""
    work = root / "update"
    zip_path = work / ASSET
    download(release["asset"], zip_path, progress)
    top = extract(zip_path, work / "new")
    zip_path.unlink(missing_ok=True)
    got = (top / "VERSION").read_text(encoding="utf-8").strip()
    if got != release["version"]:
        raise UpdateError(f"le zip est la version {got}, pas {release['version']}")
    return top


# --- git checkout -----------------------------------------------------------------------------------------------

def _git(root: Path, *args: str, timeout: float = 60.0) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout, check=True)
    except subprocess.CalledProcessError as exc:
        raise UpdateError(f"git {args[0]} : {(exc.stderr or exc.stdout).strip()}") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"git {args[0]} : {exc}") from exc
    return out.stdout.strip()


def git_version(root: Path) -> dict[str, Any]:
    return {"version": _git(root, "describe", "--tags", "--always"), "commit": _git(root, "rev-parse", "--short", "HEAD"),
            "date": int(_git(root, "log", "-1", "--format=%ct"))}


def git_check(root: Path, since: str | None = None, fetch: bool = True) -> tuple[dict[str, Any], str | None]:
    """origin/main and the commits the running app does not have (since: the commit it started on; the Pi's checkout
    also gets commits made in it, without a restart). The second value says why the update cannot run."""
    if fetch:
        _git(root, "fetch", "--quiet", "origin", "main", timeout=120)
    base = since or "HEAD"
    commits = []
    for line in _git(root, "log", "--format=%h%x09%ct%x09%s", "-n", "50", f"{base}..origin/main").splitlines():
        sha, ts, subject = line.split("\t", 2)
        commits.append({"commit": sha, "date": int(ts), "subject": subject})
    latest = {"version": _git(root, "rev-parse", "--short", "origin/main"),
              "behind": int(_git(root, "rev-list", "--count", f"{base}..origin/main")), "commits": commits}
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        return latest, f"le dépôt est sur la branche {branch}, pas main"
    ahead = int(_git(root, "rev-list", "--count", "origin/main..HEAD"))
    if ahead:
        return latest, f"{ahead} commit(s) local(aux) pas encore poussé(s) : mise à jour à faire à la main"
    return latest, None


def start_git_update(root: Path, since: str | None = None) -> None:
    """scripts/update.sh in its own session: it survives the restart of the app. since: the commit the app started
    on, so that the script also rebuilds and restarts for commits already in the checkout."""
    logs = root / "data" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MT_UPDATE_SINCE=since or "")
    with open(logs / "update.log", "ab") as out:
        subprocess.Popen(["bash", str(root / "scripts" / "update.sh")], cwd=root, stdin=subprocess.DEVNULL,
                         stdout=out, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True, env=env)


# --- service ----------------------------------------------------------------------------------------------------

class Updater:
    def __init__(self, root: Path = ROOT, mode: str | None = None, release_url: str | None = None,
                 on_exit: Callable[[int], None] | None = None) -> None:
        self.root = root
        self.mode = mode or detect_mode(root)
        self.release_url = release_url
        self.on_exit = on_exit  # set by __main__: stops the server with an exit code
        self.latest: dict[str, Any] | None = None
        self.blocked: str | None = None
        self.checked_at: float | None = None
        self.check_error: str | None = None
        self.progress: dict[str, int] | None = None
        self._busy = False
        self._lock = asyncio.Lock()
        self.started_commit: str | None = None  # git: the code this process runs
        if self.mode == "git":
            try:
                self.started_commit = _git(root, "rev-parse", "HEAD")
            except UpdateError:
                pass
        self._settle_status()

    # the current version, without network
    def current(self) -> dict[str, Any]:
        if self.mode == "portable":
            return {"version": portable_version(self.root)}
        if self.mode == "git":
            try:
                cur = git_version(self.root)
            except UpdateError:
                return {"version": None}
            if self.started_commit and not self.started_commit.startswith(cur["commit"]):
                cur["running"] = self.started_commit[:len(cur["commit"])]  # the checkout moved since the start
            return cur
        return {"version": None}

    def _current_id(self) -> str | None:
        cur = self.current()
        return cur.get("commit") if self.mode == "git" else cur.get("version")

    def _settle_status(self) -> None:
        """After a restart: did the update land? (Multitracker.exe puts the old version back if the new one fails.)"""
        st = read_status(self.root)
        if not st:
            return
        if st.get("state") == "restarting" and self.mode == "portable":
            if self._current_id() == st.get("to"):
                write_status(self.root, **{**st, "state": "done", "at": time.time(), "message": ""})
            else:
                write_status(self.root, **{**st, "state": "error", "at": time.time(),
                                           "message": "la nouvelle version n'a pas démarré : l'ancienne a été remise"})
        elif st.get("state") == "running" and time.time() - float(st.get("at") or 0) > STALE_RUNNING:
            write_status(self.root, **{**st, "state": "error", "message": "mise à jour interrompue"})

    def _adopt_done_update(self) -> None:
        """git: an update that needed no restart (interface or docs only) leaves this process on the new code."""
        st = read_status(self.root)
        if self.mode != "git" or not st or st.get("state") != "done" or not st.get("to"):
            return
        try:
            head = _git(self.root, "rev-parse", "HEAD")
        except UpdateError:
            return
        if head.startswith(str(st["to"])):
            self.started_commit = head

    def status(self) -> dict[str, Any] | None:
        st = read_status(self.root)
        if st and self.progress and st.get("state") == "running":
            st["progress"] = self.progress
        return st

    def available(self) -> bool:
        if not self.latest or self.blocked:
            return False
        if self.mode == "portable":
            return is_newer(self.latest["version"], portable_version(self.root))
        return self.latest.get("behind", 0) > 0

    def running(self) -> bool:
        st = read_status(self.root)
        return self._busy or bool(st and st.get("state") in ("running", "restarting")
                                  and time.time() - float(st.get("at") or 0) < STALE_RUNNING)

    def info(self) -> dict[str, Any]:
        self._adopt_done_update()
        return {"mode": self.mode, "current": self.current(), "latest": self.latest, "available": self.available(),
                "blocked": self.blocked, "checked_at": self.checked_at, "check_error": self.check_error,
                "running": self.running(), "status": self.status()}

    def check_sync(self) -> None:
        self._adopt_done_update()
        try:
            if self.mode == "portable":
                self.latest, self.blocked = fetch_release(self.release_url), None
            elif self.mode == "git":
                self.latest, self.blocked = git_check(self.root, self.started_commit)
            else:
                raise UpdateError("installation sans mise à jour automatique (ni dépôt git, ni version portable)")
            self.check_error = None
        except UpdateError as exc:
            self.check_error = str(exc)
        self.checked_at = time.time()

    async def check(self) -> dict[str, Any]:
        async with self._lock:
            await asyncio.to_thread(self.check_sync)
        return self.info()

    async def loop(self) -> None:
        await asyncio.sleep(FIRST_CHECK_DELAY)
        while True:
            if self.mode != "none" and not self.running():
                await self.check()
                if self.available():
                    log.info("update available: %s", self.latest and self.latest.get("version"))
            await asyncio.sleep(CHECK_EVERY)

    async def apply(self) -> None:
        """Start the update; GET /api/update follows it."""
        async with self._lock:
            if self.running():
                raise UpdateError("une mise à jour est déjà en cours")
            await asyncio.to_thread(self.check_sync)
            if self.check_error:
                raise UpdateError(self.check_error)
            if self.blocked:
                raise UpdateError(self.blocked)
            if not self.available():
                raise UpdateError("déjà à jour")
            self._busy = True
        if self.mode == "git":
            # written here too, so that the page never reads the status of the previous update meanwhile
            write_status(self.root, mode="git", state="running", step="Démarrage", message="",
                         **{"from": (self.started_commit or "")[:7], "to": (self.latest or {}).get("version")})
            try:
                await asyncio.to_thread(start_git_update, self.root, self.started_commit)
            finally:
                self._busy = False
            return
        asyncio.create_task(self._apply_portable())

    async def _apply_portable(self) -> None:
        release = self.latest or {}
        frm, to = portable_version(self.root), release.get("version")
        write_status(self.root, mode="portable", state="running", step="Téléchargement", message="", **{"from": frm, "to": to})

        def progress(done: int, total: int) -> None:
            self.progress = {"done": done, "total": total}

        try:
            await asyncio.to_thread(stage_portable, self.root, release, progress)
        except UpdateError as exc:
            write_status(self.root, mode="portable", state="error", step="Téléchargement", message=str(exc),
                         **{"from": frm, "to": to})
            return
        finally:
            self.progress = None
            self._busy = False
        write_status(self.root, mode="portable", state="restarting", step="Redémarrage", message="",
                     **{"from": frm, "to": to})
        if self.on_exit is None:  # not started by Multitracker.exe: nobody to swap the folders
            write_status(self.root, mode="portable", state="error", step="Redémarrage",
                         message="version téléchargée dans update/new : relance Multitracker.exe pour l'installer",
                         **{"from": frm, "to": to})
            return
        await asyncio.sleep(1.0)  # let the browser read the "restarting" state
        self.on_exit(EXIT_UPDATE)


def stage_from_cli(root: Path = ROOT, say: Callable[[str], None] = print) -> bool:
    """Multitracker.exe --update: True when a new version waits in update/new/ (the caller exits with EXIT_UPDATE)."""
    up = Updater(root, mode="portable")
    up.check_sync()
    if up.check_error:
        say(f"Mise à jour impossible : {up.check_error}")
        return False
    if not up.available():
        say(f"Déjà à jour ({portable_version(root)}).")
        return False
    version = up.latest["version"]
    say(f"Téléchargement de la version {version}…")
    last = [-1]

    def progress(done: int, total: int) -> None:
        pct = done * 100 // total if total else 0
        if pct // 10 != last[0]:
            last[0] = pct // 10
            say(f"  {pct} %")

    frm = portable_version(root)
    try:
        stage_portable(root, up.latest, progress)
    except UpdateError as exc:
        say(f"Mise à jour impossible : {exc}")
        return False
    write_status(root, mode="portable", state="restarting", step="Redémarrage", message="", **{"from": frm, "to": version})
    return True


if __name__ == "__main__":  # python -m multitracker.updater: show what an update would do
    u = Updater()
    u.check_sync()
    json.dump(u.info(), sys.stdout, indent=2, ensure_ascii=False)
    print()
