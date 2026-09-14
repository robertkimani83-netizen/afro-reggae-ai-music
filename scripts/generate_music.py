import json
import os
import time
from pathlib import Path

import requests

OUT = Path("output")
OUT.mkdir(exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

API_KEY = os.getenv("MUSICAPI_KEY")
BASE_URL = os.getenv("MUSICAPI_BASE_URL", "https://api.musicapi.ai")
MODEL = os.getenv("MUSICAPI_MODEL", "sonic-v6")

if not API_KEY:
    raise RuntimeError(
        "MUSICAPI_KEY is missing. Create a MusicAPI account/API key and add it "
        "to GitHub Actions secrets as MUSICAPI_KEY."
    )

prompt = meta["music_prompt"]
lyrics = meta.get("lyrics", "")
title = meta.get("title") or os.getenv("SONG_TITLE", "Afro-Reggae Song")

# MusicAPI exposes Suno-compatible Sonic generation. Custom mode lets us send
# the lyrics produced by this repository instead of asking the music service
# to invent a different lyric sheet.
tags = meta.get(
    "music_style",
    "Afro-reggae, reggae, African pop, warm bass, skank guitar, live drums, melodic vocals",
)

payload = {
    "task_type": "create_music",
    "custom_mode": True,
    "mv": MODEL,
    "title": title,
    "tags": tags,
    "prompt": lyrics,
    "gpt_description_prompt": prompt,
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

create_url = f"{BASE_URL}/api/v1/sonic/create"
print(f"Submitting song to Suno-compatible MusicAPI: {MODEL}")
print(f"Title: {title}")

response = requests.post(create_url, headers=headers, json=payload, timeout=120)
if not response.ok:
    raise RuntimeError(
        f"MusicAPI generation request failed ({response.status_code}): {response.text}"
    )

created = response.json()
task_id = created.get("task_id") or created.get("data", {}).get("task_id")
if not task_id:
    raise RuntimeError(f"MusicAPI did not return a task_id: {created!r}")

print(f"MusicAPI task created: {task_id}")

# A normal generation can take around two minutes. Give the remote job plenty
# of time while keeping the GitHub job finite.
poll_url = f"{BASE_URL}/api/v1/sonic/task/{task_id}"
deadline = time.time() + int(os.getenv("MUSICAPI_TIMEOUT_SECONDS", "900"))
result = None

while time.time() < deadline:
    time.sleep(20)
    poll = requests.get(poll_url, headers=headers, timeout=60)
    if not poll.ok:
        print(f"Polling returned HTTP {poll.status_code}: {poll.text}")
        continue

    result = poll.json()
    data = result.get("data", [])
    songs = data if isinstance(data, list) else [data]

    states = [str(song.get("state", "")).lower() for song in songs if isinstance(song, dict)]
    print(f"MusicAPI status: {states or result.get('message', 'unknown')}")

    if any(state == "failed" for state in states):
        raise RuntimeError(f"MusicAPI generation failed: {result!r}")
    if songs and all(state == "succeeded" for state in states if state):
        break
else:
    raise TimeoutError("MusicAPI generation timed out before a completed song was returned.")

if not result:
    raise RuntimeError("MusicAPI returned no task result.")

data = result.get("data", [])
songs = data if isinstance(data, list) else [data]
song = next(
    (item for item in songs if isinstance(item, dict) and item.get("audio_url")),
    None,
)
if not song:
    raise RuntimeError(f"MusicAPI returned no completed audio URL: {result!r}")

audio_url = song["audio_url"]
out = OUT / "song.mp3"
audio = requests.get(audio_url, timeout=300)
audio.raise_for_status()
out.write_bytes(audio.content)

result_metadata = {
    "provider": "MusicAPI",
    "model": MODEL,
    "task_id": task_id,
    "title": song.get("title", title),
    "duration_seconds": song.get("duration"),
    "audio_url": audio_url,
    "lyrics": song.get("lyrics", lyrics),
    "tags": song.get("tags", tags),
}
(OUT / "musicapi_result.json").write_text(
    json.dumps(result_metadata, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(f"Generated full Suno-compatible song: {out}")
