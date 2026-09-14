import json, os, time
from pathlib import Path

import requests

OUT = Path('output')
OUT.mkdir(exist_ok=True)

with open(OUT / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

base = os.getenv('ACESTEP_URL', 'http://127.0.0.1:8001').rstrip('/')
minutes = max(1, int(float(os.getenv('SONG_DURATION_MIN', '3'))))
duration = min(600, minutes * 60)

payload = {
    'prompt': meta['music_prompt'],
    'lyrics': meta['lyrics'],
    'thinking': True,
    'use_format': True,
    'vocal_language': 'en' if 'English' in meta['language'] else 'sw',
    'duration': duration,
    'audio_format': 'mp3',
    'inference_steps': 8,
    'model': 'acestep-v15-turbo',
}

print('Submitting song to local ACE-Step 1.5...')
r = requests.post(f'{base}/release_task', json=payload, timeout=120)
r.raise_for_status()
data = r.json().get('data', r.json())
task_id = data.get('task_id')
if not task_id:
    raise RuntimeError(f'ACE-Step did not return a task id: {r.text[:1000]}')

while True:
    time.sleep(5)
    q = requests.post(f'{base}/query_result', json={'task_id_list': [task_id]}, timeout=60)
    q.raise_for_status()
    result = q.json().get('data', q.json())
    row = result[0] if isinstance(result, list) else result
    status = row.get('status')
    print(f'ACE-Step status: {status}')
    if status == 1:
        raw = row.get('result', '[]')
        items = json.loads(raw) if isinstance(raw, str) else raw
        if not items:
            raise RuntimeError('ACE-Step succeeded but returned no audio file.')
        audio_path = items[0].get('file')
        if not audio_path:
            raise RuntimeError(f'No audio path in ACE-Step result: {items[0]}')
        audio_url = audio_path if audio_path.startswith('http') else base + audio_path
        audio = requests.get(audio_url, timeout=300)
        audio.raise_for_status()
        out = OUT / 'song.mp3'
        out.write_bytes(audio.content)
        (OUT / 'ace_step_result.json').write_text(json.dumps(items[0], indent=2), encoding='utf-8')
        print(f'Generated full song: {out}')
        break
    if status == 2:
        raise RuntimeError(f'ACE-Step generation failed: {row}')
