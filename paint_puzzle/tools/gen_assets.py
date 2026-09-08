# -*- coding: utf-8 -*-
"""用标准库 wave + 数学函数合成游戏音效,输出到 ../snd/。

用法: python tools/gen_assets.py
"""
import math
import os
import random
import struct
import wave

SAMPLE_RATE = 44100
OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "snd"))


def write_wav(name, samples):
    path = os.path.join(OUT_DIR, name)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples
        )
        f.writeframes(frames)
    print("生成", path)


def env(t, dur, attack=0.005, release=0.1):
    """简单的攻击-衰减包络。"""
    if t < attack:
        return t / attack
    if t > dur - release:
        return max(0.0, (dur - t) / release)
    return 1.0


def tone(freq, dur, vol=0.6, sweep=0.0, timbre=0.5):
    """单音;freq 终值 = freq*(1+sweep),timbre 控制谐波占比。"""
    n = int(SAMPLE_RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        f = freq * (1 + sweep * t / dur)
        phase += 2 * math.pi * f / SAMPLE_RATE
        s = math.sin(phase) + timbre * math.sin(2 * phase) + 0.3 * timbre * math.sin(3 * phase)
        out.append(vol * env(t, dur) * s / (1 + 1.3 * timbre))
    return out


def silence(dur):
    return [0.0] * int(SAMPLE_RATE * dur)


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for tr in tracks:
        for i, s in enumerate(tr):
            out[i] += s
    peak = max(1e-6, max(abs(s) for s in out))
    if peak > 0.95:
        out = [s * 0.95 / peak for s in out]
    return out


def concat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def gen_click():
    # 短促"嗒"声:高频短音 + 快速衰减
    write_wav("click.wav", tone(1600, 0.06, vol=0.5, sweep=-0.5, timbre=0.2))


def gen_paint():
    # 染色"刷"声:向下扫频 + 轻微噪声
    body = tone(900, 0.22, vol=0.45, sweep=-0.6, timbre=0.3)
    noise = [(random.random() * 2 - 1) * 0.12 * env(i / SAMPLE_RATE, 0.22, 0.01, 0.12)
             for i in range(int(SAMPLE_RATE * 0.22))]
    write_wav("paint.wav", mix(body, noise))


def gen_win():
    # 胜利:上行琶音 C-E-G-C
    notes = [523.25, 659.25, 783.99, 1046.5]
    parts = []
    for i, f in enumerate(notes):
        dur = 0.14 if i < 3 else 0.45
        parts.append(tone(f, dur, vol=0.55, timbre=0.4))
    write_wav("win.wav", concat(*parts))


def gen_fail():
    # 失败:两个下行低音
    write_wav("fail.wav", concat(
        tone(330, 0.18, vol=0.5, timbre=0.5),
        silence(0.03),
        tone(220, 0.35, vol=0.55, sweep=-0.15, timbre=0.5),
    ))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_click()
    gen_paint()
    gen_win()
    gen_fail()
    print("全部音效生成完毕。")


if __name__ == "__main__":
    main()
