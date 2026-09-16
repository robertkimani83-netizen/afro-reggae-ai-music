"""Generates the full sung song, trying a chain of free options before
giving up -- primarily YuE2-3B (a free open-source full-song model) via its
public Hugging Face Space, with DiffRhythm as a second free Space, each
tried both with your HF_TOKEN and anonymously.

Sept 16 2026 history, in order:
  1. Started with DiffRhythm (ASLP-lab/DiffRhythm). Its calling code was
     fully debugged and working -- it reached real model execution on
     Hugging Face's shared ZeroGPU pool -- but failed there identically 3
     times in a row with `AppError: CUDA error: no kernel image is
     available for execution on the device`. That means the PyTorch build
     baked into that Space doesn't include compiled kernels for whatever
     GPU architecture Hugging Face was handing out that day -- a
     deterministic environment bug in that Space, not something retries or
     parameter changes could fix.
  2. Switched entirely to YuE2-3B (mrfakename/yue2-3b), a different free
     Space that was actually running when checked (two others,
     fffiloni/YuE and innova-ai/YuE-music-generator-demo, were down --
     paused and build-error respectively). This worked end-to-end on a
     real run.
  3. Later hit a DIFFERENT failure: "You have exceeded your free ZeroGPU
     quota (237s requested vs. 214s left)". This is a Hugging Face
     account-wide daily GPU-second budget, shared across every free
     ZeroGPU Space called with the same HF_TOKEN -- so it wasn't a
     YuE2-3B-specific problem, and switching Spaces alone wouldn't have
     fixed it.
  4. This version: rather than fail outright on ANY error (quota or
     otherwise), try a short chain of free options before giving up --
     YuE2-3B with your token, then YuE2-3B anonymously (anonymous calls
     draw from a separate, smaller quota pool, so it can succeed even when
     the authenticated quota is exhausted), then DiffRhythm with your
     token, then DiffRhythm anonymously (in case that Space's environment
     bug from step 1 has since been fixed, or today's GPU allocation
     happens not to hit it). Robert explicitly chose to keep this chain
     free-only rather than add a paid API fallback (e.g. ElevenLabs' Music
     API) -- if this whole chain keeps failing in practice, that's the
     next thing worth reconsidering.

IMPORTANT -- like every HF Space integration before it, none of this could
be live-tested from the environment that wrote this patch (its sandbox
blocks huggingface.co outbound by policy). Parameter names/defaults come
from each Space's own app.py source and from real error messages seen in
past GitHub Actions runs. The introspection logging on each attempt is
there so that if an interface has changed, the failure shows up as a
clear, readable error in the log rather than a silent wrong result.
"""

import json
import os
import random
import re
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

HF_TOKEN = os.environ.get("HF_TOKEN") or None

lyrics = meta.get("lyrics", "")
style_prompt = meta.get(
    "music_style_prompt",
    "Warm Afro-Reggae with offbeat guitar skank, mellow bassline, African percussion, smooth romantic lead vocal",
)

if not lyrics.strip():
    raise RuntimeError("metadata.json has no lyrics -- run generate_metadata.py first.")

# A fresh random seed per run -- a fixed default would make every song's
# melody come out overly similar across runs.
seed = random.randint(1, 2_000_000_000)

MAX_ATTEMPTS_PER_BACKEND = 2  # keep short -- there are up to 4 backends to get through
RETRY_WAIT_SECONDS = 20


def _is_quota_error(err) -> bool:
    """Hugging Face's free ZeroGPU tier caps GPU-seconds per account per
    day. That error names exactly when it resets, so retrying the SAME
    backend 20 seconds later is pointless -- move on to the next backend
    (a different auth mode or Space) immediately instead."""
    return "zerogpu quota" in str(err).lower()


