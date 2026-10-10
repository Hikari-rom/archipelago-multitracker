import __main__
import os

# Archipelago's settings register an atexit autosave of host.yaml that asserts it is not running under
# pytest (noise only: the vendored host.yaml is not part of the repo). Hide pytest from that check.
__main__.__file__ = ""


def pytest_report_header(config):
    # Some worlds iterate over sets while generating: regenerating a test seed in-process only matches
    # the hosted one when string hashing is fixed. Use scripts/test.sh (PYTHONHASHSEED=0).
    if os.environ.get("PYTHONHASHSEED") != "0":
        return "WARNING: PYTHONHASHSEED is not 0, use scripts/test.sh for reproducible logic tests"
