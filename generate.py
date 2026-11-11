import asyncio
import json
import math
import random
import subprocess
import wave
import struct
from pathlib import Path
from datetime import datetime

import edge_tts
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (255, 244, 226)
INK = (55, 55, 78)
PALETTE = [(255, 219, 172), (205, 232, 245), (239, 218, 245), (215, 239, 207), (255, 229, 190)]

# Sketches humoristiques originaux, avec dialogues courts pour YouTube Shorts.
SONGS = [
    {
        "title": "Bouki et le téléphone intelligent",
        "lines": [
            "Au village, Bouki arrive tout fier : « J'ai acheté un téléphone intelligent ! »",
            "Le lion demande : « Il sait faire quoi ? » Bouki répond : « Il réfléchit à ma place ! »",
            "Le lion dit : « Alors demande-lui où tu as posé ton téléphone. »",
            "Bouki regarde sa main : « Aïe ! Je suis en train de lui parler dessus ! »",
            "Le téléphone sonne. C'est le lion qui appelle. Bouki crie : « Même mon téléphone se moque de moi ! »"
        ],
    },
    {
        "title": "Bouki devient milliardaire",
        "lines": [
            "Bouki annonce au village : « Demain, je serai milliardaire ! »",
            "Le lapin demande : « Tu as gagné à la loterie ? » Bouki répond : « Non, j'ai un grand projet ! »",
            "« Quel projet ? » demande le lion. Bouki dit : « Je vais vendre de l'eau à la rivière ! »",
            "Le lion éclate de rire : « Mais qui va acheter ça ? »",
            "Bouki sourit : « Ceux qui n'ont pas le temps d'aller jusqu'à la rivière ! »"
        ],
    },
    {
        "title": "Le repas de Bouki",
        "lines": [
            "Bouki entre dans la cuisine : « Aujourd'hui, je prépare le meilleur repas du village ! »",
            "Il met du piment, du sel, du citron... puis encore du piment.",
            "Le lapin goûte une cuillère et se met à courir en rond.",
            "Le lion demande : « Alors, c'est bon ? » Le lapin répond : « Je ne sais pas, ma bouche a démissionné ! »",
            "Bouki goûte à son tour : « Parfait ! Demain, je cuisine avec un extincteur ! »"
        ],
    },
    {
        "title": "Bouki et le parapluie inutile",
        "lines": [
            "Bouki ouvre une boutique de parapluies en plein soleil.",
            "Le lapin demande : « Mais il ne pleut même pas ! »",
            "Bouki répond : « Je vends la protection contre la pluie de demain ! »",
            "Le lion demande : « Et si demain il fait soleil ? »",
            "Bouki sourit : « Alors je vends l'ombre avec le parapluie ! »"
        ],
    },
    {
        "title": "Bouki passe son permis",
        "lines": [
            "Bouki arrive à l'examen de conduite avec un grand sourire.",
            "Le moniteur crie : « Démarre doucement ! »",
            "Bouki répond : « Impossible, monsieur, la voiture dort encore ! »",
            "Le moniteur dit : « Freine ! » Bouki demande : « Où est le bouton pause ? »",
            "Le lion conclut : « Donnez-lui plutôt un permis de marcher ! »"
        ],
    },
]

VISUAL_STYLES = {
    "Bouki et le téléphone intelligent": {
        "setting": "village",
        "characters": ["hyena", "lion", "hyena", "lion", "hyena"],
        "expressions": ["proud", "curious", "thinking", "shocked", "laughing"],
        "props": ["phone", "phone", "phone", "phone", "phone"],
    },
    "Bouki devient milliardaire": {
        "setting": "market",
        "characters": ["hyena", "rabbit", "lion", "hyena", "lion"],
        "expressions": ["proud", "curious", "scheming", "laughing", "proud"],
        "props": ["coins", "bag", "bucket", "coins", "coins"],
    },
    "Le repas de Bouki": {
        "setting": "kitchen",
        "characters": ["hyena", "hyena", "rabbit", "lion", "hyena"],
        "expressions": ["proud", "focused", "shocked", "laughing", "surprised"],
        "props": ["pot", "pepper", "bowl", "pot", "fire"],
    },
    "Bouki et le parapluie inutile": {
        "setting": "market",
        "characters": ["hyena", "rabbit", "hyena", "lion", "hyena"],
        "expressions": ["proud", "curious", "scheming", "confused", "laughing"],
        "props": ["umbrella", "umbrella", "umbrella", "sun", "umbrella"],
    },
    "Bouki passe son permis": {
        "setting": "road",
        "characters": ["hyena", "lion", "hyena", "lion", "hyena"],
        "expressions": ["proud", "shocked", "confused", "worried", "laughing"],
        "props": ["steering", "book", "steering", "sign", "steering"],
    },
}

