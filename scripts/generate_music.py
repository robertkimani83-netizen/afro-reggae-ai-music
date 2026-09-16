"""Generates the full sung song using YuE2-3B, a free open-source full-song
(lyrics + vocals + instrumentation) model, via its public Hugging Face Space
-- https://huggingface.co/spaces/mrfakename/yue2-3b.

Sept 16 2026 history, in order:
  1. Started with DiffRhythm (ASLP-lab/DiffRhythm). Its calling code was
     fully debugged and working, but it failed on the SERVER side with
     `AppError: CUDA error: no kernel image is available for execution on
     the device` -- a deterministic environment bug in that Space (its
     PyTorch build doesn't include compiled kernels for whatever GPU
     architecture Hugging Face hands ZeroGPU Spaces). Switched to YuE2-3B.
  2. Later hit "You have exceeded your free ZeroGPU quota" -- Hugging
     Face's free tier caps GPU-seconds per account per day. Added
     quota-detection so that error fails fast instead of pointlessly
     retrying (retrying the same call 30 seconds later when the message
     itself says it resets in hours is pointless).
  3. Briefly tried a free fallback chain -- YuE2-3B then DiffRhythm, each
     with Robert's HF_TOKEN and anonymously -- reasoning that an anonymous
     call might draw from a separate quota pool. A real test run proved
     that wrong: the token and anonymous calls hit the EXACT SAME quota
     numbers and reset time, meaning (at least from a GitHub Actions
     runner's IP) they share a bucket rather than having separate ones. The
     same run also confirmed DiffRhythm's CUDA bug is still there,
     unfixed, on a second separate day. So both fallback legs were dead
     weight -- real evidence, not just theory -- and Robert chose to strip
     the pipeline back down to just YuE2-3B rather than keep carrying two
     fallback paths that don't actually help. If Hugging Face's free tier
     ever proves too unreliable in practice, the next thing to reconsider
     is a small paid vocal API (e.g. ElevenLabs' Music API) as a genuine
     fallback -- Robert has declined that so far to keep this fully free.

Like DiffRhythm before it, YuE2-3B runs entirely on Hugging Face's free
"ZeroGPU" shared GPU pool -- this machine (or the GitHub-hosted runner)
never needs a GPU itself, it just calls the Space like an API over the
internet using `gradio_client` and waits for a finished song back.

Interface notes:
  - Takes plain lyrics with [Verse] / [Chorus] / [Bridge] section tags (see
    generate_metadata.py), not LRC timestamps.
  - No explicit duration parameter -- the song's length comes out of how
    much lyrics content it's given, so assemble_video.py measures the
    actual rendered song.mp3 with ffprobe rather than trusting a pre-set
    number.
  - Its "Create" tab exposes a `generate_song` function with no explicit
    api_name set on its .click() wiring, so Gradio auto-derives the API
    name from the Python function name -- expected to be "/generate_song",
    with defensive fallback-matching in case that's ever wrong.
  - Output is already an MP3 path (plus a FLAC download and an editable
    symbolic score this pipeline doesn't use) -- no wav->mp3 conversion
    needed in the normal case.

IMPORTANT -- this call could not be live-tested from the environment that
wrote this patch (its sandbox blocks huggingface.co outbound by policy).
The parameter names/defaults come from the Space's own app.py source and
from real error messages seen in past GitHub Actions runs. The
introspection logging on each attempt is there so that if the interface
has changed, the failure shows up as a clear, readable error in the log
rather than a silent wrong result.
"""

import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gradio_client import Client
from gradio_client.exceptions import AppError

OUT = Path("output")
OUT.mkdir(exist_ok=True)

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

HF_TOKEN = os.environ.get("HF_TOKEN") or None  # optional, but gives a bigger/steadier free ZeroGPU quota than anonymous calls
SPACE_ID = os.getenv("MUSIC_SPACE", "mrfakename/yue2-3b")

lyrics = meta.get("lyrics", "")
style_prompt = meta.get("music_style_prompt", "Warm Afro-Reggae with offbeat guitar skank, mellow bassline, African percussion, smooth romantic lead vocal")

if not lyrics.strip():
    raise RuntimeError("metadata.json has no lyrics -- run generate_metadata.py first.")

print(f"[music] connecting to {SPACE_ID}", file=sys.stderr)
client = Client(SPACE_ID, token=HF_TOKEN)

api_info = {}
try:
    api_info = client.view_api(return_format="dict") or {}
except Exception as err:  # noqa: BLE001 - introspection is best-effort logging, never fatal
    print(f"[music] could not introspect API (continuing anyway): {err}", file=sys.stderr)

endpoint_names = list((api_info.get("named_endpoints") or {}).keys())
print(f"[music] available endpoints: {endpoint_names}", file=sys.stderr)

