"""Shared I/O helpers for exporters."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO, cast


@contextmanager
def atomic_write(path: Path, mode: str = "w", **kwargs: Any) -> Generator[TextIO, None, None]:
    """Write to *path* via a sibling temp file and an atomic ``os.replace``.

    The destination is never truncated in place: readers only ever observe the
    previous content or the fully written replacement. On failure the temp file
    is removed and the destination is left untouched.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open(mode, **kwargs) as fh:
            yield cast("TextIO", fh)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
