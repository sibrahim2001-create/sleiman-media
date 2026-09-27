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
ORANGE=(255,132,56); YELLOW=(255,214,74); PURPLE=(166,92,255); CYAN=(58,214,255); BLUE=(49,124,255)
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
    palettes={
        "blue":   ((5,8,14),(9,16,27),BLUE),
        "red":    ((18,5,9),(38,9,16),RED),
        "green":  ((4,16,12),(7,39,28),GREEN),
        "amber":  ((18,12,4),(39,27,8),AMBER),
        "orange": ((20,9,4),(45,20,7),ORANGE),
        "yellow": ((17,15,5),(40,34,8),YELLOW),
        "purple": ((12,6,22),(31,12,52),PURPLE),
        "cyan":   ((3,14,18),(5,32,41),CYAN),
    }
    bg1,bg2,a=palettes.get(accent,palettes["blue"])
    im=Image.new("RGB",(W,H),bg1); d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/(H-1); c=tuple(int(bg1[i]*(1-t)+bg2[i]*t) for i in range(3))
        d.line((0,y,W,y),fill=c)
    grid=tuple(min(255,int(v*1.35+5)) for v in bg2)
    for x in range(0,W,120): d.line((x,0,x,H),fill=grid,width=1)
    for y in range(0,H,120): d.line((0,y,W,y),fill=grid,width=1)
    d.ellipse((760,-240,1320,320),fill=tuple(v//6 for v in a))
    d.ellipse((-260,1480,320,2060),fill=tuple(max(3,v//10) for v in a))
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
    elif kind=="pov_clock":
        card(d,(70,y0,1010,y0+430),fill=(10,20,35),outline=(48,70,99))
        d.text((100,y0+34),"FEIERABEND?",font=font(26),fill=MUTED)
        d.text((100,y0+92),"20:47",font=font(112),fill=a)
        d.text((100,y0+235),"Baustelle fertig.",font=font(31),fill=WHITE)
        d.text((100,y0+290),"Angebote  •  Rückrufe  •  Nachfassen",font=font(26,False),fill=MUTED)
        d.rounded_rectangle((100,y0+350,900,y0+390),radius=18,fill=(22,35,53))
        d.rounded_rectangle((100,y0+350,690,y0+390),radius=18,fill=a)
    elif kind=="demo_flow":
        card(d,(70,y0-10,1010,y0+465),fill=(9,22,38),outline=(45,83,133))
        d.text((100,y0+25),"WHATSAPP",font=font(23),fill=GREEN)
        d.rounded_rectangle((100,y0+72,790,y0+155),radius=22,fill=(22,54,44))
        d.text((130,y0+96),"„Wallbox nächste Woche möglich?“",font=font(28),fill=WHITE)
        d.text((100,y0+198),"KI-BRIEFING",font=font(23),fill=CYAN)
        rows=[("Leistung","Wallbox"),("Objekt","Einfamilienhaus"),("Fehlt","Fotos + Termin")]
        yy=y0+245
        for k,v in rows:
            d.text((110,yy),k.upper(),font=font(20),fill=MUTED)
            d.text((330,yy),v,font=font(27),fill=WHITE)
            yy+=66
        d.rounded_rectangle((735,y0+245,940,y0+430),radius=24,fill=(18,42,70),outline=(48,91,160))
        d.text((837,y0+300),"NÄCHSTER",font=font(18),fill=MUTED,anchor="mm")
        d.text((837,y0+338),"SCHRITT",font=font(23),fill=WHITE,anchor="mm")
        d.text((837,y0+385),"→ RÜCKFRAGE",font=font(18),fill=a,anchor="mm")
    elif kind=="followup":
        card(d,(70,y0,1010,y0+430),fill=(10,23,39),outline=(46,78,120))
        d.text((100,y0+30),"OFFENE ANGEBOTE",font=font(24),fill=a)
        rows=[("Müller","OFFEN","HEUTE"),("Bauer","GESENDET","DO"),("Schmidt","NACHFASSEN","JETZT")]
        yy=y0+92
        for name,status,when in rows:
            d.text((105,yy),name,font=font(28),fill=WHITE)
            d.text((380,yy),status,font=font(22,False),fill=MUTED)
            d.rounded_rectangle((770,yy-5,940,yy+45),radius=14,fill=(27,48,78))
            d.text((855,yy+20),when,font=font(20),fill=CYAN,anchor="mm")
            yy+=100
    elif kind=="lost_lead":
        # Phone-style missed lead visualization with escalating urgency
        card(d,(90,y0-35,990,y0+475),fill=(17,18,24),outline=(92,45,52),r=34,w=3)
        d.text((130,y0+5),"WHATSAPP",font=font(22),fill=GREEN)
        d.rounded_rectangle((130,y0+55,835,y0+142),radius=24,fill=(26,58,48))
        d.text((160,y0+82),"„Können Sie mir ein Angebot schicken?“",font=font(28),fill=WHITE)
        d.text((135,y0+184),"HEUTE",font=font(21),fill=MUTED)
        d.rounded_rectangle((130,y0+225,590,y0+292),radius=18,fill=(61,27,31))
        d.text((155,y0+246),"KEIN VERANTWORTLICHER",font=font(23),fill=RED)
        d.text((135,y0+328),"+ 3 TAGE",font=font(24),fill=AMBER)
        d.rounded_rectangle((330,y0+318,905,y0+405),radius=24,fill=(84,22,28))
        d.text((617,y0+361),"KUNDE WEG",font=font(39),fill=WHITE,anchor="mm")
    elif kind=="transform_demo":
        # Left: messy chat. Right: structured AI extraction/result
        card(d,(60,y0-35,500,y0+455),fill=(18,26,31),outline=(45,93,78),r=30)
        d.text((90,y0+3),"CHAT",font=font(22),fill=GREEN)
        d.rounded_rectangle((90,y0+55,445,y0+140),radius=22,fill=(31,66,54))
        d.text((115,y0+79),"„Wallbox nächste",font=font(25),fill=WHITE)
        d.text((115,y0+109),"Woche möglich?“",font=font(25),fill=WHITE)
        d.text((90,y0+190),"?",font=font(66),fill=AMBER)
        d.text((155,y0+203),"Termin",font=font(26),fill=MUTED)
        d.text((90,y0+270),"?",font=font(66),fill=AMBER)
        d.text((155,y0+283),"Fotos",font=font(26),fill=MUTED)
        d.polygon([(525,y0+195),(585,y0+235),(525,y0+275)],fill=a)
        card(d,(600,y0-35,1020,y0+455),fill=(10,35,39),outline=(45,135,143),r=30)
        d.text((630,y0+3),"KI-BRIEFING",font=font(22),fill=CYAN)
        chips=[("LEISTUNG","Wallbox"),("OBJEKT","EFH"),("FEHLT","Fotos + Termin")]
        yy=y0+62
        for k,v in chips:
            d.rounded_rectangle((630,yy,980,yy+82),radius=18,fill=(17,49,58))
            d.text((650,yy+12),k,font=font(17),fill=MUTED)
            d.text((650,yy+40),v,font=font(25),fill=WHITE)
            yy+=100
        d.rounded_rectangle((630,y0+372,980,y0+430),radius=18,fill=GREEN)
        d.text((805,y0+401),"NÄCHSTER SCHRITT ✓",font=font(21),fill=(5,18,13),anchor="mm")
    elif kind=="memory_overload":
        # Founder/owner memory overload metaphor
        d.ellipse((340,y0+50,740,y0+450),fill=(31,22,48),outline=a,width=4)
        d.text((540,y0+205),"CHEF",font=font(58),fill=WHITE,anchor="mm")
        d.text((540,y0+270),"= REMINDER?",font=font(30),fill=AMBER,anchor="mm")
        notes=[(70,y0+10,"MÜLLER\nNACHFASSEN"),(720,y0+20,"BAUER\nRÜCKRUF"),(40,y0+300,"ANGEBOT\nOFFEN"),(770,y0+315,"TERMIN\nFEHLT")]
        for x,y,t in notes:
            d.rounded_rectangle((x,y,x+240,y+115),radius=18,fill=(57,42,13),outline=YELLOW,width=2)
            d.multiline_text((x+120,y+58),t,font=font(22),fill=WHITE,anchor="mm",align="center",spacing=4)
    elif kind=="chat_hook":
        card(d,(65,y0-65,1015,y0+470),fill=(13,20,22),outline=(40,96,74),r=36,w=3)
        d.text((100,y0-25),"NEUE WHATSAPP",font=font(24),fill=GREEN)
        d.rounded_rectangle((105,y0+55,935,y0+188),radius=30,fill=(31,79,61))
        d.multiline_text((145,y0+82),"„Könnt ihr morgen\nkommen?“",font=font(38),fill=WHITE,spacing=4)
        d.ellipse((870,y0-20,955,y0+65),fill=RED)
        d.text((913,y0+22),"1",font=font(34),fill=WHITE,anchor="mm")
        d.text((110,y0+245),"ORT ?",font=font(34),fill=AMBER)
        d.text((390,y0+245),"FOTO ?",font=font(34),fill=AMBER)
        d.text((690,y0+245),"TERMIN ?",font=font(34),fill=AMBER)
        d.rounded_rectangle((105,y0+330,935,y0+410),radius=22,fill=(58,24,29))
        d.text((520,y0+370),"3 INFOS FEHLEN",font=font(34),fill=WHITE,anchor="mm")
    elif kind=="stop_stamp":
        d.ellipse((260,y0-20,820,y0+540),fill=(68,14,20),outline=RED,width=18)
        d.text((540,y0+220),"STOP",font=font(120),fill=WHITE,anchor="mm")
        d.text((540,y0+335),"NICHT BLIND ANTWORTEN",font=font(30),fill=AMBER,anchor="mm")
    elif kind=="boss_meme":
        card(d,(75,y0-40,1005,y0+470),fill=(25,18,42),outline=PURPLE,r=34,w=3)
        d.rounded_rectangle((115,y0+30,900,y0+125),radius=25,fill=(48,40,60))
        d.text((145,y0+58),"„CHEF, WO IST ANGEBOT MÜLLER?“",font=font(31),fill=WHITE)
        d.text((110,y0+180),"CHEF.EXE",font=font(54),fill=YELLOW)
        d.text((110,y0+245),"LÄDT ...",font=font(54),fill=WHITE)
        badges=[("RÜCKRUF",3),( "ANGEBOT",7),("TERMIN",4)]
        xx=110
        for label,num in badges:
            d.rounded_rectangle((xx,y0+345,xx+240,y0+425),radius=20,fill=(54,25,71))
            d.text((xx+120,y0+372),label,font=font(18),fill=MUTED,anchor="mm")
            d.text((xx+120,y0+400),str(num),font=font(28),fill=RED,anchor="mm")
            xx+=285
    elif kind=="system_card":
        card(d,(70,y0-50,1010,y0+475),fill=(7,31,29),outline=GREEN,r=34,w=3)
        d.text((105,y0-5),"SICHTBARER STATUS",font=font(25),fill=GREEN)
        rows=[("MÜLLER","ANGEBOT OFFEN","HEUTE","IBO"),("BAUER","RÜCKFRAGE","10:30","LEA"),("SCHMIDT","NACHFASSEN","FR","IBO")]
        yy=y0+70
        for name,status,when,owner in rows:
            d.text((105,yy),name,font=font(28),fill=WHITE)
            d.text((330,yy),status,font=font(21,False),fill=MUTED)
            d.rounded_rectangle((685,yy-8,820,yy+43),radius=14,fill=(18,75,58))
            d.text((752,yy+17),when,font=font(18),fill=WHITE,anchor="mm")
            d.rounded_rectangle((845,yy-8,950,yy+43),radius=14,fill=(22,45,67))
            d.text((897,yy+17),owner,font=font(18),fill=CYAN,anchor="mm")
            yy+=100
    elif kind=="seven_demo":
        card(d,(55,y0-50,1025,y0+480),fill=(8,23,34),outline=CYAN,r=34,w=3)
        d.text((90,y0-8),"SLEIMAN SYSTEMS • DEMO",font=font(23),fill=CYAN)
        d.rounded_rectangle((90,y0+55,440,y0+160),radius=25,fill=(30,72,55))
        d.text((265,y0+108),"ANFRAGE",font=font(32),fill=WHITE,anchor="mm")
        d.polygon([(470,y0+95),(530,y0+125),(470,y0+155)],fill=ORANGE)
        d.rounded_rectangle((560,y0+55,950,y0+160),radius=25,fill=(20,51,70))
        d.text((755,y0+90),"KI",font=font(26),fill=CYAN,anchor="mm")
        d.text((755,y0+125),"STRUKTURIERT",font=font(29),fill=WHITE,anchor="mm")
        d.rounded_rectangle((90,y0+230,950,y0+315),radius=22,fill=(18,39,59))
        d.text((130,y0+255),"OWNER",font=font(18),fill=MUTED)
        d.text((300,y0+252),"IBO",font=font(25),fill=WHITE)
        d.text((470,y0+255),"NÄCHSTER SCHRITT",font=font(18),fill=MUTED)
        d.text((760,y0+252),"RÜCKFRAGE",font=font(25),fill=WHITE)
        d.rounded_rectangle((90,y0+360,950,y0+435),radius=22,fill=GREEN)
        d.text((520,y0+397),"DU PRÜFST • FERTIG",font=font(30),fill=(5,20,15),anchor="mm")
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
    im,a=base(sc.get("accent",reel.get("accent","blue"))); d=ImageDraw.Draw(im)
    if not sc.get("hide_brand", False): brand(d,a)
    hook_mode=sc.get("hide_brand",False)
    tag_y=82 if hook_mode else 188
    head_y=175 if hook_mode else 355
    d.text((60,tag_y),sc.get("tag","").upper(),font=font(30),fill=a)
    if i==0 and not sc.get("hide_hook_badge", False):
        d.rounded_rectangle((58,246,292,310),radius=18,fill=tuple(max(0,v//2) for v in a))
        d.text((175,278),"0–3 SEKUNDEN",font=font(23),fill=WHITE,anchor="mm")
    hf=font(112 if hook_mode else (98 if i==0 else 86))
    ht=wrap(d,sc["headline"],hf,940)
    d.multiline_text((58,head_y),ht,font=hf,fill=WHITE,spacing=8)
    hb=d.multiline_textbbox((0,0),ht,font=hf,spacing=8)
    sy=min(900,head_y+(hb[3]-hb[1])+48)
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
    segs=reel.get("scene_durations") or ([3.2]+[4.0]*(len(pngs)-1)); trans=.14
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
