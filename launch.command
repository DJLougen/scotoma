#!/bin/bash
# Scotoma launcher for macOS. Double-click in Finder, or run: bash launch.command
# Builds and starts the app. First run takes several minutes.
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

need() { command -v "$1" >/dev/null 2>&1; }
if ! need cargo; then echo "Rust is missing. Install it with:  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"; read -n1 -r -p "Press any key to close."; exit 1; fi
if ! need npm;   then echo "Node is missing. Install it with:  brew install node"; read -n1 -r -p "Press any key to close."; exit 1; fi

MODEL=app/src-tauri/models/default
if [ ! -f "$MODEL/config.json" ]; then
  echo "== Fetching the detection model (one time) =="
  if need python3 && python3 -m venv .venv && . .venv/bin/activate \
     && pip install -q torch "transformers>=4.57,<5" onnx onnxruntime \
     && python scripts/fetch_model.py; then
    echo "Model ready."
  else
    echo "!! Model step failed. Continuing on rules only; the app will say so in its header."
  fi
  deactivate 2>/dev/null || true
fi

echo "== Building and starting Scotoma =="
cd app && npm install --no-audit --no-fund && npm run dev
status=$?
[ $status -ne 0 ] && { echo; echo "Build or launch failed (exit $status). Copy the error above back to Claude."; read -n1 -r -p "Press any key to close."; }
