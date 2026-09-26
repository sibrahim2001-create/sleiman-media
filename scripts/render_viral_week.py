#!/usr/bin/env python3
import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "media/viral-week-2026-09-23"
TMP = ROOT / ".fast_cut_tmp"
W, H = 1080, 1920
FPS = 30

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

WHITE = (248, 250, 252)
MUTED = (172, 184, 200)
BLUE = (40, 116, 255)
RED = (255, 72, 72)
DARK = (5, 8, 13)
DARK2 = (11, 17, 27)
CARD = (18, 27, 41)

REELS = [
    {
        "id": "viral-2026-09-27-01",
        "accent": "red",
        "scenes": [
            ("STOPP.", "ICH RUF SPÄTER ZURÜCK.", "Der teuerste Satz im Handwerk?"),
            ("48H", "SPÄTER.", "Der Kunde wartet nicht ewig."),
            ("3", "OFFENE RÜCKRUFE.", "Und keiner hat einen Termin."),
            ("CRM", "GEDÄCHTNIS IST KEINS.", "Jeder Kontakt braucht Status."),
            ("NEXT", "NÄCHSTER SCHRITT.", "Mit Datum. Sofort."),
            ("SYSTEM", "STATT GEDÄCHTNIS.", "@sleimansystems"),
        ],
    },
    {
        "id": "viral-2026-09-27-02",
        "accent": "blue",
        "scenes": [
            ("ELEKTRIKER?", "KOPIER DAS.", "Für die nächste Kundenanfrage."),
            ("1", "STRUKTURIERE.", "Was will der Kunde wirklich?"),
            ("2", "FINDE LÜCKEN.", "Welche Angaben fehlen?"),
            ("3", "3 RÜCKFRAGEN.", "Kurz. Klar. Kundentauglich."),
            ("REGEL", "NICHTS ERFINDEN.", "Unklarheiten markieren."),
            ("SAVE", "SPÄTER TESTEN.", "@sleimansystems"),
        ],
    },
    {
        "id": "viral-2026-09-27-03",
        "accent": "blue",
        "scenes": [
            ("30 MIN", "PRO ANGEBOT.", "Klingt erstmal wenig."),
            ("× 40", "ANGEBOTE.", "Im Monat."),
            ("=", "20 STUNDEN.", "Nur Angebotserstellung."),
            ("PLUS", "RÜCKFRAGEN.", "Noch nicht eingerechnet."),
            ("PLUS", "NACHFASSEN.", "Auch noch nicht."),
            ("PROZESS", "NICHT FLEISS.", "Erst Ablauf verbessern."),
        ],
    },
    {
        "id": "viral-2026-09-27-04",
        "accent": "red",
        "scenes": [
            ("ANGEBOT", "RAUS. UND DANN?", "Genau hier geht es oft verloren."),
            ("TAG 1", "GESENDET.", "Alles gut."),
            ("TAG 3", "FUNKSTILLE.", "Noch kein nächster Schritt."),
            ("TAG 7", "VERGESSEN.", "Weil keiner erinnert."),
            ("FIX", "TERMIN SETZEN.", "Direkt beim Versand."),
            ("FOLLOW-UP", "NICHT ZUFALL.", "@sleimansystems"),
        ],
    },
    {
        "id": "viral-2026-09-27-05",
        "accent": "blue",
        "scenes": [
            ("CHEF", "ALLES LANDET BEI DIR?", "Dann bist du der Flaschenhals."),
            ("ANFRAGE", "→ CHEF", "Jedes Mal."),
            ("ANGEBOT", "→ CHEF", "Jedes Mal."),
            ("RÜCKRUF", "→ CHEF", "Jedes Mal."),
            ("SYSTEM", "STATUS + OWNER + DATUM", "Aufgaben brauchen Struktur."),
            ("START", "ERST SYSTEMISIEREN.", "KI-Office Kit • Link im Profil"),
        ],
    },
]

def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size)

