#!/usr/bin/env python3
import json, math, random, shutil, subprocess, wave, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"content/daily_premium.json"
OUT=ROOT/"media/daily-premium"
TMP=ROOT/".attention_v8_tmp"
RW,RH,FPS=720,1280,30

FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
WHITE=(249,250,252); BLACK=(10,12,16); MUTED=(160,171,190)
RED=(255,65,78); GREEN=(49,222,143); CYAN=(51,214,255); BLUE=(49,116,255)
YELLOW=(255,215,66); ORANGE=(255,128,45); PURPLE=(168,83,255)

def font(n,b=True): return ImageFont.truetype(FONT_B if b else FONT_R,n)
def clamp(x,a=0,b=1): return max(a,min(b,x))
def ease(x): x=clamp(x); return 1-(1-x)**3
def back(x):
    x=clamp(x); c1=1.70158; c3=c1+1
    return 1+c3*(x-1)**3+c1*(x-1)**2

def gradient(top,bottom):
    im=Image.new("RGB",(RW,RH),top); d=ImageDraw.Draw(im)
    for y in range(RH):
        p=y/(RH-1)
        c=tuple(int(top[i]*(1-p)+bottom[i]*p) for i in range(3))
        d.line((0,y,RW,y),fill=c)
    return im

BG={
 "black":gradient((4,5,9),(13,15,22)),
 "red":gradient((39,5,10),(70,12,22)),
 "green":gradient((3,23,17),(5,48,31)),
 "blue":gradient((5,12,25),(8,31,61)),
 "cyan":gradient((3,17,24),(6,45,57)),
 "purple":gradient((18,8,33),(54,15,78)),
 "orange":gradient((40,13,4),(78,29,8)),
 "yellow":gradient((250,245,224),(255,229,138)),
 "white":gradient((250,249,244),(232,240,247)),
}
COLORS={"red":RED,"green":GREEN,"blue":BLUE,"cyan":CYAN,"purple":PURPLE,"orange":ORANGE,"yellow":YELLOW,"white":WHITE}

def grid(im,color,step=88,alpha=28):
    ov=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(ov)
    for x in range(0,RW,step): d.line((x,0,x,RH),fill=(*color,alpha),width=1)
    for y in range(0,RH,step): d.line((0,y,RW,y),fill=(*color,alpha),width=1)
    return Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB")