# The Space's own .click() wiring doesn't set an explicit api_name, so
# Gradio auto-derives one from the Python function name (generate_song).
# Fall back to fuzzy matching if that's ever changed.
api_name = "/generate_song"
if endpoint_names and api_name not in endpoint_names:
    guesses = [n for n in endpoint_names if "generate_song" in n.lower()]
    if not guesses:
        guesses = [
            n for n in endpoint_names
            if "generat" in n.lower() and "cover" not in n.lower() and "lyric" not in n.lower() and "analy" not in n.lower()
        ]
    if guesses:
        print(f"[music] '/generate_song' not found, trying closest match: {guesses[0]}", file=sys.stderr)
        api_name = guesses[0]
    else:
        raise RuntimeError(
            f"Could not find the song-generation endpoint on {SPACE_ID}. "
            f"Available endpoints were: {endpoint_names}. The Space's interface "
            "may have changed -- check https://huggingface.co/spaces/mrfakename/yue2-3b/blob/main/app.py "
            "for the current function name and update api_name above."
        )

# A fresh random seed per run -- the Space's own UI default (42) is just a
# fixed starting point for manual experimentation, not meant to be reused
# unchanged on every automated call, which would make every song's melody
# come out overly similar.
seed = random.randint(1, 2_000_000_000)

print(f"[music] requesting a song via {api_name} (seed {seed})", file=sys.stderr)

MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 30


def _is_quota_error(err) -> bool:
    """Hugging Face's free ZeroGPU tier caps GPU-seconds per account per
    day. That error names exactly when it resets, so retrying 30 seconds
    later is pointless -- fail immediately with a clear message instead.
    (Confirmed Sept 16 2026: an anonymous call hits the SAME quota/reset
    time as a token call from the same runner, so there's no free fallback
    worth trying when this happens -- just wait for the reset.)"""
    return "zerogpu quota" in str(err).lower()


result = None
for attempt in range(1, MAX_ATTEMPTS + 1):
    try:
        result = client.predict(
            style=style_prompt,
            lyrics=lyrics,
            planning_mode="off",  # "No score" -- fastest, and we don't use the editable-score output anyway
            render_quality=16,  # "Fast" -- keeps each ZeroGPU call well within its free time allocation
            seed=seed,
            api_name=api_name,
        )
        break
    except AppError as err:
        if _is_quota_error(err):
            raise RuntimeError(
                f"Out of free Hugging Face ZeroGPU quota for today: {err}\n\n"
                "This isn't a bug -- Hugging Face's free tier caps how many GPU-seconds "
                "your account gets per day. The message above tells you exactly when it "
                "resets -- wait until then and re-run. (An anonymous retry was tried as a "
                "possible workaround and confirmed NOT to help -- it hits the same quota "
                "bucket -- so this script doesn't waste time on that anymore.)"
            ) from err
        if attempt >= MAX_ATTEMPTS:
            raise RuntimeError(
                f"YuE2-3B failed on the server side {MAX_ATTEMPTS} times in a row "
                f"(most recent error: {err}). This is happening on Hugging Face's own "
                "shared ZeroGPU infrastructure, not in this script -- if it keeps "
                "failing on later runs too, this Space may be having a bad day and "
                "it's worth trying again later."
            ) from err
        print(
            f"[music] YuE2-3B returned a server-side error on attempt {attempt}/{MAX_ATTEMPTS} "
            f"(possibly a transient shared-GPU issue): {err}\n"
            f"[music] retrying in {RETRY_WAIT_SECONDS}s...",
            file=sys.stderr,
        )
        time.sleep(RETRY_WAIT_SECONDS)

# generate_song() returns (mp3_path, flac_path, score) -- a plain 3-tuple,
# not wrapped in gradio_client's usual dict/FileData shapes, since these are
# plain str/str/str return values from the Space's own Python function. But
# handle the other shapes gradio_client sometimes uses too, in case the
# Space's return signature ever changes.
audio_path = None
if isinstance(result, (list, tuple)) and result:
    first = result[0]
    audio_path = first if isinstance(first, str) else (first.get("name") or first.get("path") if isinstance(first, dict) else None)
elif isinstance(result, str):
    audio_path = result
elif isinstance(result, dict):
    audio_path = result.get("name") or result.get("path")

if not audio_path or not Path(audio_path).exists():
    raise RuntimeError(f"YuE2-3B did not return a usable audio file. Raw result: {result!r}")

print(f"[music] received generated audio: {audio_path}", file=sys.stderr)

# Normalize to output/song.mp3 -- generate_song() already returns an MP3 in
# the normal case, so this is usually a plain copy; convert only if it ever
# comes back as something else.
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
            "provider": "YuE2-3B (free Hugging Face ZeroGPU Space)",
            "space": SPACE_ID,
            "api_name": api_name,
            "seed": seed,
            "style_prompt": style_prompt,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(f"Generated song: {out}")
