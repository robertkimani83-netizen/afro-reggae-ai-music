# Setup

No self-hosted runner, no GPU, no local installs -- everything runs on
GitHub's free `ubuntu-latest` runner. You just need 3-6 free API
credentials added as repository secrets.

**GitHub -> this repo -> Settings -> Secrets and variables -> Actions ->
New repository secret**

## 1. Gemini (writes the lyrics/title/description/tags)

- `GEMINI_API_KEY` -- if you already have one from setting up
  `next-scene-news`, reuse the same value here (secrets don't carry across
  repos, so it needs to be added again in this one).
- Free tier is enough. Get one at https://aistudio.google.com/apikey if you
  don't already have one.

## 2. Hugging Face (runs the actual AI singing, for free, on their shared GPU pool)

- `HF_TOKEN` -- again, reuse your existing token if you set one up for
  `next-scene-news`'s thumbnail generator, otherwise create a free account
  at https://huggingface.co and generate a token (Settings -> Access
  Tokens -> a "read" token is enough).
- This isn't strictly required (the Space can be called anonymously), but
  an authenticated call gets a bigger, steadier free ZeroGPU quota than an
  anonymous one. Either way, this quota is a daily cap shared across every
  free Hugging Face Space you use with this token -- if a run fails with a
  quota-exceeded message, that's not a bug, just wait for the reset time
  the error reports.

## 3. Pexels (real photos for the music video)

- `PEXELS_API_KEY` -- reuse your existing key from `next-scene-news` if you
  have one, otherwise get a free one at https://www.pexels.com/api/.

## 4. YouTube upload (optional -- only needed once you're ready to publish)

This channel (NEXT VIBE MUSIC) is a different YouTube channel from
NEXTSCENE TV, so it needs its own OAuth credentials authorized against
*that* channel's Google account -- you can't reuse the `next-scene-news`
repo's YOUTUBE_* secrets here even if it's the same Google Cloud project.

- Create OAuth credentials for a desktop application in Google Cloud
  Console, enable **YouTube Data API v3**, and go through the OAuth consent
  flow signed in as whichever Google account owns/manages NEXT VIBE MUSIC,
  to get a refresh token for that channel.
- Add:
  - `YOUTUBE_CLIENT_ID`
  - `YOUTUBE_CLIENT_SECRET`
  - `YOUTUBE_REFRESH_TOKEN`
- Leave **Upload to YouTube = false** for your first several test runs.
  Every run (upload on or off) saves its result as a downloadable GitHub
  Actions artifact, so you can listen to and watch the song before it ever
  touches YouTube. Once you're happy with a run, turn upload on and start
  with `private` visibility.

## 5. Run it

**GitHub -> this repo -> Actions -> Create Afro-Reggae Song -> Run workflow**

Fill in a title, theme, mood, visual style, and a rough duration in minutes
(1-6 -- a guide for how many verse/chorus sections Gemini writes, not an
exact guarantee; the singing model decides the actual song length from how
much lyrics it's given). Leave "Upload to YouTube" unchecked for the first
run.

## 6. Cost

Genuinely free with the credentials above -- Gemini, Hugging Face ZeroGPU,
Pexels and YouTube all have free tiers this pipeline stays within for
normal use. The one thing that isn't fully under your control is that the
Hugging Face Space is a shared public resource, not dedicated compute --
see the README for the trade-off and the fallback if it's ever unreliable.
