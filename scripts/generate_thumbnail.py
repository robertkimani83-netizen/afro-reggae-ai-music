import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path('output')
with open(OUT / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

scene = OUT / 'scenes' / 'scene_01.jpg'
img = Image.open(scene).convert('RGB').resize((1280, 720))
overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)
draw.rectangle((0, 500, 1280, 720), fill=(0, 0, 0, 145))

font_candidates = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'
]
font_path = next((p for p in font_candidates if Path(p).exists()), None)
font = ImageFont.truetype(font_path, 72) if font_path else ImageFont.load_default()
small = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()

title = meta['title']
# Fit title to thumbnail width.
while draw.textbbox((0, 0), title, font=font)[2] > 1160 and font.size > 36:
    font = ImageFont.truetype(font_path, font.size - 4)

draw.text((60, 535), title, font=font, fill='white', stroke_width=3, stroke_fill='black')
draw.text((60, 630), 'AFRO-REGGAE • ORIGINAL AI MUSIC', font=small, fill='white', stroke_width=2, stroke_fill='black')

out = OUT / 'thumbnail.jpg'
Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB').save(out, quality=95, optimize=True)
print(f'Thumbnail: {out}')
