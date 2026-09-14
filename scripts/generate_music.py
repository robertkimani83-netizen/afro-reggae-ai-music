import json
import os
import time
from pathlib import Path

import requests

OUT = Path("output")
OUT.mkdir(exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

BASE_URL = os.getenv("ACESTEP_BASE_URL", "http://127.0.0.1:8001")
API_KEY = os.getenv("ACESTEP_API_KEY", "")
MAX_SECONDS = int(os.getenv("ACESTEP_MAX_SECONDS", "120"))
requested_minutes = max(1, int(float(os.getenv("SONG_DURATION_MIN", "2"))))
duration = min(requested_minutes * 60, MAX_SECONDS)

prompt = meta.get("music_prompt", "Afro-reggae song with warm bass, skank guitar and melodic vocals")
lyrics = meta.get("lyrics", "")
language_text = meta.get("language", os.getenv("SONG_LANGUAGE", "English + Swahili"))
language = "sw" if "Swahili" in language_text and "English" not in language_text else "en"

headers = {"Content-Type": "application/json"}
if API_KEY:
    headers["Authorization"] = f"Bearer {API_KEY}"

payload = {
    "prompt": prompt,
    "global_caption": prompt,
    "lyrics": lyrics,
    "thinking": True,
    "model": "acestep-v15-turbo",
    "vocal_language": language,
    "audio_duration": float(duration),
    "inference_steps": 8,
    "guidance_scale": 7.0,
    "use_random_seed": True,
    "audio_format": "mp3",
    "task_type": "text2music",
    "batch_size": 1,
    "lm_backend": "pt",
}

print(f"Using LOCAL ACE-Step at {BASE_URL}")
print(f"CPU/local generation duration: {duration}s")

health = requests.get(f"{BASE_URL}/health", timeout=20)
health.raise_for_status()

created = requests.post(
    f"{BASE_URL}/release_task",
    headers=headers,
    json=payload,
    timeout=120,
)
created.raise_for_status()
created_data = created.json()
task_id = created_data.get("data", {}).get("task_id")
if not task_id:
    raise RuntimeError(f"ACE-Step did not return task_id: {created_data!r}")

print(f"Local ACE-Step task: {task_id}")

deadline = time.time() + int(os.getenv("ACESTEP_TIMEOUT_SECONDS", "7200"))
result = None
while time.time() < deadline:
    time.sleep(15)
    response = requests.post(
        f"{BASE_URL}/query_result",
        headers=headers,
        json={"task_id_list": [task_id]},
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    items = result.get("data", [])
    item = items[0] if items else {}
    status = item.get("status", 0)
    print(f"ACE-Step status: {status}")
    if status == 2:
        raise RuntimeError(f"Local ACE-Step generation failed: {result!r}")
    if status == 1:
        break
else:
    raise TimeoutError("Local ACE-Step generation timed out.")

item = result["data"][0]
raw_result = item.get("result", "")
if isinstance(raw_result, str):
    try:
        result_items = json.loads(raw_result)
    except json.JSONDecodeError:
        result_items = []
else:
    result_items = raw_result

if not result_items:
    raise RuntimeError(f"ACE-Step returned no audio result: {result!r}")

first = result_items[0]
audio_file = first.get("file") or first.get("path")
if not audio_file:
    raise RuntimeError(f"ACE-Step result contains no audio file: {first!r}")

if audio_file.startswith("http"):
    audio_url = audio_file
else:
    audio_url = f"{BASE_URL}{audio_file}" if audio_file.startswith("/") else audio_file

audio = requests.get(audio_url, headers=headers, timeout=600)
audio.raise_for_status()
out = OUT / "song.mp3"
out.write_bytes(audio.content)

(OUT / "acestep_result.json").write_text(
    json.dumps({
        "provider": "local ACE-Step 1.5",
        "model": "acestep-v15-turbo",
        "task_id": task_id,
        "duration_seconds": duration,
        "audio_file": audio_file,
        "result": result,
    }, indent=2, ensure_ascii=False, default=str),
    encoding="utf-8",
)

print(f"Generated local song: {out}")
