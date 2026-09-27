# Himaya AI service (Brev GPU)

This Python service uses faster-whisper for multilingual recording transcription and a local Ollama model for extraction and operator triage. It does not connect to a telephone network or dispatch responders. The website's `Call 1021` link remains a separate fallback and cannot be recorded by the browser.

## Run on a Brev GPU instance

Brev instances have Python, CUDA, and Docker. On the instance, install Ollama, then run:

```bash
ollama pull qwen2.5:7b-instruct
cd himaya/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export HIMAYA_ALLOWED_ORIGINS=https://himaya-algeria-prototype.noisy-mite-4123.chatgpt.site
export WHISPER_DEVICE=cuda
uvicorn app:app --host 0.0.0.0 --port 8000
```

The first voice request downloads Whisper weights. `WHISPER_MODEL=medium` is the default; `large-v3` improves potential quality but needs more GPU memory. Ollama must be running locally. Keep the models and API on the same instance. For CPU development, set `WHISPER_DEVICE=cpu` and `WHISPER_MODEL=small`.

For a hackathon demo, do **not** use Brev's built-in `Using Tunnels` URL as the site API URL: Brev documents an authentication redirect that can break browser `fetch` calls. Instead install `cloudflared` on the Brev instance and run a Cloudflare Quick Tunnel in another terminal:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the generated `https://…trycloudflare.com` URL. Paste it into the website's **Operator view → AI service URL → Connect**, or build the website with `VITE_AI_API_URL=https://…trycloudflare.com` (no trailing slash). Never put model credentials in `VITE_` variables. The site uses the URL only for `/health`, `/api/triage`, and `/api/voice-report`. Do not expose Ollama's port 11434. Quick Tunnel URLs change when restarted and are only for testing; this endpoint is publicly reachable while the tunnel runs. Use fabricated demo recordings only. For a stable deployment, use an authenticated server-side API gateway and a managed domain/tunnel.

The API accepts at most 15 MB and three minutes of audio. Files are deleted immediately after processing, and reports remain in the browser's local storage. The backend does not persist audio or transcripts. CORS limits browser origins; it is not authentication. For use beyond a controlled hackathon demo, add authentication, rate limits, encrypted transport, retention controls, abuse protection, and human validation before any operational use.

## API

- `GET /health` — service availability.
- `POST /api/triage` — structured report in JSON; returns model generated summary, missing questions, and suggested attention.
- `POST /api/voice-report` — multipart `audio` recording; returns Whisper transcript and a model generated draft. The reporter reviews and confirms it before simulated submission.

Run locally with the same commands. The frontend remains usable for manual reporting when the AI service is absent and clearly labels AI as unavailable.

## NVIDIA Riva text to speech on Brev

Use an NVIDIA Brev instance with an NVIDIA GPU and enough available GPU memory to run Speech NIM, faster-whisper, and Ollama together. **L40S (48 GB)** is a practical starting point for this combined demo; monitor `nvidia-smi` and resize or run models separately if memory is tight. The Magpie multilingual default uses roughly 12.6 GiB on an L4 before the other models. Brev credits are billed by instance usage; check the current GPU price in your Brev console. You also need an **NGC API key** with access to the NVIDIA Speech NIM container. Keep it on Brev, never in React or a Vite environment variable.

On the Brev machine, after installing Docker and the NVIDIA Container Toolkit, sign in to NGC and launch the multilingual speech container:

```bash
export NGC_API_KEY='your-ngc-key-here'
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin
export CONTAINER_ID=magpie-tts-multilingual
docker run --rm --name himaya-riva --runtime=nvidia --gpus '"device=0"' --shm-size=8GB \
  -e NGC_API_KEY -e NIM_HTTP_API_PORT=9000 \
  -e NIM_TAGS_SELECTOR=name=magpie-tts-multilingual \
  -p 127.0.0.1:9000:9000 nvcr.io/nim/nvidia/$CONTAINER_ID:latest
```

Allow the initial model download and startup. In another Brev terminal, verify `curl http://127.0.0.1:9000/v1/health/ready` and `curl http://127.0.0.1:9000/v1/audio/list_voices`. Then start the FastAPI app as described above. It defaults to `RIVA_TTS_URL=http://127.0.0.1:9000`; the website reaches Riva only through FastAPI `/api/tts`. The TTS container port should stay bound to loopback. Restart the AI API or reconnect the website if its URL changes. The browser starts playback only when someone selects **Listen with Riva**.

The app chooses documented Magpie multilingual voices: `en-US` Aria, `fr-FR` Louise, and `ar-XA` Sofia. English operator summaries and fixed English/French/Arabic status messages are converted to speech. Generated speech is returned as WAV without server storage. This is a prototype status narration, never a phone call or a live emergency broadcast. `POST /api/tts` accepts JSON `{"text":"Report received","language":"en-US"}` with up to 500 characters. If Riva is offline, speech displays an error and the report flow still works.

For a controlled public demo, consider protecting the FastAPI URL and limiting access because the Quick Tunnel exposes this speech endpoint to anyone who has its URL; CORS alone does not protect it. Do not use real incident or patient audio.

## Fast demo setup (Whisper + Ollama first)

For a time-limited hackathon demonstration, run `bash backend/demo_setup.sh` on an Ubuntu NVIDIA Brev instance **after copying this project there**. The script checks the GPU, installs Ollama and cloudflared when missing, pulls the local Qwen model, creates the Python environment, starts the API, calls the real triage endpoint to warm the model, and starts a temporary HTTPS Quick Tunnel. It does not start Riva. Installer downloads and model weights require network access on Brev, and installation may request sudo. It leaves logs in `backend/.demo-run/`.

To also warm Whisper automatically, supply a short fictional WAV recording: `DEMO_AUDIO_FILE=/path/to/fictional.wav bash backend/demo_setup.sh`. Otherwise record one fictional report in the website **before** the stage demo; a `/health` check by itself does not load Whisper. The script prints the tunnel URL, which must be entered once in the site's Operator view → AI service → Connect. Keep the script terminal open for the demo. Reports are browser-local, so use the citizen and operator views in the same browser.

The setup script does not configure Brev billing, create an instance, or upload the project. It cannot prove the remote setup until run on your Brev machine. Stop the tunnel and GPU instance after the demo.
