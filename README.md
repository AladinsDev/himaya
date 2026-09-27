# Himaya — hackathon prototype

React/Vite citizen flow and operator dashboard, plus a Python AI service for voice transcription, incident assessment, and NVIDIA Riva text-to-speech. **No real emergency systems, telephone capture, or dispatch are connected.** The `Call 1021` link only opens the phone dialer.

## Run the website

```bash
npm install
npm run dev
```

Open the Vite URL, then `/operator/` for the dashboard. Manual reports and simulated status are stored in the current browser's local storage. They do not synchronize across devices. Only the review status advances automatically; an operator assigns, dispatches, and completes the simulated incident.

## Run the AI service

See [backend/README.md](backend/README.md) for Brev GPU setup. The service runs faster-whisper for Arabic/French/English transcription and a local Ollama model for report extraction and operator summaries. Riva Speech NIM on Brev narrates the simulated status in English, French, or Arabic and speaks the operator AI summary on demand. It stores no audio or transcript on the server. The person reporting must review a voice draft before submitting.

After exposing the FastAPI service with a direct HTTPS API URL (see backend setup), enter that URL in the operator dashboard's **AI service** connection field. That browser will then use the service on the citizen voice page and operator triage panel. For other browsers and for a deployment with the URL already configured, set `VITE_AI_API_URL` at website build time and rebuild. This is a public URL, never an API key.

## API boundary

The site calls `/health`, `/api/voice-report`, `/api/triage`, and `/api/tts`. A browser cannot read or record a separate telephone call to 1021. The in-app microphone and user-supplied recordings are the supported audio inputs. The AI returns draft information and suggestions only; an operator remains responsible for actions.

## Langues, communes et consignes

L'interface permet de choisir français, English ou العربية; le choix est conservé dans le navigateur. Le formulaire et le tableau opérateur partagent les mêmes données structurées, indépendamment de la langue. Les textes produits par le modèle IA restent en anglais et une transcription conserve la langue parlée. La lecture vocale des statuts peut être choisie séparément parmi les trois langues.

Les choix de lieu incluent Alger (Bab Ezzouar, Alger-Centre, Kouba, Birkhadem, Rouiba…), Blida (Blida, Boufarik, Beni Mered, Chiffa) et Boumerdès. Le schéma est illustratif : les points ne sont pas des coordonnées GPS et « Ma position » est simulée. La commune et la wilaya sélectionnées apparaissent dans le résumé et dans la console; il faut confirmer le lieu réel avant tout usage au-delà de la démo.

Après les réponses et dans le suivi du rapport, un encadré donne des consignes générales selon le type d'urgence. Pour un incendie, il couvre l'évacuation et la fumée, l'odeur de gaz (sortir, éviter interrupteurs/flammes) et le refroidissement d'une brûlure à l'eau courante fraîche. Ces consignes sont des textes statiques traduits, jamais une décision de l'IA. Elles ne remplacent pas les secours réels. Références : [Ready.gov incendies](https://www.ready.gov/home-fires), [Ready.gov gaz](https://www.ready.gov/sites/default/files/2021-11/are-you-ready-guide.pdf), [Croix-Rouge brûlures](https://www.redcross.org/take-a-class/resources/learn-first-aid/burns), [Croix-Rouge sécurité aquatique](https://www.redcross.org/get-help/how-to-prepare-for-emergencies/types-of-emergencies/water-safety.html).

For a fast Brev demo, see `backend/demo_setup.sh` and `backend/demo_warm.py`. Run the script on the Brev GPU machine after uploading the project; it prioritizes Whisper and Ollama and skips Riva.
