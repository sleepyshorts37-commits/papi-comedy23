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
    skin = (150, 91, 62)
    shirt = BLUE if role == "homme" else PINK
    # body and neck
    draw.rounded_rectangle((cx-125, cy+155, cx+125, cy+510), radius=85, fill=shirt, outline=INK, width=8)
    draw.rectangle((cx-35, cy+110, cx+35, cy+205), fill=skin, outline=INK, width=5)
    # head
    draw.ellipse((cx-145, cy-145, cx+145, cy+160), fill=skin, outline=INK, width=8)
    # hair
    if role == "homme":
        draw.pieslice((cx-150, cy-165, cx+150, cy+85), 180, 360, fill=(28, 24, 25), outline=INK, width=5)
    else:
        draw.arc((cx-165, cy-170, cx+165, cy+175), 175, 365, fill=(28, 24, 25), width=34)
        draw.ellipse((cx-160, cy-20, cx-95, cy+210), fill=(28,24,25))
        draw.ellipse((cx+95, cy-20, cx+160, cy+210), fill=(28,24,25))
    # eyes and eyebrows
    draw.ellipse((cx-78, cy-25, cx-42, cy+15), fill="white", outline=INK, width=4)
    draw.ellipse((cx+42, cy-25, cx+78, cy+15), fill="white", outline=INK, width=4)
    draw.ellipse((cx-65, cy-12, cx-50, cy+7), fill=INK)
    draw.ellipse((cx+55, cy-12, cx+70, cy+7), fill=INK)
    if mood == "surprised":
        draw.ellipse((cx-25, cy+65, cx+25, cy+115), fill=(75, 25, 28), outline=INK, width=4)
        draw.arc((cx-95, cy-65, cx-25, cy-20), 180, 350, fill=INK, width=8)
        draw.arc((cx+25, cy-65, cx+95, cy-20), 190, 360, fill=INK, width=8)
    elif mood == "angry":
        draw.line((cx-90, cy-55, cx-35, cy-30), fill=INK, width=10)
        draw.line((cx+35, cy-30, cx+90, cy-55), fill=INK, width=10)
        draw.arc((cx-45, cy+65, cx+45, cy+130), 190, 350, fill=INK, width=9)
    else:
        draw.arc((cx-55, cy+45, cx+55, cy+125), 10, 170, fill=INK, width=8)

def make_frame(path, title, role, line, index, total):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # top banner and accents
    d.rounded_rectangle((55, 55, W-55, 270), radius=45, fill=INK)
    title_font = font(48, True)
    title_lines = wrap(d, title, title_font, W-150)
    y = 90
    for t in title_lines[:2]:
        box = d.textbbox((0,0), t, font=title_font)
        d.text(((W-(box[2]-box[0]))/2, y), t, font=title_font, fill="white")
        y += 66
    d.ellipse((75, 335, 170, 430), fill=YELLOW)
    d.text((100, 348), "!", font=font(52, True), fill=INK)
    d.text((205, 365), f"SCÈNE {index+1}/{total}", font=font(36, True), fill=INK)
    # speech bubble
    bubble = (70, 520, 1010, 1050)
    d.rounded_rectangle(bubble, radius=65, fill="white", outline=INK, width=9)
    d.polygon([(690,1045),(770,1045),(735,1120)], fill="white")
    d.line((690,1045,735,1120,770,1045), fill=INK, width=8)
    who = "LE MARI" if role == "homme" else "LA FEMME"
    d.rounded_rectangle((115, 570, 440, 650), radius=30, fill=BLUE if role=="homme" else PINK)
    d.text((145, 585), who, font=font(38, True), fill="white")
    dialogue_font = font(54, True)
    lines = wrap(d, line, dialogue_font, 790)
    text_height = len(lines) * 78
    ty = 720 + max(0, (250-text_height)//2)
    for t in lines[:4]:
        box = d.textbbox((0,0), t, font=dialogue_font)
        d.text(((W-(box[2]-box[0]))/2, ty), t, font=dialogue_font, fill=INK)
        ty += 78
    # cartoon duo
    draw_character(d, 345, 1290, "homme", "surprised" if role=="femme" else "smile")
    draw_character(d, 745, 1290, "femme", "angry" if role=="femme" else "smile")
    # speaker spotlight
    sx = 345 if role=="homme" else 745
    d.rounded_rectangle((sx-145, 1770, sx+145, 1845), radius=30, fill=YELLOW, outline=INK, width=5)
    d.text((sx-100, 1786), "PARLE", font=font(34, True), fill=INK)
    im.save(path, quality=92)

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
