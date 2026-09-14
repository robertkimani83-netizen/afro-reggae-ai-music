# FREE GPU SETUP — Afro-Reggae AI Music

## Important

The GitHub-hosted `ubuntu-latest` runner does **not** provide an NVIDIA GPU for this workload. The normal workflow therefore stays on a self-hosted GPU runner. GitHub documents standard public runners as CPU VMs; GPU-powered larger runners are a separate feature. 

Your Dell OptiPlex 7040 with GT 730 is not a practical machine for ACE-Step + SDXL generation.

## Best no-cost test route

Use a free GPU notebook service for testing the pipeline, then move to a permanent GPU runner when you have one. Free GPU services are temporary and availability/limits can change.

### Option A — Kaggle Notebook

1. Open Kaggle and create a new Notebook.
2. In Notebook settings, enable **GPU**.
3. Open a terminal cell or use Python cells to clone this repository.
4. Install the dependencies from `requirements.txt` and `requirements-vision.txt`.
5. Install and start ACE-Step 1.5 locally.
6. Run:

```bash
python scripts/generate_metadata.py \\
  --title "Sweet Island Loving" \\
  --theme "Romantic island love under the African sunset" \\
  --mood "Romantic, warm, uplifting" \\
  --language "English + Swahili" \\
  --video-style "African tropical island, cinematic, romantic, realistic" \\
  --duration 3
```

Then run the music, scene, video and thumbnail scripts in the same order as `.github/workflows/create-song.yml`.

### Option B — Google Colab

A free Colab GPU can also be used for a manual test. Free Colab GPU access is not guaranteed and sessions are temporary, so it should not be treated as the permanent GitHub runner.

## Permanent automation

For one-click GitHub Actions automation, the machine needs to be a self-hosted Linux GPU runner with these labels:

- `self-hosted`
- `linux`
- `gpu`

The existing workflow already targets:

```yaml
runs-on: [self-hosted, linux, gpu]
```

A suitable NVIDIA GPU should have enough VRAM for ACE-Step and SDXL. The exact requirement depends on the model/offloading configuration.

## Do not add YouTube secrets yet

First make one song successfully. After generation works, add these GitHub Actions secrets:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

For the first upload test, use **private** visibility.

## Free means no paid AI API

This project uses local/open-source generation rather than a paid AI generation API. The remaining limitation is compute: free GPU notebook sessions are temporary, while a permanent self-hosted GPU requires hardware you control or a provider that supplies free compute.
