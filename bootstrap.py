#!/usr/bin/env python3
"""
MeetingScribe Bootstrap (very simple)

Goals (non-intrusive):
- Create a local Python venv in .venv (if missing)
- Install requirements.txt into that venv
- Create storage folders used by the Raycast extension
- Generate a .env.sample with useful variables (if missing)
- Print precise next steps to run the Raycast extension (npm install / dev)

It does NOT try to install Node/Raycast or modify your global system.
Run from repo root:
  python bootstrap.py
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
import platform


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            check=False,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError as e:
        return 127, "", str(e)


def venv_python_path(venv_dir: Path) -> Path:
    if platform.system().lower().startswith("win"):
        p = venv_dir / "Scripts" / "python.exe"
        if p.exists():
            return p
        # fallback
        p = venv_dir / "Scripts" / "python"
        return p
    else:
        p = venv_dir / "bin" / "python3"
        if p.exists():
            return p
        return venv_dir / "bin" / "python"


def main() -> int:
    repo_root = Path(__file__).resolve().parent

    # 1) Check Python version
    if sys.version_info < (3, 10):
        print("[!] Python 3.10+ is required. Found:", sys.version)
        print("    Please install a recent Python and rerun: python bootstrap.py")
        return 1

    # 2) Create venv if needed
    venv_dir = repo_root / ".venv"
    if not venv_dir.exists():
        print("[*] Creating local virtualenv in .venv ...")
        rc, out, err = run([sys.executable, "-m", "venv", str(venv_dir)])
        if rc != 0:
            print("[!] Failed to create venv:\n", err)
            return rc
    else:
        print("[*] Using existing .venv")

    vpy = venv_python_path(venv_dir)
    if not vpy.exists():
        print("[!] Could not locate venv python at:", vpy)
        return 1

    # 3) Upgrade pip + install requirements
    req = repo_root / "requirements.txt"
    if not req.exists():
        print("[!] requirements.txt not found at repo root; nothing to install.")
    else:
        print("[*] Upgrading pip ...")
        rc, out, err = run([str(vpy), "-m", "pip", "install", "-U", "pip"])
        if rc != 0:
            print("[!] pip upgrade failed:\n", err)
            return rc

        print("[*] Installing requirements.txt ...")
        rc, out, err = run([str(vpy), "-m", "pip", "install", "-r", str(req)])
        if rc != 0:
            print("[!] pip install failed:\n", err)
            # Print brief hint for common blockers
            print("Hint: On Windows, ensure you have internet and no corporate proxy blocks pip.")
            return rc

    # 4) Ensure storage folders
    rec_dir = repo_root / "storage" / "recordings"
    trn_dir = repo_root / "storage" / "transcriptions"
    rec_dir.mkdir(parents=True, exist_ok=True)
    trn_dir.mkdir(parents=True, exist_ok=True)

    # 5) Create .env.sample
    env_sample = repo_root / ".env.sample"
    if not env_sample.exists():
        env_sample.write_text(
            """# MeetingScribe sample env\n"
            "GEMINI_API_KEY=\n"
            "GEMINI_MODEL=models/gemini-2.0-flash-exp\n"
            "GEMINI_OPTIMIZE=0\n"
            "# AUDIO_FILE_PATH=absolute/or/relative/path.wav\n",
            encoding="utf-8",
        )
        print("[*] Created .env.sample (configure Gemini if you plan to use Import Google)")

    # 6) Print next steps
    print("\n== Bootstrap complete ==")
    print("Python venv:", vpy)
    print("Repo root:", repo_root)
    print("\nNext steps:")
    print("1) Open Raycast extension preferences and set:")
    print("   - pythonPath:", vpy)
    print("   - projectPath:", repo_root)
    print("2) From a terminal:")
    print("   cd raycast-extension && npm install && npm run dev")
    print("\nTips:")
    print("- On Windows loopback, play some audio so Start Recording captures frames.")
    print("- For Import Google, set GEMINI_API_KEY (env or preferences) and try the command.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