def get_font(size, bold=False):
    choices = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in choices:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def wrap(draw, text, fnt, width):
    result, current = [], ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= width:
            current = candidate
        else:
            if current:
                result.append(current)
            current = word
    if current:
        result.append(current)
    return result

def draw_star(draw, x, y, radius, color):
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.42
        points.append((x + math.cos(angle) * r, y + math.sin(angle) * r))
    draw.polygon(points, fill=color)


def draw_scene_background(draw, setting, index):
    # Décors vectoriels distincts pour éviter cinq images quasi identiques.
    if setting == "market":
        draw.rectangle((0, 430, W, 1320), fill=(250, 221, 177))
        for x in range(-30, W, 220):
            draw.polygon([(x, 470), (x + 110, 350), (x + 220, 470)], fill=(218, 102, 87))
            draw.rectangle((x + 20, 470, x + 200, 560), fill=(255, 238, 199))
            draw.rectangle((x + 25, 1080, x + 195, 1290), fill=(186, 126, 82), outline=INK, width=5)
        for x, y, color in [(130, 1190, (240, 115, 90)), (190, 1190, (245, 190, 70)), (870, 1190, (110, 175, 110))]:
            draw.ellipse((x - 28, y - 28, x + 28, y + 28), fill=color, outline=INK, width=3)
    elif setting == "kitchen":
        draw.rectangle((0, 400, W, 1350), fill=(240, 226, 205))
        for x in range(0, W, 135):
            draw.line((x, 420, x, 1320), fill=(216, 199, 177), width=3)
        for y in range(450, 1350, 135):
            draw.line((0, y, W, y), fill=(216, 199, 177), width=3)
        draw.rectangle((70, 500, 300, 770), fill=(185, 220, 231), outline=INK, width=7)
        draw.line((185, 500, 185, 770), fill=INK, width=5)
        draw.line((70, 635, 300, 635), fill=INK, width=5)
        draw.rectangle((760, 1110, 1030, 1270), fill=(150, 104, 77), outline=INK, width=7)
    elif setting == "river":
        draw.rectangle((0, 760, W, 1370), fill=(126, 199, 220))
        for y in range(820, 1320, 90):
            for x in range(80 + (y % 3) * 30, W, 250):
                draw.arc((x, y, x + 170, y + 55), 185, 350, fill=(255, 255, 245), width=6)
        draw.ellipse((790, 390, 970, 570), fill=(255, 203, 93))
        for x in (70, 970):
            draw.line((x, 1150, x - 25, 780), fill=(74, 137, 83), width=12)
            draw.ellipse((x - 85, 800, x + 20, 870), fill=(99, 165, 94))
    elif setting == "road":
        draw.rectangle((0, 500, W, 1330), fill=(210, 229, 237))
        draw.rectangle((0, 1030, W, 1370), fill=(91, 97, 111))
        for x in range(50, W, 260):
            draw.rectangle((x, 1180, x + 135, 1200), fill=(255, 229, 139))
        draw.polygon([(0, 680), (170, 580), (340, 680)], fill=(222, 157, 105))
        draw.rectangle((35, 680, 305, 870), fill=(250, 226, 187), outline=INK, width=6)
        draw.rectangle((785, 620, 1015, 830), fill=(255, 248, 224), outline=INK, width=6)
        draw.text((820, 675), "STOP", font=get_font(42, True), fill=(180, 65, 65))
    else:
        draw.rectangle((0, 450, W, 1350), fill=(221, 235, 202))
        draw.ellipse((820, 380, 1000, 560), fill=(255, 205, 99))
        for x in (80, 930):
            draw.rectangle((x - 18, 770, x + 18, 1190), fill=(125, 87, 58))
            draw.ellipse((x - 130, 570, x + 130, 900), fill=(76, 151, 91))
        for x in (280, 720):
            draw.polygon([(x, 680), (x + 130, 570), (x + 260, 680)], fill=(194, 111, 82))
            draw.rectangle((x + 18, 680, x + 242, 900), fill=(249, 219, 170), outline=INK, width=5)
            draw.rectangle((x + 95, 760, x + 165, 900), fill=(125, 91, 70))


