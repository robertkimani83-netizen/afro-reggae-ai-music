import json, os
from pathlib import Path

import torch
import soundfile as sf
from transformers import AutoProcessor, MusicgenForConditionalGeneration

OUT = Path('output')
SEGMENTS = OUT / 'music_segments'
SEGMENTS.mkdir(parents=True, exist_ok=True)

with open(OUT / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

minutes = max(1, int(float(os.getenv('SONG_DURATION_MIN', '3'))))
segment_seconds = 30
segments = max(1, (minutes * 60 + segment_seconds - 1) // segment_seconds)
model_id = os.getenv('MUSICGEN_MODEL', 'facebook/musicgen-small')

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Loading {model_id} on {device}')
if device == 'cpu':
    raise SystemExit('MusicGen generation requires a capable GPU runner for this free pipeline.')

processor = AutoProcessor.from_pretrained(model_id)
model = MusicgenForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.float16).to(device)
model.eval()

prompts = [
    meta['music_prompt'] + ', instrumental intro and gentle male vocal feel',
    meta['music_prompt'] + ', energetic chorus, catchy hook and danceable groove',
    meta['music_prompt'] + ', romantic verse, warm vocal melody and deep bass',
    meta['music_prompt'] + ', uplifting bridge with African percussion and reggae guitar',
    meta['music_prompt'] + ', joyful final chorus, layered harmonies and tropical atmosphere',
]

files = []
for i in range(segments):
    prompt = prompts[i % len(prompts)]
    inputs = processor(text=[prompt], padding=True, return_tensors='pt').to(device)
    max_new_tokens = int(segment_seconds * 50)
    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, guidance_scale=3.0)
    audio = audio_values[0, 0].detach().float().cpu().numpy()
    path = SEGMENTS / f'segment_{i+1:02d}.wav'
    sf.write(path, audio, model.config.audio_encoder.sampling_rate)
    files.append(str(path))
    print(f'Generated {path}')

(OUT / 'music_segments.txt').write_text('\n'.join(files), encoding='utf-8')
print('Music generation complete.')
