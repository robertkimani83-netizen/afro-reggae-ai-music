import json, os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

OUT = Path('output')
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

client_id = os.environ['YOUTUBE_CLIENT_ID']
client_secret = os.environ['YOUTUBE_CLIENT_SECRET']
refresh_token = os.environ['YOUTUBE_REFRESH_TOKEN']

creds = Credentials(
    None,
    refresh_token=refresh_token,
    token_uri='https://oauth2.googleapis.com/token',
    client_id=client_id,
    client_secret=client_secret,
    scopes=SCOPES,
)
youtube = build('youtube', 'v3', credentials=creds)

with open(OUT / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

video = youtube.videos().insert(
    part='snippet,status',
    body={
        'snippet': {
            'title': meta['title'],
            'description': meta['description'],
            'tags': meta['tags'],
            'categoryId': '10'
        },
        'status': {
            'privacyStatus': os.getenv('YOUTUBE_PRIVACY', 'private'),
            'selfDeclaredMadeForKids': False
        }
    },
    media_body=MediaFileUpload(str(OUT / 'afro-reggae-music-video.mp4'), mimetype='video/mp4', resumable=True)
).execute()

video_id = video['id']
print(f'Uploaded YouTube video: https://www.youtube.com/watch?v={video_id}')

thumb = OUT / 'thumbnail.jpg'
youtube.thumbnails().set(
    videoId=video_id,
    media_body=MediaFileUpload(str(thumb), mimetype='image/jpeg')
).execute()

(OUT / 'youtube.json').write_text(json.dumps({'video_id': video_id, 'url': f'https://www.youtube.com/watch?v={video_id}'}, indent=2), encoding='utf-8')
print('Custom thumbnail uploaded.')
