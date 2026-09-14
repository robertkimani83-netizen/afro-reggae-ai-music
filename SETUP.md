# Setup

## 1. Self-hosted GPU runner

The generation workflow intentionally targets:

`self-hosted, linux, gpu`

Install GitHub Actions Runner on a Linux machine with an NVIDIA GPU and NVIDIA drivers/CUDA working. The runner must have `python3` and `ffmpeg` available.

A GitHub-hosted runner does not provide the dedicated GPU needed for practical local MusicGen/SDXL generation.

## 2. Models

### Music

The code uses MusicGen from AudioCraft through Transformers. The first run downloads the model from Hugging Face and caches it on the runner.

### Visuals

The scene generator uses an SDXL-compatible Diffusers model. Set `IMAGE_MODEL_ID` if you want another model. Default:

`stabilityai/stable-diffusion-xl-base-1.0`

Model licenses and usage restrictions are the responsibility of the user. Check the license before commercial publishing.

## 3. YouTube upload

The upload script uses Google's official YouTube Data API. Create OAuth credentials for a desktop application in Google Cloud, enable YouTube Data API v3, and obtain a refresh token for the channel you want to publish to.

Add these repository secrets:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Do not put credentials in source files.

The first version defaults to `private` visibility so you can test before making a video public.

## 4. Run it

Open the repository's **Actions** tab → **Create Afro-Reggae Song** → **Run workflow**. GitHub supports manually triggered workflows with form inputs using `workflow_dispatch`. citeturn0search2

Example:

- Title: Sweet Island Loving
- Theme: Romantic island love
- Mood: Romantic, warm, uplifting
- Language: English + Swahili
- Video style: African tropical island, cinematic, romantic
- Duration: 3
- Upload: false for the first test

## 5. Cost

This repository does not call paid AI APIs. The software stack is free/open source. Compute is the only practical limitation: local AI generation needs a capable GPU.
