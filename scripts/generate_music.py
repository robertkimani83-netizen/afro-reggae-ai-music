import json
import os
import time
from pathlib import Path

import requests
from gradio_client import Client

OUT = Path("output")
OUT.mkdir(exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

SPACE = os.getenv("ACE_STEP_SPACE", "ACE-Step/Ace-Step-v1.5")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
MAX_FREE_SPACE_SECONDS = int(os.getenv("ACE_STEP_MAX_SECONDS", "110"))
requested_minutes = max(1, int(float(os.getenv("SONG_DURATION_MIN", "2"))))
requested_duration = min(600, requested_minutes * 60)
duration = min(requested_duration, MAX_FREE_SPACE_SECONDS)

language = "en" if "English" in meta.get("language", "") else "sw"
prompt = meta["music_prompt"]
lyrics = meta["lyrics"]

print(f"Connecting to official ACE-Step Hugging Face Space: {SPACE}")
print(f"Requested duration: {requested_duration}s; online free-space safe duration: {duration}s")

client = Client(SPACE, hf_token=HF_TOKEN) if HF_TOKEN else Client(SPACE)

# Official Space UI/API inputs:
# prompt, lyrics, duration, BPM, vocal language, instrumental mode, guidance, seed.
bpm = None
instrumental = "自動判定"
ui_language = "英文 (en)" if language == "en" else "自動判定"
guidance = 7.0
seed = None

last_error = None
for attempt in range(3):
    try:
        result = client.predict(
            prompt,
            lyrics,
            float(duration),
            bpm,
            ui_language,
            instrumental,
            guidance,
            seed,
            api_name="/generate_music",
        )
        last_error = None
        break
    except Exception as exc:
        last_error = exc
        print(f"ACE-Step online attempt {attempt + 1}/3 failed: {exc}")
        if attempt < 2:
            time.sleep(10 * (attempt + 1))

if last_error is not None:
    raise RuntimeError(
        "The official ACE-Step online Space could not generate the song. "
        "If Hugging Face asks for authentication/quota, add a Hugging Face "
        "read token as the GitHub Actions secret HF_TOKEN."
    ) from last_error


def find_audio_path(value):
    if isinstance(value, str):
        lower = value.lower()
        if lower.endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a")) or lower.startswith("http"):
            return value
    if isinstance(value, dict):
        for key in ("path", "url", "name"):
            if key in value:
                found = find_audio_path(value[key])
                if found:
                    return found
        for item in value.values():
            found = find_audio_path(item)
            if found:
                return found
    if isinstance(value, (list, tuple)):
        for item in value:
            found = find_audio_path(item)
            if found:
                return found
    return None

source = find_audio_path(result)
if not source:
    raise RuntimeError(f"ACE-Step returned an unexpected audio result: {result!r}")

out = OUT / "song.mp3"
if source.startswith("http"):
    response = requests.get(source, timeout=300)
    response.raise_for_status()
    out.write_bytes(response.content)
else:
    source_path = Path(source)
    if not source_path.exists():
        raise RuntimeError(f"ACE-Step returned a local path that does not exist: {source}")
    out.write_bytes(source_path.read_bytes())

result_metadata = {
    "space": SPACE,
    "requested_duration_seconds": requested_duration,
    "generated_duration_seconds": duration,
    "prompt": prompt,
    "language": language,
    "raw_result": result,
}
(OUT / "ace_step_result.json").write_text(
    json.dumps(result_metadata, indent=2, default=str), encoding="utf-8"
)
print(f"Generated full song: {out}")
