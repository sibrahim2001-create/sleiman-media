#!/usr/bin/env python3
import json, math, shutil, subprocess, wave, struct, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content/daily_premium.json"
OUT = ROOT / "media/daily-premium"
TMP = ROOT / ".daily_premium_tmp"
W,H,FPS = 1080,1920,30

FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
WHITE=(248,250,252); MUTED=(164,178,198); BLUE=(49,124,255); CYAN=(58,214,255)
RED=(255,78,86); GREEN=(55,211,153); AMBER=(255,185,72)
BG=(5,8,14); BG2=(9,16,27); CARD=(15,24,39); LINE=(38,55,79)

def font(n,b=True): return ImageFont.truetype(FONT_B if b else FONT_R,n)

def wrap(d,t,f,mw):
    out=[]; cur=""
    for w in t.split():
        x=(cur+" "+w).strip()
        if d.textbbox((0,0),x,font=f)[2] <= mw: cur=x
        else:
            if cur: out.append(cur)
            cur=w
    if cur: out.append(cur)
    return "\n".join(out)

def base(accent):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/(H-1); c=tuple(int(BG[i]*(1-t)+BG2[i]*t) for i in range(3))
        d.line((0,y,W,y),fill=c)
    for x in range(0,W,120): d.line((x,0,x,H),fill=(11,19,31),width=1)
    for y in range(0,H,120): d.line((0,y,W,y),fill=(11,19,31),width=1)
    a={"red":RED,"green":GREEN,"amber":AMBER}.get(accent,BLUE)
    d.ellipse((760,-240,1320,320),fill=tuple(v//7 for v in a))
    d.ellipse((-260,1480,320,2060),fill=(8,31,62))
    return im,a

def brand(d,a):
    d.rounded_rectangle((58,58,88,88),radius=8,fill=a)
    d.text((108,54),"SLEIMAN SYSTEMS",font=font(31),fill=WHITE)
    d.text((108,96),"KI-SYSTEME FÜRS HANDWERK",font=font(20,False),fill=MUTED)

def card(d,xy,fill=CARD,outline=LINE,r=28,w=2):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=w)

def visual(d,kind,a,y0=980):
    if kind=="pipeline":
        labels=["ANFRAGE","PRÜFEN","ANGEBOT","NACHFASSEN"]
        x=72; y=y0+150
        for i,l in enumerate(labels):
            ww=205
            card(d,(x,y,x+ww,y+112),fill=(13,27,46),outline=(43,78,125),r=22)
            d.text((x+ww/2,y+56),l,font=font(24),fill=WHITE,anchor="mm")
            if i<len(labels)-1:
                d.line((x+ww+8,y+56,x+ww+42,y+56),fill=a,width=6)
                d.polygon([(x+ww+42,y+56),(x+ww+27,y+46),(x+ww+27,y+66)],fill=a)
            x += 250
    elif kind=="inbox":
        card(d,(70,y0,1010,y0+430))
        d.text((100,y0+34),"NEUE ANFRAGE",font=font(28),fill=a)
        d.text((100,y0+92),"„Hallo, wir brauchen eine Wallbox …“",font=font(35),fill=WHITE)
        d.text((100,y0+154),"Objekt: Einfamilienhaus",font=font(27,False),fill=MUTED)
        d.text((100,y0+205),"Termin: fehlt",font=font(27,False),fill=RED)
        d.text((100,y0+256),"Fotos: fehlen",font=font(27,False),fill=RED)
        d.rounded_rectangle((100,y0+322,470,y0+390),radius=18,fill=(20,55,92))
        d.text((285,y0+356),"BRIEFING ERSTELLEN",font=font(23),fill=WHITE,anchor="mm")
    elif kind=="prompt":
        card(d,(70,y0,1010,y0+430))
        d.text((100,y0+30),"PROMPT",font=font(25),fill=CYAN)
        lines=["Fasse die Anfrage zusammen.","Markiere fehlende Angaben.","Nenne die nächsten 3 Schritte."]
        yy=y0+92
        for i,t in enumerate(lines):
            d.text((105,yy),f"{i+1}.",font=font(29),fill=a)
            d.text((155,yy),t,font=font(29,False),fill=WHITE)
            yy+=80
        d.text((100,y0+355),"Regel: Nichts erfinden.",font=font(26),fill=AMBER)
    elif kind=="score":
        card(d,(70,y0,1010,y0+430),fill=(10,24,42),outline=(42,80,135))
        d.text((100,y0+30),"KOSTENLOSE PROZESSANALYSE",font=font(25),fill=a)
        d.text((100,y0+96),"9 Bereiche",font=font(38),fill=WHITE)
        d.text((100,y0+152),"Score 0–100",font=font(38),fill=WHITE)
        d.text((100,y0+222),"Kommunikation  •  Angebote  •  Nachfassen",font=font(24,False),fill=MUTED)
        d.text((100,y0+270),"Einsatz  •  Doku  •  Finanzen  •  Material",font=font(24,False),fill=MUTED)
        d.rounded_rectangle((100,y0+338,920,y0+370),radius=16,fill=(25,38,57))
        d.rounded_rectangle((100,y0+338,650,y0+370),radius=16,fill=a)
    elif kind=="kit":
        card(d,(70,y0-20,1010,y0+470),fill=(9,24,45),outline=(48,91,160))
        d.text((105,y0+20),"KI-OFFICE KIT",font=font(42),fill=WHITE)
        d.text((105,y0+85),"79 € EINMALIG",font=font(40),fill=CYAN)
        items=["Tracker","Prompts","Vorlagen","Workflow"]
        yy=y0+175
        for t in items:
            d.ellipse((110,yy+8,132,yy+30),fill=GREEN)
            d.text((160,yy),t,font=font(31),fill=WHITE)
            yy+=67
    elif kind=="status":
        card(d,(70,y0,1010,y0+430))
        rows=[("Müller GmbH","Angebot offen","HEUTE"),("Schmidt","Rückfrage","10:30"),("Bauer","Nachfassen","FR")]
        yy=y0+45
        for name,status,when in rows:
            d.text((105,yy),name,font=font(29),fill=WHITE)
            d.text((390,yy),status,font=font(25,False),fill=MUTED)
            d.rounded_rectangle((780,yy-6,940,yy+46),radius=14,fill=(27,48,78))
            d.text((860,yy+20),when,font=font(21),fill=CYAN,anchor="mm")
            d.line((105,yy+62,940,yy+62),fill=LINE,width=1)
            yy+=105
    else:
        d.rounded_rectangle((75,y0+100,1005,y0+120),radius=10,fill=(31,45,65))
        d.rounded_rectangle((75,y0+100,710,y0+120),radius=10,fill=a)

def make_scene(reel,i,sc,path):
    im,a=base(reel.get("accent","blue")); d=ImageDraw.Draw(im); brand(d,a)
    d.text((60,188),sc.get("tag","").upper(),font=font(28),fill=a)
    if i==0:
        d.rounded_rectangle((58,246,292,310),radius=18,fill=tuple(max(0,v//2) for v in a))
        d.text((175,278),"0–3 SEKUNDEN",font=font(23),fill=WHITE,anchor="mm")
    hf=font(98 if i==0 else 86)
    ht=wrap(d,sc["headline"],hf,940)
    d.multiline_text((58,355),ht,font=hf,fill=WHITE,spacing=8)
    hb=d.multiline_textbbox((0,0),ht,font=hf,spacing=8)
    sy=min(910,355+(hb[3]-hb[1])+58)
    sub=wrap(d,sc.get("sub",""),font(35,False),920)
    d.multiline_text((62,sy),sub,font=font(35,False),fill=MUTED,spacing=12)
    visual(d,sc.get("visual","bar"),a,1060)
    if sc.get("cta"):
        d.rounded_rectangle((60,1655,1020,1780),radius=30,fill=a)
        d.text((540,1718),sc["cta"],font=font(39),fill=WHITE,anchor="mm")
    else:
        d.text((60,1760),"WENIGER BÜRO. MEHR STRUKTUR.",font=font(28),fill=MUTED)
    d.text((1020,1830),f"{i+1}/{len(reel['scenes'])}",font=font(24),fill=(92,111,137),anchor="ra")
    im.save(path)

def make_audio(total,path,transitions):
    sr=44100; n=int(total*sr); data=[0.0]*n; bpm=126; beat=60/bpm
    for b in [x*beat for x in range(int(total/beat)+2)]:
        st=int(b*sr)
        for j in range(min(int(.16*sr),n-st)):
            t=j/sr; env=math.exp(-t*24)
            data[st+j]+=0.20*env*math.sin(2*math.pi*(72-28*t)*t)
    for b in [beat/2+x*beat for x in range(int(total/beat)+2)]:
        st=int(b*sr)
        for j in range(min(int(.035*sr),n-st)):
            env=1-j/(.035*sr); data[st+j]+=0.035*env*(random.random()*2-1)
    for tr in transitions:
        st=int(max(0,tr-.07)*sr)
        for j in range(min(int(.14*sr),n-st)):
            t=j/sr; env=math.sin(math.pi*min(1,t/.14))
            data[st+j]+=0.055*env*(random.random()*2-1)
    with wave.open(str(path),"w") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
        frames=bytearray()
        for x in data:
            v=max(-1,min(1,x)); frames += struct.pack("<h",int(v*32767))
        f.writeframes(frames)

def render(reel):
    work=TMP/reel["id"]; shutil.rmtree(work,ignore_errors=True); work.mkdir(parents=True)
    pngs=[]
    for i,sc in enumerate(reel["scenes"]):
        p=work/f"s{i}.png"; make_scene(reel,i,sc,p); pngs.append(p)
    segs=[1.75]+[2.05]*(len(pngs)-1); trans=.14
    total=sum(segs)-trans*(len(segs)-1); transition_times=[]
    args=["ffmpeg","-y"]
    for p,seg in zip(pngs,segs): args += ["-loop","1","-framerate",str(FPS),"-t",str(seg),"-i",str(p)]
    filters=[]
    for i,seg in enumerate(segs):
        d=max(1,int(seg*FPS))
        z="min(zoom+0.0022,1.065)" if i%2==0 else "min(zoom+0.0015,1.045)"
        x="'iw/2-(iw/zoom/2)'" if i%2==0 else "'iw/2-(iw/zoom/2)+8*sin(on/5)'"
        filters.append(f"[{i}:v]scale=1210:2151,zoompan=z='{z}':x={x}:y='ih/2-(ih/zoom/2)':d={d}:s={W}x{H}:fps={FPS},format=yuv420p,setsar=1[v{i}]")
    prev="v0"; offset=segs[0]-trans
    trs=["slideleft","wipeleft","slideup","slideright"]
    for i in range(1,len(pngs)):
        out=f"x{i}"; transition_times.append(offset)
        filters.append(f"[{prev}][v{i}]xfade=transition={trs[(i-1)%len(trs)]}:duration={trans}:offset={offset:.3f}[{out}]")
        prev=out; offset += segs[i]-trans
    wav=work/"beat.wav"; make_audio(total,wav,transition_times); args += ["-i",str(wav)]
    filters.append(f"[{len(pngs)}:a]volume=0.55,afade=t=in:st=0:d=.08,afade=t=out:st={max(0,total-.3):.3f}:d=.3[a]")
    outfile=OUT/f"{reel['id']}.mp4"
    args += ["-filter_complex",";".join(filters),"-map",f"[{prev}]","-map","[a]","-t",f"{total:.3f}","-r",str(FPS),"-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",str(outfile)]
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print(f"rendered {outfile.relative_to(ROOT)} {total:.2f}s")

def main():
    OUT.mkdir(parents=True,exist_ok=True); TMP.mkdir(parents=True,exist_ok=True)
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    for reel in data["reels"]: render(reel)
    shutil.rmtree(TMP,ignore_errors=True)

if __name__=="__main__": main()
