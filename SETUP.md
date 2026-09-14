# Setup

## 1. GPU runner

The generation workflow targets:

`self-hosted, linux, gpu`

You need a Linux machine with an NVIDIA GPU, working NVIDIA drivers, Python 3, curl and FFmpeg. The machine should have enough free disk space for the models.

GitHub Actions is only the automation layer. Heavy AI generation runs on your own runner so there is no paid AI API.

### Add the runner

In GitHub open:

**Repository → Settings → Actions → Runners → New self-hosted runner**

Choose Linux/x64 and follow GitHub's commands on the GPU machine.

Give the runner the labels:

- `self-hosted`
- `linux`
- `gpu`

## 2. Music model

The workflow downloads and installs the open-source **ACE-Step 1.5** project automatically on the runner. ACE-Step supports full-song generation with lyrics/vocals and local inference. Its current documentation lists automatic model download and a REST API server on port 8001.

The workflow starts the local ACE-Step API and then sends it the generated lyrics and Afro-Reggae prompt.

## 3. AI visual model

The scene generator uses:

`stabilityai/stable-diffusion-xl-base-1.0`

You can change the model by setting `IMAGE_MODEL_ID` in the workflow/environment later.

The six generated images are converted into a music-video sequence with FFmpeg camera movement. This keeps the whole system free and local.

## 4. YouTube upload

The upload script uses the official YouTube Data API.

Create Google OAuth credentials for a desktop application, enable **YouTube Data API v3**, authorize your YouTube channel, and obtain a refresh token.

Add these repository secrets:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Never put these values inside the code.

For the first test, keep **Upload to YouTube = false**. After the video is successfully generated, test with YouTube visibility `private`.

## 5. Run the pipeline

Open:

**GitHub → afro-reggae-ai-music → Actions → Create Afro-Reggae Song → Run workflow**

GitHub supports manually running a `workflow_dispatch` workflow and filling its input fields from the Actions page.

Use:

- Title: `Sweet Island Loving`
- Theme: `Romantic island love under the African sunset`
- Mood: `Romantic, warm, uplifting`
- Language: `English + Swahili`
- Video style: `African tropical island, cinematic, romantic, realistic`
- Duration: `3`
- Upload: `false`

## 6. Cost

There are no paid AI APIs in this repository. ACE-Step, SDXL, FFmpeg, Python and the other software are used locally.

The only unavoidable requirement is computing hardware. Your GT 730 is not powerful enough for this workload. A stronger NVIDIA GPU machine must be used as the self-hosted runner.
