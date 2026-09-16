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
  via a public Space (`scripts/generate_music.py`). This machine (or the
  GitHub runner) never needs a GPU itself -- it just sends a request over
  the internet and gets a finished song back, the same pattern already used
  for FLUX thumbnail backgrounds in `next-scene-news`. (Originally built
  against DiffRhythm, then switched to YuE2-3B after DiffRhythm turned out
  to have a standing server-side bug -- see "Free, and what 'free' depends
  on" below.)
- **Music-video scenes are now real photos from Pexels** (free stock photo
  API, same service the news channel already uses), instead of plain
  color-gradient cards.
- **The whole workflow runs on a normal free `ubuntu-latest` GitHub runner**
  -- no self-hosted runner, no Windows, no local model installs. This is
  also cheaper on your free Actions minutes (Windows runners count double).

## One real limitation: English only, for now

The singing model's own lyrics tools only list English (plus a few other
languages depending on the model) -- no Swahili -- which strongly suggests
it wasn't trained on it. Feeding it Swahili lines would likely come out
mispronounced or garbled. So for now, songs are written and sung in English
only, even though your channel's earlier videos mixed in Swahili phrases.
Once this pipeline is proven working end-to-end, it's worth revisiting --
either testing how the model actually handles a few Swahili words anyway,
or looking at whether a better-suited free model exists by then.

## Complete pipeline

1. Open GitHub Actions -> **Create Afro-Reggae Song** -> Run workflow.
2. Enter a song title/theme/mood/visual style, and a rough target duration
   in minutes (a guide for how many verse/chorus sections Gemini writes,
   not an exact guarantee -- the singing model decides the actual length
   from how much lyrics it's given).
3. Gemini writes real lyrics (structured with [Verse]/[Chorus]/[Bridge]
   section tags), a title, a music style description, six photo search
   queries, a YouTube description and tags.
4. YuE2-3B (free HF Space) generates the actual sung song from those
   lyrics.
5. Pexels supplies six real photos matching the song's story/mood.
6. FFmpeg turns those photos into a slow Ken Burns-style video, measures
   the actual song length, and mixes the song in.
7. A thumbnail is generated -- your NEXT VIBE MUSIC logo, the song title in
   a bold display font, a genre tag, and an "ORIGINAL SONG" badge, over one
   of the fetched photos.
8. YouTube upload is optional (off by default for testing).
9. Everything generated is saved as a GitHub Actions artifact either way,
   so you can review a run before ever enabling upload.

## Free, and what "free" depends on

No paid AI API is required:

- Gemini: free tier (same key you already use for `next-scene-news`).
- Singing: `generate_music.py` calls YuE2-3B (`mrfakename/yue2-3b`), a free
  Hugging Face ZeroGPU Space. It's a shared public resource, not Robert's
  dedicated compute, so it can occasionally be slow, change its interface,
  or hit Hugging Face's free-tier daily quota (a cap on GPU-seconds per
  account per day, shared across every free ZeroGPU Space called with the
  same token). A run that fails with a quota message just needs to wait for
  the reset time the error itself reports, then run again.
  Two things were tried and ruled out as workarounds, based on real test
  runs rather than assumption: an anonymous (no-token) retry, which turned
  out to hit the exact same quota bucket as the token call rather than a
  separate one; and falling back to a second free Space (DiffRhythm), which
  turned out to have a standing server-side bug (`CUDA error: no kernel
  image is available for execution on the device`) that failed identically
  on two separate days of testing. Neither is worth the added complexity,
  so the pipeline stays simple: one Space, fail fast and clearly on a
  quota error, retry a couple of times on a genuinely transient one.
  If Hugging Face's free tier ever proves too unreliable in practice, the
  next thing to reconsider is a small paid vocal API (e.g. ElevenLabs'
  official Music API, roughly $0.64/minute) as a real fallback -- Robert
  has chosen to keep this fully free for now. (An earlier draft of this
  README named "Suno's official API" for that role -- that was wrong; Suno
  has no official public API, only unofficial third-party resellers, which
  isn't something worth building on.)
- Pexels: free tier stock photos (same key you already use for
  `next-scene-news`).
- YouTube upload: free, standard YouTube Data API.

See `SETUP.md` for exactly which secrets to add.
