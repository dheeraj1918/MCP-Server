"""
Factory OS — unified launcher.

Usage:
    python run.py          # starts API backend + Vite frontend
    python run.py --api    # API only  (http://localhost:8000)
    python run.py --ui     # UI only   (http://localhost:5173)
"""

import argparse
import os
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _stream(proc: subprocess.Popen, prefix: str):
    for line in proc.stdout:  # type: ignore[union-attr]
        print(f"{prefix} {line}", end="", flush=True)


def start_api() -> subprocess.Popen:
    print("▶  Starting FastAPI backend  →  http://localhost:8000")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.api"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=_stream, args=(proc, "[API]"), daemon=True).start()
    return proc


def start_ui() -> subprocess.Popen:
    print("▶  Starting Vite dev server  →  http://localhost:5173")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=_stream, args=(proc, "[UI] "), daemon=True).start()
    return proc


def main():
    parser = argparse.ArgumentParser(description="Factory OS launcher")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--api", action="store_true", help="Start API server only")
    group.add_argument("--ui",  action="store_true", help="Start UI dev server only")
    args = parser.parse_args()

    procs: list[subprocess.Popen] = []
    if args.api:
        procs.append(start_api())
    elif args.ui:
        procs.append(start_ui())
    else:
        procs.append(start_api())
        procs.append(start_ui())

    print("\nFactory OS is running. Press Ctrl+C to stop.\n")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\nShutting down…")
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
