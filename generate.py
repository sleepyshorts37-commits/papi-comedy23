
import asyncio
import random
import subprocess
from pathlib import Path
from datetime import datetime

import edge_tts

# Papi Comedy : sketches courts
SKETCHES = [
    {
        "title": "Quand ta femme dit : fais comme tu veux 😂",
        "dialogue": [
            "Le mari : Chérie, je peux sortir avec mes amis ce soir ?",
            "La femme : Fais comme tu veux.",
            "Le mari : Merci mon amour !",
            "La femme : Mais n'oublie pas la maison, les enfants et les factures !",
            "Le mari : Seigneur, je voulais juste boire un jus !"
        ]
    },
    {
        "title": "Le Sénégalais et son salaire 😂",
        "dialogue": [
            "Le patron : Tu as reçu ton salaire ?",
            "L'employé : Oui, patron.",
            "Le patron : Alors pourquoi tu demandes une avance ?",
            "L'employé : Mon salaire est déjà arrivé chez mes créanciers !",
            "Le patron : Et il te reste quoi ?",
            "L'employé : L'expérience, patron !"
        ]
    },
    {
        "title": "Quand maman appelle 😂",
        "dialogue": [
            "Le fils : Allô maman ?",
            "La maman : Tu es où ?",
            "Le fils : Je suis presque arrivé.",
            "La maman : Tu es parti d'où ?",
            "Le fils : Maman, je suis encore au lit.",
            "La maman : Tu vas voir quand je vais arriver !"
        ]
    }
]

async def main():
    sketch = random.choice(SKETCHES)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    work = Path("build")
    work.mkdir(exist_ok=True)
    output = Path("videos")
    output.mkdir(exist_ok=True)

    narration = " . ".join(sketch["dialogue"])
    audio_file = work / "narration.mp3"
    title_file = work / "title.txt"
    video_file = output / f"papi_comedy_{timestamp}.mp4"

    title_file.write_text(sketch["title"], encoding="utf-8")

    voice = edge_tts.Communicate(
        narration,
        voice="fr-FR-HenriNeural",
        rate="+8%"
    )
    await voice.save(str(audio_file))

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=0x19152F:s=1080x1920:r=30",
        "-i", str(audio_file),
        "-vf",
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"textfile={title_file}:fontcolor=white:fontsize=66:"
        "x=(w-text_w)/2:y=(h-text_h)/2:"
        "box=1:boxcolor=0xE85D75@0.85:boxborderw=35,"
        "format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(video_file)
    ], check=True)

    print(f"VIDEO CREEE : {video_file}")
    print(f"TITRE : {sketch['title']}")

if __name__ == "__main__":
    asyncio.run(main())
