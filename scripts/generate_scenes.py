import json, os
from pathlib import Path

import torch
from diffusers import StableDiffusionXLPipeline

OUT = Path('output')
SCENES = OUT / 'scenes'
SCENES.mkdir(parents=True, exist_ok=True)

with open(OUT / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

model_id = os.getenv('IMAGE_MODEL_ID', 'stabilityai/stable-diffusion-xl-base-1.0')
device = 'cuda' if torch.cuda.is_available() else 'cpu'
if device != 'cuda':
    raise SystemExit('AI scene generation requires a GPU runner in this free-first build.')

print(f'Loading image model: {model_id}')
dtype = torch.float16
pipe = StableDiffusionXLPipeline.from_pretrained(model_id, torch_dtype=dtype, use_safetensors=True)
pipe = pipe.to(device)
pipe.enable_attention_slicing()

for i, prompt in enumerate(meta['scene_prompts'], start=1):
    image = pipe(
        prompt=prompt,
        negative_prompt='text, watermark, logo, blurry, distorted hands, duplicate people, low quality',
        width=1280,
        height=720,
        num_inference_steps=25,
        guidance_scale=6.5,
    ).images[0]
    path = SCENES / f'scene_{i:02d}.jpg'
    image.save(path, quality=95)
    print(f'Created {path}')

print('AI scenes complete.')
