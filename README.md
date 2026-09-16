# Afro-Reggae AI Music

A free, fully-automated pipeline for creating original Afro-Reggae/Lovers
Rock love songs -- real AI-written lyrics, real AI-sung vocals, a music
video built from real photos, a thumbnail, and (optionally) a direct upload
to NEXT VIBE MUSIC.

This project is intentionally separate from `next-scene-news` (the
NEXTSCENE TV pipeline) -- different channel, different content, its own
repo and secrets.

## Sept 15 2026 rebuild -- what changed and why

The previous version of this pipeline never actually produced a video. All
3 test runs failed. On top of that, two things were quietly broken even
before the failure:

- **Lyrics weren't AI-generated at all.** `generate_metadata.py` used two
  hardcoded lyric templates and returned the literal same "Sweet island
  loving..." song every single run, no matter what title/theme/mood you
  typed into the workflow form.
- **The music engine needed a real GPU.** It tried to run ACE-Step 1.5 (a
  full AI singing model) locally, either on your own PC or on a GitHub
  runner. Neither has a GPU capable of that: your PC's GT 730 was already
  flagged in this repo's own old notes as too weak, and GitHub's free
  runners have no GPU at all. The last attempt just sat waiting ~25 minutes
  for the model to start, then gave up.

This rebuild fixes both:

- **Lyrics, title, style, description and tags now come from a real Gemini
  call** (`scripts/generate_metadata.py`), the same way the news channel's
  pipeline writes real scripts -- so every song is genuinely about what you
  typed in, not a fixed template.
- **Singing now happens on Hugging Face's free "ZeroGPU" shared GPU pool**,
  via the open-source [DiffRhythm](https://github.com/ASLP-lab/DiffRhythm)
  model's public Space (`scripts/generate_music.py`). This machine (or the
  GitHub runner) never needs a GPU itself -- it just sends a request over
  the internet and gets a finished song back, the same pattern already used
  for FLUX thumbnail backgrounds in `next-scene-news`.
- **Music-video scenes are now real photos from Pexels** (free stock photo
  API, same service the news channel already uses), instead of plain
  color-gradient cards.
- **The whole workflow runs on a normal free `ubuntu-latest` GitHub runner**
  -- no self-hosted runner, no Windows, no local model installs. This is
  also cheaper on your free Actions minutes (Windows runners count double).

## One real limitation: English only, for now

DiffRhythm's own lyrics tool only lists English and Chinese as supported
languages -- there's no Swahili option, which strongly suggests the model
wasn't trained on it. Feeding it Swahili lines would likely come out
mispronounced or garbled. So for now, songs are written and sung in English
only, even though your channel's earlier videos mixed in Swahili phrases.
Once this pipeline is proven working end-to-end, it's worth revisiting --
either testing how the model actually handles a few Swahili words anyway,
or looking at whether a better-suited free model exists by then.

## Complete pipeline

1. Open GitHub Actions -> **Create Afro-Reggae Song** -> Run workflow.
2. Enter a song title/theme/mood/visual style, and a target duration
   (1.6-4.75 minutes -- DiffRhythm's supported range).
3. Gemini writes real lyrics, a title, a music style description, six photo
   search queries, a YouTube description and tags.
4. The lyrics are time-stamped into the LRC format DiffRhythm needs.
5. DiffRhythm (free HF Space) generates the actual sung song.
6. Pexels supplies six real photos matching the song's story/mood.
7. FFmpeg turns those photos into a slow Ken Burns-style video and mixes in
   the song.
8. A thumbnail is generated.
9. YouTube upload is optional (off by default for testing).
10. Everything generated is saved as a GitHub Actions artifact either way,
    so you can review a run before ever enabling upload.

## Free, and what "free" depends on

No paid AI API is required:

- Gemini: free tier (same key you already use for `next-scene-news`).
- DiffRhythm singing: Hugging Face's free ZeroGPU Space -- a shared public
  resource. It's genuinely free, but it's not Robert's dedicated compute:
  it could occasionally be slow, hit a shared usage limit, or change its
  interface, since none of that is under your control. If it becomes
  unreliable in practice, the fallback is a small per-song paid vocal API
  (e.g. Suno's official API) instead of this free shared one.
- Pexels: free tier stock photos (same key you already use for
  `next-scene-news`).
- YouTube upload: free, standard YouTube Data API.

See `SETUP.md` for exactly which secrets to add.
