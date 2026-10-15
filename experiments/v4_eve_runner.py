"""Run EvE with LLMAO's external tmux failure trace installed."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(os.environ["LLMAO_PROJECT_ROOT"]).resolve(strict=True)
    eve_source_root = Path(os.environ["LLMAO_EVE_SOURCE_ROOT"]).resolve(strict=True)
    sys.path[:0] = [str(project_root), str(eve_source_root)]

    from experiments.v4_tmux_failure_capture import install_tmux_failure_capture

    trace_value = os.environ.get("LLMAO_V4_TMUX_TRACE_PATH")
    if not trace_value:
        raise RuntimeError("LLMAO_V4_TMUX_TRACE_PATH is required")
    install_tmux_failure_capture(Path(trace_value))

    from scaling_evolve.algorithms.eve.runner import main as eve_main

    eve_main()


if __name__ == "__main__":
    main()
