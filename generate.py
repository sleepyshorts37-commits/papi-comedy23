import asyncio
import random
import subprocess
import textwrap
from pathlib import Path
from datetime import datetime

import edge_tts
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (250, 239, 220)
INK = (35, 31, 42)
PINK = (235, 83, 120)
BLUE = (69, 126, 184)
YELLOW = (255, 203, 75)

SKETCHES = [
    {
        "title": "Quand ta femme dit : fais comme tu veux 😂",
        "dialogue": [
            ("homme", "Chérie, je peux sortir avec mes amis ce soir ?"),
            ("femme", "Fais comme tu veux."),
            ("homme", "Merci mon amour !"),
            ("femme", "Mais n'oublie pas la maison, les enfants et les factures !"),
            ("homme", "Seigneur, je voulais juste boire un jus !"),
        ],
    },
    {
        "title": "Le Sénégalais et son salaire 😂",
        "dialogue": [
            ("homme", "Patron, mon salaire est arrivé ?"),
            ("femme", "Oui. Tu as reçu ton salaire hier."),
            ("homme", "Alors pourquoi mon compte est déjà vide ?"),
            ("femme", "Tes créanciers ont été plus rapides que toi !"),
            ("homme", "Même l'argent ne veut pas rester avec moi !"),
        ],
    },
    {
        "title": "Quand maman t'appelle 😂",
        "dialogue": [
            ("femme", "Allô ! Tu es où ?"),
            ("homme", "Je suis presque arrivé, maman."),
            ("femme", "Tu es parti d'où exactement ?"),
            ("homme", "Du lit... je cherche encore mes chaussures."),
            ("femme", "Attends-moi. J'arrive te réveiller !"),
        ],
    },
    {
        "title": "Le fameux je suis en route 😂",
        "dialogue": [
            ("femme", "Tu es où ? On t'attend depuis une heure !"),
            ("homme", "Je suis en route, j'arrive dans cinq minutes."),
            ("femme", "Mais j'entends la télé derrière toi !"),
            ("homme", "C'est la circulation qui passe à la télé."),
            ("femme", "Toi, tu vas finir par épouser ton canapé !"),
        ],
    },
]

