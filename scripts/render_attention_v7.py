#!/usr/bin/env python3
import json, math, random, shutil, subprocess, wave, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"content/daily_premium.json"
OUT=ROOT/"media/daily-premium"
TMP=ROOT/".attention_v7_tmp"
RW,RH,FPS=720,1280,30

FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
WHITE=(248,250,252); BLACK=(10,12,16); MUTED=(166,176,192)
RED=(255,66,78); GREEN=(50,222,144); CYAN=(48,214,255); BLUE=(45,117,255)
YELLOW=(255,214,65); ORANGE=(255,126,44); PURPLE=(166,82,255)

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
 "green":gradient((3,22,17),(4,45,30)),
 "red":gradient((35,5,10),(62,10,20)),
 "yellow":gradient((248,244,225),(255,229,135)),
 "cyan":gradient((3,17,24),(5,43,55)),
 "purple":gradient((18,8,32),(49,15,73)),
 "blue":gradient((5,12,25),(8,28,55)),
 "orange":gradient((36,12,4),(74,26,7)),
 "white":gradient((248,247,241),(231,239,245)),
 "black":gradient((3,4,7),(12,14,20))
}
ACC={"green":GREEN,"red":RED,"yellow":YELLOW,"cyan":CYAN,"purple":PURPLE,"blue":BLUE,"orange":ORANGE,"white":BLACK,"black":WHITE}

