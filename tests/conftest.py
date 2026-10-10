import __main__

# Archipelago's settings register an atexit autosave of host.yaml that asserts it is not running under
# pytest (noise only: the vendored host.yaml is not part of the repo). Hide pytest from that check.
__main__.__file__ = ""
