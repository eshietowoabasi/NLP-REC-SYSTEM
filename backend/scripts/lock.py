"""Regenerate the pinned lockfiles from requirements.in / requirements-dev.in.

    python scripts/lock.py          (from backend/, inside the virtualenv)

The lockfiles target the Docker image (Linux, Python 3.11) whatever machine this runs on, so
they are identical on Windows, macOS and Linux. uv resolves from package metadata without
installing anything.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND.parent / ".env")
COMMON = [
    "--python-version",
    "3.11",
    "--python-platform",
    "x86_64-manylinux_2_28",
    # Take each package's best matching version from any index (PyPI or the PyTorch CPU index).
    "--index-strategy",
    "unsafe-best-match",
    "--emit-index-url",
    "--no-header",
    "--no-python-downloads",
    "--quiet",
]


def compile_lock(source: str, target: str) -> None:
    extra = []
    # Same switch as the app (see app/utils/tls.py): trust the OS certificate store.
    if os.environ.get("USE_SYSTEM_CERTS", "").lower() == "true":
        extra.append("--system-certs")
    subprocess.run(
        [sys.executable, "-m", "uv", "pip", "compile", source, "-o", target, *COMMON, *extra],
        cwd=BACKEND,
        check=True,
    )
    print(f"wrote {target}")


if __name__ == "__main__":
    compile_lock("requirements.in", "requirements.txt")
    compile_lock("requirements-dev.in", "requirements-dev.txt")
