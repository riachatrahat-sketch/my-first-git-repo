"""Render the LinkedIn promo video for Rahat's Fiverr client reviews.

Frames are drawn with Pillow and piped to ffmpeg; the narration is the ElevenLabs
voice-over, mixed with a generated background bed (music.py) that ducks under the voice.

    python3 render.py                    # full render -> output/fiverr-reviews-linkedin.mp4
    python3 render.py --stills 3 12 28   # PNG previews of single frames -> output/stills/

The review screenshots are only ever scaled and positioned, never edited or cropped.
"""
import argparse
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT_DIR = os.path.join(HERE, "output")
OUTPUT = os.path.join(OUT_DIR, "fiverr-reviews-linkedin.mp4")

W, H, FPS = 1920, 1080, 30
DURATION = 35.0  # narration is 33.8 s; the end card holds briefly after the last word

# ---- Brand -------------------------------------------------------------------------------
BG_TOP = (9, 14, 28)
BG_BOTTOM = (16, 24, 44)
WHITE = (255, 255, 255)
MUTED = (160, 172, 196)
GOLD = (242, 196, 109)
GLOW_A = (232, 180, 90)
GLOW_B = (64, 120, 255)

SELLER_NAME = "Rahat"
SELLER_LINE = "UX Design on Fiverr"
CLIENT_COUNTRIES = "Australia  ·  Poland  ·  Canada  ·  Lithuania  ·  South Africa"

# ---- Timeline (seconds), aligned to the narration's word timings -----------------------------
# 0.0  "Every five-star review tells the story of trust, quality and client satisfaction" (ends 5.5)
# 6.0  "I'm grateful to my Fiverr clients for trusting my work and sharing ..."
# 12.0 "My goal is simple: to deliver high-quality designs, pay attention to every detail ..."
# 20.3 "Your satisfaction is my biggest motivation to keep improving ..." (ends 25.8)
# 26.3 "Thank you to all my amazing clients for your trust and support" (ends 30.2)
# 30.75 "Looking for a reliable designer?"  32.7 "Let's work together" (ends 33.3)
INTRO_END = 5.9
REVIEW_BOUNDS = [5.9, 9.6, 14.0, 17.9, 22.2, 26.1]  # five slots; longer texts get longer slots
THANKS_END = 30.45
LETS_WORK_AT = 32.4
END_CARD_AT = 33.2

REVIEWS = [os.path.join(ASSETS, "reviews", f"review-0{i}.png") for i in range(1, 6)]


def font(name, size):
    return ImageFont.truetype(os.path.join(ASSETS, "fonts", name), size)


# ---- Easing ----------------------------------------------------------------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def progress(t, start, end):
    return clamp((t - start) / (end - start))


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return x * x * (3 - 2 * x)


def fade_window(t, start, end, fade_in=0.6, fade_out=0.45):
    """Opacity 0..1 for an element visible in [start, end] with eased edges."""
    return ease_out(progress(t, start, start + fade_in)) * (1 - ease_in_out(progress(t, end - fade_out, end)))


# ---- Sprites -----------------------------------------------------------------------------------
def text_sprite(text, fnt, color, tracking=0):
    if tracking:
        widths = [fnt.getlength(c) for c in text]
        width = int(sum(widths) + tracking * (len(text) - 1)) + 4
    else:
        width = int(fnt.getlength(text)) + 4
    ascent, descent = fnt.getmetrics()
    img = Image.new("RGBA", (width, ascent + descent + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tracking:
        x = 0
        for c, cw in zip(text, widths):
            d.text((x, 0), c, font=fnt, fill=color)
            x += cw + tracking
    else:
        d.text((0, 0), text, font=fnt, fill=color)
    return img


def star_sprite(size, color):
    ss = 4
    img = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    c, r_out = size * ss / 2, size * ss / 2
    r_in = r_out * 0.45
    pts = []
    for k in range(10):
        r = r_out if k % 2 == 0 else r_in
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((c + r * math.cos(a), c + r * math.sin(a) + size * ss * 0.04))
    ImageDraw.Draw(img).polygon(pts, fill=color)
    return img.resize((size, size), Image.LANCZOS)


def glow_sprite(radius, color, strength):
    size = radius * 2
    img = Image.new("L", (size, size), 0)
    ImageDraw.Draw(img).ellipse((radius * 0.75, radius * 0.75, radius * 1.25, radius * 1.25), fill=int(255 * strength))
    img = img.filter(ImageFilter.GaussianBlur(radius * 0.24))
    sprite = Image.new("RGBA", (size, size), color + (0,))
    sprite.putalpha(img)
    return sprite


def with_alpha(img, alpha):
    if alpha >= 0.999:
        return img
    a = img.getchannel("A").point(lambda v: int(v * alpha))
    out = img.copy()
    out.putalpha(a)
    return out


def blit(frame, sprite, cx, cy, alpha=1.0, scale=1.0, anchor="center"):
    """Composite sprite onto frame; (cx, cy) is its center (or left-middle with anchor='left')."""
    if alpha <= 0.003:
        return
    if abs(scale - 1) > 1e-3:
        sprite = sprite.resize((max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))), Image.BICUBIC)
    sprite = with_alpha(sprite, alpha)
    x = cx - sprite.width / 2 if anchor == "center" else cx
    y = cy - sprite.height / 2
    frame.alpha_composite(sprite, (round(x), round(y)))


