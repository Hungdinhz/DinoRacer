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


def main():
    sounds_dir = os.path.join(os.path.dirname(__file__), 'assets', 'sounds')
    os.makedirs(sounds_dir, exist_ok=True)

    files = {
        'jump.wav':     generate_jump,
        'gameover.wav': generate_gameover,
        'score.wav':    generate_score,
    }

    for fname, gen_fn in files.items():
        path = os.path.join(sounds_dir, fname)
        samples = gen_fn()
        write_wav(path, samples)
        print(f"✅ Tạo {fname} ({len(samples)} samples, {len(samples)/22050:.2f}s)")

    print(f"\nĐã lưu vào: {sounds_dir}")


if __name__ == '__main__':
    main()
