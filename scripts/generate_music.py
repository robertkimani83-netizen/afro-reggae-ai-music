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


def norm(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def choose_endpoint(api_info):
    candidates = []
    for name, info in api_info.get("named_endpoints", {}).items():
        params = info.get("parameters", [])
        names = [norm(p.get("parameter_name") or p.get("label", "")) for p in params]
        score = 0
        if any(x in names for x in ("prompt", "caption", "musicprompt", "description")):
            score += 5
        if "lyrics" in names:
            score += 5
        if any(x in names for x in ("duration", "audioduration")):
            score += 3
        if any(x in names for x in ("vocal_language", "vocallanguage", "language")):
            score += 1
        if any(token in str(name).lower() for token in ("generate", "music", "infer")):
            score += 2
        candidates.append((score, str(name), info))

    for fn_index, info in api_info.get("unnamed_endpoints", {}).items():
        params = info.get("parameters", [])
        names = [norm(p.get("parameter_name") or p.get("label", "")) for p in params]
        score = 0
        if any(x in names for x in ("prompt", "caption", "musicprompt", "description")):
            score += 5
        if "lyrics" in names:
            score += 5
        if any(x in names for x in ("duration", "audioduration")):
            score += 3
        candidates.append((score, int(fn_index), info))

    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates or candidates[0][0] < 5:
        raise RuntimeError(f"Could not identify the ACE-Step generation endpoint. Available API: {api_info!r}")
    return candidates[0]


def default_value(parameter):
    if parameter.get("parameter_has_default"):
        return parameter.get("parameter_default")
    example = parameter.get("example_input")
    if example is not None:
        return example
    python_type = str(parameter.get("python_type", {}).get("type", ""))
    if "bool" in python_type:
        return False
    if "int" in python_type or "float" in python_type:
        return 0
    return ""


def build_endpoint_args(parameters):
    values = {}
    for parameter in parameters:
        key = parameter.get("parameter_name") or parameter.get("label")
        nkey = norm(key)
        value = default_value(parameter)

        if nkey in ("prompt", "caption", "musicprompt", "description", "musicdescription"):
            value = prompt
        elif nkey == "lyrics":
            value = lyrics
        elif nkey in ("duration", "audioduration", "durationseconds"):
            value = float(duration)
        elif nkey in ("vocallanguage", "language", "vocal_languages"):
            value = "en" if language == "en" else "sw"
        elif nkey in ("guidance", "guidancescale", "cfgscale"):
            value = 7.0
        elif nkey in ("seed", "manualseed", "manualseeds"):
            value = None
        elif nkey in ("bpm", "tempo"):
            value = None
        elif nkey in ("tasktype", "task"):
            value = "text2music"
        elif nkey in ("instrumental", "instrumentalmode"):
            value = False

        values[key] = value
    return values


last_error = None
result = None
for attempt in range(3):
    try:
        api_info = client.view_api(all_endpoints=True, print_info=False, return_format="dict")
        score, endpoint, endpoint_info = choose_endpoint(api_info)
        parameters = endpoint_info.get("parameters", [])
        kwargs = build_endpoint_args(parameters)

        print(f"Using ACE-Step API endpoint: {endpoint} (score {score})")
        print("ACE-Step endpoint parameters:")
        for parameter in parameters:
            print(f"  - {parameter.get('parameter_name') or parameter.get('label')}")

        if isinstance(endpoint, str):
            result = client.predict(**kwargs, api_name=endpoint)
        else:
            result = client.predict(**kwargs, fn_index=int(endpoint))
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
        "The workflow now discovers the live Gradio API instead of assuming a fixed endpoint. "
        "If Hugging Face asks for authentication/quota, add a Hugging Face read token "
        "as the GitHub Actions secret HF_TOKEN."
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