# ---- Static layers -------------------------------------------------------------------------------
class Assets:
    def __init__(self):
        grad = Image.new("RGB", (1, H))
        for y in range(H):
            k = y / (H - 1)
            grad.putpixel((0, y), tuple(round(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * k) for i in range(3)))
        self.background = grad.resize((W, H)).convert("RGBA")
        vignette = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vignette).ellipse((-W * 0.2, -H * 0.35, W * 1.2, H * 1.35), fill=255)
        vignette = vignette.filter(ImageFilter.GaussianBlur(160))
        self.vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.vignette.putalpha(vignette.point(lambda v: int((255 - v) * 0.55)))
        self.glow_a = glow_sprite(620, GLOW_A, 0.14)
        self.glow_b = glow_sprite(700, GLOW_B, 0.26)
        # Static dither so the dark gradients do not band after H.264 compression
        self.dither = np.random.default_rng(1).normal(0, 1.2, (H, W, 1)).astype(np.float32)

        f_display_bold = lambda s: font("InterDisplay-Bold.otf", s)
        self.eyebrow = text_sprite("CLIENT TESTIMONIALS", font("Inter-SemiBold.otf", 26), GOLD, tracking=7)
        self.headline_1 = text_sprite("5-Star Reviews.", f_display_bold(118), WHITE)
        self.headline_2 = text_sprite("Real Client Satisfaction.", f_display_bold(118), GOLD)
        self.countries_label = text_sprite("Happy clients from", font("Inter-Regular.otf", 28), MUTED)
        self.countries = text_sprite(CLIENT_COUNTRIES, font("Inter-Medium.otf", 30), WHITE)
        self.star_big = star_sprite(54, GOLD)
        self.star_small = star_sprite(26, GOLD)

        self.header_label = text_sprite("Verified Fiverr Reviews", font("Inter-SemiBold.otf", 30), WHITE)
        counter_font = font("Inter-Medium.otf", 28)
        self.counters = [text_sprite(f"0{i + 1}  /  0{len(REVIEWS)}", counter_font, MUTED) for i in range(len(REVIEWS))]
        self.cards = [self._card(p) for p in REVIEWS]

        self.thanks = text_sprite("Thank You for Your Trust!", f_display_bold(108), WHITE)
        self.thanks_sub = text_sprite("Grateful to every client who shared their experience.", font("Inter-Regular.otf", 34), MUTED)
        self.cta_q = text_sprite("Looking for a Reliable Designer?", font("InterDisplay-SemiBold.otf", 84), WHITE)
        self.cta_a = text_sprite("Let's Work Together!", f_display_bold(118), GOLD)
        self.pill = self._pill()

    def _card(self, path):
        """Original screenshot on a white rounded panel with a soft shadow. Screenshot pixels untouched."""
        shot = Image.open(path).convert("RGBA")
        max_w, max_h = 1660, 640
        scale = min(max_w / shot.width, max_h / shot.height)
        shot = shot.resize((round(shot.width * scale), round(shot.height * scale)), Image.LANCZOS)
        pad, radius, blur = 26, 30, 40
        pw, ph = shot.width + pad * 2, shot.height + pad * 2
        margin = blur * 3
        card = Image.new("RGBA", (pw + margin * 2, ph + margin * 2), (0, 0, 0, 0))
        shadow = Image.new("L", card.size, 0)
        ImageDraw.Draw(shadow).rounded_rectangle((margin, margin + 24, margin + pw, margin + ph + 24), radius, fill=150)
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
        card.paste((0, 0, 0, 255), (0, 0), shadow)
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius, fill=255)
        panel = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
        panel.alpha_composite(shot, (pad, pad))
        card.paste(panel, (margin, margin), mask)
        return card

    def _pill(self):
        name = text_sprite(SELLER_NAME, font("Inter-SemiBold.otf", 34), WHITE)
        dot = text_sprite("·", font("Inter-SemiBold.otf", 34), GOLD)
        line = text_sprite(SELLER_LINE, font("Inter-Medium.otf", 34), MUTED)
        star = star_sprite(28, GOLD)
        gap = 18
        inner_w = star.width + gap + name.width + gap + dot.width + gap + line.width
        pw, ph = inner_w + 80, 84
        pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(pill)
        d.rounded_rectangle((0, 0, pw - 1, ph - 1), ph // 2, fill=(255, 255, 255, 14), outline=GOLD + (200,), width=2)
        x = 40
        for spr in (star, name, dot, line):
            pill.alpha_composite(spr, (x, (ph - spr.height) // 2))
            x += spr.width + gap
        return pill


# ---- Scenes ----------------------------------------------------------------------------------------
def draw_background(frame, a, t):
    frame.alpha_composite(a.background)
    ax = 1450 + 120 * math.sin(t * 0.18)
    ay = 180 + 60 * math.cos(t * 0.23)
    bx = 360 + 140 * math.cos(t * 0.15)
    by = 930 + 70 * math.sin(t * 0.21)
    blit(frame, a.glow_a, ax, ay)
    blit(frame, a.glow_b, bx, by)
    frame.alpha_composite(a.vignette)


def draw_stars(frame, sprite, cx, cy, spacing, t, start, stagger=0.1, alpha=1.0):
    n = 5
    for k in range(n):
        p = ease_out(progress(t, start + k * stagger, start + k * stagger + 0.45))
        x = cx + (k - (n - 1) / 2) * spacing
        blit(frame, sprite, x, cy, alpha * p, 0.6 + 0.4 * p)


def draw_intro(frame, a, t):
    if t > INTRO_END:
        return
    out = ease_in_out(progress(t, INTRO_END - 0.5, INTRO_END))
    fade, lift = 1 - out, -24 * out
    cx = W / 2
    blit(frame, a.eyebrow, cx, 300 + lift, fade * ease_out(progress(t, 0.1, 0.7)))
    draw_stars(frame, a.star_big, cx, 378 + lift, 72, t, 0.25, alpha=fade)
    for sprite, y, start in ((a.headline_1, 498, 0.45), (a.headline_2, 628, 0.95)):
        p = ease_out(progress(t, start, start + 0.8))
        blit(frame, sprite, cx, y + 36 * (1 - p) + lift, fade * p)
    line_p = ease_out(progress(t, 1.8, 2.6))
    if line_p > 0:
        half = 130 * line_p
        ImageDraw.Draw(frame).rounded_rectangle((cx - half, 722 + lift, cx + half, 726 + lift), 2, fill=GOLD + (int(255 * fade),))
    p = ease_out(progress(t, 2.4, 3.2))
    blit(frame, a.countries_label, cx, 790 + 14 * (1 - p) + lift, fade * p)
    blit(frame, a.countries, cx, 840 + 14 * (1 - p) + lift, fade * p)


def draw_reviews(frame, a, t):
    first, last = REVIEW_BOUNDS[0], REVIEW_BOUNDS[-1]
    if t < first - 0.2 or t > last:
        return
    section = fade_window(t, first - 0.1, last, fade_in=0.5, fade_out=0.4)

    # Header: stars + label on the left, counter on the right
    draw_stars(frame, a.star_small, 120 + 2 * 32, 108, 32, t, first - 0.1, stagger=0.06, alpha=section)
    blit(frame, a.header_label, 120 + 5 * 32 + 14, 110, section, anchor="left")
    idx = max(0, min(len(REVIEWS) - 1, next((i for i in range(len(REVIEWS)) if t < REVIEW_BOUNDS[i + 1]), len(REVIEWS) - 1)))
    counter = a.counters[idx]
    blit(frame, counter, W - 120 - counter.width, 110, section, anchor="left")
    ImageDraw.Draw(frame).line((120, 160, W - 120, 160), fill=(255, 255, 255, int(28 * section)), width=1)

    # Cards: enter (slide up + fade), slow push-in, exit (fade + lift), slight overlap for a crossfade
    for i, card in enumerate(a.cards):
        start, end = REVIEW_BOUNDS[i], REVIEW_BOUNDS[i + 1]
        if t < start - 0.2 or t > end + 0.05:
            continue
        enter = ease_out(progress(t, start - 0.2, start + 0.45))
        leave = ease_in_out(progress(t, end - 0.45, end))
        zoom = 1.0 + 0.045 * ease_in_out(progress(t, start - 0.2, end))
        y = 570 + 46 * (1 - enter) - 30 * leave
        blit(frame, card, W / 2, y, enter * (1 - leave), 0.97 + 0.03 * enter + (zoom - 1))

    # Progress indicator
    d = ImageDraw.Draw(frame)
    seg_w, gap, y = 64, 14, 1000
    total = len(REVIEWS) * seg_w + (len(REVIEWS) - 1) * gap
    x0 = W / 2 - total / 2
    for i in range(len(REVIEWS)):
        x = x0 + i * (seg_w + gap)
        d.rounded_rectangle((x, y, x + seg_w, y + 5), 3, fill=(255, 255, 255, int(40 * section)))
        fill = progress(t, REVIEW_BOUNDS[i], REVIEW_BOUNDS[i + 1])
        if fill > 0:
            d.rounded_rectangle((x, y, x + max(5, seg_w * fill), y + 5), 3, fill=GOLD + (int(255 * section),))


def draw_closing(frame, a, t):
    start = REVIEW_BOUNDS[-1]
    if t < start:
        return
    cx = W / 2
    # "Thank You for Your Trust!"
    if t < THANKS_END:
        out = ease_in_out(progress(t, THANKS_END - 0.45, THANKS_END))
        fade, lift = 1 - out, -24 * out
        draw_stars(frame, a.star_big, cx, 400 + lift, 72, t, start + 0.1, alpha=fade)
        p = ease_out(progress(t, start + 0.25, start + 1.05))
        blit(frame, a.thanks, cx, 530 + 36 * (1 - p) + lift, fade * p)
        p = ease_out(progress(t, start + 0.9, start + 1.6))
        blit(frame, a.thanks_sub, cx, 640 + 16 * (1 - p) + lift, fade * p)
        return
    # "Looking for a Reliable Designer? / Let's Work Together!" + end card
    p = ease_out(progress(t, THANKS_END + 0.05, THANKS_END + 0.85))
    blit(frame, a.cta_q, cx, 400 + 30 * (1 - p), p)
    p = ease_out(progress(t, LETS_WORK_AT, LETS_WORK_AT + 0.7))
    blit(frame, a.cta_a, cx, 528 + 30 * (1 - p), p, 0.96 + 0.04 * p)
    p = ease_out(progress(t, END_CARD_AT, END_CARD_AT + 0.7))
    if p > 0:
        half = 130 * p
        ImageDraw.Draw(frame).rounded_rectangle((cx - half, 622, cx + half, 626), 2, fill=GOLD + (int(255 * p),))
    blit(frame, a.pill, cx, 724 + 20 * (1 - p), p)


def render_frame(a, t):
    frame = Image.new("RGBA", (W, H))
    draw_background(frame, a, t)
    draw_intro(frame, a, t)
    draw_reviews(frame, a, t)
    draw_closing(frame, a, t)
    rgb = np.asarray(frame.convert("RGB"), dtype=np.float32) + a.dither
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


# ---- Output ------------------------------------------------------------------------------------------
def build_audio(tmp_dir):
    music = os.path.join(tmp_dir, "music.wav")
    subprocess.run([sys.executable, os.path.join(HERE, "music.py"), music, str(DURATION)], check=True)
    return music


def render_video():
    os.makedirs(OUT_DIR, exist_ok=True)
    music = build_audio(OUT_DIR)
    voice = os.path.join(ASSETS, "voiceover.mp3")
    # Voice: gentle cleanup + compression. Music: low bed, ducked further whenever the voice speaks.
    audio_filter = (
        "[1:a]aresample=48000,highpass=f=70,acompressor=threshold=0.125:ratio=2.5:attack=10:release=200,"
        "pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"
        "[2:a]aresample=48000,volume=0.11[m];"
        "[m][vsc]sidechaincompress=threshold=0.02:ratio=5:attack=40:release=600[mduck];"
        "[v][mduck]amix=inputs=2:duration=longest:normalize=0,apad,"
        "loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-stats",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", voice, "-i", music,
        "-filter_complex", audio_filter, "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", str(DURATION), "-movflags", "+faststart", OUTPUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    a = Assets()
    total = int(DURATION * FPS)
    for n in range(total):
        proc.stdin.write(render_frame(a, n / FPS).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    os.remove(music)
    print(f"\nWrote {OUTPUT}")


def render_stills(times):
    a = Assets()
    still_dir = os.path.join(OUT_DIR, "stills")
    os.makedirs(still_dir, exist_ok=True)
    for t in times:
        path = os.path.join(still_dir, f"t{t:05.2f}.png")
        render_frame(a, t).save(path)
        print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stills", nargs="*", type=float, help="render preview PNGs at these times instead of the video")
    args = parser.parse_args()
    if args.stills:
        render_stills(args.stills)
    else:
        render_video()