def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap(draw, text, fnt, max_width):
    words, lines, line = text.split(), [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def draw_character(draw, cx, cy, role, mood):
    skin = (111, 65, 45)
    shirt = (39, 105, 170) if role == "homme" else (203, 65, 112)
    dark = (28, 23, 27)
    # Neck, shoulders and torso with layered clothing
    draw.rounded_rectangle((cx-150, cy+150, cx+150, cy+540), radius=95, fill=shirt, outline=dark, width=10)
    draw.polygon([(cx-52,cy+170),(cx,cy+245),(cx+52,cy+170)], fill=(245,238,226), outline=dark)
    draw.line((cx,cy+245,cx,cy+490), fill=(245,238,226), width=7)
    draw.ellipse((cx-48,cy+105,cx+48,cy+220), fill=skin, outline=dark, width=7)
    # Ears and face
    draw.ellipse((cx-165,cy-65,cx-105,cy+55), fill=skin, outline=dark, width=8)
    draw.ellipse((cx+105,cy-65,cx+165,cy+55), fill=skin, outline=dark, width=8)
    draw.ellipse((cx-145,cy-155,cx+145,cy+170), fill=skin, outline=dark, width=10)
    # Hair style
    if role == "homme":
        draw.pieslice((cx-152,cy-180,cx+152,cy+100),180,360,fill=(25,21,22),outline=dark,width=7)
        for dx in [-100,-50,0,50,100]:
            draw.arc((cx+dx-28,cy-165,cx+dx+28,cy-100),180,350,fill=(65,42,34),width=8)
    else:
        draw.arc((cx-175,cy-190,cx+175,cy+180),175,365,fill=(22,18,22),width=42)
        draw.rounded_rectangle((cx-165,cy-25,cx-115,cy+270),radius=24,fill=(22,18,22))
        draw.rounded_rectangle((cx+115,cy-25,cx+165,cy+270),radius=24,fill=(22,18,22))
        # head scarf detail
        draw.arc((cx-135,cy-175,cx+135,cy+30),185,355,fill=(245,183,73),width=12)
    # expressive brows and eyes
    if mood == "angry":
        draw.line((cx-90,cy-45,cx-35,cy-20),fill=dark,width=13)
        draw.line((cx+35,cy-20,cx+90,cy-45),fill=dark,width=13)
    elif mood == "surprised":
        draw.arc((cx-100,cy-75,cx-30,cy-25),180,350,fill=dark,width=10)
        draw.arc((cx+30,cy-75,cx+100,cy-25),190,360,fill=dark,width=10)
    else:
        draw.line((cx-88,cy-42,cx-38,cy-48),fill=dark,width=9)
        draw.line((cx+38,cy-48,cx+88,cy-42),fill=dark,width=9)
    for ex in (cx-62,cx+62):
        draw.ellipse((ex-23,cy-20,ex+23,cy+28),fill="white",outline=dark,width=4)
        draw.ellipse((ex-9,cy-7,ex+9,cy+20),fill=dark)
        draw.ellipse((ex-4,cy-3,ex+2,cy+3),fill="white")
    draw.ellipse((cx-13,cy+35,cx+13,cy+55),fill=(92,48,36))
    if mood == "surprised":
        draw.ellipse((cx-30,cy+75,cx+30,cy+140),fill=(75,22,30),outline=dark,width=6)
    elif mood == "angry":
        draw.arc((cx-65,cy+75,cx+65,cy+150),200,340,fill=dark,width=10)
    else:
        draw.arc((cx-70,cy+65,cx+70,cy+155),10,170,fill=dark,width=10)
    # hands and cuffs
    draw.ellipse((cx-180,cy+390,cx-110,cy+465),fill=skin,outline=dark,width=6)
    draw.ellipse((cx+110,cy+390,cx+180,cy+465),fill=skin,outline=dark,width=6)

def make_frame(path, title, role, line, index, total):
    im = Image.new("RGB", (W, H), (248, 235, 215))
    d = ImageDraw.Draw(im)
    # Soft illustrated background, decorative rays and city-like silhouettes
    for x in range(0, W, 120):
        d.line((x, 300, x-180, 1050), fill=(240, 220, 193), width=5)
    d.ellipse((-180, 1120, 420, 1730), fill=(239, 218, 190))
    d.ellipse((740, 1150, 1280, 1740), fill=(239, 218, 190))
    d.rounded_rectangle((45, 45, W-45, 285), radius=55, fill=(31, 29, 40))
    d.rounded_rectangle((65, 65, W-65, 265), radius=42, outline=(245, 190, 83), width=5)
    title_font = font(48, True)
    title_lines = wrap(d, title, title_font, W-170)
    y = 95 if len(title_lines) == 1 else 78
    for t in title_lines[:2]:
        box = d.textbbox((0, 0), t, font=title_font)
        d.text(((W-(box[2]-box[0]))/2+3, y+4), t, font=title_font, fill=(90,75,70))
        d.text(((W-(box[2]-box[0]))/2, y), t, font=title_font, fill="white")
        y += 68
    # Scene counter
    d.rounded_rectangle((70, 330, 470, 425), radius=38, fill=(255, 199, 76), outline=(31,29,40), width=6)
    d.text((105, 350), f"ÉPISODE  •  {index+1}/{total}", font=font(34, True), fill=(31,29,40))
    # Dialogue card with depth
    d.rounded_rectangle((83, 520, 1015, 1085), radius=65, fill=(205,185,160))
    d.rounded_rectangle((65, 495, 997, 1060), radius=65, fill=(255,255,250), outline=(31,29,40), width=10)
    who = "LE MARI" if role == "homme" else "LA FEMME"
    badge = (39,105,170) if role == "homme" else (203,65,112)
    d.rounded_rectangle((112, 545, 440, 640), radius=34, fill=badge, outline=(31,29,40), width=4)
    d.text((150, 565), who, font=font(40, True), fill="white")
    dialogue_font = font(55, True)
    lines = wrap(d, line, dialogue_font, 800)
    text_height = len(lines) * 82
    ty = 735 + max(0, (250-text_height)//2)
    for t in lines[:4]:
        box = d.textbbox((0,0), t, font=dialogue_font)
        d.text(((W-(box[2]-box[0]))/2, ty), t, font=dialogue_font, fill=(31,29,40))
        ty += 82
    # Character spotlights and richer cartoon portraits
    d.ellipse((155, 1120, 535, 1510), fill=(255,255,250), outline=(31,29,40), width=7)
    d.ellipse((545, 1120, 925, 1510), fill=(255,255,250), outline=(31,29,40), width=7)
    draw_character(d, 345, 1290, "homme", "surprised" if role=="femme" else "smile")
    draw_character(d, 735, 1290, "femme", "angry" if role=="femme" else "smile")
    # Active speaker marker
    sx = 345 if role=="homme" else 735
    d.rounded_rectangle((sx-150, 1790, sx+150, 1870), radius=32, fill=(255,199,76), outline=(31,29,40), width=6)
    d.text((sx-85, 1807), "À TOI !", font=font(38, True), fill=(31,29,40))
    im.save(path, quality=95)

async def synthesize(text, role, path):
    voice = "fr-FR-HenriNeural" if role == "homme" else "fr-FR-DeniseNeural"
    rate = "+10%" if role == "homme" else "+6%"
    await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(path))

async def main():
    sketch = random.choice(SKETCHES)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work, output = Path("build"), Path("videos")
    work.mkdir(exist_ok=True)
    output.mkdir(exist_ok=True)
    frames, audios, durations = [], [], []
    for i, (role, line) in enumerate(sketch["dialogue"]):
        frame = work / f"frame_{i:02d}.jpg"
        audio = work / f"line_{i:02d}.mp3"
        make_frame(frame, sketch["title"], role, line, i, len(sketch["dialogue"]))
        await synthesize(line, role, audio)
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio)
        ], text=True).strip()
        duration = float(probe) + 0.45
        frames.append(frame)
        audios.append(audio)
        durations.append(duration)

    frame_list, audio_list = work/"frames.txt", work/"audios.txt"
    with frame_list.open("w", encoding="utf-8") as f:
        for frame, duration in zip(frames, durations):
            f.write(f"file '{frame.resolve()}'\n")
            f.write(f"duration {duration:.3f}\n")
        f.write(f"file '{frames[-1].resolve()}'\n")
    with audio_list.open("w", encoding="utf-8") as f:
        for audio in audios:
            f.write(f"file '{audio.resolve()}'\n")

    joined_audio = work/"narration.mp3"
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(audio_list),"-c:a","libmp3lame","-q:a","4",str(joined_audio)],check=True)
    video_file = output / f"papi_comedy_{stamp}.mp4"
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0","-i",str(frame_list),"-i",str(joined_audio),
        "-vf","scale=1080:1920,format=yuv420p",
        "-r","30","-c:v","libx264","-preset","ultrafast","-tune","stillimage",
        "-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(video_file)
    ],check=True)
    print(f"VIDEO CREATED: {video_file}")
    print(f"TITLE: {sketch['title']}")

if __name__ == "__main__":
    asyncio.run(main())
