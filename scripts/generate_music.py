"""Generates the full sung song using DiffRhythm, a free open-source
full-song (lyrics + vocals + instrumentation) model, via its public
Hugging Face Space -- https://huggingface.co/spaces/ASLP-lab/DiffRhythm.

Sept 15 2026: replaces the local ACE-Step 1.5 approach, which failed all 3
times it was tried (the most recent failure was the local API never
finishing startup within its 15-minute wait window on GitHub's free Windows
runner). The core problem was architectural: ACE-Step needs real GPU compute
to run in reasonable time, and neither GitHub's free runners nor this
project's available hardware have one.

DiffRhythm sidesteps that by NOT running locally at all -- the actual model
runs on Hugging Face's free "ZeroGPU" shared GPU pool (this Space has had
ZeroGPU access since March 2025), and this script just calls it like an API
over the internet using `gradio_client`, the same way generate_scenes.py
used to reach for a local SDXL pipeline. This machine (or the GitHub-hosted
runner) never needs a GPU -- it's just sending a request and waiting for the
result, which is normally fast (published benchmarks put a ~4-5 minute song
at well under a minute of actual GPU time).

Known limitation (Sept 15 2026): this Space's own lyrics-writing tool only
lists English and Chinese as supported languages -- there's no Swahili
option, which strongly suggests the underlying model wasn't trained on it.
generate_metadata.py writes English-only lyrics for this reason. See the
comment there for more.

This also means generation quality/availability depends on a public,
shared, free HF Space that isn't under Robert's control -- it could change
its interface, get paused, or hit shared usage limits at busy times. That's
a real trade-off of using a free shared resource instead of paid, dedicated
compute. If this becomes unreliable in practice, the fallback is a small
per-song paid vocal API (e.g. Suno's official API).

IMPORTANT -- this call could not be live-tested from the environment that
wrote this patch (its sandbox blocks huggingface.co outbound by policy, the
same restriction that applies to unrelated services -- this is a sandbox
policy, not a sign the service itself is down). The exact keyword names below
come from reading the Space's own app.py source directly. The defensive
introspection logging below is there specifically so that if the interface
has changed a parameter name since, the failure shows up as a clear,
readable error in the GitHub Actions log instead of a silent wrong result --
check that log first if this step ever fails.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from gradio_client import Client

OUT = Path("output")
OUT.mkdir(exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

HF_TOKEN = os.environ.get("HF_TOKEN") or None  # optional, but gives a bigger/steadier free ZeroGPU quota than anonymous calls
SPACE_ID = os.getenv("DIFFRHYTHM_SPACE", "ASLP-lab/DiffRhythm")

lrc = meta.get("lrc", "")
style_prompt = meta.get("music_style_prompt", "Warm Afro-Reggae with offbeat guitar skank, mellow bassline, African percussion, smooth romantic lead vocal")
duration_seconds = float(meta.get("target_duration_seconds", 120))
# DiffRhythm's own slider only accepts 95-285 seconds -- generate_metadata.py
# already clamps to this range, but re-clamp here too in case this script
# is ever run on an older metadata.json.
duration_seconds = max(95.0, min(285.0, duration_seconds))

if not lrc.strip():
    raise RuntimeError("metadata.json has no lrc lyrics -- run generate_metadata.py first.")

print(f"[music] connecting to {SPACE_ID}", file=sys.stderr)
client = Client(SPACE_ID, hf_token=HF_TOKEN)

api_info = {}
try:
    api_info = client.view_api(return_format="dict") or {}
except Exception as err:  # noqa: BLE001 - introspection is best-effort logging, never fatal
    print(f"[music] could not introspect API (continuing anyway): {err}", file=sys.stderr)

endpoint_names = list((api_info.get("named_endpoints") or {}).keys())
print(f"[music] available endpoints: {endpoint_names}", file=sys.stderr)

# Prefer the exact name from the Space's source; fall back to any endpoint
# that looks like the main song generator (and isn't the separate
# lyrics-writing helper endpoints) if the exact name has since changed.
api_name = "/infer_music"
if endpoint_names and api_name not in endpoint_names:
    guesses = [n for n in endpoint_names if "infer_music" in n.lower()]
    if not guesses:
        guesses = [n for n in endpoint_names if "infer" in n.lower() and "r1" not in n.lower() and "lyric" not in n.lower()]
    if guesses:
        print(f"[music] '/infer_music' not found, trying closest match: {guesses[0]}", file=sys.stderr)
        api_name = guesses[0]
    else:
        raise RuntimeError(
            f"Could not find the song-generation endpoint on {SPACE_ID}. "
            f"Available endpoints were: {endpoint_names}. The Space's interface "
            "may have changed -- check https://huggingface.co/spaces/ASLP-lab/DiffRhythm/blob/main/app.py "
            "for the current function name and update api_name above."
        )

print(f"[music] requesting a {duration_seconds:.0f}s song via {api_name}", file=sys.stderr)

result = client.predict(
    lrc=lrc,
    ref_audio_path=None,
    text_prompt=style_prompt,
    current_prompt_type="text",  # "text" (style-description) mode rather than "audio" (reference-clip) mode -- we have no reference audio
    seed=0,
    randomize_seed=True,
    steps=32,
    cfg_strength=4.0,
    file_type="wav",
    odeint_method="euler",
    preference_infer="quality first",
    Music_Duration=duration_seconds,
    edit=False,
    edit_segments=None,
    api_name=api_name,
)

# The Audio output component can come back as a plain filepath string, or as
# a dict/tuple wrapping one, depending on gradio_client version -- handle
# whichever shape shows up rather than assuming one.
audio_path = None
if isinstance(result, str):
    audio_path = result
elif isinstance(result, (list, tuple)) and result:
    first = result[0]
    audio_path = first if isinstance(first, str) else (first.get("name") or first.get("path") if isinstance(first, dict) else None)
elif isinstance(result, dict):
    audio_path = result.get("name") or result.get("path")

if not audio_path or not Path(audio_path).exists():
    raise RuntimeError(f"DiffRhythm did not return a usable audio file. Raw result: {result!r}")

print(f"[music] received generated audio: {audio_path}", file=sys.stderr)

# Normalize to output/song.mp3 regardless of what format the Space returned
# (requested wav, since that's guaranteed valid; convert here rather than
# guessing at whichever format string the Space's file_type option expects).
out = OUT / "song.mp3"
if Path(audio_path).suffix.lower() == ".mp3":
    shutil.copyfile(audio_path, out)
else:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path), "-c:a", "libmp3lame", "-b:a", "192k", str(out)],
        check=True,
    )

(OUT / "music_generation_result.json").write_text(
    json.dumps(
        {
            "provider": "DiffRhythm (free Hugging Face ZeroGPU Space)",
            "space": SPACE_ID,
            "api_name": api_name,
            "duration_seconds": duration_seconds,
            "style_prompt": style_prompt,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(f"Generated song: {out}")
