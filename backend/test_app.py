from pathlib import Path

from fastapi.testclient import TestClient

import app as service

client = TestClient(service.app)


def test_triage_uses_model_output(monkeypatch):
    async def model(prompt, schema):
        assert 'Bab Ezzouar' in prompt
        return service.Assessment(summary='Traffic accident, three injured; road blocked.',
                                  missing_information=['Is anyone unconscious?'],
                                  suggested_attention_level='HIGH')
    monkeypatch.setattr(service, 'ask_model', model)
    response = client.post('/api/triage', json={'type': 'traffic', 'location': 'Bab Ezzouar',
        'injured': 'Yes', 'count': '3', 'answers': {'roadBlocked': 'Yes'}})
    assert response.status_code == 200
    assert response.json()['suggested_attention_level'] == 'HIGH'
    assert response.json()['summary'].startswith('Traffic accident')


def test_voice_transcript_becomes_reviewable_draft_and_file_is_removed(monkeypatch):
    seen = []
    def transcribe(path):
        assert Path(path).exists()
        seen.append(Path(path))
        return 'Accident à Bab Ezzouar, trois blessés.', 'fr', 8.0
    async def model(prompt, schema):
        assert 'trois blessés' in prompt
        return service.Draft(type='traffic', location='Not a map location', injured='Yes', count='3',
            answers={'roadBlocked': 'Unknown', 'invented': 'Yes'}, description='Accident reported',
            summary='Reported accident involving three injured people.',
            missing_information=['Is the road blocked?'], suggested_attention_level='HIGH')
    monkeypatch.setattr(service, 'transcribe_audio', transcribe)
    monkeypatch.setattr(service, 'ask_model', model)
    response = client.post('/api/voice-report', files={'audio': ('call.webm', b'a' * 1200, 'audio/webm')})
    assert response.status_code == 200
    body = response.json()
    assert body['detected_language'] == 'fr'
    assert body['draft']['location'] is None
    assert body['draft']['answers'] == {'roadBlocked': 'Unknown'}
    assert not seen[0].exists()


def test_voice_rejects_oversize_audio():
    response = client.post('/api/voice-report', files={'audio': ('call.webm', b'x' * (service.MAX_AUDIO_BYTES + 1), 'audio/webm')})
    assert response.status_code == 413


def test_riva_tts_proxies_language_voice_and_returns_wav(monkeypatch):
    import httpx
    requests = []
    wav = b'RIFF' + b'\0' * 4 + b'WAVEfmt ' + b'\0' * 32
    def handler(request):
        requests.append(request)
        body = request.content.decode('utf-8')
        assert 'Magpie-Multilingual.FR-FR.Louise' in body
        assert 'fr-FR' in body and 'Bonjour' in body
        return httpx.Response(200, content=wav, headers={'Content-Type': 'audio/wav'})
    real = service.httpx.AsyncClient
    monkeypatch.setattr(service.httpx, 'AsyncClient', lambda **kwargs: real(transport=httpx.MockTransport(handler), **kwargs))
    response = client.post('/api/tts', json={'text': 'Bonjour', 'language': 'fr-FR'})
    assert response.status_code == 200
    assert response.content == wav
    assert response.headers['content-type'] == 'audio/wav'
    assert response.headers['cache-control'] == 'no-store'
    assert requests[0].url.path == '/v1/audio/synthesize'


def test_riva_tts_rejects_invalid_or_blank_input():
    assert client.post('/api/tts', json={'text': 'hello', 'language': 'xx-XX'}).status_code == 422
    assert client.post('/api/tts', json={'text': '  ', 'language': 'en-US'}).status_code == 422
    assert client.post('/api/tts', json={'text': 'x' * 501, 'language': 'en-US'}).status_code == 422


def test_riva_tts_unavailable_returns_503(monkeypatch):
    import httpx
    real = service.httpx.AsyncClient
    monkeypatch.setattr(service.httpx, 'AsyncClient', lambda **kwargs: real(
        transport=httpx.MockTransport(lambda request: httpx.Response(503)), **kwargs))
    assert client.post('/api/tts', json={'text': 'Status received', 'language': 'en-US'}).status_code == 503
