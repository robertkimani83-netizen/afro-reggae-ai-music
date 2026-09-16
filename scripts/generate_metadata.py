"""Generates real, theme-specific song lyrics/metadata with Gemini.

Sept 15 2026: this used to be two hardcoded lyric templates ("English +
Swahili" and "English") that returned the literal SAME "Sweet island
loving..." lyrics every single run, completely ignoring the title/theme/mood
inputs. That's why every song sounded identical regardless of what you typed
into the workflow form -- it was never actually calling an AI. This rewrite
calls Gemini for real, the same way generate-short.mjs / generate-
documentary.mjs do in the next-scene-news repo, so lyrics genuinely follow
the theme/mood you give it.

Language note (Sept 15 2026): the free DiffRhythm model used for singing
(see generate_music.py) only supports English and Chinese vocals -- its own
built-in lyrics tool literally only offers those two languages, no Swahili.
Singing Swahili lines through it would likely come out mispronounced/
garbled since the model was never trained on it. So this generates English
lyrics for now. Once the pipeline is proven end-to-end, mixing in Swahili
phrases can be revisited (e.g. testing how the model actually handles a few
Swahili words even though it's unsupported, or looking at other models).

NOTE ON STRING FORMATTING: this file builds the Gemini prompt with plain
string concatenation / f-strings around whole variables, NOT str.format()
on a template containing a literal embedded JSON example. That's deliberate
-- the thumbnail generator in next-scene-news had a real, reproduced bug
where an embedded JSON example inside a .format() template crashed with a
KeyError because its curly braces weren't escaped. Avoiding that pattern
here sidesteps the whole class of bug rather than relying on remembering to
escape every brace.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests

OUT = Path("output")
OUT.mkdir(exist_ok=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODELS = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

title = os.getenv("SONG_TITLE", "Sweet Island Loving")
theme = os.getenv("SONG_THEME", "Romantic island love under the African sunset")
mood = os.getenv("SONG_MOOD", "Romantic, warm, uplifting")
language = os.getenv("SONG_LANGUAGE", "English")
style = os.getenv("VIDEO_STYLE", "African tropical island, cinematic, romantic, realistic")

# DiffRhythm's Music_Duration input only accepts 95-285 seconds -- clamp
# whatever the workflow was given into that range rather than letting an
# out-of-range value fail deep inside generate_music.py.
requested_minutes = max(1.0, float(os.getenv("SONG_DURATION_MIN", "2")))
target_duration_seconds = max(95, min(285, int(requested_minutes * 60)))


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw)
    return raw.strip()


PROMPT_INTRO = (
    "You are a professional songwriter for NEXT VIBE MUSIC, a channel of "
    "original AI-produced Afro-Reggae / Lovers Rock love songs.\n\n"
    "Write ONE original song for a music video. Return ONLY valid JSON, no "
    "markdown fences, in this exact shape (all strings; lyrics_lines is an "
    "array of short singable lines with NO section labels like [Chorus] "
    "mixed into the text itself):\n\n"
    '{\n'
    '  "title": "a short catchy song title",\n'
    '  "lyrics_lines": ["line one", "line two", "... 16 to 24 short singable lines covering verse/chorus/verse/chorus, each under 10 words"],\n'
    '  "music_style_prompt": "one sentence describing the musical style/instrumentation for an AI music generator, e.g. warm Afro-Reggae with offbeat guitar skank, mellow bassline, African percussion, smooth romantic lead vocal",\n'
    '  "scene_queries": ["6 short (2-5 word) stock-photo search queries for real photos matching this song\'s story/mood, e.g. couple beach sunset, tropical palm trees, ocean waves sunset"],\n'
    '  "description": "a 2-3 sentence YouTube description for the video, mentioning it is an original AI-composed song",\n'
    '  "tags": ["8-12 relevant YouTube tags as short strings"]\n'
    '}\n\n'
    "Keep every lyric line simple, warm and singable -- this goes straight "
    "into an AI singing model, so avoid punctuation-heavy or awkward "
    "phrasing.\n\n"
)

prompt = (
    PROMPT_INTRO
    + f'Song title (use as inspiration, you may improve it): "{title}"\n'
    + f'Theme/story: {theme}\n'
    + f'Mood: {mood}\n'
    + f'Language: {language}\n'
    + f'Visual style for the music video: {style}\n'
)


def analyze_with_gemini():
    if not GEMINI_API_KEY:
        print("[metadata] no GEMINI_API_KEY set, using rule-based fallback", file=sys.stderr)
        return None
    last_err = None
    for model in GEMINI_MODELS:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(_clean_json(text))
            print(f"[metadata] lyrics generated via {model}", file=sys.stderr)
            return parsed
        except Exception as err:  # noqa: BLE001 - deliberately broad, tries next model
            last_err = err
            print(f"[metadata] {model} failed: {err}, trying next model...", file=sys.stderr)
    print(f"[metadata] all Gemini models failed ({last_err}), using rule-based fallback", file=sys.stderr)
    return None


def fallback_song():
    """Non-fatal fallback if Gemini is unreachable/misconfigured -- keeps the
    pipeline runnable (e.g. for a quick smoke test) instead of hard-crashing,
    same philosophy as thumbnail-gen.mjs's fallback in next-scene-news. This
    is intentionally generic; a real run should always have GEMINI_API_KEY
    set so this path isn't the normal case."""
    return {
        "title": title,
        "lyrics_lines": [
            "Under the island moon your hand is in mine",
            "Your love is shining and everything feels fine",
            "Sweet island loving come closer tonight",
            "Dancing by the ocean everything feels right",
            "Sweet island loving just you and me",
            "Lost in the rhythm beside the sea",
            "Palm trees are moving while the warm wind calls",
            "Your love is stronger than any walls",
            "Sweet island loving come closer tonight",
            "Dancing by the ocean everything feels right",
            "Hold me slowly let the rhythm play",
            "We will keep dancing until the break of day",
        ],
        "music_style_prompt": f"Afro-Reggae, {mood}, warm bass guitar, offbeat reggae guitar, African percussion, melodic lead vocal, polished studio production. No spoken intro.",
        "scene_queries": [
            "couple beach sunset",
            "tropical palm trees",
            "ocean waves sunset",
            "beach bonfire night",
            "african sunrise coastline",
            "tropical island aerial",
        ],
        "description": f"{title} - an original Afro-Reggae love song, AI-composed and produced for NEXT VIBE MUSIC.",
        "tags": ["Afro-Reggae", "Afrobeat", "Reggae", "African Music", "AI Music", "Tropical Music", "Love Song"],
    }


