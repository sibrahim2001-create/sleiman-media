#!/usr/bin/env python3
import json, os, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"content"/"week1.json"
OUT=ROOT/"media"/"week1"
TMP=ROOT/".tmp_week1"
W,H=1080,1920
BG=(8,10,14)
CARD=(16,20,27)
TEXT=(245,247,251)
MUTED=(168,176,191)
BLUE=(47,124,255)
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(path,size):
    return ImageFont.truetype(path,size)

def wrap(draw, text, fnt, maxw):
    lines=[]
    for para in text.split("\n"):
        words=para.split()
        if not words:
            lines.append(""); continue
        cur=words[0]
        for word in words[1:]:
            trial=cur+" "+word
            if draw.textbbox((0,0),trial,font=fnt)[2] <= maxw:
                cur=trial
            else:
                lines.append(cur); cur=word
        lines.append(cur)
    return lines

def scene_png(text, idx, total, outpath):
    im=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(im)
    # top brand
    d.rounded_rectangle((70,90,1010,220),radius=28,fill=CARD)
    d.ellipse((105,125,155,175),fill=BLUE)
    d.text((185,122),"SLEIMAN SYSTEMS",font=font(FONT_BOLD,38),fill=TEXT)
    d.text((185,172),"KI • SYSTEME • HANDWERK",font=font(FONT_REG,23),fill=MUTED)
    # main copy
    is_hook = idx==0
    fnt=font(FONT_BOLD,76 if is_hook else 66)
    lines=wrap(d,text,fnt,900)
    line_h=(fnt.getbbox("Ag")[3]-fnt.getbbox("Ag")[1])+24
    total_h=line_h*len(lines)
    y=(H-total_h)//2-20
    for line in lines:
        box=d.textbbox((0,0),line,font=fnt)
        x=(W-(box[2]-box[0]))//2
        d.text((x,y),line,font=fnt,fill=TEXT,align="center")
        y+=line_h
    # accent / footer
    d.rounded_rectangle((70,1655,1010,1665),radius=5,fill=(35,42,55))
    seg=940/total
    d.rounded_rectangle((70,1655,70+seg*(idx+1),1665),radius=5,fill=BLUE)
    d.text((70,1715),f"{idx+1}/{total}",font=font(FONT_BOLD,28),fill=MUTED)
    d.text((70,1790),"Weniger Büro. Mehr Struktur.",font=font(FONT_BOLD,34),fill=TEXT)
    im.save(outpath,quality=95)

def run(cmd):
    subprocess.run(cmd,check=True)

def make_reel(reel):
    rid=reel["id"]
    rtmp=TMP/rid
    rtmp.mkdir(parents=True,exist_ok=True)
    scenes=[]
    for idx,text in enumerate(reel["scenes"]):
        p=rtmp/f"scene_{idx}.png"
        scene_png(text,idx,len(reel["scenes"]),p)
        scenes.append(p)
    concat=rtmp/"concat.txt"
    duration=3.2
    with concat.open("w") as f:
        for p in scenes:
            f.write(f"file '{p.as_posix()}'\n")
            f.write(f"duration {duration}\n")
        f.write(f"file '{scenes[-1].as_posix()}'\n")
    out=OUT/f"{rid}.mp4"
    total=duration*len(scenes)
    # subtle royalty-free synthetic ambient bed generated locally
    run([
      "ffmpeg","-y",
      "-f","concat","-safe","0","-i",str(concat),
      "-f","lavfi","-i",f"sine=frequency=110:duration={total}",
      "-f","lavfi","-i",f"sine=frequency=164.81:duration={total}",
      "-filter_complex","[1:a]volume=0.018[a1];[2:a]volume=0.012[a2];[a1][a2]amix=inputs=2,afade=t=in:st=0:d=1,afade=t=out:st="+str(max(total-1,0))+":d=1[a]",
      "-map","0:v","-map","[a]",
      "-vf","scale=1080:1920,format=yuv420p",
      "-r","30","-c:v","libx264","-preset","veryfast","-crf","27",
      "-c:a","aac","-b:a","96k","-shortest",str(out)
    ])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    TMP.mkdir(parents=True,exist_ok=True)
    data=json.loads(DATA.read_text())
    for reel in data["reels"]:
        make_reel(reel)
        print("generated",reel["id"])

if __name__=="__main__":
    main()
