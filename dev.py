"""
Development server launcher - runs both FastAPI backend and Vite frontend.
Usage: python dev.py
"""

import subprocess
import sys
import os
import signal
from pathlib import Path

ROOT_DIR = Path(__file__).parent
UI_DIR = ROOT_DIR / "ui"


def main():
    processes = []

    try:
        # Start FastAPI backend
        print("[dev] Starting FastAPI backend on http://localhost:8000")
        backend = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=ROOT_DIR
        )
        processes.append(backend)

        # Start Vite frontend
        print("[dev] Starting Vite frontend on http://localhost:5173")

        # Use npm.cmd on Windows, npm on Unix
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=UI_DIR
        )
        processes.append(frontend)

        print("\n[dev] Both servers running. Press Ctrl+C to stop.\n")

        # Wait for either process to exit
        while all(p.poll() is None for p in processes):
            try:
                processes[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass

    except KeyboardInterrupt:
        print("\n[dev] Shutting down...")

    finally:
        # Clean up all processes
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()

        print("[dev] Stopped.")


if __name__ == "__main__":
    main()
