# Fiverr Reviews: LinkedIn Promo Video

**Final video:** [`output/fiverr-reviews-linkedin.mp4`](output/fiverr-reviews-linkedin.mp4)
1920×1080 (16:9), 30 fps, H.264 High + AAC 192 kbps, 35 s, loudness-normalised to −14 LUFS.

## Timeline (synced to the voice-over)

| Time | Scene | Narration |
|---|---|---|
| 0.0 – 5.9 | Headline: *5-Star Reviews. Real Client Satisfaction.* with stars and client countries | "Every five-star review tells the story of trust, quality and client satisfaction." |
| 5.9 – 26.1 | The 5 original review screenshots, one at a time, with a slow push-in and a progress bar | "I'm grateful to my Fiverr clients… My goal is simple… Your satisfaction is my biggest motivation…" |
| 26.1 – 30.45 | *Thank You for Your Trust!* | "Thank you to all my amazing clients for your trust and support." |
| 30.45 – 35.0 | *Looking for a Reliable Designer? Let's Work Together!* + name card | "Looking for a reliable designer? Let's work together." |

The narration is 33.8 s, so the video runs 35 s instead of 30 s. That keeps every scene on its own line of narration without cutting the voice.

## Authenticity
- `assets/reviews/review-01…05.png` are the uploaded screenshots, byte-for-byte. The renderer only scales and positions them. It never crops, retouches, or retypes them.
- The text outside the screenshots does not quote or paraphrase any review. The country list (Australia, Poland, Canada, Lithuania, South Africa) comes straight from the screenshots.

## Re-rendering

Requires Python 3 with Pillow and NumPy, plus ffmpeg.

```bash
python3 render.py                  # full render (about 2 min)
python3 render.py --stills 3 12 28 # quick PNG previews of single moments
```

To change text, colours, the name card (`SELLER_NAME` / `SELLER_LINE`) or scene timings, edit the constants at the top of `render.py`.
To swap the music, replace the `music.py` call in `build_audio()` with your own track.

## Files
- `render.py`: draws the scenes, mixes the audio and encodes the MP4
- `music.py`: generates the background music from scratch (royalty-free, no samples)
- `assets/voiceover.mp3`: the ElevenLabs narration
- `assets/fonts/`: Inter (SIL Open Font License)
