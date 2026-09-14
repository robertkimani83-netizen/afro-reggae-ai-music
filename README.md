# Afro-Reggae AI Music

A separate, free-first pipeline for creating Afro-Reggae songs, AI-generated visual scenes, thumbnails, and YouTube-ready videos.

## Important

This project is intentionally separate from `next-scene-news`.

The pipeline uses open-source software and does not require paid AI APIs. Heavy AI generation is designed for a **self-hosted runner with a suitable GPU**; GitHub-hosted runners are used only for lightweight automation unless you change the workflow.

## Pipeline

1. Enter song title/theme/genre/mood/language.
2. Generate original lyrics and metadata locally.
3. Generate music with MusicGen/AudioCraft locally.
4. Generate AI visual scenes with Stable Diffusion/SDXL locally.
5. Assemble the scenes and music with FFmpeg.
6. Generate a 1280x720 thumbnail locally.
7. Optionally upload the finished video to YouTube.
8. Save the final files as GitHub Actions artifacts.

GitHub Actions supports manually triggered workflows with inputs through `workflow_dispatch`. See the official GitHub documentation: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow

## Free-first design

- Python
- PyTorch
- Hugging Face Transformers/Diffusers
- MusicGen / AudioCraft
- SDXL or another locally installed image model
- Pillow
- FFmpeg
- Google/YouTube API for upload

No paid music, video, thumbnail, or LLM API is included.

## Hardware

AI generation is GPU-heavy. A GT 730 is not suitable for MusicGen + SDXL generation. Use a stronger local NVIDIA GPU, a self-hosted GPU machine, or another machine you control that can run the models.

## First run

See `SETUP.md` for the exact setup and YouTube OAuth steps.
