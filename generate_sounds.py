"""
Sound Generator - Tạo các file WAV đơn giản cho DinoRacer
Chạy: python generate_sounds.py
"""
import wave
import struct
import math
import os


def write_wav(filename, samples, sample_rate=22050, channels=1, sampwidth=2):
    """Ghi list giá trị float [-1, 1] ra file WAV."""
    with wave.open(filename, 'w') as f:
        f.setnchannels(channels)
        f.setsampwidth(sampwidth)
        f.setframerate(sample_rate)
        max_val = (2 ** (sampwidth * 8 - 1)) - 1
        data = struct.pack(f'<{len(samples)}h',
                           *[int(s * max_val) for s in samples])
        f.writeframes(data)


def sine(freq, duration, rate=22050, amplitude=0.6):
    n = int(rate * duration)
    return [amplitude * math.sin(2 * math.pi * freq * i / rate) for i in range(n)]


def envelope(samples, attack=0.01, decay=0.0, sustain=1.0, release=0.1, rate=22050):
    """Áp dụng ADSR envelope đơn giản."""
    n = len(samples)
    a = int(attack * rate)
    r = int(release * rate)
    out = []
    for i, s in enumerate(samples):
        if i < a:
            gain = i / a
        elif i >= n - r:
            gain = (n - i) / r
        else:
            gain = sustain
        out.append(s * gain)
    return out


def mix(a, b):
    """Trộn 2 danh sách samples, pad chiều dài nếu cần."""
    n = max(len(a), len(b))
    result = []
    for i in range(n):
        va = a[i] if i < len(a) else 0.0
        vb = b[i] if i < len(b) else 0.0
        result.append(max(-1.0, min(1.0, va + vb)))
    return result


def generate_jump(rate=22050):
    """Âm thanh nhảy: sweep từ 200Hz lên 600Hz trong 0.2s."""
    duration = 0.18
    n = int(rate * duration)
    samples = []
    for i in range(n):
        t = i / rate
        freq = 200 + (600 - 200) * (t / duration) ** 0.5
        samples.append(0.55 * math.sin(2 * math.pi * freq * t))
    return envelope(samples, attack=0.005, release=0.06, rate=rate)


def generate_gameover(rate=22050):
    """Game over: nốt giảm dần + reverb đơn giản."""
    freqs  = [440, 370, 330, 220]
    durs   = [0.15, 0.15, 0.15, 0.35]
    result = []
    for freq, dur in zip(freqs, durs):
        seg = sine(freq, dur, rate, amplitude=0.55)
        seg = envelope(seg, attack=0.01, release=0.08, rate=rate)
        result.extend(seg)
    return result


def generate_score(rate=22050):
    """Score sound: 2 nốt ngắn vui tươi."""
    s1 = sine(523, 0.07, rate, 0.5)   # C5
    s2 = sine(659, 0.07, rate, 0.5)   # E5
    s1 = envelope(s1, attack=0.005, release=0.03, rate=rate)
    s2 = envelope(s2, attack=0.005, release=0.03, rate=rate)
    gap = [0.0] * int(rate * 0.02)
    return s1 + gap + s2


def generate_duck(rate=22050):
    """Âm thanh cúi: tần số thấp, ngắn."""
    duration = 0.12
    n = int(rate * duration)
    samples = []
    for i in range(n):
        t = i / rate
        freq = 150 + 50 * math.sin(2 * math.pi * 5 * t)
        samples.append(0.4 * math.sin(2 * math.pi * freq * t))
    return envelope(samples, attack=0.005, release=0.05, rate=rate)


def generate_bird(rate=22050):
    """Âm thanh chim: tiếng kêu chirp."""
    duration = 0.25
    n = int(rate * duration)
    samples = []
    for i in range(n):
        t = i / rate
        # Chirping pattern
        freq = 1200 + 800 * math.sin(2 * math.pi * 15 * t)
        samples.append(0.25 * math.sin(2 * math.pi * freq * t))
    return envelope(samples, attack=0.01, release=0.08, rate=rate)


def generate_menu_hover(rate=22050):
    """Âm thanh hover menu: nhẹ, ngắn."""
    duration = 0.05
    n = int(rate * duration)
    samples = sine(600, duration, rate, 0.3)
    return envelope(samples, attack=0.005, release=0.02, rate=rate)


def generate_menu_click(rate=22050):
    """Âm thanh click menu."""
    duration = 0.08
    n = int(rate * duration)
    samples = sine(800, duration, rate, 0.4)
    return envelope(samples, attack=0.005, release=0.03, rate=rate)


def generate_pause_sound(rate=22050):
    """Âm thanh pause."""
    duration = 0.12
    n = int(rate * duration)
    samples = sine(440, duration, rate, 0.4)
    return envelope(samples, attack=0.005, release=0.05, rate=rate)


def generate_achievement(rate=22050):
    """Âm thanh achievement: arpeggio vui vẻ."""
    duration = 0.5
    n = int(rate * duration)
    result = []
    # C5, E5, G5, C6 arpeggio
    freqs = [523, 659, 784, 1047]
    for freq in freqs:
        seg = sine(freq, 0.12, rate, 0.35)
        seg = envelope(seg, attack=0.01, release=0.08, rate=rate)
        result.extend(seg)
        result.extend([0.0] * int(rate * 0.02))
    return result[:n]


def generate_combo(rate=22050):
    """Âm thanh combo."""
    duration = 0.15
    n = int(rate * duration)
    samples = sine(700, duration, rate, 0.35)
    return envelope(samples, attack=0.005, release=0.06, rate=rate)


def generate_hit(rate=22050):
    """Âm thanh va chạm: tạp âm + low thump."""
    duration = 0.15
    n = int(rate * duration)
    import random
    samples = []
    for i in range(n):
        t = i / rate
        # Low thump
        thump = 0.4 * math.sin(2 * math.pi * 100 * t)
        # Noise
        noise = 0.2 * (random.random() * 2 - 1)
        samples.append(thump + noise)
    return envelope(samples, attack=0.005, release=0.08, rate=rate)


def main():
    sounds_dir = os.path.join(os.path.dirname(__file__), 'assets', 'sounds')
    os.makedirs(sounds_dir, exist_ok=True)

    files = {
        'jump.wav':     generate_jump,
        'gameover.wav': generate_gameover,
        'score.wav':    generate_score,
        'duck.wav':     generate_duck,
        'bird.wav':     generate_bird,
        'menu_hover.wav': generate_menu_hover,
        'menu_click.wav': generate_menu_click,
        'pause.wav':    generate_pause_sound,
        'achievement.wav': generate_achievement,
        'combo.wav':   generate_combo,
        'hit.wav':      generate_hit,
    }

    for fname, gen_fn in files.items():
        path = os.path.join(sounds_dir, fname)
        samples = gen_fn()
        write_wav(path, samples)
        print(f"✅ Tạo {fname} ({len(samples)} samples, {len(samples)/22050:.2f}s)")

    for fname, gen_fn in files.items():
        path = os.path.join(sounds_dir, fname)
        samples = gen_fn()
        write_wav(path, samples)
        print(f"✅ Tạo {fname} ({len(samples)} samples, {len(samples)/22050:.2f}s)")

    print(f"\nĐã lưu vào: {sounds_dir}")


if __name__ == '__main__':
    main()
