# Afro-Reggae AI Music

A completely separate, free, local-first pipeline for creating Afro-Reggae songs with vocals, music-video visuals, thumbnails, and YouTube-ready videos.

## Important

This project is intentionally separate from `next-scene-news`.

The music generator now uses **local ACE-Step 1.5** on your own Windows PC. There is no Suno API, no MusicAPI, no Hugging Face Space, no `HF_TOKEN`, and no paid music service.

ACE-Step officially supports CPU-only inference, although it is significantly slower than GPU inference. The workflow therefore uses the PC as a self-hosted GitHub Actions runner and forces CPU mode. citeturn0search1

## Complete pipeline

1. Open GitHub Actions.
2. Choose **Create Afro-Reggae Song**.
3. Enter song title, theme, mood, language, visual style and duration.
4. GitHub sends the job to the Windows self-hosted runner.
5. The runner starts local ACE-Step 1.5.
6. Lyrics and music metadata are generated.
7. The lyrics and Afro-Reggae prompt are sent to local ACE-Step.
8. ACE-Step creates the sung song locally.
9. The generated MP3 is saved as `output/song.mp3`.
10. Cinematic visual scenes are created.
11. FFmpeg combines the visuals and song.
12. A 1280x720 thumbnail is created.
13. YouTube upload is optional.
14. All generated files are saved as a GitHub Actions artifact.

The current ACE-Step API uses `POST /release_task`, `POST /query_result`, and `/v1/audio` for asynchronous local generation and audio download. citeturn1search4turn1search7

## No API / no payment

The music stage requires:

- No Suno account
- No Suno API
- No MusicAPI key
- No Hugging Face token
- No paid subscription
- No paid music credits

ACE-Step is downloaded and run locally. Models are downloaded on the first run. citeturn0search1

## PC requirement

The current PC can run the pipeline in CPU mode, but music generation can be slow. ACE-Step's documentation explicitly says CPU inference is supported and significantly slower. citeturn0search1

The repository includes `scripts/setup_local_acestep.ps1`, which downloads ACE-Step and installs its environment automatically when the workflow first runs.

## GitHub runner

The workflow uses:

```text
runs-on: [self-hosted, Windows, X64]
```

This means the Windows PC must have a GitHub self-hosted runner registered for this repository. Once registered, GitHub can send the complete job to the PC automatically.

## YouTube

YouTube upload is optional. The first test should use `Upload to YouTube = false`. After the generated files work correctly, YouTube can be enabled with the existing YouTube secrets.
