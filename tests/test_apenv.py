"""apenv: the stubs reach child processes even after setup() put them on our own path."""
import os

from multitracker import apenv


def test_subprocess_env_keeps_stubs_after_setup(monkeypatch):
    monkeypatch.setattr(apenv.importlib.util, "find_spec", lambda name: None)  # the real package is missing
    monkeypatch.setattr(apenv.sys, "path", [p for p in apenv.sys.path if p != str(apenv.STUBS_DIR)])
    apenv.setup()
    assert apenv.sys.path.count(str(apenv.STUBS_DIR)) == 1
    apenv.setup()  # idempotent
    assert apenv.sys.path.count(str(apenv.STUBS_DIR)) == 1
    assert str(apenv.STUBS_DIR) in apenv.subprocess_env()["PYTHONPATH"].split(os.pathsep)


def test_core_overrides_from_catalog(tmp_path):
    catalog = tmp_path / "apworlds.yaml"
    catalog.write_text("apworlds:\n"
                       "  tunic: {game: TUNIC, source: github, filename: tunic.apworld, replaces_core: true}\n"
                       "  other: {game: Other, source: github, filename: other.apworld}\n"
                       "  broken: {game: Broken, source: github, replaces_core: true}\n", encoding="utf-8")
    assert apenv.core_overrides(catalog) == {"worlds.tunic": apenv.AP_DIR / "custom_worlds" / "tunic.apworld"}
    assert apenv.core_overrides(tmp_path / "missing.yaml") == {}


def test_core_override_finder_imports_from_the_apworld(tmp_path):
    import zipfile
    apworld = tmp_path / "fakecore.apworld"
    with zipfile.ZipFile(apworld, "w") as zf:
        zf.writestr("fakecore/__init__.py", "SOURCE = 'apworld'\n")
    finder = apenv._CoreOverrideFinder()
    finder.apworlds = {"worlds.fakecore": apworld, "worlds.gone": tmp_path / "gone.apworld"}
    spec = finder.find_spec("worlds.fakecore", None)
    assert spec is not None and spec.origin.endswith("fakecore.apworld/fakecore/__init__.py")
    assert finder.find_spec("worlds.gone", None) is None  # not downloaded: the core world loads as usual
    assert finder.find_spec("worlds.celeste", None) is None


def test_resource_listdir_sorted_like_windows(tmp_path, monkeypatch):
    import pkg_resources
    apenv.setup()
    pkg = tmp_path / "listpkg"
    (pkg / "data").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    for name in ("b.json", "c.json", "a.json"):
        (pkg / "data" / name).write_text("{}")
    monkeypatch.syspath_prepend(str(tmp_path))
    listdir = os.listdir  # ext4 lists in hash order: make sure the folder is not already in name order
    monkeypatch.setattr(os, "listdir", lambda path: ["c.json", "a.json", "b.json"] if str(path).endswith("data")
                        else listdir(path))
    assert pkg_resources.resource_listdir("listpkg", "data") == ["a.json", "b.json", "c.json"]