def build_lrc(lines, duration_seconds):
    """Evenly time-stamps plain lyric lines into DiffRhythm's required
    "[mm:ss.xx]text" LRC format. This is a simple, fully local/deterministic
    step -- no extra API call needed just to timestamp lines -- leaving only
    ONE external call (the actual singing generation) as something that can
    fail. Leaves a short intro/outro pad so the song doesn't start singing
    at 0:00 or run vocals right to the last frame."""
    lines = [l.strip() for l in lines if l.strip()]
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

    out = []
    t = intro_pad
    for line in lines:
        out.append(f"{fmt(t)}{line}")
        t += per_line
    return "\n".join(out)


analyzed = analyze_with_gemini() or fallback_song()

fallback = fallback_song()
lyrics_lines = analyzed.get("lyrics_lines") or fallback["lyrics_lines"]
final_title = analyzed.get("title") or title
lrc = build_lrc(lyrics_lines, target_duration_seconds)
plain_lyrics = "\n".join(lyrics_lines)

data = {
    "title": final_title,
    "theme": theme,
    "mood": mood,
    "language": language,
    "video_style": style,
    "lyrics": plain_lyrics,
    "lrc": lrc,
    "target_duration_seconds": target_duration_seconds,
    "music_style_prompt": analyzed.get("music_style_prompt") or fallback["music_style_prompt"],
    "scene_queries": analyzed.get("scene_queries") or fallback["scene_queries"],
    "description": analyzed.get("description") or f"{final_title} - an original Afro-Reggae love song, AI-composed and produced for NEXT VIBE MUSIC.",
    "tags": analyzed.get("tags") or fallback["tags"],
}

(OUT / "metadata.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "lyrics.txt").write_text(plain_lyrics, encoding="utf-8")
(OUT / "song.lrc").write_text(lrc, encoding="utf-8")
print(f"Created metadata for: {final_title}")