def draw_prop(draw, prop, x, y):
    outline = INK
    if prop == "phone":
        draw.rounded_rectangle((x - 55, y - 105, x + 55, y + 105), radius=20, fill=(67, 76, 94), outline=outline, width=7)
        draw.rounded_rectangle((x - 42, y - 78, x + 42, y + 70), radius=10, fill=(160, 220, 235), outline=(255, 255, 255), width=4)
        draw.ellipse((x - 7, y + 82, x + 7, y + 96), fill=(245, 245, 245))
    elif prop in {"pot", "bowl", "fire"}:
        draw.rounded_rectangle((x - 85, y - 30, x + 85, y + 90), radius=25, fill=(190, 100, 72), outline=outline, width=7)
        draw.arc((x - 110, y - 65, x + 110, y + 25), 180, 360, fill=outline, width=8)
        if prop == "fire":
            draw.polygon([(x - 35, y - 35), (x - 5, y - 110), (x + 18, y - 45), (x + 55, y - 120), (x + 60, y - 30)], fill=(245, 145, 61))
    elif prop == "umbrella":
        draw.pieslice((x - 105, y - 95, x + 105, y + 95), 180, 360, fill=(215, 92, 103), outline=outline, width=6)
        draw.line((x, y, x, y + 130), fill=outline, width=9)
        draw.arc((x - 35, y + 95, x + 35, y + 160), 0, 180, fill=outline, width=8)
    elif prop == "coins":
        for i in range(4):
            xx = x - 55 + i * 35
            draw.ellipse((xx - 25, y - 15, xx + 25, y + 35), fill=(250, 198, 74), outline=outline, width=4)
    elif prop == "bucket":
        draw.polygon([(x - 70, y - 55), (x + 70, y - 55), (x + 52, y + 95), (x - 52, y + 95)], fill=(110, 177, 207), outline=outline)
        draw.arc((x - 70, y - 100, x + 70, y + 5), 180, 360, fill=outline, width=7)
    elif prop == "steering":
        draw.ellipse((x - 85, y - 85, x + 85, y + 85), outline=outline, width=15)
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=(230, 170, 92), outline=outline, width=5)
        draw.line((x, y, x, y - 75), fill=outline, width=8)
        draw.line((x, y, x - 68, y + 35), fill=outline, width=8)
        draw.line((x, y, x + 68, y + 35), fill=outline, width=8)
    elif prop == "sign":
        draw.rectangle((x - 10, y - 95, x + 10, y + 110), fill=(126, 87, 58))
        draw.rounded_rectangle((x - 95, y - 90, x + 95, y + 25), radius=18, fill=(245, 202, 93), outline=outline, width=6)
        draw.text((x - 55, y - 58), "STOP", font=get_font(34, True), fill=outline)
    elif prop == "sun":
        draw.ellipse((x - 70, y - 70, x + 70, y + 70), fill=(255, 202, 78), outline=outline, width=5)
        for angle in range(0, 360, 45):
            x1 = x + math.cos(math.radians(angle)) * 85
            y1 = y + math.sin(math.radians(angle)) * 85
            x2 = x + math.cos(math.radians(angle)) * 120
            y2 = y + math.sin(math.radians(angle)) * 120
            draw.line((x1, y1, x2, y2), fill=(230, 154, 61), width=7)
    else:
        draw.rounded_rectangle((x - 80, y - 95, x + 80, y + 95), radius=15, fill=(242, 216, 155), outline=outline, width=7)
        draw.line((x, y - 85, x, y + 85), fill=outline, width=4)