def wrap(draw,text,f,mw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if draw.textbbox((0,0),test,font=f)[2] <= mw: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return "\n".join(lines)

def grid(im, color, step=90, alpha=30):
    ov=Image.new("RGBA",im.size,(0,0,0,0)); d=ImageDraw.Draw(ov)
    for x in range(0,RW,step): d.line((x,0,x,RH),fill=(*color,alpha),width=1)
    for y in range(0,RH,step): d.line((0,y,RW,y),fill=(*color,alpha),width=1)
    return Image.alpha_composite(im.convert("RGBA"),ov).convert("RGB")

def brand(d,light=False):
    c=BLACK if light else WHITE
    d.rounded_rectangle((36,38,58,60),radius=5,fill=BLUE)
    d.text((72,35),"SLEIMAN SYSTEMS",font=font(19),fill=c)

def pill(d,xy,text,fill,textfill=WHITE,fs=17):
    d.rounded_rectangle(xy,radius=16,fill=fill)
    d.text(((xy[0]+xy[2])//2,(xy[1]+xy[3])//2),text,font=font(fs),fill=textfill,anchor="mm")

def headline(d,text,y,color=WHITE,size=70,center=False):
    f=font(size)
    txt=wrap(d,text,f,RW-70)
    if center:
        box=d.multiline_textbbox((0,0),txt,font=f,spacing=2,align="center")
        w=box[2]-box[0]
        d.multiline_text(((RW-w)//2,y),txt,font=f,fill=color,spacing=2,align="center")
    else:
        d.multiline_text((34,y),txt,font=f,fill=color,spacing=2)

def sub(d,text,y,color=MUTED,size=25):
    f=font(size,False); txt=wrap(d,text,f,RW-70)
    d.multiline_text((36,y),txt,font=f,fill=color,spacing=6)

def chat_card(d,y,text,scale=1.0,shake=0):
    x=55+shake; w=610
    d.rounded_rectangle((x,y,x+w,y+230),radius=28,fill=(18,24,27),outline=(50,115,89),width=3)
    d.text((x+28,y+22),"NEUE WHATSAPP",font=font(18),fill=GREEN)
    d.rounded_rectangle((x+28,y+64,x+w-28,y+153),radius=22,fill=(34,93,70))
    d.text((x+52,y+88),text,font=font(30),fill=WHITE)
    d.ellipse((x+w-85,y+12,x+w-24,y+73),fill=RED)
    d.text((x+w-54,y+43),"1",font=font(25),fill=WHITE,anchor="mm")

def missing_chips(d,y,p=1.0,dark=True):
    labels=[("ORT ?",ORANGE),("FOTO ?",YELLOW),("TERMIN ?",RED)]
    xs=[44,255,466]
    for i,(lab,c) in enumerate(labels):
        q=clamp((p-i*0.15)/0.65)
        if q<=0: continue
        h=int(70*back(q)); cy=y+35
        fill=(22,24,28) if dark else (255,255,255)
        d.rounded_rectangle((xs[i],cy-h//2,xs[i]+190,cy+h//2),radius=18,fill=fill,outline=c,width=3)
        d.text((xs[i]+95,cy),lab,font=font(25),fill=c,anchor="mm")

def briefing(d,y,progress=1.0,light=False):
    fill=(255,255,255) if light else (8,33,40)
    text=BLACK if light else WHITE
    line=(205,214,224) if light else (38,90,105)
    d.rounded_rectangle((44,y,676,y+360),radius=28,fill=fill,outline=line,width=3)
    d.text((70,y+24),"KI-BRIEFING",font=font(20),fill=CYAN if not light else BLUE)
    rows=[("LEISTUNG","Wallbox"),("OBJEKT","Einfamilienhaus"),("FEHLT","Foto + Termin")]
    for i,(k,v) in enumerate(rows):
        q=clamp((progress-i*0.17)/0.66)
        yy=y+82+i*78
        d.text((70,yy),k,font=font(16),fill=MUTED if not light else (100,110,125))
        if q>0:
            maxw=360
            boxw=int(maxw*ease(q))
            d.rounded_rectangle((218,yy-7,218+boxw,yy+42),radius=13,fill=(18,55,65) if not light else (228,239,247))
            if q>0.55: d.text((238,yy+4),v,font=font(21),fill=text)
    if progress>0.8:
        pill(d,(70,y+304,420,y+348),"NÄCHSTER SCHRITT ✓",GREEN,BLACK,17)

def dashboard(d,y,progress=1.0):
    d.rounded_rectangle((38,y,682,y+385),radius=28,fill=(8,25,38),outline=(38,86,130),width=3)
    d.text((65,y+24),"OFFENE VORGÄNGE",font=font(19),fill=CYAN)
    rows=[("MÜLLER","ANGEBOT","HEUTE","IBO"),("BAUER","RÜCKFRAGE","10:30","LEA"),("SCHMIDT","NACHFASSEN","FR","IBO")]
    for i,row in enumerate(rows):
        q=clamp((progress-i*0.14)/0.7)
        if q<=0: continue
        yy=y+82+i*88
        xoff=int((1-ease(q))*110)
        d.text((65+xoff,yy),row[0],font=font(23),fill=WHITE)
        d.text((240+xoff,yy+2),row[1],font=font(17,False),fill=MUTED)
        pill(d,(490+xoff,yy-5,578+xoff,yy+38),row[2],(20,60,80),WHITE,14)
        pill(d,(592+xoff,yy-5,654+xoff,yy+38),row[3],(27,55,78),CYAN,14)

def brain_meme(d,y,t):
    # original meme-style "CHEF.EXE" overload, not copied from a third-party meme
    cx,cy=360,y+190
    pulse=1+0.035*math.sin(t*18)
    r=int(135*pulse)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(54,27,77),outline=PURPLE,width=5)
    d.text((cx,cy-22),"CHEF.EXE",font=font(38),fill=YELLOW,anchor="mm")
    d.text((cx,cy+34),"99% RAM",font=font(24),fill=WHITE,anchor="mm")
    badges=[("RÜCKRUF",0.2),("ANGEBOT",1.1),("TERMIN",2.0),("NACHFASSEN",2.8)]
    for i,(lab,ph) in enumerate(badges):
        ang=t*1.5+ph
        x=cx+int(math.cos(ang)*245)-75
        yy=cy+int(math.sin(ang)*160)-25
        d.rounded_rectangle((x,yy,x+150,yy+52),radius=14,fill=(62,25,78),outline=RED,width=2)
        d.text((x+75,yy+26),lab,font=font(15),fill=WHITE,anchor="mm")

def timer_ring(d,cx,cy,p,color=ORANGE):
    r=145
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(75,75,82),width=18)
    start=-90; end=start+360*clamp(p)
    d.arc((cx-r,cy-r,cx+r,cy+r),start=start,end=end,fill=color,width=18)
    sec=max(0,7-int(p*7))
    d.text((cx,cy-10),str(sec),font=font(86),fill=WHITE,anchor="mm")
    d.text((cx,cy+66),"SEK.",font=font(18),fill=MUTED,anchor="mm")

def frame_whatsapp(t):
    if t<0.7:
        im=grid(BG["green"].copy(),(29,92,70)); d=ImageDraw.Draw(im)
        headline(d,"„KÖNNT IHR MORGEN KOMMEN?“",105,size=63)
        shake=int(math.sin(t*45)*5)
        chat_card(d,610,"„Könnt ihr morgen kommen?“",shake=shake)
    elif t<1.3:
        im=grid(BG["red"].copy(),(100,35,42)); d=ImageDraw.Draw(im)
        p=back((t-0.7)/0.6); size=int(80+45*p)
        d.text((RW//2,240),"STOP",font=font(size),fill=WHITE,anchor="mm")
        r=int(170*p)
        d.ellipse((RW//2-r,500-r,RW//2+r,500+r),outline=RED,width=max(3,int(14*p)))
        d.text((RW//2,500),"STOP",font=font(int(72*p+1)),fill=WHITE,anchor="mm")
        d.text((RW//2,610),"NICHT BLIND ANTWORTEN",font=font(22),fill=YELLOW,anchor="mm")
    elif t<2.25:
        im=BG["yellow"].copy(); d=ImageDraw.Draw(im)
        headline(d,"3 INFOS FEHLEN.",110,color=BLACK,size=72)
        sub(d,"Genau hier entstehen die Rückfragen.",210,color=(65,65,70),size=25)
        missing_chips(d,500,(t-1.3)/0.95,dark=False)
    elif t<4.45:
        im=grid(BG["cyan"].copy(),(20,85,105)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"KI MARKIERT, WAS FEHLT.",120,size=57)
        chat_card(d,360,"„Könnt ihr morgen kommen?“")
        briefing(d,650,progress=(t-2.25)/2.2)
        # moving arrow
        x=80+int(((t-2.25)/2.2)*520)
        d.line((80,1030,x,1030),fill=CYAN,width=7)
        d.polygon([(x,1030),(x-20,1015),(x-20,1045)],fill=CYAN)
    elif t<7.0:
        im=grid(BG["blue"].copy(),(22,65,120)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"AUS CHAT WIRD BRIEFING.",125,size=61)
        briefing(d,460,progress=1.0)
        pill(d,(65,875,655,945),"LEISTUNG • OBJEKT • FEHLENDES", (18,55,89),WHITE,18)
    else:
        im=grid(BG["green"].copy(),(28,95,67)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"DU PRÜFST. FERTIG.",160,size=72)
        dashboard(d,470,1.0)
        pill(d,(55,1040,665,1120),"KOSTENLOSE PROZESSANALYSE",GREEN,BLACK,20)
        sub(d,"Link im Profil",1145,color=WHITE,size=23)
    return im

def frame_boss(t):
    if t<0.65:
        im=BG["yellow"].copy(); d=ImageDraw.Draw(im)
        headline(d,"„CHEF, WO IST ANGEBOT MÜLLER?“",95,color=BLACK,size=59)
        # notification bubbles bounce in
        for i,x in enumerate([70,285,500]):
            q=back(clamp((t-i*0.12)/0.4))
            yy=650-int(160*q)
            pill(d,(x,yy,x+150,yy+70),["RÜCKRUF","ANGEBOT","TERMIN"][i],RED,WHITE,16)
    elif t<1.35:
        im=grid(BG["purple"].copy(),(95,36,130)); d=ImageDraw.Draw(im)
        headline(d,"CHEF.EXE",100,color=YELLOW,size=82)
        sub(d,"lädt ...",205,color=WHITE,size=30)
        brain_meme(d,410,t)
    elif t<2.35:
        im=grid(BG["red"].copy(),(105,27,42)); d=ImageDraw.Draw(im)
        # glitch text
        headline(d,"ALLES NUR IM KOPF?",135,size=72)
        off=int(math.sin(t*42)*5)
        d.text((40+off,370),"DANN HÄNGT DER ABLAUF",font=font(33),fill=CYAN)
        d.text((40-off,410),"AN EINER PERSON.",font=font(39),fill=YELLOW)
        brain_meme(d,610,t)
    elif t<5.2:
        im=grid(BG["blue"].copy(),(23,65,125)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"STATUS MUSS SICHTBAR SEIN.",110,size=57)
        dashboard(d,400,progress=(t-2.35)/2.85)
    elif t<8.0:
        im=BG["white"].copy(); d=ImageDraw.Draw(im); brand(d,light=True)
        headline(d,"STATUS. DATUM. OWNER.",125,color=BLACK,size=61)
        y=430
        vals=[("STATUS","ANGEBOT OFFEN",BLUE),("DATUM","HEUTE",ORANGE),("OWNER","IBO",PURPLE)]
        for i,(k,v,c) in enumerate(vals):
            q=back(clamp(((t-5.2)-i*0.22)/0.7))
            if q<=0: continue
            x=int(45+(1-q)*500)
            d.rounded_rectangle((x,y+i*145,675,y+110+i*145),radius=22,fill=(255,255,255),outline=c,width=4)
            d.text((x+25,y+18+i*145),k,font=font(17),fill=(90,100,115))
            d.text((x+25,y+50+i*145),v,font=font(31),fill=BLACK)
    else:
        im=grid(BG["green"].copy(),(30,100,71)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"WENIGER NACHFRAGEN.",150,size=70)
        headline(d,"MEHR KLARHEIT.",255,color=GREEN,size=70)
        pill(d,(55,730,665,815),"STIMMT ODER NICHT?",YELLOW,BLACK,23)
        sub(d,"Schreib's in die Kommentare.",850,color=WHITE,size=27)
    return im

def frame_demo(t):
    if t<0.65:
        im=grid(BG["orange"].copy(),(115,55,20)); d=ImageDraw.Draw(im)
        headline(d,"7 SEKUNDEN.",105,size=84)
        sub(d,"Was macht Sleiman Systems?",210,color=WHITE,size=28)
        timer_ring(d,360,650,t/0.65,ORANGE)
    elif t<1.30:
        im=grid(BG["cyan"].copy(),(22,88,108)); d=ImageDraw.Draw(im)
        headline(d,"NICHT ERKLÄREN.",115,size=68)
        headline(d,"ZEIGEN.",235,color=CYAN,size=82)
        d.polygon([(330,560),(430,640),(330,720)],fill=GREEN)
    elif t<2.25:
        im=grid(BG["green"].copy(),(25,95,70)); d=ImageDraw.Draw(im)
        headline(d,"1. ANFRAGE REIN.",110,size=65)
        chat_card(d,460,"„Wallbox nächste Woche?“",shake=int(math.sin(t*30)*3))
    elif t<4.35:
        im=grid(BG["purple"].copy(),(93,35,127)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"2. KI STRUKTURIERT.",110,size=60)
        briefing(d,400,progress=(t-2.25)/2.1)
    elif t<6.45:
        im=grid(BG["blue"].copy(),(24,68,125)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"3. OWNER + NÄCHSTER SCHRITT.",100,size=52)
        dashboard(d,390,progress=(t-4.35)/2.1)
    elif t<7.65:
        im=BG["white"].copy(); d=ImageDraw.Draw(im); brand(d,light=True)
        headline(d,"4. DU PRÜFST.",155,color=BLACK,size=78)
        d.rounded_rectangle((135,530,585,790),radius=38,fill=(233,249,240),outline=GREEN,width=7)
        d.text((360,625),"✓",font=font(110),fill=GREEN,anchor="mm")
        d.text((360,720),"ENTSCHEIDUNG BLEIBT BEI DIR",font=font(19),fill=BLACK,anchor="mm")
    else:
        im=grid(BG["green"].copy(),(29,98,70)); d=ImageDraw.Draw(im); brand(d)
        headline(d,"DAS IST SLEIMAN SYSTEMS.",130,size=61)
        sub(d,"Anfrage → Struktur → Verantwortung → nächster Schritt",245,color=WHITE,size=24)
        pill(d,(55,720,665,810),"KOSTENLOSE PROZESSANALYSE",GREEN,BLACK,20)
        sub(d,"Link im Profil",840,color=WHITE,size=25)
    return im

def make_bed(total,path):
    sr=48000; n=int(total*sr); data=[0.0]*n
    beat=60/132
    for k in range(int(total/beat)+2):
        st=int(k*beat*sr)
        for j in range(min(int(.12*sr),n-st)):
            tt=j/sr; env=math.exp(-tt*27)
            data[st+j]+=0.17*env*math.sin(2*math.pi*(72-25*tt)*tt)
    for k in range(int(total/(beat/2))+2):
        st=int((k*beat/2)*sr)
        for j in range(min(int(.025*sr),n-st)):
            env=1-j/(.025*sr); data[st+j]+=0.020*env*(random.random()*2-1)
    with wave.open(str(path),"w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames=bytearray()
        for x in data:
            x=max(-1,min(1,x)); frames += struct.pack("<h",int(x*32767))
        wf.writeframes(frames)

def render(reel):
    durations=reel.get("scene_durations") or []
    total=sum(durations)-0.14*(len(durations)-1) if durations else 10.0
    fmt=reel.get("format","")
    frame_fn=frame_whatsapp if "whatsapp" in fmt else frame_boss if "boss" in fmt else frame_demo
    work=TMP/reel["id"]; shutil.rmtree(work,ignore_errors=True); work.mkdir(parents=True)
    bed=work/"bed.wav"; make_bed(total,bed)
    out=OUT/f"{reel['id']}.mp4"
    cmd=[
      "ffmpeg","-y",
      "-f","rawvideo","-pix_fmt","rgb24","-s",f"{RW}x{RH}","-r",str(FPS),"-i","-",
      "-i",str(bed),
      "-vf","scale=1080:1920:flags=lanczos,format=yuv420p",
      "-map","0:v:0","-map","1:a:0","-t",f"{total:.3f}",
      "-c:v","libx264","-preset","veryfast","-crf","21",
      "-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)
    ]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frames=max(1,int(total*FPS))
    for i in range(frames):
        t=i/FPS
        im=frame_fn(t)
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); rc=p.wait()
    if rc!=0: raise RuntimeError(f"ffmpeg failed for {reel['id']}")
    print(f"rendered-attention {out.relative_to(ROOT)} {total:.2f}s")

def main():
    OUT.mkdir(parents=True,exist_ok=True); TMP.mkdir(parents=True,exist_ok=True)
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    for reel in data["reels"]: render(reel)
    shutil.rmtree(TMP,ignore_errors=True)

if __name__=="__main__": main()