def wrap(draw, text, fnt, width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return "\n".join(lines)

def bg(accent, idx):
    im = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(im)
    # diagonal depth bands
    for y in range(H):
        t = y / H
        c = (
            int(DARK[0] * (1-t) + DARK2[0] * t),
            int(DARK[1] * (1-t) + DARK2[1] * t),
            int(DARK[2] * (1-t) + DARK2[2] * t),
        )
        d.line((0, y, W, y), fill=c)
    a = RED if accent == "red" else BLUE
    # huge cropped accent circle adds motion-friendly depth
    cx = W + 120 - (idx % 3) * 70
    cy = 270 + (idx % 2) * 150
    d.ellipse((cx-380, cy-380, cx+380, cy+380), fill=tuple(max(0, x//5) for x in a))
    # small grid / dashboard feeling
    for x in range(0, W, 135):
        d.line((x, 0, x, H), fill=(13, 20, 31), width=1)
    for y in range(0, H, 135):
        d.line((0, y, W, y), fill=(13, 20, 31), width=1)
    return im

def make_scene(reel, idx, scene, path):
    kicker, headline, body = scene
    im = bg(reel["accent"], idx)
    d = ImageDraw.Draw(im)
    a = RED if reel["accent"] == "red" else BLUE

    # top identity — deliberately tiny, hook dominates
    d.rounded_rectangle((60, 66, 82, 88), radius=6, fill=a)
    d.text((101, 60), "SLEIMAN SYSTEMS", font=font(29), fill=WHITE)

    # sequence indicator
    for i in range(6):
        x0 = 62 + i * 154
        d.rounded_rectangle((x0, 125, x0 + 128, 135), radius=5,
                            fill=a if i == idx else (45, 55, 70))

    # kicker chip
    kf = font(50)
    kw = d.textbbox((0,0), kicker, font=kf)[2] + 56
    d.rounded_rectangle((64, 260, min(W-64, 64+kw), 348), radius=25,
                        fill=a)
    d.text((92, 275), kicker, font=kf, fill=WHITE)

    # headline
    hf = font(105)
    htxt = wrap(d, headline, hf, 930)
    bbox = d.multiline_textbbox((0,0), htxt, font=hf, spacing=12)
    hh = bbox[3] - bbox[1]
    hy = 455
    d.multiline_text((64, hy), htxt, font=hf, fill=WHITE, spacing=12)

    # body card
    by = min(1260, hy + hh + 100)
    d.rounded_rectangle((64, by, W-64, by+250), radius=34, fill=CARD,
                        outline=(43, 57, 78), width=2)
    bf = font(48, False)
    btxt = wrap(d, body, bf, 840)
    d.multiline_text((100, by+58), btxt, font=bf, fill=MUTED, spacing=14)

    # punchy bottom stripe
    d.rectangle((0, H-165, W, H), fill=a)
    bottom = "WENIGER BÜRO. MEHR STRUKTUR." if idx < 5 else "@sleimansystems"
    d.text((W//2, H-82), bottom, font=font(38), fill=WHITE, anchor="mm")
    im.save(path)

def render(reel):
    work = TMP / reel["id"]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    pngs = []
    for i, scene in enumerate(reel["scenes"]):
        p = work / f"s{i}.png"
        make_scene(reel, i, scene, p)
        pngs.append(p)

    # 0.95 sec per card; quick 0.12 sec wipes: around 5.2 sec total.
    seg, trans = 0.95, 0.12
    args = ["ffmpeg", "-y"]
    for p in pngs:
        args += ["-loop", "1", "-framerate", str(FPS), "-t", str(seg), "-i", str(p)]

    total = seg * len(pngs) - trans * (len(pngs)-1)
    # zero-cost generated tick + low bass pulse
    args += [
        "-f", "lavfi", "-t", f"{total:.3f}", "-i",
        "sine=frequency=95:sample_rate=44100",
        "-f", "lavfi", "-t", f"{total:.3f}", "-i",
        "sine=frequency=880:sample_rate=44100",
    ]

    filters = []
    # slight different zoom/crop per scene -> more perspective change
    for i in range(len(pngs)):
        z = "min(zoom+0.0025,1.08)" if i % 2 == 0 else "min(zoom+0.0015,1.05)"
        filters.append(
            f"[{i}:v]scale=1200:2133,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d={int(seg*FPS)}:s={W}x{H}:fps={FPS},"
            f"format=yuv420p,setsar=1[v{i}]"
        )

    transitions = ["slideleft", "slideright", "wipeleft", "slideup", "wiperight"]
    prev = "v0"
    offset = seg - trans
    for i in range(1, len(pngs)):
        out = f"x{i}"
        tr = transitions[(i-1) % len(transitions)]
        filters.append(f"[{prev}][v{i}]xfade=transition={tr}:duration={trans}:offset={offset:.2f}[{out}]")
        prev = out
        offset += seg - trans

    a0, a1 = len(pngs), len(pngs)+1
    filters.append(f"[{a0}:a]volume=0.028,apulsator=hz=2.0[a0]")
    filters.append(f"[{a1}:a]volume=0.010,apulsator=hz=4.0[a1]")
    filters.append("[a0][a1]amix=inputs=2:duration=longest,afade=t=in:st=0:d=0.08[a]")

    outfile = OUT / f"{reel['id']}.mp4"
    args += [
        "-filter_complex", ";".join(filters),
        "-map", f"[{prev}]", "-map", "[a]",
        "-t", f"{total:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart", str(outfile),
    ]
    subprocess.run(args, check=True)
    print(f"rendered {outfile.relative_to(ROOT)} ({total:.2f}s)")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    for reel in REELS:
        render(reel)
    shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    main()