def draw_animal(draw, kind, cx, cy, scale=1.0, expression="happy"):
    dark = (76, 63, 76)
    if kind == "lion":
        fur, mane = (250, 196, 91), (221, 137, 63)
        draw.ellipse((cx-190,cy-210,cx+190,cy+170), fill=mane, outline=dark, width=9)
        draw.ellipse((cx-140,cy-165,cx+140,cy+135), fill=fur, outline=dark, width=7)
        for ex in (cx-115,cx+115):
            draw.ellipse((ex-43,cy-185,ex+43,cy-105), fill=fur, outline=dark, width=7)
            draw.ellipse((ex-20,cy-165,ex+20,cy-125), fill=(239,151,151))
    elif kind == "elephant":
        skin = (151, 190, 205)
        draw.ellipse((cx-160,cy-160,cx+160,cy+155), fill=skin, outline=dark, width=8)
        draw.ellipse((cx-215,cy-95,cx-95,cy+75), fill=(178,210,220), outline=dark, width=7)
        draw.ellipse((cx+95,cy-95,cx+215,cy+75), fill=(178,210,220), outline=dark, width=7)
        draw.rounded_rectangle((cx-38,cy-5,cx+38,cy+190), radius=35, fill=skin, outline=dark, width=8)
        draw.arc((cx-20,cy+95,cx+100,cy+225), 5, 180, fill=dark, width=7)
    elif kind == "rabbit":
        fur = (248, 235, 222)
        draw.ellipse((cx-135,cy-325,cx-45,cy-165), fill=fur, outline=dark, width=8)
        draw.ellipse((cx+45,cy-325,cx+135,cy-165), fill=fur, outline=dark, width=8)
        draw.ellipse((cx-155,cy-180,cx+155,cy+145), fill=fur, outline=dark, width=8)
        draw.ellipse((cx-92,cy-275,cx-63,cy-190), fill=(240,160,170))
        draw.ellipse((cx+63,cy-275,cx+92,cy-190), fill=(240,160,170))
    elif kind == "hyena":
        fur = (191, 145, 103)
        draw.ellipse((cx-155,cy-185,cx+155,cy+150), fill=fur, outline=dark, width=9)
        draw.ellipse((cx-150,cy-235,cx-55,cy-115), fill=(153, 104, 79), outline=dark, width=7)
        draw.ellipse((cx+55,cy-235,cx+150,cy-115), fill=(153, 104, 79), outline=dark, width=7)
        draw.ellipse((cx-118,cy-215,cx-78,cy-145), fill=(231, 174, 158))
        draw.ellipse((cx+78,cy-215,cx+118,cy-145), fill=(231, 174, 158))
        for sx, sy in [(-95,-35),(-125,35),(112,-5),(95,80),(-70,100)]:
            draw.ellipse((cx+sx-10,cy+sy-10,cx+sx+10,cy+sy+10), fill=(105,75,67))
        draw.ellipse((cx-95,cy+35,cx+95,cy+135), fill=(218, 184, 147), outline=dark, width=5)
    else:
        fur = (232, 190, 220)
        draw.ellipse((cx-145,cy-155,cx+145,cy+145), fill=fur, outline=dark, width=8)

    # Expressions de type manga : sourcils, yeux et bouche changent selon la scène.
    for side, ex in enumerate((cx-58, cx+58)):
        if expression == "laughing":
            draw.arc((ex-22,cy-55,ex+22,cy-10), 190, 350, fill=dark, width=8)
        else:
            draw.ellipse((ex-19,cy-48,ex+19,cy-2), fill=dark)
            draw.ellipse((ex-8,cy-40,ex+4,cy-28), fill="white")
        if expression == "angry":
            if side == 0:
                draw.line((ex-25,cy-75,ex+18,cy-58), fill=dark, width=9)
            else:
                draw.line((ex-18,cy-58,ex+25,cy-75), fill=dark, width=9)
        elif expression == "confused" and side == 1:
            draw.arc((ex-28,cy-90,ex+28,cy-48), 190, 340, fill=dark, width=8)
        elif expression == "worried":
            draw.arc((ex-25,cy-90,ex+25,cy-42), 190, 350, fill=dark, width=7)

    draw.ellipse((cx-112,cy+25,cx-70,cy+60), fill=(246,165,164))
    draw.ellipse((cx+70,cy+25,cx+112,cy+60), fill=(246,165,164))
    if expression in {"shocked", "surprised"}:
        draw.ellipse((cx-24,cy+35,cx+24,cy+100), fill=(91,55,63), outline=dark, width=5)
    elif expression == "laughing":
        draw.ellipse((cx-45,cy+30,cx+45,cy+100), fill=(105,49,61), outline=dark, width=5)
        draw.arc((cx-30,cy+60,cx+30,cy+95), 180, 360, fill=(255,210,210), width=6)
    elif expression in {"worried", "confused"}:
        draw.arc((cx-45,cy+50,cx+45,cy+105), 190, 350, fill=dark, width=7)
    else:
        draw.arc((cx-48,cy+20,cx+48,cy+90), 5, 175, fill=dark, width=7)