def wrap(draw,text,f,mw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if draw.textbbox((0,0),test,font=f)[2] <= mw: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def brand(d,light=False):
    c=BLACK if light else WHITE
    d.rounded_rectangle((32,30,54,52),radius=5,fill=BLUE)
    d.text((67,28),"SLEIMAN SYSTEMS",font=font(18),fill=c)

def pill(d,xy,text,fill,textfill=WHITE,fs=17,outline=None):
    d.rounded_rectangle(xy,radius=16,fill=fill,outline=outline,width=2 if outline else 1)
    d.text(((xy[0]+xy[2])//2,(xy[1]+xy[3])//2),text,font=font(fs),fill=textfill,anchor="mm")

def headline(d,text,y,color=WHITE,size=66,center=False):
    f=font(size); lines=wrap(d,text,f,RW-64); txt="\n".join(lines)
    if center:
        box=d.multiline_textbbox((0,0),txt,font=f,spacing=2,align="center")
        w=box[2]-box[0]
        d.multiline_text(((RW-w)//2,y),txt,font=f,fill=color,spacing=2,align="center")
    else:
        d.multiline_text((32,y),txt,font=f,fill=color,spacing=2)

def sub(d,text,y,color=MUTED,size=24):
    f=font(size,False); lines=wrap(d,text,f,RW-64)
    d.multiline_text((34,y),"\n".join(lines),font=f,fill=color,spacing=5)

def progress_bar(d,t,total,accent):
    x0,y0,x1=32,73,688
    d.rounded_rectangle((x0,y0,x1,y0+8),radius=4,fill=(48,52,61))
    p=clamp(t/total)
    d.rounded_rectangle((x0,y0,x0+int((x1-x0)*p),y0+8),radius=4,fill=accent)

def draw_caption(im,reel,t):
    cues=reel.get("captions",[])
    cue=None
    for c in cues:
        if float(c["start"]) <= t < float(c["end"]):
            cue=c; break
    if not cue: return im
    accent=COLORS.get(cue.get("accent",reel.get("caption_accent","yellow")),YELLOW)
    layer=Image.new("RGBA",(RW,RH),(0,0,0,0)); d=ImageDraw.Draw(layer)
    p=back(clamp((t-float(cue["start"]))/0.14))
    y=int(830+(1-p)*16)
    text=cue["text"].upper()
    highlight=(cue.get("highlight") or "").upper()
    f=font(32)
    words=text.split()
    # break into at most two balanced lines
    line1=[]; line2=[]; target=max(1,(len(words)+1)//2)
    line1=words[:target]; line2=words[target:]
    lines=[line1]+([line2] if line2 else [])
    widths=[]
    for line in lines:
        w=sum(d.textbbox((0,0),wd,font=f)[2]+12 for wd in line)-12
        widths.append(w)
    card_w=min(570,max(widths)+46)
    card_h=82 if len(lines)==1 else 124
    x0=(RW-card_w)//2
    d.rounded_rectangle((x0,y,x0+card_w,y+card_h),radius=22,fill=(5,7,11,228),outline=(*accent,235),width=3)
    d.rounded_rectangle((x0+22,y+13,x0+95,y+19),radius=3,fill=(*accent,255))
    yy=y+25
    for li,line in enumerate(lines):
        w=widths[li]; x=(RW-w)//2
        for wd in line:
            bbox=d.textbbox((0,0),wd,font=f); ww=bbox[2]-bbox[0]
            clean=wd.strip(".,!?„“:;")
            is_hi=highlight and (clean==highlight or highlight in clean)
            if is_hi:
                d.rounded_rectangle((x-6,yy-4,x+ww+6,yy+42),radius=10,fill=(*accent,255))
                tc=BLACK if accent in (YELLOW,GREEN,CYAN,ORANGE) else WHITE
                d.text((x,yy),wd,font=f,fill=tc)
            else:
                # subtle shadow
                d.text((x+2,yy+2),wd,font=f,fill=(0,0,0,180))
                d.text((x,yy),wd,font=f,fill=WHITE)
            x += ww+12
        yy += 41
    return Image.alpha_composite(im.convert("RGBA"),layer).convert("RGB")

def chat_card(d,y,text,shake=0,accent=GREEN):
    x=52+shake; w=616
    d.rounded_rectangle((x,y,x+w,y+220),radius=28,fill=(16,22,25),outline=accent,width=3)
    d.text((x+26,y+20),"WHATSAPP",font=font(18),fill=GREEN)
    d.rounded_rectangle((x+26,y+60,x+w-26,y+148),radius=22,fill=(34,91,69))
    d.text((x+48,y+86),text,font=font(29),fill=WHITE)

def briefing(d,y,progress=1.0,light=False):
    fill=(255,255,255) if light else (8,31,39)
    text=BLACK if light else WHITE
    line=(202,213,224) if light else (38,91,105)
    d.rounded_rectangle((44,y,676,y+360),radius=28,fill=fill,outline=line,width=3)
    d.text((70,y+24),"KI-BRIEFING",font=font(20),fill=CYAN if not light else BLUE)
    rows=[("LEISTUNG","Wallbox"),("OBJEKT","Einfamilienhaus"),("FEHLT","Foto + Termin")]
    for i,(k,v) in enumerate(rows):
        q=clamp((progress-i*0.16)/0.66)
        yy=y+82+i*78
        d.text((70,yy),k,font=font(16),fill=MUTED if not light else (92,102,118))
        if q>0:
            maxw=360; boxw=int(maxw*ease(q))
            d.rounded_rectangle((218,yy-7,218+boxw,yy+42),radius=13,fill=(18,55,65) if not light else (227,239,247))
            if q>0.52: d.text((238,yy+4),v,font=font(21),fill=text)
    if progress>0.80: pill(d,(70,y+304,420,y+348),"NÄCHSTER SCHRITT ✓",GREEN,BLACK,17)

def dashboard(d,y,progress=1.0):
    d.rounded_rectangle((38,y,682,y+370),radius=28,fill=(8,25,38),outline=(39,87,132),width=3)
    d.text((65,y+24),"OFFENE VORGÄNGE",font=font(19),fill=CYAN)
    rows=[("MÜLLER","ANGEBOT","HEUTE","IBO"),("BAUER","RÜCKFRAGE","10:30","LEA"),("SCHMIDT","NACHFASSEN","FR","IBO")]
    for i,row in enumerate(rows):
        q=clamp((progress-i*0.14)/0.70)
        if q<=0: continue
        yy=y+82+i*84; xoff=int((1-ease(q))*120)
        d.text((65+xoff,yy),row[0],font=font(23),fill=WHITE)
        d.text((240+xoff,yy+2),row[1],font=font(17,False),fill=MUTED)
        pill(d,(490+xoff,yy-5,578+xoff,yy+38),row[2],(20,60,80),WHITE,14)
        pill(d,(592+xoff,yy-5,654+xoff,yy+38),row[3],(27,55,78),CYAN,14)

def frame_challenge(t,total):
    accent=YELLOW
    if t<1.15:
        im=grid(BG["black"].copy(),(85,70,15)); d=ImageDraw.Draw(im)
        progress_bar(d,t,total,accent)
        pill(d,(34,105,210,157),"HANDWERKSBÜRO",GREEN,BLACK,16)
        pill(d,(226,105,440,157),"3-SEKUNDEN-TEST",YELLOW,BLACK,16)
        headline(d,"WAS FEHLT HIER?",195,size=76)
        pill(d,(84,320,636,382),"„KÖNNT IHR MORGEN KOMMEN?“",(22,63,49),WHITE,18,GREEN)
        # countdown pulses
        n=3-int(clamp(t/1.15)*3)
        r=int(145*(1+0.04*math.sin(t*18)))
        d.ellipse((360-r,610-r,360+r,610+r),outline=YELLOW,width=18)
        d.text((360,600),str(max(1,n)),font=font(115),fill=WHITE,anchor="mm")
        d.text((360,700),"SCHAU GENAU.",font=font(22),fill=MUTED,anchor="mm")
    elif t<3.25:
        im=grid(BG["green"].copy(),(25,90,65)); d=ImageDraw.Draw(im)
        progress_bar(d,t,total,GREEN)
        headline(d,"„KÖNNT IHR MORGEN KOMMEN?“",120,size=60)
        shake=int(math.sin(t*38)*4)
        chat_card(d,430,"„Könnt ihr morgen kommen?“",shake=shake)
        d.text((360,775),"WAS FEHLT?",font=font(34),fill=YELLOW,anchor="mm")
        for i,x in enumerate([100,310,520]):
            q=back(clamp(((t-1.15)-i*0.18)/0.55))
            if q>0:
                rr=int(28*q)
                d.ellipse((x-rr,850-rr,x+rr,850+rr),fill=RED)
                d.text((x,850),"? ",font=font(25),fill=WHITE,anchor="mm")
    elif t<5.20:
        im=BG["yellow"].copy(); d=ImageDraw.Draw(im)
        progress_bar(d,t,total,ORANGE)
        headline(d,"DIE ANTWORT:",125,color=BLACK,size=61)
        labels=[("ORT",ORANGE),("FOTO",PURPLE),("TERMIN",RED)]
        yy=420
        for i,(lab,c) in enumerate(labels):
            q=back(clamp(((t-3.25)-i*0.34)/0.65))
            if q<=0: continue
            x=int(60+(1-q)*520)
            d.rounded_rectangle((x,yy+i*125,660,yy+90+i*125),radius=22,fill=(255,255,255),outline=c,width=5)
            d.text((x+30,yy+20+i*125),lab,font=font(42),fill=BLACK)
            d.text((615,yy+45+i*125),"✓",font=font(35),fill=c,anchor="mm")
    elif t<8.70:
        im=grid(BG["cyan"].copy(),(20,83,104)); d=ImageDraw.Draw(im); brand(d)
        progress_bar(d,t,total,CYAN)
        headline(d,"DAS SYSTEM ERKENNT ES SOFORT.",105,size=55)
        chat_card(d,330,"„Könnt ihr morgen kommen?“")
        briefing(d,590,progress=(t-5.2)/3.5)
    else:
        im=grid(BG["green"].copy(),(27,96,68)); d=ImageDraw.Draw(im); brand(d)
        progress_bar(d,t,total,GREEN)
        headline(d,"AUS 1 NACHRICHT",145,size=62)
        headline(d,"WIRD 1 KLARER NÄCHSTER SCHRITT.",245,color=GREEN,size=52)
        briefing(d,500,1.0)
        pill(d,(52,1135,668,1205),"KOSTENLOSE PROZESSANALYSE",GREEN,BLACK,19)
    return im

def tab_window(d,x,y,w,h,title,color,angle=0):
    # simple browser-tab card, intentionally original
    d.rounded_rectangle((x,y,x+w,y+h),radius=18,fill=(22,24,31),outline=color,width=3)
    d.rounded_rectangle((x+15,y+15,x+w-15,y+55),radius=12,fill=(37,40,50))
    d.ellipse((x+28,y+29,x+38,y+39),fill=RED)
    d.ellipse((x+45,y+29,x+55,y+39),fill=YELLOW)
    d.ellipse((x+62,y+29,x+72,y+39),fill=GREEN)
    d.text((x+92,y+22),title,font=font(15),fill=WHITE)

def frame_tabs(t,total):
    if t<1.3:
        im=grid(BG["white"].copy(),(205,214,224)); d=ImageDraw.Draw(im)
        progress_bar(d,t,total,PURPLE)
        pill(d,(34,104,230,154),"HANDWERKSBÜRO",BLUE,WHITE,16)
        headline(d,"17 OFFENE TABS.",180,color=BLACK,size=76)
        sub(d,"Im Kopf des Chefs.",280,color=(55,60,70),size=29)
        labs=["RÜCKRUF","ANGEBOT","TERMIN","WHATSAPP","RECHNUNG","MATERIAL"]
        for i,lab in enumerate(labs):
            q=back(clamp((t-i*0.12)/0.55))
            if q<=0: continue
            x=35+(i%2)*335; y=390+(i//2)*170-int(35*q)
            tab_window(d,x,y,310,135,lab,[RED,ORANGE,PURPLE,GREEN,BLUE,CYAN][i])
    elif t<3.25:
        im=grid(BG["purple"].copy(),(92,35,126)); d=ImageDraw.Draw(im)
        progress_bar(d,t,total,PURPLE)
        headline(d,"CHEF.EXE",95,color=YELLOW,size=82)
        d.text((360,260),"RAM 99%",font=font(44),fill=WHITE,anchor="mm")
        # orbiting tasks
        labs=["ANGEBOT","TERMIN","RÜCKRUF","MAIL","WHATSAPP","NACHFASSEN"]
        for i,lab in enumerate(labs):
            ang=t*1.8+i*math.pi/3
            x=360+int(math.cos(ang)*245); y=630+int(math.sin(ang)*250)
            pill(d,(x-75,y-28,x+75,y+28),lab,(59,26,76),WHITE,14,RED)
        d.ellipse((255,525,465,735),fill=(50,24,71),outline=YELLOW,width=6)
        d.text((360,615),"CHEF",font=font(45),fill=WHITE,anchor="mm")
        d.text((360,670),"LOADING...",font=font(20),fill=MUTED,anchor="mm")
    elif t<5.10:
        im=grid(BG["red"].copy(),(105,27,42)); d=ImageDraw.Draw(im)
        progress_bar(d,t,total,RED)
        headline(d,"ERROR:",115,size=72)
        headline(d,"GEDÄCHTNIS ≠ SYSTEM.",245,color=YELLOW,size=62)
        # error bar
        p=(t-3.25)/1.85
        d.rounded_rectangle((65,560,655,620),radius=20,fill=(65,20,27))
        d.rounded_rectangle((65,560,65+int(590*clamp(p)),620),radius=20,fill=RED)
        d.text((360,690),"Wenn jeder Rückruf ein Gedächtnistest ist.",font=font(23),fill=WHITE,anchor="mm")
    elif t<9.20:
        im=grid(BG["blue"].copy(),(22,65,120)); d=ImageDraw.Draw(im); brand(d)
        progress_bar(d,t,total,BLUE)
        headline(d,"RAUS AUS DEM KOPF.",105,size=68)
        sub(d,"Status + Verantwortlicher + nächster Schritt",205,color=WHITE,size=26)
        dashboard(d,420,progress=(t-5.1)/4.1)
        # tabs shrink into dashboard
        q=clamp((t-5.1)/2.2)
        if q<1:
            for i,lab in enumerate(["RÜCKRUF","ANGEBOT","TERMIN"]):
                sx=80+i*210; sy=890
                ex=140+i*180; ey=730
                x=int(sx+(ex-sx)*ease(q)); y=int(sy+(ey-sy)*ease(q))
                pill(d,(x-70,y-24,x+70,y+24),lab,(35,39,50),WHITE,13)
    else:
        im=grid(BG["green"].copy(),(28,96,68)); d=ImageDraw.Draw(im); brand(d)
        progress_bar(d,t,total,GREEN)
        headline(d,"KEIN GEDÄCHTNISTEST MEHR.",145,size=61)
        headline(d,"JEDER SIEHT DEN STATUS.",250,color=GREEN,size=54)
        dashboard(d,500,1.0)
        pill(d,(52,1135,668,1205),"PROZESSANALYSE • LINK IM PROFIL",YELLOW,BLACK,18)
    return im

def lane(d,x0,y0,w,label,color,progress,steps):
    d.text((x0,y0-58),label,font=font(28),fill=color)
    d.rounded_rectangle((x0,y0,x0+w,y0+26),radius=13,fill=(45,48,58))
    d.rounded_rectangle((x0,y0,x0+int(w*clamp(progress)),y0+26),radius=13,fill=color)
    yy=y0+65
    for i,step in enumerate(steps):
        threshold=(i+1)/len(steps)
        active=progress>=threshold
        fill=color if active else (55,58,68)
        d.ellipse((x0,yy+i*72,x0+26,yy+26+i*72),fill=fill)
        d.text((x0+40,yy-2+i*72),step,font=font(18),fill=WHITE if active else MUTED)

def frame_race(t,total):
    im=BG["black"].copy(); d=ImageDraw.Draw(im)
    progress_bar(d,t,total,CYAN)
    if t<1.25:
        # Immediate niche-specific split-screen: same inquiry, two workflows.
        d.rectangle((0,90,360,RH),fill=(48,9,15))
        d.rectangle((360,90,RW,RH),fill=(4,43,31))
        pill(d,(245,108,475,156),"HANDWERKSBÜRO",YELLOW,BLACK,15)
        d.text((360,225),"GLEICHE ANFRAGE.",font=font(48),fill=WHITE,anchor="mm")
        d.text((360,285),"ZWEI ABLÄUFE.",font=font(48),fill=YELLOW,anchor="mm")
        d.text((180,390),"SUCHEN",font=font(38),fill=RED,anchor="mm")
        d.text((180,455),"NACHFRAGEN",font=font(29),fill=WHITE,anchor="mm")
        d.text((180,515),"ERINNERN",font=font(29),fill=WHITE,anchor="mm")
        d.text((540,390),"ANFRAGE",font=font(38),fill=GREEN,anchor="mm")
        d.text((540,455),"KI → OWNER",font=font(29),fill=WHITE,anchor="mm")
        d.text((540,515),"NÄCHSTER SCHRITT",font=font(24),fill=WHITE,anchor="mm")
        d.text((360,655),"WELCHER ABLAUF GEWINNT?",font=font(31),fill=YELLOW,anchor="mm")
    elif t<8.80:
        d.rectangle((0,90,360,RH),fill=(40,8,13))
        d.rectangle((360,90,RW,RH),fill=(3,36,28))
        d.line((360,100,360,1120),fill=(110,115,130),width=3)
        headline(d,"DER GLEICHE VORGANG.",105,size=53)
        p=(t-1.25)/7.55
        left=clamp(p*0.58)
        right=clamp(p*1.28)
        lane(d,40,355,270,"OHNE SYSTEM",RED,left,["SUCHEN","NACHFRAGEN","ERINNERN","WARTEN"])
        lane(d,400,355,270,"MIT SYSTEM",GREEN,right,["ANFRAGE","KI","OWNER","NÄCHSTER SCHRITT"])
        if right>=1 and t<7.8:
            pill(d,(412,870,666,930),"FERTIG ✓",GREEN,BLACK,24)
        if t>6.6 and left<1:
            pill(d,(55,870,305,930),"NOCH OFFEN …",RED,WHITE,19)
    elif t<10.20:
        im=grid(BG["green"].copy(),(28,96,68)); d=ImageDraw.Draw(im)
        headline(d,"GEWINNER:",140,size=57)
        headline(d,"DER KLARE PROZESS.",250,color=GREEN,size=75)
        d.text((360,650),"✓",font=font(180),fill=GREEN,anchor="mm")
        d.text((360,790),"Nicht schneller reden.\nSchneller wissen, was als Nächstes passiert.",font=font(24),fill=WHITE,anchor="mm",align="center",spacing=7)
    else:
        im=grid(BG["cyan"].copy(),(21,83,102)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"DU SIEHST DEN UNTERSCHIED.",145,size=60)
        briefing(d,480,1.0)
        pill(d,(52,1135,668,1205),"KOSTENLOSE PROZESSANALYSE",GREEN,BLACK,19)
    return im

def make_bed(total,path):
    sr=48000; n=int(total*sr); data=[0.0]*n; beat=60/134
    for k in range(int(total/beat)+2):
        st=int(k*beat*sr)
        for j in range(min(int(.11*sr),n-st)):
            tt=j/sr; env=math.exp(-tt*28)
            data[st+j]+=0.16*env*math.sin(2*math.pi*(74-25*tt)*tt)
    for k in range(int(total/(beat/2))+2):
        st=int(k*beat/2*sr)
        for j in range(min(int(.022*sr),n-st)):
            env=1-j/(.022*sr); data[st+j]+=0.018*env*(random.random()*2-1)
    with wave.open(str(path),"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames=bytearray()
        for x in data:
            x=max(-1,min(1,x)); frames += struct.pack("<h",int(x*32767))
        wf.writeframes(frames)

def render(reel):
    total=float(reel.get("duration",12.4))
    fmt=reel.get("format","challenge")
    frame_fn=frame_challenge if "challenge" in fmt else frame_tabs if "tabs" in fmt else frame_race
    work=TMP/reel["id"]; shutil.rmtree(work,ignore_errors=True); work.mkdir(parents=True)
    bed=work/"bed.wav"; make_bed(total,bed)
    out=OUT/f"{reel['id']}.mp4"
    cmd=[
      "ffmpeg","-y",
      "-f","rawvideo","-pix_fmt","rgb24","-s",f"{RW}x{RH}","-r",str(FPS),"-i","-",
      "-i",str(bed),
      "-vf","scale=1080:1920:flags=lanczos,format=yuv420p",
      "-map","0:v:0","-map","1:a:0","-t",f"{total:.3f}",
      "-c:v","libx264","-preset","veryfast","-crf","20",
      "-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)
    ]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frames=max(1,int(total*FPS))
    for i in range(frames):
        t=i/FPS
        im=frame_fn(t,total)
        im=draw_caption(im,reel,t)
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); rc=p.wait()
    if rc!=0: raise RuntimeError(f"ffmpeg failed for {reel['id']}")
    print(f"rendered-attention-v8 {out.relative_to(ROOT)} {total:.2f}s")

def main():
    OUT.mkdir(parents=True,exist_ok=True); TMP.mkdir(parents=True,exist_ok=True)
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    for reel in data["reels"]: render(reel)
    shutil.rmtree(TMP,ignore_errors=True)

if __name__=="__main__": main()
