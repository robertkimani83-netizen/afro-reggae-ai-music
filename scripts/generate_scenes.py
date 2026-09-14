import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
SCENES = OUT / "scenes"
SCENES.mkdir(parents=True, exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

# GitHub-hosted runners do not provide the NVIDIA GPU needed for SDXL.
# Keep the pipeline fully runnable by creating clean cinematic visual cards
# when no local GPU is available. A GPU self-hosted runner can still opt into
# the original SDXL path with GENERATE_AI_SCENES=true.
try:
    import torch
    from diffusers import StableDiffusionXLPipeline
    gpu_available = torch.cuda.is_available()
except Exception:
    gpu_available = False

use_ai = gpu_available and str(__import__("os").getenv("GENERATE_AI_SCENES", "false")).lower() == "true"

if use_ai:
    import os

    model_id = os.getenv("IMAGE_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
    print(f"Loading image model: {model_id}")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16, use_safetensors=True
    ).to("cuda")
    pipe.enable_attention_slicing()

    for i, prompt in enumerate(meta["scene_prompts"], start=1):
        image = pipe(
            prompt=prompt,
            negative_prompt="text, watermark, logo, blurry, distorted hands, duplicate people, low quality",
            width=1280,
            height=720,
            num_inference_steps=25,
            guidance_scale=6.5,
        ).images[0]
        path = SCENES / f"scene_{i:02d}.jpg"
        image.save(path, quality=95)
        print(f"Created AI scene {path}")
else:
    title = meta.get("title", "Afro-Reggae")
    prompts = meta.get("scene_prompts", [])
    print("No local GPU available; creating lightweight cinematic visual cards.")

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    for i, prompt in enumerate(prompts, start=1):
        width, height = 1280, 720
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        phase = i * 0.8
        for y in range(height):
            for x in range(width):
                wave = (math.sin(x / 150 + phase) + math.sin(y / 95 + phase)) * 10
                pixels[x, y] = (
                    max(0, min(255, int(35 + y / height * 45 + wave))),
                    max(0, min(255, int(75 + x / width * 55 + wave))),
                    max(0, min(255, int(55 + (1 - y / height) * 35 + wave))),
                )

        draw = ImageDraw.Draw(image, "RGBA")
        draw.rectangle((55, 55, width - 55, height - 55), fill=(0, 0, 0, 80), outline=(255, 255, 255, 110), width=2)
        draw.text((90, 90), title, font=font, fill=(255, 255, 255, 245))
        short_prompt = prompt.replace("\n", " ")[:170]
        draw.text((90, 155), short_prompt, font=small_font, fill=(255, 255, 255, 220))
        draw.text((90, height - 80), f"AFRO-REGGAE • ORIGINAL AI MUSIC • SCENE {i:02d}", font=small_font, fill=(255, 255, 255, 210))

        path = SCENES / f"scene_{i:02d}.jpg"
        image.save(path, quality=94)
        print(f"Created fallback scene {path}")

print("Music-video scenes complete.")