def make_frame(path, title, lyric, index, total, style):
    im = Image.new("RGB", (W, H), PALETTE[index % len(PALETTE)])
    d = ImageDraw.Draw(im)
    setting = style.get("setting", "village")
    draw_scene_background(d, setting, index)

    # Lignes d'impact discrètes pour une composition plus dynamique.
    positions = [(520, 900), (590, 880), (470, 920), (610, 930), (540, 870)]
    cx, cy = positions[index % len(positions)]
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x1, y1 = cx + math.cos(rad) * 245, cy + math.sin(rad) * 245
        x2, y2 = cx + math.cos(rad) * 330, cy + math.sin(rad) * 330
        d.line((x1, y1, x2, y2), fill=(255, 250, 230), width=8)

    # Bandeau titre
    d.rounded_rectangle((55,55,1025,300), radius=65, fill=(255,255,250), outline=(75,65,90), width=8)
    title_font = get_font(48, True)
    title_lines = wrap(d,title,title_font,850)
    yy = 105 if len(title_lines)==1 else 75
    for t in title_lines[:2]:
        box=d.textbbox((0,0),t,font=title_font)
        d.text(((W-(box[2]-box[0]))/2,yy),t,font=title_font,fill=INK)
        yy += 65

    d.rounded_rectangle((390,350,690,435), radius=35, fill=(255,214,120), outline=INK, width=5)
    label=f"SCÈNE {index+1}/{total}"
    d.text((425,370),label,font=get_font(31,True),fill=INK)

    # Plateau central légèrement décalé selon la scène.
    d.ellipse((cx-365,cy-390,cx+365,cy+390), fill=(255,255,248), outline=(255,255,255), width=14)
    animal = style.get("characters", ["hyena","lion","rabbit","hyena","lion"])[index % 5]
    expression = style.get("expressions", ["happy","curious","shocked","laughing","proud"])[index % 5]
    prop = style.get("props", ["phone","coins","pot","umbrella","book"])[index % 5]
    prop_x = 155 if index % 2 == 0 else 925
    draw_prop(d, prop, prop_x, 1010)
    draw_animal(d, animal, cx, cy, expression=expression)

    # Cartouche de dialogue lisible sur mobile.
    d.rounded_rectangle((55,1410,1025,1815), radius=65, fill=(255,255,250), outline=(75,65,90), width=7)
    lines=wrap(d,lyric,get_font(48,True),820)
    block_h=len(lines)*72
    ty=1605-block_h//2
    for line in lines[:4]:
        box=d.textbbox((0,0),line,font=get_font(48,True))
        d.text(((W-(box[2]-box[0]))/2,ty),line,font=get_font(48,True),fill=INK)
        ty += 72
    d.text((390,1850),"PAPI COMEDY • SKETCH ORIGINAL",font=get_font(25,True),fill=(115,105,130))
    im.save(path,quality=95)


