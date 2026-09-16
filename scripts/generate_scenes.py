"""Fetches real photos for the music-video scenes from Pexels (free stock
photo API, same service and API key pattern next-scene-news already uses
for its video clips).

Sept 15 2026: replaces the old SDXL-on-local-GPU path. That path could never
actually run -- GitHub-hosted runners have no NVIDIA GPU, and it silently
fell back to drawing plain color-gradient cards with text on them instead of
real images. Real stock photography is a much better result for free, and
it's the same approach that's already working reliably for the news
channel's videos, just images instead of video clips.

If PEXELS_API_KEY isn't set, or a particular search comes back empty, this
still falls back to the old gradient card for THAT scene only, so a missing
key or one unlucky query never blocks the whole run -- but the output
directly reflects the query text used to fetch (in [square brackets] on the
fallback card) so a run using fallback cards is obvious to spot in the
generated artifact rather than looking like it worked.
"""

import json
import math
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

OUT = Path("output")
SCENES = OUT / "scenes"
SCENES.mkdir(parents=True, exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
title = meta.get("title", "Afro-Reggae")
queries = meta.get("scene_queries") or meta.get("scene_prompts") or [
    "couple beach sunset",
    "tropical palm trees",
    "ocean waves sunset",
    "beach bonfire night",
    "african sunrise coastline",
    "tropical island aerial",
]


def _fallback_card(path, query, index):
    """Same gradient-card generator this file used to always use -- kept
    only as a per-scene safety net now, not the normal path."""
    width, height = 1280, 720
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    phase = index * 0.8
    for y in range(height):
        for x in range(width):
            wave = (math.sin(x / 150 + phase) + math.sin(y / 95 + phase)) * 10
            pixels[x, y] = (
                max(0, min(255, int(35 + y / height * 45 + wave))),
                max(0, min(255, int(75 + x / width * 55 + wave))),
                max(0, min(255, int(55 + (1 - y / height) * 35 + wave))),
            )
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((55, 55, width - 55, height - 55), fill=(0, 0, 0, 80), outline=(255, 255, 255, 110), width=2)
    draw.text((90, 90), title, font=font, fill=(255, 255, 255, 245))
    draw.text((90, 155), f"[{query}]", font=small_font, fill=(255, 255, 255, 220))
    draw.text((90, height - 80), f"AFRO-REGGAE • ORIGINAL AI MUSIC • SCENE {index:02d}", font=small_font, fill=(255, 255, 255, 210))
    image.save(path, quality=94)
    print(f"[scenes] fallback card for scene {index} (query: {query!r})")


def _fetch_pexels_photo(query):
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": 3, "orientation": "landscape"},
        timeout=30,
    )
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        return None
    src = photos[0].get("src", {})
    url = src.get("landscape") or src.get("large2x") or src.get("large") or src.get("original")
    if not url:
        return None
    img_resp = requests.get(url, timeout=60)
    img_resp.raise_for_status()
    return img_resp.content


for i, query in enumerate(queries, start=1):
    path = SCENES / f"scene_{i:02d}.jpg"
    if not PEXELS_API_KEY:
        _fallback_card(path, query, i)
        continue
    try:
        raw = _fetch_pexels_photo(query)
        if not raw:
            print(f"[scenes] no Pexels results for {query!r}, using fallback card")
            _fallback_card(path, query, i)
            continue
        tmp = SCENES / f"_raw_{i:02d}.jpg"
        tmp.write_bytes(raw)
        img = Image.open(tmp).convert("RGB")
        # Cover-crop to 1280x720 so every scene has a consistent frame for
        # assemble_video.py's zoompan effect, regardless of the source
        # photo's native aspect ratio.
        target_ratio = 1280 / 720
        w, h = img.size
        current_ratio = w / h
        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x0 = (w - new_w) // 2
            img = img.crop((x0, 0, x0 + new_w, h))
        else:
            new_h = int(w / target_ratio)
            y0 = (h - new_h) // 2
            img = img.crop((0, y0, w, y0 + new_h))
        img = img.resize((1280, 720))
        img.save(path, quality=95)
        tmp.unlink(missing_ok=True)
        print(f"[scenes] fetched Pexels photo for scene {i} (query: {query!r})")
    except Exception as err:  # noqa: BLE001 - one bad photo shouldn't fail the whole run
        print(f"[scenes] Pexels fetch failed for {query!r} ({err}), using fallback card")
        _fallback_card(path, query, i)

print("Music-video scenes complete.")
