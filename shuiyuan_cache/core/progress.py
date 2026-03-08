from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TextIO

ProgressCallback = Callable[[str], None]


def build_stream_progress_reporter(
    prefix: str = "sync",
    stream: TextIO | None = None,
) -> ProgressCallback:
    output = stream or sys.stderr
    label = prefix.strip() or "sync"

    def report(message: str) -> None:
        print(f"[{label}] {message}", file=output, flush=True)

    return report
