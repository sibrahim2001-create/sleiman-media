#!/usr/bin/env python3
import json
import math
import os
import random
import shutil
import subprocess
import urllib.request
import wave
from array import array
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"content/daily_premium.json"
OUT=ROOT/"media/daily-premium"
TMP=ROOT/".voiceover_v9_tmp"

def fish_reference_id() -> str:
    configured = os.environ.get("FISH_AUDIO_VOICE_ID")
    if configured:
        return configured
    data = json.loads((ROOT / "content/voice_system.json").read_text(encoding="utf-8"))
    return str((data.get("primary_voice") or {}).get("voice_id") or "")

def synthesize_fish_voice(text: str, destination: Path) -> None:
    api_key = os.environ.get("FISH_AUDIO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing Actions secret SEC (FISH_AUDIO_API_KEY).")
    voice_id = fish_reference_id()
    if not voice_id:
        raise RuntimeError("Fish Audio voice_id is missing from content/voice_system.json.")
    data = json.loads((ROOT / "content/voice_system.json").read_text(encoding="utf-8"))
    model = str((data.get("primary_voice") or {}).get("model") or "s2.1-pro-free")
    if model != "s2.1-pro-free":
        raise RuntimeError("This renderer is restricted to the free Fish Audio model s2.1-pro-free.")
    payload = json.dumps({"text": text, "reference_id": voice_id, "format": "mp3"}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.fish.audio/v1/tts",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "model": model},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            audio = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"Fish Audio HTTP {error.code}: {detail}") from error
    valid_mp3 = audio.startswith(b"ID3") or (len(audio) > 2 and audio[0] == 0xff and (audio[1] & 0xe0) == 0xe0)
    if not valid_mp3:
        raise RuntimeError("Fish Audio did not return a valid MP3.")
    destination.write_bytes(audio)

def materialize_voice(source: dict, destination: Path) -> bool:
    text = str(source.get("text") or "").strip()
    if text:
        synthesize_fish_voice(text, destination)
        print(f"Fish Audio TTS generated {destination.name} ({destination.stat().st_size} bytes).")
        return True
    url = source.get("url")
    if url:
        urllib.request.urlretrieve(url, destination)
        return True
    return False

def probe_duration(path: Path) -> float:
    p=subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(path)],
        check=True,capture_output=True,text=True
    )
    return float(p.stdout.strip())

def atempo_chain(rate: float) -> str:
    if rate <= 1.0001:
        return "anull"
    parts=[]
    while rate>2.0:
        parts.append("atempo=2.0"); rate/=2.0
    if abs(rate-1.0)>0.0001:
        parts.append(f"atempo={rate:.5f}")
    return ",".join(parts) if parts else "anull"

def synth_sfx_track(reel,duration,path,sr=48000):
    n=max(1,int((duration+0.1)*sr))
    buf=array("f",[0.0])*n
    def add(i,v):
        if 0<=i<n: buf[i]+=v
    def sine(start,dur,f0,amp=.5,f1=None):
        st=int(start*sr); count=max(1,int(dur*sr)); phase=0.0
        for j in range(count):
            x=j/max(1,count-1); f=f0 if f1 is None else f0+(f1-f0)*x
            phase+=2*math.pi*f/sr
            env=(1-x)**1.7
            add(st+j,math.sin(phase)*amp*env)
    def noise(start,dur,amp=.25,rise=False):
        st=int(start*sr); count=max(1,int(dur*sr)); last=0.0
        for j in range(count):
            x=j/max(1,count-1)
            last=last*.75+random.uniform(-1,1)*.25
            env=(x**1.5) if rise else ((1-x)**1.7)
            add(st+j,last*amp*env)
    for ev in reel.get("sfx",[]):
        typ=ev.get("type","click"); t=float(ev.get("at",0)); g=float(ev.get("gain",1))
        if typ=="notification":
            sine(t,.14,900,.40*g); sine(t+.10,.20,1320,.32*g)
        elif typ=="bass_hit":
            sine(t,.36,82,.72*g,48); noise(t,.10,.12*g)
        elif typ=="whoosh":
            noise(t,.32,.28*g,True); sine(t+.20,.14,430,.10*g,760)
        elif typ=="record_scratch":
            noise(t,.24,.35*g); sine(t,.22,1100,.12*g,180)
        elif typ=="stamp":
            noise(t,.07,.38*g); sine(t,.16,95,.48*g,58)
        elif typ=="cash":
            sine(t,.11,1047,.27*g); sine(t+.09,.13,1319,.24*g); sine(t+.19,.20,1568,.21*g)
        elif typ=="error":
            sine(t,.15,440,.30*g,300); sine(t+.14,.19,300,.24*g,190)
        else:
            noise(t,.04,.22*g); sine(t,.05,900,.12*g)
    pcm=array("h")
    for v in buf:
        v=max(-.98,min(.98,v)); pcm.append(int(v*32767))
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())

