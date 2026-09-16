"""Generates real, theme-specific song lyrics/metadata with Gemini.

Sept 15 2026: this used to be two hardcoded lyric templates ("English +
Swahili" and "English") that returned the literal SAME "Sweet island
loving..." lyrics every single run, completely ignoring the title/theme/mood
inputs. That's why every song sounded identical regardless of what you typed
into the workflow form -- it was never actually calling an AI. This rewrite
calls Gemini for real, the same way generate-short.mjs / generate-
documentary.mjs do in the next-scene-news repo, so lyrics genuinely follow
the theme/mood you give it.

Language note (Sept 15 2026): the free singing model used by generate_music.py
only supports English and Chinese vocals, no Swahili. So this generates
English lyrics for now. Once the pipeline is proven end-to-end, mixing in
Swahili phrases can be revisited (e.g. testing how the model actually
handles a few Swahili words even though it's unsupported, or looking at
other models).

Sept 16 2026: switched the singing model from DiffRhythm to YuE2-3B (see
generate_music.py's docstring for why -- short version: DiffRhythm hit a
deterministic server-side CUDA/environment bug on its Hugging Face Space
that retries couldn't fix). This changed the required lyrics FORMAT: it no
longer takes evenly-timestamped LRC text, it takes plain lyrics with
[Verse]/[Chorus]/[Bridge] section tags and a blank line between sections --
the song's actual length comes out of how much lyrics content is given to
it (more sections = a longer song) rather than a separate duration
parameter, and assemble_video.py already measures the real rendered
song.mp3 with ffprobe rather than trusting a pre-set number, so no change
was needed there. This file now asks Gemini directly for that tagged
format, and uses the requested duration only as a rough guide for how many
verse/chorus sections to write, not a strict clamp.

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

# YuE2-3B has no duration input -- the song's length follows however much
# lyrics content it's given. Use the requested minutes as a rough guide for
# how many verse/chorus sections to ask Gemini to write, loosely clamped to
# a sane range (a 1-section song or a 12-verse epic are both a bad time).
requested_minutes = max(1.0, min(6.0, float(os.getenv("SONG_DURATION_MIN", "2"))))
# ~35-45s of sung content per verse or chorus section is a reasonable rule
# of thumb, so roughly (minutes*60/40) sections, kept to an even number
# (verse/chorus pairs) and at least 4 (one verse + one chorus, twice).
approx_sections = max(4, min(14, round((requested_minutes * 60 / 40) / 2) * 2))


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
    "markdown fences, in this exact shape (all strings):\n\n"
    '{\n'
    '  "title": "a short catchy song title",\n'
    '  "lyrics": "the full lyrics as ONE string, structured with section tags on their own line -- [Verse], [Chorus], and optionally [Bridge] -- with a BLANK LINE between each section, e.g. \\"[Verse]\\\\nline one\\\\nline two\\\\n\\\\n[Chorus]\\\\nline one\\\\nline two\\\\n\\\\n[Verse]\\\\n...\\". Keep each line short, warm and singable (under 10 words), no punctuation-heavy or awkward phrasing -- this goes straight into an AI singing model.",\n'
    '  "music_style_prompt": "one sentence describing the musical style/instrumentation for an AI music generator, e.g. warm Afro-Reggae with offbeat guitar skank, mellow bassline, African percussion, smooth romantic lead vocal",\n'
    '  "scene_queries": ["6 short (2-5 word) stock-photo search queries for real photos matching this song\'s story/mood, e.g. couple beach sunset, tropical palm trees, ocean waves sunset"],\n'
    '  "description": "a 2-3 sentence YouTube description for the video, mentioning it is an original AI-composed song",\n'
    '  "tags": ["8-12 relevant YouTube tags as short strings"]\n'
    '}\n\n'
)

prompt = (
    PROMPT_INTRO
    + f'Song title (use as inspiration, you may improve it): "{title}"\n'
    + f'Theme/story: {theme}\n'
    + f'Mood: {mood}\n'
    + f'Language: {language}\n'
    + f'Visual style for the music video: {style}\n'
    + f'Requested rough length: about {requested_minutes:.1f} minute(s) -- write approximately '
    + f'{approx_sections} sections total (alternating [Verse] and [Chorus], repeating the chorus '
    + 'lyrics where natural) to roughly match that length; a longer request means more sections, '
    + 'not longer individual lines.\n'
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
        "lyrics": (
            "[Verse]\n"
            "Under the island moon your hand is in mine\n"
            "Your love is shining and everything feels fine\n"
            "Sweet island loving come closer tonight\n"
            "Dancing by the ocean everything feels right\n"
            "\n"
            "[Chorus]\n"
            "Sweet island loving just you and me\n"
            "Lost in the rhythm beside the sea\n"
            "Palm trees are moving while the warm wind calls\n"
            "Your love is stronger than any walls\n"
            "\n"
            "[Verse]\n"
            "Sweet island loving come closer tonight\n"
            "Dancing by the ocean everything feels right\n"
            "Hold me slowly let the rhythm play\n"
            "We will keep dancing until the break of day\n"
            "\n"
            "[Chorus]\n"
            "Sweet island loving just you and me\n"
            "Lost in the rhythm beside the sea\n"
            "Palm trees are moving while the warm wind calls\n"
            "Your love is stronger than any walls"
        ),
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


def _normalize_lyrics(raw: str) -> str:
    """Defensive cleanup: make sure section tags are on their own line and
    trim stray whitespace, in case Gemini's formatting drifts slightly from
    what was asked for. Doesn't try to fully re-derive structure -- just
    tidies what's there."""
    text = (raw or "").strip()
    if not text:
        return text
    # Make sure a tag like "[Verse]something" that landed glued to the next
    # word gets split onto its own line.
    text = re.sub(r"(\[(?:Verse|Chorus|Bridge)[^\]]*\])\s*", r"\1\n", text, flags=re.IGNORECASE)
    lines = [l.rstrip() for l in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


analyzed = analyze_with_gemini() or fallback_song()

fallback = fallback_song()
final_title = analyzed.get("title") or title
lyrics = _normalize_lyrics(analyzed.get("lyrics")) or fallback["lyrics"]

data = {
    "title": final_title,
    "theme": theme,
    "mood": mood,
    "language": language,
    "video_style": style,
    "lyrics": lyrics,
    "requested_duration_minutes": requested_minutes,
    "music_style_prompt": analyzed.get("music_style_prompt") or fallback["music_style_prompt"],
    "scene_queries": analyzed.get("scene_queries") or fallback["scene_queries"],
    "description": analyzed.get("description") or f"{final_title} - an original Afro-Reggae love song, AI-composed and produced for NEXT VIBE MUSIC.",
    "tags": analyzed.get("tags") or fallback["tags"],
}

(OUT / "metadata.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "lyrics.txt").write_text(lyrics, encoding="utf-8")
print(f"Created metadata for: {final_title}")
