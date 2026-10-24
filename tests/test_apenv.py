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
