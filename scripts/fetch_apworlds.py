#!/usr/bin/env python3
"""Download the apworlds listed in config/apworlds.yaml into Archipelago's custom_worlds/.

- `source: core` entries ship with Archipelago itself: nothing to download.
- `source: user` entries are not distributed by the app: each user imports them from their own Archipelago
  install (page Configuration, D27); nothing to download.
- `source: github` entries are resolved to a GitHub release (`tag: latest` or a pinned tag),
  the asset matching `asset` (a glob) is downloaded, and the resolved version is written
  to config/apworlds.lock.yaml.
- `source: github` entries with `commit: <sha>` (and `filename: <module>.apworld`) take the repository itself at
  that commit, for apworlds used from a branch rather than a release: the archive's top folder is renamed to
  the module name (the apworld file name without `.apworld`).

Idempotent: an asset already present with the sha256 recorded in the lock is not re-downloaded.
Use `--update` to re-resolve `latest` tags instead of reusing the locked tag.

A GitHub token is optional (GITHUB_TOKEN env var, or `gh auth token` if gh is installed);
without one the anonymous API limit (60 requests/hour) is enough for a normal run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "apworlds.yaml"
LOCK = ROOT / "config" / "apworlds.lock.yaml"
DEST = ROOT / "vendor" / "Archipelago" / "custom_worlds"
API = "https://api.github.com"


def github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    if shutil.which("gh"):
        try:
            out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None


class GitHub:
    def __init__(self) -> None:
        self.token = github_token()

    def _request(self, url: str, accept: str = "application/vnd.github+json") -> urllib.request.Request:
        req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "archipelago-multitracker"})
        if self.token and url.startswith(API):
            req.add_header("Authorization", f"Bearer {self.token}")
        return req

    def get_json(self, path: str):
        with urllib.request.urlopen(self._request(f"{API}{path}"), timeout=30) as resp:
            return json.load(resp)

    def release(self, repo: str, tag: str, allow_prerelease: bool) -> dict:
        if tag != "latest":
            return self.get_json(f"/repos/{repo}/releases/tags/{tag}")
        releases = self.get_json(f"/repos/{repo}/releases?per_page=30")
        for rel in releases:
            if rel.get("draft"):
                continue
            if rel.get("prerelease") and not allow_prerelease:
                continue
            return rel
        raise RuntimeError(f"no suitable release found for {repo}")

    def download(self, url: str, dest: Path, expected_size: int | None, max_size: int = 200 << 20) -> str:
        """Download to dest atomically; returns the sha256. Checks the size reported by GitHub."""
        tmp = dest.with_name(dest.name + ".part")
        h = hashlib.sha256()
        size = 0
        try:
            with urllib.request.urlopen(self._request(url, "application/octet-stream"), timeout=120) as resp, \
                    open(tmp, "wb") as fh:
                for chunk in iter(lambda: resp.read(1 << 20), b""):
                    size += len(chunk)
                    if size > max_size:
                        raise RuntimeError(f"download larger than {max_size} bytes: {url}")
                    h.update(chunk)
                    fh.write(chunk)
            if expected_size is not None and size != expected_size:
                raise RuntimeError(f"truncated download ({size} of {expected_size} bytes): {url}")
            tmp.replace(dest)
        finally:
            tmp.unlink(missing_ok=True)
        return h.hexdigest()


def repack_archive(archive: Path, dest: Path) -> None:
    """Repository archive -> apworld: rename its single top folder to the module name (atomic write)."""
    module = dest.name[: -len(".apworld")]
    tmp = dest.with_name(dest.name + ".part")
    try:
        with zipfile.ZipFile(archive) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            infos = src.infolist()
            tops = {info.filename.split("/", 1)[0] for info in infos}
            if len(tops) != 1 or any("/" not in info.filename for info in infos):
                raise RuntimeError(f"expected one top folder in the repository archive, found {sorted(tops)}")
            for info in infos:
                rest = info.filename.split("/", 1)[1]
                parts = PurePosixPath(rest).parts
                if rest.startswith("/") or ".." in parts or "\\" in rest:
                    raise RuntimeError(f"unsafe path in the repository archive: {info.filename!r}")
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError(f"symbolic link in the repository archive: {info.filename!r}")
                new = zipfile.ZipInfo(f"{module}/{rest}" if rest else f"{module}/", info.date_time)
                new.external_attr, new.compress_type = info.external_attr, zipfile.ZIP_DEFLATED
                out.writestr(new, b"" if info.is_dir() else src.read(info))
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def safe_filename(name: str) -> str:
    """Asset / lock file names are joined to DEST: refuse anything that is not a plain *.apworld name."""
    if Path(name).name != name or name.startswith(".") or not name.endswith(".apworld"):
        raise RuntimeError(f"refusing unsafe apworld file name {name!r}")
    return name


def resolve_entry(gh: GitHub, key: str, entry: dict, locked: dict | None, update: bool) -> dict:
    repo = entry["repo"]
    if entry.get("commit"):
        commit = str(entry["commit"])
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            raise RuntimeError(f"{key}: commit must be a full 40-character sha, got {commit!r}")
        if not entry.get("filename"):
            raise RuntimeError(f"{key}: an entry with `commit` needs `filename` (<module>.apworld)")
        return {"repo": repo, "commit": commit, "url": f"https://codeload.github.com/{repo}/zip/{commit}",
                "file": safe_filename(entry["filename"]), "archive": True}
    tag = str(entry.get("tag", "latest"))
    pattern = entry.get("asset", "*.apworld")
    if locked and not update and locked.get("repo") == repo and (tag == "latest" or locked.get("tag") == tag) \
            and locked.get("asset_pattern") == pattern:
        tag = locked["tag"]  # reuse the locked version unless --update
    rel = gh.release(repo, tag, bool(entry.get("allow_prerelease", False)))
    assets = [a for a in rel.get("assets", []) if fnmatch.fnmatch(a["name"], pattern)]
    if len(assets) != 1:
        names = [a["name"] for a in rel.get("assets", [])]
        raise RuntimeError(f"{key}: expected exactly one asset matching {pattern!r} in {repo}@{rel['tag_name']}, "
                           f"found {[a['name'] for a in assets]} among {names}")
    asset = assets[0]
    filename = safe_filename(entry.get("filename") or asset["name"])
    return {
        "repo": repo,
        "tag": rel["tag_name"],
        "published": rel.get("published_at"),
        "asset_pattern": pattern,
        "asset": asset["name"],
        "url": asset["browser_download_url"],
        "size": asset.get("size"),
        "file": filename,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true", help="re-resolve 'latest' tags")
    parser.add_argument("--only", nargs="*", help="only these keys")
    args = parser.parse_args()

    config = load_yaml(CONFIG)
    lock = load_yaml(LOCK)
    locked_entries: dict = lock.get("apworlds", {}) or {}
    DEST.mkdir(parents=True, exist_ok=True)
    gh = GitHub()

    wanted = {**config.get("apworlds", {}), **config.get("tools", {})}
    failures: list[str] = []
    new_lock: dict = {}
    for key, entry in wanted.items():
        if entry.get("source", "github") in ("core", "user"):
            new_lock[key] = {"source": entry["source"], "game": entry.get("game")}
            continue
        if args.only and key not in args.only:
            if key in locked_entries:
                new_lock[key] = locked_entries[key]
            continue
        locked = locked_entries.get(key)
        try:
            resolved = resolve_entry(gh, key, entry, locked, args.update)
            dest = DEST / resolved["file"]
            same_version = bool(locked) and locked.get("url") == resolved["url"] and bool(locked.get("sha256"))
            if same_version and dest.exists() and sha256(dest) == locked["sha256"]:
                resolved["sha256"] = locked["sha256"]
                resolved["downloaded_at"] = locked.get("downloaded_at")
                print(f"= {key}: {resolved['repo']}@{resolved.get('tag') or resolved.get('commit')} ({resolved['file']}) already present")
            else:
                if resolved.get("archive"):
                    archive = dest.with_name(dest.name + ".zip")
                    try:
                        gh.download(resolved["url"], archive, None)
                        repack_archive(archive, dest)
                    finally:
                        archive.unlink(missing_ok=True)
                    digest = sha256(dest)
                else:
                    digest = gh.download(resolved["url"], dest, resolved.get("size"))
                # A commit archive is immutable: its repack may differ by a byte (zlib) but not in content.
                if same_version and digest != locked["sha256"] and not args.update and not resolved.get("archive"):
                    dest.unlink(missing_ok=True)
                    raise RuntimeError(f"sha256 mismatch for {resolved['url']} (asset replaced upstream?); "
                                       f"rerun with --update to accept the new file")
                # remove a previously locked file with a different name, only once the new one is in place
                if locked and locked.get("file") and locked["file"] != resolved["file"]:
                    (DEST / safe_filename(locked["file"])).unlink(missing_ok=True)
                resolved["sha256"] = digest
                resolved["downloaded_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                print(f"+ {key}: {resolved['repo']}@{resolved.get('tag') or resolved.get('commit')} -> {resolved['file']}")
            resolved["source"] = "github"
            resolved["game"] = entry.get("game")
            new_lock[key] = resolved
        except (urllib.error.URLError, RuntimeError, KeyError, OSError, ValueError, TypeError) as exc:
            failures.append(key)
            print(f"! {key}: {exc}", file=sys.stderr)
            if locked:
                new_lock[key] = locked

    known = {v.get("file") for v in new_lock.values()}
    known |= {f"{k}.apworld" for k, v in new_lock.items() if v.get("source") == "user"}  # put there by hand
    try:  # the user's imported apworlds, copied there by the app (D27)
        known |= set(json.loads((DEST / ".user_apworlds.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        pass
    for stray in sorted(DEST.glob("*.apworld")):
        if stray.name not in known:
            print(f"? {stray.name} is in custom_worlds/ but not in config/apworlds.yaml (still loaded by AP)",
                  file=sys.stderr)
    with open(LOCK, "w", encoding="utf-8") as fh:
        fh.write("# Generated by scripts/fetch_apworlds.py — versions actually downloaded. Do not edit by hand.\n")
        yaml.safe_dump({"apworlds": new_lock}, fh, sort_keys=False, allow_unicode=True)
    if failures:
        print(f"{len(failures)} failure(s): {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
