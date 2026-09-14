# Afro-Reggae AI Music

A completely separate, free-first pipeline for creating Afro-Reggae songs with vocals, music-video visuals, thumbnails, and YouTube-ready videos.

## Important

This project is intentionally separate from `next-scene-news`.

The music generator now uses the **official ACE-Step 1.5 Hugging Face Space** as the online AI music engine, so your Dell GT 730 is not used for music generation. Hugging Face Spaces expose Gradio apps as callable APIs, and the official ACE-Step Space runs on ZeroGPU. citeturn0search0turn3search0

## Pipeline

1. Enter song title, theme, mood, language, visual style and duration.
2. Generate lyrics and metadata.
3. Send the music prompt and lyrics to the official ACE-Step 1.5 online Space.
4. Download the generated audio into `output/song.mp3`.
5. Create lightweight cinematic visual scenes on the GitHub-hosted runner when no local GPU is available.
6. Animate the scenes with FFmpeg and combine them with the song.
7. Generate a 1280x720 thumbnail.
8. Optionally upload the finished MP4 and thumbnail to YouTube.
9. Save the generated files as a GitHub Actions artifact.

GitHub Actions supports manually triggered workflows with input fields using `workflow_dispatch`, so the song settings can be entered from the Actions page.

## ACE-Step online limits

The official ACE-Step v1.5 Space is currently a ZeroGPU Space. Its current deployment has a roughly 120-second GPU execution limit for free-tier generation, so this workflow defaults to about 110 seconds per generation to leave headroom. citeturn0search8

For more reliable access and higher daily quota, add a Hugging Face read token to the repository secret named `HF_TOKEN`. Hugging Face documents that authenticated free accounts receive a larger ZeroGPU daily quota than unauthenticated requests. citeturn3search0

The ACE-Step 1.5 model itself supports lyrics, vocals, 50+ languages, and variable-length music generation, and is MIT licensed. citeturn0search3turn5search1

## Free software

- ACE-Step 1.5 — online music generation
- Hugging Face Spaces / ZeroGPU — hosted AI compute
- Pillow — visual fallback and thumbnail
- FFmpeg — video/audio assembly
- Python
- Google YouTube Data API — optional upload
- GitHub Actions — orchestration

No ElevenLabs, Runway, paid image API, paid video API, or paid music API is required for the current workflow.

## Hardware

The workflow now uses `ubuntu-latest`, not a self-hosted GPU runner. Your GT 730 is therefore not required for the music-generation stage.

If a stronger NVIDIA GPU is added later, the project can be extended to use local SDXL scenes again by enabling the GPU scene path.

## YouTube

YouTube upload is optional. The first test should use `Upload to YouTube = false`. After the generated files work correctly, add the three YouTube secrets described in `SETUP.md` and test with `private` visibility first.
