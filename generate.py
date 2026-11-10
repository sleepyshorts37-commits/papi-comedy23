import asyncio
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

# Comptines originales : paroles inédites, adaptées aux tout-petits.
SONGS = [
    {
        "title": "Le petit lion compte les étoiles",
        "lines": [
            "Petit lion ferme les yeux, une étoile brille dans les cieux.",
            "Un, deux, trois, les étoiles dansent avec toi.",
            "Petit éléphant tape des mains, quatre, cinq, tout va bien.",
            "La lune sourit, le vent est doux, les petits rêves viennent à nous.",
            "Dors mon bébé, la nuit est jolie, demain le soleil te sourit."
        ],
    },
    {
        "title": "Les couleurs du petit arc-en-ciel",
        "lines": [
            "Rouge comme une jolie fleur, jaune comme un rayon de bonheur.",
            "Bleu comme la mer qui fait coucou, vert comme les feuilles tout partout.",
            "Orange comme un fruit sucré, violet comme un ciel enchanté.",
            "Toutes les couleurs font la ronde, elles mettent des sourires dans le monde.",
            "Tape des mains, tourne doucement, l'arc-en-ciel chante avec les enfants."
        ],
    },
    {
        "title": "Un, deux, trois petits animaux",
        "lines": [
            "Un petit lapin saute dans le jardin.",
            "Deux papillons volent au matin.",
            "Trois petits canards font coin-coin dans l'eau.",
            "Quatre oiseaux chantent tout là-haut.",
            "Cinq amis dansent, bravo, bravo !"
        ],
    },
]

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

def draw_animal(draw, kind, cx, cy, scale=1.0):
    dark = (76, 63, 76)
    if kind == "lion":
        fur, mane = (250, 196, 91), (221, 137, 63)
        draw.ellipse((cx-190,cy-210,cx+190,cy+170), fill=mane, outline=dark, width=9)
        draw.ellipse((cx-140,cy-165,cx+140,cy+135), fill=fur, outline=dark, width=7)
        # ears
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
    else:
        fur = (232, 190, 220)
        draw.ellipse((cx-145,cy-155,cx+145,cy+145), fill=fur, outline=dark, width=8)
    # face
    for ex in (cx-58,cx+58):
        draw.ellipse((ex-17,cy-45,ex+17,cy-5), fill=dark)
        draw.ellipse((ex-7,cy-38,ex+3,cy-28), fill="white")
    draw.ellipse((cx-18,cy+10,cx+18,cy+35), fill=(236,137,145))
    draw.arc((cx-48,cy+20,cx+48,cy+90), 5, 175, fill=dark, width=7)
    # rosy cheeks
    draw.ellipse((cx-112,cy+25,cx-70,cy+60), fill=(246,165,164))
    draw.ellipse((cx+70,cy+25,cx+112,cy+60), fill=(246,165,164))

def make_frame(path, title, lyric, index, total, kind):
    im = Image.new("RGB", (W, H), PALETTE[index % len(PALETTE)])
    d = ImageDraw.Draw(im)
    # soft clouds and floating stars
    d.ellipse((-160,120,390,520), fill=(255,255,245))
    d.ellipse((180,75,620,420), fill=(255,255,245))
    d.ellipse((720,120,1240,520), fill=(255,255,245))
    for x,y,r in [(120,650,28),(900,700,34),(180,1120,22),(880,1160,25),(540,470,25),(760,900,20)]:
        draw_star(d,x,y,r,(255,190,75))
    # title banner
    d.rounded_rectangle((55,55,1025,300), radius=65, fill=(255,255,250), outline=(115,105,130), width=7)
    title_font = get_font(48, True)
    title_lines = wrap(d,title,title_font,850)
    yy = 105 if len(title_lines)==1 else 75
    for t in title_lines[:2]:
        box=d.textbbox((0,0),t,font=title_font)
        d.text(((W-(box[2]-box[0]))/2,yy),t,font=title_font,fill=INK)
        yy += 65
    # scene number
    d.rounded_rectangle((390,350,690,435), radius=35, fill=(255,214,120), outline=INK, width=5)
    label=f"CHANSON {index+1}/{total}"
    d.text((425,370),label,font=get_font(31,True),fill=INK)
    # character stage
    d.ellipse((175,520,905,1330), fill=(255,255,248), outline=(255,255,255), width=14)
    animal = kind[index % len(kind)]
    draw_animal(d,animal,540,900)
    # lyric panel
    d.rounded_rectangle((55,1410,1025,1815), radius=65, fill=(255,255,250), outline=(115,105,130), width=7)
    lines=wrap(d,lyric,get_font(48,True),820)
    block_h=len(lines)*72
    ty=1605-block_h//2
    for line in lines[:4]:
        box=d.textbbox((0,0),line,font=get_font(48,True))
        d.text(((W-(box[2]-box[0]))/2,ty),line,font=get_font(48,True),fill=INK)
        ty += 72
    d.text((390,1850),"PAPI • PETITES CHANSONS",font=get_font(25,True),fill=(115,105,130))
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
            f.write(f"file '{part.resolve()}'\\n")
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
    song=random.choice(SONGS)
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    work, output=Path("build"),Path("videos")
    work.mkdir(exist_ok=True)
    output.mkdir(exist_ok=True)
    frames,audios,durations=[],[],[]
    animals=["lion","elephant","rabbit","bear","lion"]
    for i,line in enumerate(song["lines"]):
        frame=work/f"nursery_{i:02d}.jpg"
        audio=work/f"voice_{i:02d}.mp3"
        make_frame(frame,song["title"],line,i,len(song["lines"]),animals)
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
    video=output/f"papi_comptine_{stamp}.mp4"
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
    print(f"TITLE: {song['title']} | Comptine originale pour bébé")
    print("FORMAT: comptine française, voix douce et mélodie instrumentale originale")

if __name__=="__main__":
    asyncio.run(main())