async def make_voice(text, path):
    # Chant mélodique : chaque segment de phrase est interprété sur une note
    # différente de la gamme, puis les segments sont assemblés sans voix parlée continue.
    words = text.replace(";", ",").split(",")
    phrases = [p.strip() for p in words if p.strip()]
    if not phrases:
        phrases = [text]
    pitches = ["-2Hz", "+3Hz", "+7Hz", "+10Hz", "+5Hz", "+1Hz", "-3Hz", "+5Hz"]
    parts = []
    for i, phrase in enumerate(phrases):
        part = path.parent / f"{path.stem}_part_{i:02d}.mp3"
        await edge_tts.Communicate(
            phrase,
            voice="fr-FR-DeniseNeural",
            rate="-8%",
            pitch=pitches[i % len(pitches)]
        ).save(str(part))
        parts.append(part)
    concat = path.parent / f"{path.stem}_parts.txt"
    with concat.open("w", encoding="utf-8") as f:
        for part in parts:
            f.write(f"file '{part.resolve()}'\n")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-af", "apad=pad_dur=0.10", "-c:a", "libmp3lame", "-q:a", "3", str(path)
    ], check=True)

def make_music(path, seconds):
    # Petite mélodie originale en notes douces, synthétisée sans sample protégé.
    sample_rate = 22050
    notes = [523.25, 587.33, 659.25, 587.33, 523.25, 392.00, 440.00, 523.25]
    beat = 0.36
    total = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        chunk = 4096
        for start in range(0,total,chunk):
            frames=[]
            for n in range(start,min(start+chunk,total)):
                t=n/sample_rate
                note_index=int(t/beat) % len(notes)
                local=t % beat
                envelope=min(1.0,local/0.025)*max(0.0,min(1.0,(beat-local)/0.07))
                melody=math.sin(2*math.pi*notes[note_index]*t)
                harmony=math.sin(2*math.pi*(notes[note_index]/2)*t)*0.22
                sample=int(32767*0.10*envelope*(melody+harmony))
                frames.append(struct.pack("<h",max(-32767,min(32767,sample))))
            wav.writeframes(b"".join(frames))

async def main():
    last_path = Path("last_sketch.json")
    try:
        last_title = json.loads(last_path.read_text(encoding="utf-8")).get("title")
    except (OSError, ValueError):
        last_title = None
    choices = [item for item in SONGS if item["title"] != last_title] or SONGS
    song = random.choice(choices)
    last_path.write_text(json.dumps({"title": song["title"]}, ensure_ascii=False), encoding="utf-8")
    style = VISUAL_STYLES.get(song["title"], {})
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    work, output=Path("build"),Path("videos")
    work.mkdir(exist_ok=True)
    output.mkdir(exist_ok=True)
    frames,audios,durations=[],[],[]
    for i,line in enumerate(song["lines"]):
        frame=work/f"sketch_{i:02d}.jpg"
        audio=work/f"voice_{i:02d}.mp3"
        make_frame(frame,song["title"],line,i,len(song["lines"]),style)
        await make_voice(line,audio)
        probe=subprocess.check_output([
            "ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",str(audio)
        ],text=True).strip()
        duration=float(probe)+0.55
        frames.append(frame)
        audios.append(audio)
        durations.append(duration)

    frame_list=work/"frames.txt"
    audio_list=work/"audios.txt"
    with frame_list.open("w",encoding="utf-8") as f:
        for frame,duration in zip(frames,durations):
            f.write(f"file '{frame.resolve()}'\n")
            f.write(f"duration {duration:.3f}\n")
        f.write(f"file '{frames[-1].resolve()}'\n")
    with audio_list.open("w",encoding="utf-8") as f:
        for audio in audios:
            f.write(f"file '{audio.resolve()}'\n")

    narration=work/"narration.mp3"
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(audio_list),"-c:a","libmp3lame","-q:a","4",str(narration)],check=True)
    total=sum(durations)
    music=work/"original_melody.wav"
    make_music(music,total+1)
    video=output/f"papi_sketch_{stamp}.mp4"
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0","-i",str(frame_list),
        "-i",str(narration),"-i",str(music),
        "-filter_complex","[1:a]volume=1.0[voice];[2:a]volume=0.22[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map","0:v","-map","[a]",
        "-vf","scale=2160:3840:flags=lanczos,unsharp=5:5:0.35:5:5:0.0,format=yuv420p",
        "-r","30","-c:v","libx264","-preset","medium","-crf","18","-tune","stillimage",
        "-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(video)
    ],check=True)
    print(f"VIDEO CREATED: {video}")
    print(f"TITLE: {song['title']} | Sketch humoristique original")
    print("FORMAT: sketch humoristique français, dialogues et mélodie originale")

if __name__=="__main__":
    asyncio.run(main())
