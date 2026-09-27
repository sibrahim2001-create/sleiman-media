#!/usr/bin/env python3
import json
import math
import shutil
import subprocess
import urllib.request
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
        mixed = TMP / f"{reel['id']}-mixed.mp4"
        urllib.request.urlretrieve(url, voice)

        video_dur = probe_duration(video)
        voice_dur = probe_duration(voice)
        target = max(0.5, video_dur - 0.18)
        speed = max(1.0, voice_dur / target)
        tempo = atempo_chain(speed)

        filt = (
            f"[0:a]volume=0.055[bed];"
            f"[1:a]{tempo},highpass=f=75,"
            f"acompressor=threshold=-18dB:ratio=3:attack=5:release=70,"
            f"volume=2.35,adelay=40|40,loudnorm=I=-15.5:TP=-1.2:LRA=6[vo];"
            f"[bed][vo]sidechaincompress=threshold=0.03:ratio=8:attack=5:release=180[ducked];"
            f"[ducked][vo]amix=inputs=2:duration=first:dropout_transition=0,"
            f"alimiter=limit=0.95[a]"
        )

        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(voice),
            "-filter_complex", filt,
            "-map", "0:v:0",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "160k",
            "-movflags", "+faststart",
            str(mixed)
        ], check=True)

        shutil.move(str(mixed), str(video))
        print(
            f"voiceover {reel['id']}: video={video_dur:.2f}s "
            f"voice={voice_dur:.2f}s tempo={speed:.3f}x"
        )

    shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    main()
