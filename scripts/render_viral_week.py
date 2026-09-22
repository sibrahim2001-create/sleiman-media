#!/usr/bin/env python3
import json, os, subprocess, textwrap, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"content/viral_week_2026-09-23.json"
OUT=ROOT/"media/viral-week-2026-09-23"
TMP=ROOT/".render_tmp"
W,H=1080,1920
BG_TOP=(7,10,15)
BG_BOTTOM=(12,18,28)
BLUE=(47,124,255)
BLUE2=(117,160,255)
WHITE=(246,248,252)
MUTED=(170,181,196)
CARD=(17,25,37)
LINE=(39,52,73)

FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(size,bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG,size)

def wrap(draw,text,f,max_width):
    words=text.split()
    lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if draw.textbbox((0,0),test,font=f)[2] <= max_width:
            cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return "\n".join(lines)

def gradient():
    im=Image.new("RGB",(W,H))
    px=im.load()
    for y in range(H):
        r=y/(H-1)
        c=tuple(int(BG_TOP[i]*(1-r)+BG_BOTTOM[i]*r) for i in range(3))
        for x in range(W):
            px[x,y]=c
    return im

def rounded(draw,xy,r,fill,outline=None,width=1):
    draw.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=width)

def scene_image(scene,fmt,idx,total,path):
    im=gradient(); d=ImageDraw.Draw(im)
    # subtle grid
    for x in range(0,W,120): d.line((x,0,x,H),fill=(12,18,27),width=1)
    for y in range(0,H,120): d.line((0,y,W,y),fill=(12,18,27),width=1)

    # top brand
    d.rounded_rectangle((62,70,88,96),radius=7,fill=BLUE)
    d.text((108,67),"SLEIMAN SYSTEMS",font=font(34),fill=WHITE)
    d.text((108,110),"KI-SYSTEME FÜRS HANDWERK",font=font(24,False),fill=MUTED)

    # right progress
    gap=18; dot=13
    start=W-62-(total*dot+(total-1)*gap)
    for i in range(total):
        fill=BLUE if i==idx else (64,74,90)
        d.ellipse((start+i*(dot+gap),80,start+i*(dot+gap)+dot,80+dot),fill=fill)

    kicker=scene.get("kicker","").upper()
    headline=scene.get("headline","")
    body=scene.get("body","")

    # format accent
    accent_y=265
    if fmt=="number":
        rounded(d,(62,250,W-62,360),28,(11,25,49),outline=(35,74,135),width=2)
    elif fmt in ("prompt","template","tip"):
        d.rectangle((62,245,72,1430),fill=BLUE)
    elif fmt=="demo":
        rounded(d,(62,245,W-62,1435),34,CARD,outline=LINE,width=2)
    elif fmt=="contrarian":
        rounded(d,(62,245,W-62,380),34,(22,24,31),outline=(74,82,99),width=2)
    elif fmt=="offer":
        rounded(d,(62,245,W-62,1435),34,(12,24,43),outline=(44,89,158),width=2)
    elif fmt=="community":
        rounded(d,(62,245,W-62,1435),34,(14,22,36),outline=LINE,width=2)

    # kicker
    kf=font(34)
    d.text((82,285),kicker,font=kf,fill=BLUE2)

    # headline
    hf=font(92)
    htxt=wrap(d,headline,hf,900)
    hb=d.multiline_textbbox((0,0),htxt,font=hf,spacing=14)
    hheight=hb[3]-hb[1]
    h_y=410
    d.multiline_text((82,h_y),htxt,font=hf,fill=WHITE,spacing=14)

    # body
    bf=font(47,False)
    btxt=wrap(d,body,bf,880)
    body_y=min(1120,h_y+hheight+80)
    d.multiline_text((82,body_y),btxt,font=bf,fill=MUTED,spacing=18)

    # visual accents / CTA style
    if fmt=="offer":
        rounded(d,(82,1475,W-82,1595),28,BLUE)
        d.text((W//2,1535),"LINK IM PROFIL",font=font(42),fill=WHITE,anchor="mm")
    elif fmt=="demo":
        # small faux UI chips
        labels=["ANFRAGE","PRÜFEN","NÄCHSTER SCHRITT"]
        x=82
        for lab in labels:
            ww=d.textbbox((0,0),lab,font=font(24))[2]+44
            rounded(d,(x,1485,x+ww,1550),20,(23,34,50),outline=(50,67,92),width=1)
            d.text((x+22,1501),lab,font=font(24),fill=BLUE2)
            x+=ww+14
    else:
        d.line((82,1500,W-82,1500),fill=(44,57,77),width=2)
        d.text((82,1530),"WENIGER BÜRO. MEHR STRUKTUR.",font=font(32),fill=WHITE)

    # bottom handle
    d.text((82,1760),"@sleimansystems",font=font(32),fill=BLUE2)
    d.text((W-82,1760),"sleiman-systems.de",font=font(28,False),fill=MUTED,anchor="ra")
    im.save(path,quality=95)

def render_one(reel):
    rid=reel["id"]
    work=TMP/rid
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True,exist_ok=True)
    scene_files=[]
    for i,sc in enumerate(reel["scenes"]):
        p=work/f"scene_{i}.png"
        scene_image(sc,reel.get("format",""),i,len(reel["scenes"]),p)
        scene_files.append(p)

    seg=3.25
    trans=0.25
    args=["ffmpeg","-y"]
    for p in scene_files:
        args += ["-loop","1","-framerate","30","-t",str(seg),"-i",str(p)]
    total=seg*len(scene_files)-trans*(len(scene_files)-1)
    # audio: two very quiet synthetic tones, mixed
    args += ["-f","lavfi","-t",f"{total:.3f}","-i","sine=frequency=95:sample_rate=44100",
             "-f","lavfi","-t",f"{total:.3f}","-i","sine=frequency=190:sample_rate=44100"]

    filters=[]
    for i in range(len(scene_files)):
        filters.append(f"[{i}:v]scale={W}:{H},format=yuv420p,setsar=1[v{i}]")
    prev="v0"
    offset=seg-trans
    for i in range(1,len(scene_files)):
        out=f"x{i}"
        filters.append(f"[{prev}][v{i}]xfade=transition=fade:duration={trans}:offset={offset:.2f}[{out}]")
        prev=out
        offset += seg-trans
    a0=len(scene_files); a1=len(scene_files)+1
    filters.append(f"[{a0}:a]volume=0.018[a0q]")
    filters.append(f"[{a1}:a]volume=0.009[a1q]")
    filters.append("[a0q][a1q]amix=inputs=2:duration=longest,afade=t=in:st=0:d=0.3,afade=t=out:st="+f"{max(0,total-0.5):.2f}"+":d=0.5[a]")

    outfile=OUT/(rid+".mp4")
    args += ["-filter_complex",";".join(filters),"-map",f"[{prev}]","-map","[a]",
             "-t",f"{total:.3f}","-r","30","-c:v","libx264","-preset","veryfast","-crf","24",
             "-pix_fmt","yuv420p","-c:a","aac","-b:a","96k","-movflags","+faststart",str(outfile)]
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print(outfile.relative_to(ROOT))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    TMP.mkdir(parents=True,exist_ok=True)
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    for reel in data["reels"]:
        render_one(reel)
    shutil.rmtree(TMP,ignore_errors=True)

if __name__=="__main__":
    main()
