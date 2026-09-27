#!/usr/bin/env python3
import json
import math
import random
import shutil
import subprocess
import urllib.request
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content/daily_premium.json"
OUT = ROOT / "media/daily-premium"
TMP = ROOT / ".voiceover_tmp"

def probe_duration(path: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True
    )
    return float(p.stdout.strip())

def atempo_chain(rate: float) -> str:
    if rate <= 1.0001:
        return "anull"
    parts = []
    while rate > 2.0:
        parts.append("atempo=2.0")
        rate /= 2.0
    if rate < 0.5:
        while rate < 0.5:
            parts.append("atempo=0.5")
            rate /= 0.5
    if abs(rate - 1.0) > 0.0001:
        parts.append(f"atempo={rate:.5f}")
    return ",".join(parts) if parts else "anull"

def synth_sfx_track(reel: dict, duration: float, path: Path, sr: int = 48000):
    n = max(1, int((duration + 0.1) * sr))
    buf = array("f", [0.0]) * n

    def add_sample(i, v):
        if 0 <= i < n:
            buf[i] += v

    def sine(start, dur, freq0, amp=0.5, freq1=None, attack=0.005, decay=True):
        start_i = int(start * sr)
        count = max(1, int(dur * sr))
        phase = 0.0
        for j in range(count):
            t = j / sr
            x = j / max(1, count - 1)
            freq = freq0 if freq1 is None else freq0 + (freq1 - freq0) * x
            phase += 2 * math.pi * freq / sr
            a = min(1.0, t / max(attack, 1e-4))
            if decay:
                a *= (1.0 - x) ** 1.6
            add_sample(start_i + j, math.sin(phase) * amp * a)

    def noise(start, dur, amp=0.25, rise=False):
        start_i = int(start * sr)
        count = max(1, int(dur * sr))
        last = 0.0
        for j in range(count):
            x = j / max(1, count - 1)
            raw = random.uniform(-1, 1)
            # mild low-pass makes it less harsh
            last = last * 0.76 + raw * 0.24
            env = (x ** 1.5) if rise else ((1.0 - x) ** 1.7)
            add_sample(start_i + j, last * amp * env)

    def add_event(ev):
        kind = ev.get("type", "click")
        t = float(ev.get("at", 0))
        g = float(ev.get("gain", 1.0))
        if kind == "notification":
            sine(t, 0.16, 880, 0.42*g)
            sine(t + 0.12, 0.24, 1320, 0.36*g)
        elif kind == "bass_hit":
            sine(t, 0.42, 82, 0.85*g, 48, attack=0.001)
            noise(t, 0.12, 0.16*g)
        elif kind == "whoosh":
            noise(t, 0.38, 0.34*g, rise=True)
            sine(t + 0.25, 0.16, 420, 0.12*g, 760)
        elif kind == "record_scratch":
            noise(t, 0.28, 0.42*g)
            sine(t, 0.25, 1100, 0.14*g, 180)
        elif kind == "stamp":
            noise(t, 0.08, 0.44*g)
            sine(t, 0.20, 95, 0.60*g, 58, attack=0.001)
        elif kind == "cash":
            sine(t, 0.13, 1047, 0.32*g)
            sine(t + 0.10, 0.15, 1319, 0.30*g)
            sine(t + 0.22, 0.25, 1568, 0.26*g)
        elif kind == "error":
            sine(t, 0.18, 440, 0.34*g, 300)
            sine(t + 0.16, 0.22, 300, 0.28*g, 190)
        else:
            noise(t, 0.045, 0.28*g)
            sine(t, 0.06, 900, 0.14*g)

    for ev in reel.get("sfx", []):
        add_event(ev)

    pcm = array("h")
    for v in buf:
        v = max(-0.98, min(0.98, v))
        pcm.append(int(v * 32767))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    TMP.mkdir(parents=True, exist_ok=True)

    for reel in data.get("reels", []):
        vo = reel.get("voiceover") or {}
        url = vo.get("url")
        if not url:
            print(f"skip {reel['id']}: no voiceover url")
            continue

        video = OUT / f"{reel['id']}.mp4"
        if not video.exists():
            raise FileNotFoundError(video)

        voice = TMP / f"{reel['id']}.mp3"
        sfx = TMP / f"{reel['id']}-sfx.wav"
        mixed = TMP / f"{reel['id']}-mixed.mp4"
        urllib.request.urlretrieve(url, voice)

        video_dur = probe_duration(video)
        voice_dur = probe_duration(voice)
        target = max(0.5, video_dur - 0.12)
        speed = max(1.0, voice_dur / target)
        tempo = atempo_chain(speed)
        synth_sfx_track(reel, video_dur, sfx)

        # Voice-first social mix:
        # - bed is deliberately low
        # - voice gets presence + compression
        # - bed ducks under voice
        # - final whole mix is normalized to a strong short-form target
        filt = (
            f"[0:a]volume=0.040[bed];"
            f"[1:a]{tempo},highpass=f=70,"
            f"equalizer=f=3200:t=q:w=1.2:g=2.6,"
            f"acompressor=threshold=-20dB:ratio=3.5:attack=4:release=75,"
            f"volume=2.6,adelay=25|25[vo0];"
            f"[vo0]asplit=2[side][mix];"
            f"[bed][side]sidechaincompress=threshold=0.02:ratio=10:attack=3:release=160[ducked];"
            f"[2:a]volume=1.15[sfx];"
            f"[ducked][mix][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
            f"loudnorm=I=-13:TP=-1:LRA=5,alimiter=limit=0.98[a]"
        )

        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(voice),
            "-i", str(sfx),
            "-filter_complex", filt,
            "-map", "0:v:0",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-ar", "48000",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(mixed)
        ], check=True)

        shutil.move(str(mixed), str(video))
        print(
            f"voiceover {reel['id']}: video={video_dur:.2f}s "
            f"voice={voice_dur:.2f}s tempo={speed:.3f}x sfx={len(reel.get('sfx', []))}"
        )

    shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    main()
