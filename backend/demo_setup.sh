#!/usr/bin/env bash
# Run on an Ubuntu NVIDIA Brev instance from any directory: bash backend/demo_setup.sh
set -Eeuo pipefail

backend_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
run_dir="$backend_dir/.demo-run"
mkdir -p "$run_dir"

say(){ printf '\n[Himaya demo] %s\n' "$*"; }
fail(){ printf '\n[Himaya demo] ERROR: %s\n' "$*" >&2; exit 1; }
command -v nvidia-smi >/dev/null || fail 'No NVIDIA GPU driver found. Use a Brev NVIDIA GPU instance.'
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || fail 'GPU is not accessible.'
command -v python3 >/dev/null || fail 'Python 3 is required.'
command -v curl >/dev/null || fail 'curl is required.'

if ! command -v ollama >/dev/null; then
  say 'Installing Ollama from its official Linux installer (may request sudo).'
  curl -fsSL https://ollama.com/install.sh -o "$run_dir/ollama-install.sh"
  sh "$run_dir/ollama-install.sh"
fi

if ! curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null; then
  say 'Starting Ollama locally.'
  nohup ollama serve >"$run_dir/ollama.log" 2>&1 </dev/null &
  for i in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then break; fi
    sleep 1
  done
fi
curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null || fail "Ollama did not start. Read $run_dir/ollama.log"

say 'Pulling qwen2.5:7b-instruct while Python dependencies install.'
(ollama pull qwen2.5:7b-instruct >"$run_dir/ollama-pull.log" 2>&1) &
pull_pid=$!
python3 -m venv "$backend_dir/.venv"
"$backend_dir/.venv/bin/python" -m pip install -r "$backend_dir/requirements.txt"
wait "$pull_pid" || fail "Model pull failed. Read $run_dir/ollama-pull.log"
say 'Ollama model ready.'

if ! command -v cloudflared >/dev/null; then
  command -v dpkg >/dev/null || fail 'cloudflared is missing. Install it using the Cloudflare Linux instructions.'
  arch="$(dpkg --print-architecture)"
  case "$arch" in amd64|arm64) ;; *) fail "Unsupported cloudflared package architecture: $arch";; esac
  say 'Installing cloudflared from the official Cloudflare release (may request sudo).'
  curl -fL --retry 3 -o "$run_dir/cloudflared.deb" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}.deb"
  sudo dpkg -i "$run_dir/cloudflared.deb"
fi

if ! curl -fsS --max-time 2 http://127.0.0.1:8000/health >/dev/null; then
  say 'Starting the Himaya API.'
  (cd "$backend_dir" && nohup env WHISPER_DEVICE="${WHISPER_DEVICE:-cuda}" HIMAYA_ALLOWED_ORIGINS="${HIMAYA_ALLOWED_ORIGINS:-https://himaya-algeria-prototype.noisy-mite-4123.chatgpt.site,http://localhost:5173}" .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 >"$run_dir/api.log" 2>&1 </dev/null &)
fi
for i in {1..30}; do
  if curl -fsS --max-time 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/health || fail "API did not start. Read $run_dir/api.log"

say 'Warming Ollama and checking the real triage endpoint.'
warm_args=()
if [[ -n "${DEMO_AUDIO_FILE:-}" ]]; then warm_args=(--audio "$DEMO_AUDIO_FILE"); fi
"$backend_dir/.venv/bin/python" "$backend_dir/demo_warm.py" "${warm_args[@]}"

say 'Starting a temporary Cloudflare Quick Tunnel. Keep this terminal running.'
say 'Copy the HTTPS URL below into Himaya Operator view → AI service → Connect.'
say 'The tunnel makes the unauthenticated demo API public to anyone with its URL. Stop it after judging (Ctrl+C), then stop the Brev instance.'
exec cloudflared tunnel --url http://127.0.0.1:8000