def main():
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    TMP.mkdir(parents=True,exist_ok=True)

    for reel in data.get("reels",[]):
        video=OUT/f"{reel['id']}.mp4"
        if not video.exists(): raise FileNotFoundError(video)
        video_dur=probe_duration(video)
        sfx=TMP/f"{reel['id']}-sfx.wav"
        mixed=TMP/f"{reel['id']}-mixed.mp4"
        synth_sfx_track(reel,video_dur,sfx)

        segments=reel.get("voice_segments") or []
        if not segments:
            vo=reel.get("voiceover") or {}
            if vo.get("text") or vo.get("url"):
                segments=[{"text":vo.get("text"),"url":vo.get("url"),"at":0.02,"gain":vo.get("mix_gain",2.30)}]
        if not segments:
            print(f"skip {reel['id']}: no voice"); continue

        inputs=["ffmpeg","-y","-i",str(video)]
        segpaths=[]
        for idx,seg in enumerate(segments):
            p=TMP/f"{reel['id']}-seg{idx}.wav"
            if not materialize_voice(seg, p):
                raise ValueError(f"Voice segment {idx} in {reel['id']} has neither text nor url.")
            segpaths.append(p)
            inputs += ["-i",str(p)]
        inputs += ["-i",str(sfx)]
        sfx_input=1+len(segpaths)

        filters=[]
        # bed
        bed_gain=float(reel.get("bed_mix_gain",0.022))
        filters.append(f"[0:a]volume={bed_gain:.3f}[bed]")

        voice_labels=[]
        for idx,(seg,p) in enumerate(zip(segments,segpaths),start=1):
            raw_dur=probe_duration(p)
            max_dur=float(seg.get("max_duration",0) or 0)
            rate=1.0
            if max_dur>0 and raw_dur>max_dur:
                rate=max(1.0,raw_dur/max_dur)
            tempo=atempo_chain(rate)
            delay=max(0,int(float(seg.get("at",0))*1000))
            gain=float(seg.get("gain",2.30))
            # trim leading/trailing silence and shorten only long internal pauses; words keep natural speed
            filters.append(
                f"[{idx}:a]{tempo},"
                f"silenceremove=start_periods=1:start_threshold=-46dB:start_silence=0.02,"
                f"silenceremove=stop_periods=-1:stop_duration=0.34:stop_threshold=-46dB:stop_silence=0.13,"
                f"areverse,silenceremove=start_periods=1:start_threshold=-46dB:start_silence=0.02,areverse,"
                f"highpass=f=65,equalizer=f=180:t=q:w=1.0:g=1.4,"
                f"equalizer=f=2850:t=q:w=1.3:g=1.8,lowpass=f=15000,"
                f"acompressor=threshold=-18dB:ratio=2.3:attack=8:release=115,"
                f"volume={gain:.2f},adelay={delay}|{delay}[v{idx}]"
            )
            voice_labels.append(f"[v{idx}]")

        # mix voice segments, duck bed, then add SFX
        filters.append("".join(voice_labels)+f"amix=inputs={len(voice_labels)}:duration=longest:dropout_transition=0:normalize=0[vox0]")
        filters.append("[vox0]asplit=2[side][vox]")
        filters.append("[bed][side]sidechaincompress=threshold=0.018:ratio=12:attack=3:release=170[ducked]")
        sfx_gain=float(reel.get("sfx_mix_gain",0.82))
        filters.append(f"[{sfx_input}:a]volume={sfx_gain:.2f}[sfx]")
        filters.append(
            "[ducked][vox][sfx]amix=inputs=3:duration=first:dropout_transition=0:normalize=0,"
            "loudnorm=I=-11.8:TP=-0.8:LRA=4.0,alimiter=limit=0.98[a]"
        )

        cmd=inputs+[
            "-filter_complex",";".join(filters),
            "-map","0:v:0","-map","[a]","-t",f"{video_dur:.3f}",
            "-c:v","copy","-c:a","aac","-ar","48000","-b:a","192k",
            "-movflags","+faststart",str(mixed)
        ]
        subprocess.run(cmd,check=True)
        shutil.move(str(mixed),str(video))
        print(f"voice-v9 {reel['id']}: {len(segments)} segments, video={video_dur:.2f}s")

    shutil.rmtree(TMP,ignore_errors=True)

if __name__=="__main__": main()
