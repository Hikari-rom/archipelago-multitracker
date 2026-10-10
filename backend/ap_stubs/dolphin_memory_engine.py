"""Stub of the `dolphin_memory_engine` package.

Some apworlds (PokePark, The Wind Waker client...) import it at world-import time
although only their game client uses it. The real package does not build on the Pi
(aarch64, broken sdist), and the tracker never reads Dolphin's memory, so every
memory access here fails loudly.
"""


class DolphinException(Exception):
    pass


def _unavailable(*_args, **_kwargs):
    raise DolphinException("dolphin_memory_engine is a stub in archipelago-multitracker")


def is_hooked() -> bool:
    return False


def get_status():
    return None


hook = un_hook = _unavailable
read_byte = read_bytes = read_word = read_float = read_double = _unavailable
write_byte = write_bytes = write_word = write_float = write_double = _unavailable
follow_pointers = _unavailable
