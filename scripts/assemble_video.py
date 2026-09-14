import subprocess
from pathlib import Path

OUT = Path('output')
SCENES = sorted((OUT / 'scenes').glob('scene_*.jpg'))
if not SCENES:
    raise SystemExit('No AI scenes found.')

audio = OUT / 'song.mp3'
if not audio.exists():
    raise SystemExit('song.mp3 is missing.')

clips = OUT / 'clips'
clips.mkdir(exist_ok=True)

def duration(path):
    return float(subprocess.check_output([
        'ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)
    ]).decode().strip())

total = duration(audio)
per = total / len(SCENES)

for i, scene in enumerate(SCENES, start=1):
    clip = clips / f'clip_{i:02d}.mp4'
    frames = max(2, int(per * 30))
    vf = f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.0008,1.12)':d={frames}:s=1280x720:fps=30,format=yuv420p"
    subprocess.run([
        'ffmpeg','-y','-loop','1','-i',str(scene),'-t',str(per),'-vf',vf,
        '-an','-c:v','libx264','-preset','medium','-crf','20',str(clip)
    ], check=True)

concat = OUT / 'concat.txt'
concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in sorted(clips.glob('clip_*.mp4'))), encoding='utf-8')
video_only = OUT / 'video_only.mp4'
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(video_only)], check=True)

final = OUT / 'afro-reggae-music-video.mp4'
subprocess.run([
    'ffmpeg','-y','-i',str(video_only),'-i',str(audio),
    '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',str(final)
], check=True)

print(f'Final video: {final}')