def _resolve_endpoint(client, primary_name, include_kw, exclude_kw, space_id):
    api_info = {}
    try:
        api_info = client.view_api(return_format="dict") or {}
    except Exception as err:  # noqa: BLE001 - introspection is best-effort logging, never fatal
        print(f"[music] could not introspect API (continuing anyway): {err}", file=sys.stderr)
    endpoint_names = list((api_info.get("named_endpoints") or {}).keys())
    print(f"[music] {space_id} available endpoints: {endpoint_names}", file=sys.stderr)

    if not endpoint_names or primary_name in endpoint_names:
        return primary_name

    guesses = [n for n in endpoint_names if all(kw in n.lower() for kw in include_kw)]
    if not guesses:
        guesses = [
            n for n in endpoint_names
            if any(kw in n.lower() for kw in include_kw) and not any(kw in n.lower() for kw in exclude_kw)
        ]
    if guesses:
        print(f"[music] '{primary_name}' not found on {space_id}, trying closest match: {guesses[0]}", file=sys.stderr)
        return guesses[0]

    raise RuntimeError(
        f"Could not find the song-generation endpoint on {space_id}. "
        f"Available endpoints were: {endpoint_names}. That Space's interface may have changed."
    )


def _lyrics_to_lrc(tagged_lyrics, duration_seconds):
    """DiffRhythm needs old-style timestamped LRC text, not the
    [Verse]/[Chorus]-tagged plain lyrics generate_metadata.py now writes
    for YuE2-3B. Strip the section tags and evenly time-stamp what's left
    -- a simple, fully local/deterministic conversion, so this fallback
    doesn't need its own extra API call or a change to generate_metadata.py."""
    lines = [l.strip() for l in tagged_lyrics.splitlines() if l.strip() and not re.match(r"^\[[A-Za-z][^\]]*\]$", l.strip())]
    if not lines:
        lines = ["La la la"]
    intro_pad = min(4.0, duration_seconds * 0.05)
    outro_pad = min(6.0, duration_seconds * 0.08)
    usable = max(10.0, duration_seconds - intro_pad - outro_pad)
    per_line = usable / len(lines)

    def fmt(t):
        m = int(t // 60)
        s = t - m * 60
        return f"[{m:02d}:{s:05.2f}]"

    out_lines = []
    t = intro_pad
    for line in lines:
        out_lines.append(f"{fmt(t)}{line}")
        t += per_line
    return "\n".join(out_lines)


def _call_yue2(token):
    space_id = "mrfakename/yue2-3b"
    print(f"[music] connecting to {space_id} ({'with token' if token else 'anonymous'})", file=sys.stderr)
    client = Client(space_id, token=token)
    api_name = _resolve_endpoint(client, "/generate_song", ["generate_song"], ["cover", "lyric", "analy"], space_id)
    print(f"[music] requesting a song via {space_id}{api_name} (seed {seed})", file=sys.stderr)
    result = client.predict(
        style=style_prompt,
        lyrics=lyrics,
        planning_mode="off",  # "No score" -- fastest, and we don't use the editable-score output anyway
        render_quality=16,  # "Fast" -- keeps each ZeroGPU call well within its free time allocation
        seed=seed,
        api_name=api_name,
    )
    return result, {"provider": "YuE2-3B (free Hugging Face ZeroGPU Space)", "space": space_id, "api_name": api_name, "auth": "token" if token else "anonymous"}


def _call_diffrhythm(token):
    space_id = "ASLP-lab/DiffRhythm"
    requested_minutes = float(meta.get("requested_duration_minutes", 2))
    duration_seconds = max(95.0, min(285.0, requested_minutes * 60))
    lrc = _lyrics_to_lrc(lyrics, duration_seconds)

    print(f"[music] connecting to {space_id} ({'with token' if token else 'anonymous'})", file=sys.stderr)
    client = Client(space_id, token=token)
    api_name = _resolve_endpoint(client, "/infer_music", ["infer_music"], ["lyric", "r1"], space_id)
    print(f"[music] requesting a {duration_seconds:.0f}s song via {space_id}{api_name} (seed {seed})", file=sys.stderr)
    result = client.predict(
        lrc=lrc,
        ref_audio_path=None,  # explicit None -- omitting it makes gradio_client try to resolve the Space's cached default file, which fails on a fresh runner
        text_prompt=style_prompt,
        seed=seed,
        randomize_seed=False,
        steps=32,
        cfg_strength=4.0,
        file_type="mp3",
        odeint_method="euler",
        preference_infer="quality first",
        Music_Duration=duration_seconds,  # capital M -- matches the real Python function signature, not the lowercase shown in its pretty-printed usage text
        api_name=api_name,
    )
    return result, {"provider": "DiffRhythm (free Hugging Face ZeroGPU Space)", "space": space_id, "api_name": api_name, "auth": "token" if token else "anonymous"}


BACKENDS = [
    ("YuE2-3B (token)", lambda: _call_yue2(HF_TOKEN)) if HF_TOKEN else None,
    ("YuE2-3B (anonymous)", lambda: _call_yue2(None)),
    ("DiffRhythm (token)", lambda: _call_diffrhythm(HF_TOKEN)) if HF_TOKEN else None,
    ("DiffRhythm (anonymous)", lambda: _call_diffrhythm(None)),
]
BACKENDS = [b for b in BACKENDS if b is not None]

result = None
result_info = None
errors = []
for name, call in BACKENDS:
    succeeded = False
    for attempt in range(1, MAX_ATTEMPTS_PER_BACKEND + 1):
        try:
            result, result_info = call()
            succeeded = True
            break
        except AppError as err:
            errors.append(f"{name}: {err}")
            if _is_quota_error(err):
                print(f"[music] {name} is out of quota ({err}) -- moving to the next free option", file=sys.stderr)
                break
            if attempt >= MAX_ATTEMPTS_PER_BACKEND:
                print(f"[music] {name} failed {MAX_ATTEMPTS_PER_BACKEND} times ({err}) -- moving to the next free option", file=sys.stderr)
                break
            print(f"[music] {name} returned a server-side error (attempt {attempt}/{MAX_ATTEMPTS_PER_BACKEND}): {err}\n[music] retrying in {RETRY_WAIT_SECONDS}s...", file=sys.stderr)
            time.sleep(RETRY_WAIT_SECONDS)
        except Exception as err:  # noqa: BLE001 - connection errors, endpoint-not-found, etc: also move to the next backend rather than dying outright
            errors.append(f"{name}: {err}")
            print(f"[music] {name} failed to even start ({err}) -- moving to the next free option", file=sys.stderr)
            break
    if succeeded:
        print(f"[music] succeeded via {name}", file=sys.stderr)
        break

if result is None:
    details = "\n".join(f"  - {e}" for e in errors)
    raise RuntimeError(
        f"Every free option failed ({len(BACKENDS)} tried):\n{details}\n\n"
        "This chain covers both free Hugging Face Spaces known to work (YuE2-3B and "
        "DiffRhythm), each tried with your token and anonymously. If they're all "
        "failing, it's likely either a shared free-tier outage affecting everyone right "
        "now, or today's free ZeroGPU quota being exhausted account-wide (check the "
        "errors above for a quota message and how long until it resets) -- both are "
        "worth just trying again later. Robert chose to keep this pipeline free-only "
        "rather than add a paid fallback API; that's the next thing to reconsider if "
        "this keeps happening."
    )

# Output shapes differ slightly by backend -- YuE2-3B returns a plain
# (mp3_path, flac_path, score) tuple of strings; DiffRhythm's Audio output
# can come back as a plain filepath string or wrapped in a dict/tuple,
# depending on gradio_client version. Handle whichever shape shows up.
audio_path = None
if isinstance(result, (list, tuple)) and result:
    first = result[0]
    audio_path = first if isinstance(first, str) else (first.get("name") or first.get("path") if isinstance(first, dict) else None)
elif isinstance(result, str):
    audio_path = result
elif isinstance(result, dict):
    audio_path = result.get("name") or result.get("path")

if not audio_path or not Path(audio_path).exists():
    raise RuntimeError(f"{result_info['provider']} did not return a usable audio file. Raw result: {result!r}")

print(f"[music] received generated audio: {audio_path}", file=sys.stderr)

# Normalize to output/song.mp3 -- both backends are asked for mp3 directly,
# so this is usually a plain copy; convert only if it ever comes back as
# something else.
out = OUT / "song.mp3"
if Path(audio_path).suffix.lower() == ".mp3":
    shutil.copyfile(audio_path, out)
else:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path), "-c:a", "libmp3lame", "-b:a", "192k", str(out)],
        check=True,
    )

(OUT / "music_generation_result.json").write_text(
    json.dumps({**result_info, "seed": seed, "style_prompt": style_prompt}, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Generated song: {out} (via {result_info['provider']}, {result_info['auth']})")
