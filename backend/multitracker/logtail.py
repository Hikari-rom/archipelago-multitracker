"""Follow the app's log file (data/logs/app.log, written by scripts/app.sh) for the "Journal" page.

Reads the file like `tail -f`: the last lines first, then what gets appended. Copes with the rotation done by
scripts/app.sh at start (file replaced or truncated). The room password is masked if it ever shows up.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

TAIL_MAX_BYTES = 512 * 1024  # how far back the first batch may look
CHUNK_MAX_BYTES = 256 * 1024  # max read per poll (a burst is sent over several polls)
LINE_MAX_CHARS = 4000


def last_lines(path: Path, count: int) -> tuple[list[str], int, int]:
    """The last `count` complete lines of `path`, the offset just after them and the file's inode.

    A partial last line (being written) is left for the next read. Missing file: no lines, offset 0.
    """
    try:
        with open(path, "rb") as f:
            st = os.fstat(f.fileno())
            size = st.st_size
            start = max(0, size - TAIL_MAX_BYTES)
            f.seek(start)
            data = f.read(size - start)
    except FileNotFoundError:
        return [], 0, 0
    end = data.rfind(b"\n") + 1  # complete lines only
    lines = data[:end].decode("utf-8", "replace").splitlines()
    if start > 0 and lines:
        lines = lines[1:]  # the first one is probably cut
    return [_clip(line) for line in lines[-count:]] if count > 0 else [], start + end, st.st_ino


@dataclass
class Follower:
    """Reads what was appended to the log since the last call."""
    path: Path
    offset: int
    inode: int
    _partial: bytes = field(default=b"", repr=False)

    def poll(self) -> tuple[bool, list[str]]:
        """(reset, new complete lines). reset: the file was replaced or truncated, reading restarted at 0."""
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return False, []
        reset = False
        if st.st_ino != self.inode or st.st_size < self.offset:
            reset = self.inode != 0 or self.offset > 0
            self.inode, self.offset, self._partial = st.st_ino, 0, b""
        if st.st_size == self.offset:
            return reset, []
        with open(self.path, "rb") as f:
            f.seek(self.offset)
            data = f.read(min(st.st_size - self.offset, CHUNK_MAX_BYTES))
        self.offset += len(data)
        data = self._partial + data
        end = data.rfind(b"\n") + 1
        self._partial = data[end:]
        if len(self._partial) > LINE_MAX_CHARS * 4:  # a huge line without newline: send it anyway
            end, self._partial = len(data), b""
        return reset, [_clip(line) for line in data[:end].decode("utf-8", "replace").splitlines()]


def _clip(line: str) -> str:
    return line if len(line) <= LINE_MAX_CHARS else line[:LINE_MAX_CHARS] + " …"


def mask(lines: list[str], secrets: list[str]) -> list[str]:
    secrets = [s for s in secrets if s and len(s) >= 3]
    if not secrets:
        return lines
    out = []
    for line in lines:
        for s in secrets:
            line = line.replace(s, "•••")
        out.append(line)
    return out
