"""Preflight actual Himaya model endpoints with fictional incident data."""
import argparse
from pathlib import Path
import httpx

BASE = 'http://127.0.0.1:8000'
parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=Path, help='Short fictional WAV audio to warm Whisper and extraction')
args = parser.parse_args()

report = {'type':'traffic','location':'Bab Ezzouar, Algiers','injured':'Yes','count':'1',
          'answers':{'roadBlocked':'Unknown','trapped':'Unknown','smoke':'Unknown','fuel':'Unknown'},
          'description':'Fictional practice report for demo warm-up.'}
with httpx.Client(timeout=180) as client:
    response = client.post(f'{BASE}/api/triage', json=report)
    response.raise_for_status()
    data = response.json()
    assert data.get('summary') and data.get('suggested_attention_level')
    print('TRIAGE READY:', data['summary'])
    if args.audio:
        if not args.audio.is_file():
            parser.error(f'Audio file does not exist: {args.audio}')
        with args.audio.open('rb') as recording:
            response = client.post(f'{BASE}/api/voice-report', files={'audio':(args.audio.name,recording,'audio/wav')})
        response.raise_for_status()
        data=response.json()
        assert data.get('transcript') and data.get('draft')
        print('WHISPER + EXTRACTION READY:', data['transcript'][:160])
    else:
        print('VOICE NOT WARMED: set DEMO_AUDIO_FILE=/path/to/fictional.wav and rerun this preflight,')
        print('or record one fictional report from the website before presenting.')
