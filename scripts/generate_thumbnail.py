"""Generates the YouTube thumbnail for the finished song.

Sept 16 2026: rebuilt from a plain "darken the bottom third and print the
title in white" thumbnail into something that actually matches the style of
Robert's existing NEXT VIBE MUSIC thumbnails -- his channel logo in the
corner, a big bold display-font title, a genre tag, and a small "ORIGINAL
SONG" badge (worded that way rather than "AUDIO COVER" since these are
original AI compositions, not covers of existing songs -- Robert's own call
when this was built).

Assets this depends on (committed into the repo, not downloaded at runtime,
so a run never depends on an extra network call just for branding):
  - assets/next-vibe-logo.png -- Robert's channel logo, supplied by him as a
    square image with a solid black background, cut out to a transparent
    PNG once here in this same rebuild (flood-fill from the corners) rather
    than on every run.
  - assets/fonts/Anton-Regular.ttf -- free (OFL-licensed) bold condensed
    display font from Google Fonts, used for the big title text. The
    previous version used plain DejaVu Sans Bold, which doesn't have the
    same poster-style impact as the fonts used in Robert's existing
    thumbnails.
  - assets/fonts/Montserrat-Variable.ttf -- free (OFL-licensed) variable
    font from Google Fonts, used at its ExtraBold instance for the smaller
    badge/tag text.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path("output")
ASSETS = Path("assets")

with open(OUT / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

W, H = 1280, 720


def _cover_crop(img, w, h):
    """Resize+crop an image to exactly (w, h), filling the frame without
    distorting the aspect ratio (same "cover" behavior CSS background-size
    uses) -- the source scene photos aren't guaranteed to already be 16:9."""
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_h = h
        new_w = int(h * src_ratio)
    else:
        new_w = w
        new_h = int(w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _load_montserrat(size, weight=b"ExtraBold"):
    font = ImageFont.truetype(str(ASSETS / "fonts" / "Montserrat-Variable.ttf"), size)
    try:
        font.set_variation_by_name(weight)
    except Exception:  # noqa: BLE001 - cosmetic only, never fatal
        pass
    return font


def _gradient_pill(size, color1, color2, radius):
    """A rounded-rect filled with a horizontal linear gradient between two
    colors, returned as an RGBA image ready to paste -- gives the badge a
    bit of the same blue-to-magenta gradient look as the channel logo,
    instead of a flat color block."""
    w, h = size
    grad = Image.new("RGB", (w, 1))
    for x in range(w):
        t = x / max(1, w - 1)
        px = tuple(int(color1[i] + (color2[i] - color1[i]) * t) for i in range(3))
        grad.putpixel((x, 0), px)
    grad = grad.resize((w, h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def _fit_title_lines(draw, text, font_path, max_width, start_size, min_size, max_lines=2):
    """Finds the largest font size (down to min_size) that lets `text` wrap
    into at most max_lines lines of width <= max_width, and returns
    (font, lines)."""
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        words = text.split()
        lines, current = [], ""
        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= max_lines and all(draw.textbbox((0, 0), l, font=font)[2] <= max_width for l in lines):
            return font, lines
        size -= 4
    # Fall back to the smallest size even if it still overflows slightly --
    # better than crashing or shrinking to an unreadable size.
    font = ImageFont.truetype(font_path, min_size)
    return font, [text]


def _text_with_shadow(draw, xy, text, font, fill="white", shadow=(0, 0, 0, 180), offset=4, stroke_width=2, stroke_fill=(0, 0, 0, 255)):
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


# ---------------------------------------------------------------------------
# Background: the first generated scene photo, cover-cropped to 1280x720,
# with a bottom-heavy dark gradient so text stays legible over any photo.
# ---------------------------------------------------------------------------
scene_path = OUT / "scenes" / "scene_01.jpg"
if scene_path.exists():
    bg = _cover_crop(Image.open(scene_path).convert("RGB"), W, H)
else:
    # Extremely defensive fallback -- generate_scenes.py should always have
    # produced at least a gradient-card scene_01.jpg by this point, but a
    # thumbnail script crashing over a missing background would be a silly
    # way to lose an otherwise-successful run.
    bg = Image.new("RGB", (W, H), (20, 20, 30))

canvas = bg.convert("RGBA")

gradient = Image.new("L", (1, H), 0)
for y in range(H):
    # Gentle darkening from the top, much stronger across the bottom ~45%
    # where the title/tag sit -- mirrors the "photo fading into a dark bar"
    # look of Robert's existing thumbnails rather than a flat dark strip.
    t = y / H
    if t < 0.45:
        alpha = int(60 * (t / 0.45))
    else:
        alpha = int(60 + (215 - 60) * ((t - 0.45) / 0.55))
    gradient.putpixel((0, y), alpha)
gradient = gradient.resize((W, H))
shade = Image.new("RGBA", (W, H), (5, 5, 15, 0))
shade.putalpha(gradient)
canvas = Image.alpha_composite(canvas, shade)

draw = ImageDraw.Draw(canvas)

# ---------------------------------------------------------------------------
# Logo, top-left.
# ---------------------------------------------------------------------------
logo_path = ASSETS / "next-vibe-logo.png"
if logo_path.exists():
    logo_size = 132
    logo = Image.open(logo_path).convert("RGBA").resize((logo_size, logo_size), Image.LANCZOS)
    # A soft dark disc behind the logo keeps it readable against a bright
    # photo without needing to darken the whole top-left corner.
    pad = 14
    backing = Image.new("RGBA", (logo_size + pad * 2, logo_size + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(backing).ellipse((0, 0, backing.width, backing.height), fill=(0, 0, 0, 120))
    backing = backing.filter(ImageFilter.GaussianBlur(2))
    canvas.alpha_composite(backing, (28 - pad, 28 - pad))
    canvas.alpha_composite(logo, (28, 28))

# ---------------------------------------------------------------------------
# "ORIGINAL SONG" badge, top-right.
# ---------------------------------------------------------------------------
badge_text = "ORIGINAL SONG"
badge_font = _load_montserrat(28)
badge_w = draw.textbbox((0, 0), badge_text, font=badge_font)[2] + 56
badge_h = 52
badge = _gradient_pill((badge_w, badge_h), (34, 100, 230), (168, 60, 220), radius=badge_h // 2)
canvas.alpha_composite(badge, (W - badge_w - 28, 28))
bd = ImageDraw.Draw(canvas)
bd.text((W - badge_w - 28 + badge_w / 2, 28 + badge_h / 2), badge_text, font=badge_font, fill="white", anchor="mm")

# ---------------------------------------------------------------------------
# Title, big and bold, bottom-left, wrapped to at most 2 lines. Computed
# BEFORE the genre tag below, because the tag needs to sit just above
# however tall the title block ends up being -- a fixed offset here would
# make a 2-line title collide with the tag (found by testing with a
# deliberately long title locally before this shipped).
# ---------------------------------------------------------------------------
title = meta.get("title", "Untitled")
max_title_width = W - 120
anton_path = str(ASSETS / "fonts" / "Anton-Regular.ttf")
font, lines = _fit_title_lines(draw, title.upper(), anton_path, max_title_width, start_size=104, min_size=48, max_lines=2)
line_height = font.size * 1.05
title_total_h = line_height * len(lines)
title_y = H - 60 - title_total_h

# ---------------------------------------------------------------------------
# Genre tag, small pill sitting just above the title block.
# ---------------------------------------------------------------------------
tag_text = "AFRO-REGGAE  •  ORIGINAL AI MUSIC"
tag_font = _load_montserrat(24)
tag_w = draw.textbbox((0, 0), tag_text, font=tag_font)[2] + 48
tag_h = 44
tag_gap = 18
tag_y = title_y - tag_gap - tag_h
# Never let the tag climb into the logo/badge row at the very top, even for
# an extreme multi-line title -- clamp so it stays below y=110 no matter
# what the title block's height turns out to be.
tag_y = max(tag_y, 110)
draw.rounded_rectangle((60, tag_y, 60 + tag_w, tag_y + tag_h), radius=tag_h // 2, outline=(255, 255, 255, 200), width=2)
draw.text((60 + tag_w / 2, tag_y + tag_h / 2), tag_text, font=tag_font, fill="white", anchor="mm")

# ---------------------------------------------------------------------------
# Now draw the title itself, on top.
# ---------------------------------------------------------------------------
y = title_y
for line in lines:
    _text_with_shadow(draw, (60, y), line, font, fill="white", stroke_width=4, stroke_fill=(0, 0, 0, 255))
    y += line_height

out = OUT / "thumbnail.jpg"
canvas.convert("RGB").save(out, quality=95, optimize=True)
print(f"Thumbnail: {out}")
