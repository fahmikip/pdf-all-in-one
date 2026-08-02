"""Safe filesystem primitives used by document operations."""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def atomic_output(destination: str | Path) -> Iterator[Path]:
    """Yield a sibling temporary path and publish it only after success."""
    output = Path(destination).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{output.stem}-", suffix=output.suffix, dir=output.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        yield temporary
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise OSError("The PDF operation produced an empty output file.")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_distinct_paths(source: str | Path, destination: str | Path) -> None:
    if Path(source).expanduser().resolve() == Path(destination).expanduser().resolve():
        raise ValueError("Output must be a new file. The original PDF will not be overwritten.")
