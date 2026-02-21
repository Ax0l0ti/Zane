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

        # Show Tailscale access info
        try:
            ts_result = subprocess.run(
                ["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2
            )
            ts_ip = ts_result.stdout.strip()
            if ts_ip:
                print(f"[dev] Tailscale IP: {ts_ip}")
                print(f"[dev]   Backend:  http://{ts_ip}:8000")
                print(f"[dev]   Frontend: http://{ts_ip}:5173")
        except Exception:
            print("[dev] Tailscale not detected — localhost only")

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
