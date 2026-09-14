# Afro-Reggae AI Music

A completely separate, free-first pipeline for creating Afro-Reggae songs with vocals, AI visual scenes, thumbnails, and YouTube-ready videos.

## Important

This project is intentionally separate from `next-scene-news`.

There are **no paid AI APIs** in this project. AI models run locally on a self-hosted GPU runner.

## Pipeline

1. Enter song title, theme, mood, language, visual style and duration.
2. Generate original lyrics and metadata locally.
3. Generate a complete vocal song with **ACE-Step 1.5** locally.
4. Generate six AI visual scenes with SDXL locally.
5. Animate the scenes with a slow camera/zoom effect and combine them with the song using FFmpeg.
6. Generate a 1280x720 thumbnail locally.
7. Optionally upload the finished MP4 and thumbnail to YouTube.
8. Save the generated files as a GitHub Actions artifact.

GitHub Actions supports manually triggered workflows with input fields using `workflow_dispatch`, so the song settings can be entered from the Actions page.

## Free software

- ACE-Step 1.5 — full music with vocals/lyrics, local
- Stable Diffusion XL — AI visual scenes, local
- Pillow — thumbnail
- FFmpeg — video/audio assembly
- Python
- Google YouTube Data API — upload
- GitHub Actions — orchestration

No ElevenLabs, Runway, Suno, paid image API, or paid video API is used.

## Hardware

The GitHub-hosted runner is not used for the heavy AI work. The workflow requires a self-hosted runner with a GPU.

ACE-Step 1.5 supports local generation on consumer hardware; its current documentation lists about 4 GB VRAM for DiT-only mode and about 6 GB for LM + DiT, with CPU offload available for lower-VRAM systems. SDXL is heavier and benefits from substantially more VRAM.

Your GT 730 is not suitable for this AI workload, so the next step is to connect a stronger NVIDIA GPU machine as the self-hosted runner.

## YouTube

YouTube upload is optional. The first test should use `Upload to YouTube = false`. After the generated files work correctly, add the three YouTube secrets described in `SETUP.md` and test with `private` visibility first.
