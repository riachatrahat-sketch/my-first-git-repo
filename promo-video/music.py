"""Synthesize a subtle, uplifting corporate background bed (royalty-free, generated from scratch).

Soft pad + gentle plucked arpeggio + warm sub bass in D major (D - A - Bm - G), 96 BPM.
Usage: python3 music.py out.wav [duration_seconds]
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT

# MIDI notes: chord tones per bar (I - V - vi - IV)
PROGRESSION = [
    (50, [62, 66, 69, 74]),  # D
    (45, [61, 64, 69, 73]),  # A
    (47, [62, 66, 71, 74]),  # Bm
    (43, [62, 67, 71, 74]),  # G
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def pad_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    sig = np.zeros_like(t)
    for detune in (-0.12, 0.0, 0.12):
        f = freq * 2 ** (detune / 12)
        sig += np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    trem = 1 + 0.06 * np.sin(2 * np.pi * 0.25 * t)
    return sig * trem * env_adsr(len(t), 0.9, 1.2) / 3


def pluck(freq, dur=1.2):
    t = np.arange(int(dur * SR)) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) * np.exp(-t * 6)
    return sig * np.exp(-t * 3.2) * np.minimum(1, t / 0.004)


def bass(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * freq * t) + 0.15 * np.sin(4 * np.pi * freq * t)) * env_adsr(len(t), 0.02, 0.4) * np.exp(-t * 0.6)


def add(buf, sig, start):
    i = int(start * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def reverb(x, seconds=2.2, mix=0.28):
    rng = np.random.default_rng(7)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6, n))
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return (1 - mix) * x + mix * wet


def render(duration):
    n = int(duration * SR)
    pad, arp, low, hat = (np.zeros(n) for _ in range(4))
    rng = np.random.default_rng(3)
    bars = int(np.ceil(duration / BAR)) + 1
    arp_pattern = [0, 1, 2, 3, 2, 1, 2, 3]
    for b in range(bars):
        root, chord = PROGRESSION[b % 4]
        t0 = b * BAR
        for m in chord[:3]:
            add(pad, pad_voice(hz(m - 12), BAR + 1.0), t0)
        if b >= 1:  # arpeggio enters after the first bar
            for k, idx in enumerate(arp_pattern):
                add(arp, pluck(hz(chord[idx] + 12)) * (0.9 if k % 2 == 0 else 0.6), t0 + k * BEAT / 2)
        add(low, bass(hz(root - 12), BEAT * 2), t0)
        add(low, bass(hz(root - 12), BEAT * 2) * 0.7, t0 + 2 * BEAT)
        if b >= 2:  # very soft shaker on off-beats
            for k in range(4):
                noise = rng.standard_normal(int(0.06 * SR))
                noise = np.diff(noise, prepend=0) * np.exp(-np.linspace(0, 8, len(noise)))
                add(hat, noise, t0 + k * BEAT + BEAT / 2)
    mix = 0.55 * pad + 0.32 * arp + 0.45 * low + 0.05 * hat
    mix = reverb(mix)
    t = np.arange(n) / SR
    mix *= np.minimum(1, t / 1.5) * np.clip((duration - t) / 2.5, 0, 1)
    mix /= np.max(np.abs(mix)) + 1e-9
    stereo = np.stack([mix, np.roll(mix, int(0.012 * SR))], axis=1) * 0.89
    return stereo


def main():
    out = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 35.0
    data = (render(duration) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    main()
