import json, os, re
from pathlib import Path

OUT = Path('output')
OUT.mkdir(exist_ok=True)

TEMPLATES = {
    'English + Swahili': {
        'verse1': 'Under the island moon, your hand is in mine,\nMoyo wangu, baby, your love is divine.',
        'chorus': 'Sweet island loving, come closer tonight,\nMapenzi ya kweli, everything feels right.\nSweet island loving, dancing by the sea,\nWewe na mimi, just you and me.',
        'verse2': 'Palm trees are moving while the warm wind calls,\nNakupenda sana, love has no walls.',
        'bridge': 'Hold me slowly, let the rhythm play,\nTupendane, until the break of day.'
    },
    'English': {
        'verse1': 'Under the island moon, your hand is in mine,\nYour love is shining and everything feels fine.',
        'chorus': 'Sweet island loving, come closer tonight,\nDancing by the ocean, everything feels right.\nSweet island loving, just you and me,\nLost in the rhythm beside the sea.',
        'verse2': 'Palm trees are moving while the warm wind calls,\nYour love is stronger than any walls.',
        'bridge': 'Hold me slowly, let the rhythm play,\nWe will keep dancing until the break of day.'
    }
}

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

title = os.getenv('SONG_TITLE', 'Sweet Island Loving')
theme = os.getenv('SONG_THEME', 'Romantic island love')
mood = os.getenv('SONG_MOOD', 'Romantic, warm, uplifting')
language = os.getenv('SONG_LANGUAGE', 'English + Swahili')
style = os.getenv('VIDEO_STYLE', 'African tropical island, cinematic, romantic, realistic')

base = TEMPLATES.get(language, TEMPLATES['English'])
lyrics = f'''{title}\n\n[Verse 1]\n{base['verse1']}\n\n[Chorus]\n{base['chorus']}\n\n[Verse 2]\n{base['verse2']}\n\n[Chorus]\n{base['chorus']}\n\n[Bridge]\n{base['bridge']}\n\n[Final Chorus]\n{base['chorus']}'''

prompts = [
    f'{style}, romantic African couple walking on a tropical beach at golden sunset, cinematic music video, joyful, natural skin, realistic photography',
    f'{style}, Afro-Reggae beach party with dancers, palm trees, warm sunset, cinematic music video frame, realistic',
    f'{style}, romantic couple beside turquoise ocean, gentle waves, African tropical island, cinematic, realistic',
    f'{style}, night beach with lanterns and dancing, warm atmosphere, Afro-Reggae music video, cinematic realistic',
    f'{style}, sunrise over tropical African coastline, couple dancing together, hopeful romantic mood, cinematic realistic',
    f'{style}, wide final shot of tropical beach, ocean and palm trees, joyful Afro-Reggae celebration, cinematic realistic'
]

data = {
    'title': title,
    'theme': theme,
    'mood': mood,
    'language': language,
    'video_style': style,
    'lyrics': lyrics,
    'music_prompt': f'Afro-Reggae, {mood}, warm bass guitar, offbeat reggae guitar, African percussion, melodic lead vocal, polished studio production, song about {theme}. No spoken intro.',
    'scene_prompts': prompts,
    'description': f'{title} — an original Afro-Reggae song about {theme}.\n\nAI-generated music and visuals created with open-source tools.\n\n#AfroReggae #AfricanMusic #Reggae #AIMusic',
    'tags': ['Afro-Reggae', 'Afrobeat', 'Reggae', 'African Music', 'AI Music', 'Tropical Music', 'Swahili Music']
}

(OUT / 'metadata.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
(OUT / 'lyrics.txt').write_text(lyrics, encoding='utf-8')
print(f'Created metadata for: {title}')
