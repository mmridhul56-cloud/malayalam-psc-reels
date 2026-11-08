#!/usr/bin/env python3
import asyncio
import datetime
import jsonimport asyncio, datetime, json, math, os, subprocess, textwrap, time
from pathlib import Path
import edge_tts, requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("MALAYALAM_VOICE", "ml-IN-MidhunNeural")
KEY = os.getenv("GEMINI_API_KEY", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
OUT, TMP, HIST = Path("output"), Path("temp_build"), Path("used_topics.json")

FALLBACK_SCRIPT = {
    "topic": "വൈക്കം സത്യഗ്രഹം (1924-1925)",
    "instagram_caption": "വൈക്കം സത്യഗ്രഹം — കേരള നവോത്ഥാന ചരിത്രത്തിലെ പ്രധാന വസ്തുതകൾ 📌 #keralapsc #psctips #malayalampsc",
    "scenes": [
        {
            "section_tag": "ഇന്നത്തെ PSC ചോദ്യം",
            "headline": "വൈക്കം സത്യഗ്രഹം ആരംഭിച്ച വർഷവും തീയതിയും എന്നാണ്?",
            "highlight_answer": "1924 മാർച്ച് 30",
            "bullet_points": ["ആകെ നീണ്ടുനിന്നത്: 603 ദിവസങ്ങൾ", "സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള ആദ്യ സംഘടിത സമരം"],
            "voiceover": "കേരള പി എസ് സി പരീക്ഷകളിൽ സ്ഥിരമായി ചോദിക്കുന്ന ചോദ്യമാണ് വൈക്കം സത്യഗ്രഹം ആരംഭിച്ചത് എന്നാണെന്ന്. ഉത്തരം 1924 മാർച്ച് 30 ആണ്."
        },
        {
            "section_tag": "എന്തുകൊണ്ട് ഇങ്ങനെ സംഭവിച്ചു?",
            "headline": "സമരത്തിന്റെ പ്രധാന കാരണം",
            "highlight_answer": "സഞ്ചാര സ്വാതന്ത്ര്യം",
            "bullet_points": ["വൈക്കം മഹാദേവ ക്ഷേത്രത്തിന് ചുറ്റുമുള്ള വഴികളിലൂടെ അവർണ്ണർക്ക് നടക്കാൻ വിലക്കുണ്ടായിരുന്നു", "1923-ലെ കാക്കിനഡ കോൺഗ്രസ് സമ്മേളനത്തിൽ ടി.കെ. മാധവൻ പ്രമേയം അവതരിപ്പിച്ചു"],
            "voiceover": "വൈക്കം മഹാദേവ ക്ഷേത്രത്തിന് ചുറ്റുമുള്ള പൊതുവഴികളിലൂടെ എല്ലാവർക്കും സഞ്ചാര സ്വാതന്ത്ര്യം നേടിയെടുക്കുക എന്നതായിരുന്നു ഈ സമരത്തിന്റെ പ്രധാന ലക്ഷ്യം."
        },
        {
            "section_tag": "ചരിത്രപരമായ വസ്തുതകൾ",
            "headline": "പ്രധാന നേതാക്കളും സംഭവങ്ങളും",
            "highlight_answer": "ടി.കെ. മാധവൻ, കെ.പി. കേശവമേനോൻ",
            "bullet_points": ["സവർണ്ണ ജാഥ നയിച്ചത്: മന്നത്ത് പത്മനാഭൻ", "തമിഴ്നാട്ടിൽ നിന്ന് എത്തിയ നേതാവ്: ഇ.വി. രാമസ്വാമി നായ്ക്കർ (വൈക്കം വീരർ)"],
            "voiceover": "ടി കെ മാധവൻ, കെ പി കേശവമേനോൻ, മന്നത്ത് പത്മനാഭൻ എന്നിവർ ഇതിന് നേതൃത്വം നൽകി. സമരത്തിന് പിന്തുണയുമായി എത്തിയ ഇ വി രാമസ്വാമി നായ്ക്കർ വൈക്കം വീരർ എന്നറിയപ്പെട്ടു."
        },
        {
            "section_tag": "PSC പരീക്ഷാ പോയിന്റുകൾ",
            "headline": "ഓർത്തിരിക്കേണ്ട അനുബന്ധ ചോദ്യങ്ങൾ",
            "highlight_answer": "1925 നവംബർ 23",
            "bullet_points": ["ഗാന്ധിജി വൈക്കം സന്ദർശിച്ച വർഷം: 1925 മാർച്ച്", "സത്യഗ്രഹം അവസാനിച്ചത്: 1925 നവംബർ 23 (റാണി സേതു ലക്ഷ്മി ഭായിയുടെ കാലത്ത്)"],
            "voiceover": "ഗാന്ധിജിയുടെ ഇടപെടലിലൂടെ 1925 നവംബർ 23-ന് തിരുവിതാംകൂർ റീജന്റ് റാണി സേതു ലക്ഷ്മി ഭായി കിഴക്കേ നട ഒഴികെയുള്ള വഴികൾ തുറന്നുകൊടുത്തതോടെ സമരം അവസാനിച്ചു."
        },
        {
            "section_tag": "റിവിഷൻ & ഫോളോ",
            "headline": "ദിവസവും ഒരു PSC അറിവ്!",
            "highlight_answer": "Follow & Save",
            "bullet_points": ["വീഡിയോ സേവ് ചെയ്യുക", "കൂട്ടുകാർക്ക് ഷെയർ ചെയ്യുക"],
            "voiceover": "ഇത്തരം പ്രധാനപ്പെട്ട പി എസ് സി അറിവുകൾ ദിവസവും മനസ്സിലാക്കാൻ ഈ വീഡിയോ സേവ് ചെയ്യൂ, പേജ് ഫോളോ ചെയ്യൂ."
        }
    ]
}

def get_script():
    used = json.loads(HIST.read_text("utf-8")) if HIST.exists() else []
    client = genai.Client(api_key=KEY)
    prompt = (
        "നിങ്ങൾ ഒരു കേരള PSC അദ്ധ്യാപകനാണ്. PSC പരീക്ഷകളിൽ ആവർത്തിച്ചു ചോദിക്കുന്ന ഒരു പ്രധാന ചോദ്യം എടുത്ത്, "
        "ആ ചോദ്യവും അതിന്റെ ഉത്തരവും, എന്തുകൊണ്ട് അങ്ങനെ സംഭവിച്ചു എന്ന ചരിത്രപരമോ ശാസ്ത്രീയമോ ഭരണഘടനാപരമോ ആയ "
        "കാരണങ്ങളും ലളിതമായി പഠിപ്പിച്ചു കൊടുക്കുന്ന 60-സെക്കൻഡ് എക്സ്പ്ലെയ്നർ വീഡിയോ സ്ക്രിപ്റ്റ് തയ്യാറാക്കുക. "
        f"ഇതൊരു ക്വിസ് വീഡിയോ അല്ല. മുൻപ് ഉപയോഗിച്ചവ ഒഴിവാക്കുക: {', '.join(used[-30:]) or 'None'}. "
        "scenes ലിസ്റ്റിൽ കൃത്യം 5 സീനുകൾ (1. ഇന്നത്തെ PSC ചോദ്യം, 2. എന്തുകൊണ്ട് ഇങ്ങനെ സംഭവിച്ചു?, 3. ചരിത്രപരമായ വസ്തുതകൾ, 4. PSC പരീക്ഷാ പോയിന്റുകൾ, 5. റിവിഷൻ & ഫോളോ) ഉണ്ടായിരിക്കണം. JSON format only:\n"
        '{"topic":"വിഷയം","instagram_caption":"ക്യാപ്ഷൻ #keralapsc","scenes":['
        '{"section_tag":"ഇന്നത്തെ PSC ചോദ്യം","headline":"ചോദ്യം","highlight_answer":"ഉത്തരം","bullet_points":["പോയിന്റ് 1","പോയിന്റ് 2"],"voiceover":"മലയാളം വിശദീകരണം (10-12 സെക്കൻഡ്)"}'
        "]}"
    )
    models = ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"]
    try:
        for m in client.models.list():
            n = getattr(m, "name", "").replace("models/", "")
            if "gemini" in n and ("flash" in n or "pro" in n) and not any(x in n for x in ["tts", "image", "embedding", "vision", "audio", "live", "2.5-flash"]):
                if n not in models:
                    models.append(n)
    except Exception as e:
        print("List models note:", e)
    resp = None
    for m in models:
        for attempt in range(2):
            try:
                print(f"Trying model {m} (attempt {attempt + 1})...")
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7),
                )
                if resp and resp.text:
                    break
            except Exception as e:
                print("Model attempt failed:", m, e)
                time.sleep(4)
        if resp and resp.text:
            break
    if resp and resp.text:
        data = json.loads(resp.text)
        if isinstance(data, list):
            data = data[0]
    else:
        print("All models temporarily busy; using curated PSC explainer script.")
        data = FALLBACK_SCRIPT
    if "topic" in data and data["topic"] not in used:
        used.append(data["topic"])
        HIST.write_text(json.dumps(used[-200:], ensure_ascii=False, indent=2), "utf-8")
    return data

def get_font(sz, bold=False):
    for p in [
        f"/usr/share/fonts/truetype/smc/Manjari-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/noto/NotoSansMalayalam-{'Bold' if bold else 'Regular'}.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=sz)
    return ImageFont.load_default()

def wrap_txt(draw, txt, font, x, y, mc, fill, sp=16):
    cy = y
    for ln in textwrap.wrap(str(txt), width=mc):
        draw.text((x, cy), ln, font=font, fill=fill)
        bb = draw.textbbox((x, cy), ln, font=font)
        cy += (bb[3] - bb[1]) + sp
    return cy

async def build():
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    data = get_script()
    dt = datetime.date.today().isoformat()
    (OUT / f"psc_script_{dt}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

    bg = Image.new("RGB", (W, H), (13, 17, 28))
    bd = ImageDraw.Draw(bg)
    for y in range(H):
        r = y / H
        bd.line([(0, y), (W, y)], fill=(int(13*(1-r)+25*r), int(17*(1-r)+33*r), int(28*(1-r)+56*r)))

    f_tag, f_hd, f_ans, f_bul, f_sub = get_font(38, True), get_font(52, True), get_font(60, True), get_font(40), get_font(35)
    scenes = data.get("scenes", [])
    clips = []

    for idx, sc in enumerate(scenes):
        mp3 = TMP / f"s_{idx}.mp3"
        mp4 = TMP / f"s_{idx}.mp4"
        await edge_tts.Communicate(text=sc["voiceover"], voice=VOICE, rate="-2%").save(str(mp3))
        res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)], capture_output=True, text=True, check=True)
        dur = max(3.0, float(res.stdout.strip())) + 0.3
        n_frames = int(math.ceil(dur * FPS))
        fdir = TMP / f"f_{idx}"
        fdir.mkdir(parents=True, exist_ok=True)

        for f in range(n_frames):
            t = f / FPS
            ease = 1 - (1 - min(1.0, t / 0.45)) ** 3
            off = int((1 - ease) * 70)
            img = bg.copy().convert("RGBA")
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)

            ty = 140 + off
            d.rounded_rectangle([(70, ty), (W - 70, ty + 85)], radius=24, fill=(56, 189, 248, int(45 * ease)), outline=(56, 189, 248), width=3)
            d.text((110, ty + 18), f"#{idx + 1}  {sc.get('section_tag', 'PSC Explainer')}", font=f_tag, fill=(56, 189, 248))

            ct = 270 + off
            d.rounded_rectangle([(70, ct), (W - 70, 1320 + off)], radius=36, fill=(32, 43, 70, 235), outline=(255, 255, 255, 45), width=2)
            cy = wrap_txt(d, sc.get("headline", ""), f_hd, 120, ct + 60, 24, (248, 250, 252), 20)

            ap = max(0.0, min(1.0, (t - 0.25) / 0.4))
            if ap > 0:
                cy += 30
                d.rounded_rectangle([(115, cy), (W - 115, cy + 130)], radius=24, fill=(255, 204, 0, int(35 * ap)), outline=(255, 204, 0), width=4)
                d.text((150, cy + 30), str(sc.get("highlight_answer", "")), font=f_ans, fill=(255, 204, 0))
                cy += 185

            for bi, bt in enumerate(sc.get("bullet_points", [])):
                if t >= 0.5 + bi * 0.35:
                    cy = wrap_txt(d, f"• {bt}", f_bul, 125, cy, 28, (74, 222, 128) if bi % 2 == 0 else (248, 250, 252), 18) + 25

            d.rounded_rectangle([(70, 1380), (W - 70, 1740)], radius=28, fill=(15, 23, 42, 220))
            wrap_txt(d, sc.get("voiceover", ""), f_sub, 105, 1420, 32, (148, 163, 184), 14)

            bw = int((W - 140) * ((idx + (f / n_frames)) / len(scenes)))
            d.rounded_rectangle([(70, 1810), (W - 70, 1826)], radius=8, fill=(255, 255, 255, 50))
            d.rounded_rectangle([(70, 1810), (70 + max(16, bw), 1826)], radius=8, fill=(255, 204, 0))

            Image.alpha_composite(img, ov).convert("RGB").save(fdir / f"frame_{f:04d}.jpg", quality=92)

        subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(fdir / "frame_%04d.jpg"), "-i", str(mp3), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-shortest", str(mp4)], check=True)
        clips.append(mp4)

    lst = TMP / "list.txt"
    lst.write_text("\n".join([f"file '{p.resolve()}'" for p in clips]), "utf-8")
    final_mp4 = OUT / f"malayalam_psc_reel_{dt}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final_mp4)], check=True)

    if TG_TOKEN and TG_CHAT:
        with open(final_mp4, "rb") as vf:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={"chat_id": TG_CHAT, "caption": f"📌 {data.get('topic','')}\n\n{data.get('instagram_caption','')}"[:1000]}, files={"video": vf}, timeout=120).raise_for_status()
    print("Video ready:", final_mp4)

if __name__ == "__main__":
    asyncio.run(build())
import math
import os
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import edge_tts
import requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1920
FPS = 30

VOICE_NAME = os.getenv("MALAYALAM_VOICE", "ml-IN-MidhunNeural")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp_build")
HISTORY_FILE = Path("used_topics.json")

BG_TOP = (13, 17, 28)
BG_BOTTOM = (25, 33, 56)
CARD_BG = (32, 43, 70, 235)
ACCENT_GOLD = (255, 204, 0)
ACCENT_CYAN = (56, 189, 248)
ACCENT_GREEN = (74, 222, 128)
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)


def load_used_topics() -> List[str]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_used_topic(topic: str) -> None:
    topics = load_used_topics()
    if topic not in topics:
        topics.append(topic)
        HISTORY_FILE.write_text(
            json.dumps(topics[-200:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def generate_psc_script() -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    used_topics = load_used_topics()
    avoid_str = ", ".join(used_topics[-30:]) if used_topics else "None"

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
നിങ്ങൾ ഒരു കേരള PSC അദ്ധ്യാപകനാണ്. PSC പരീക്ഷകളിൽ ആവർത്തിച്ചു ചോദിക്കുന്ന ഒരു പ്രധാന ചോദ്യം എടുത്ത്, ആ ചോദ്യവും അതിന്റെ ഉത്തരവും, എന്തുകൊണ്ട് അങ്ങനെ സംഭവിച്ചു എന്ന ചരിത്രപരമോ ശാസ്ത്രീയമോ ഭരണഘടനാപരമോ ആയ കാരണങ്ങളും ലളിതമായി പഠിപ്പിച്ചു കൊടുക്കുന്ന 60-സെക്കൻഡ് എക്സ്പ്ലെയ്നർ വീഡിയോ സ്ക്രിപ്റ്റ് തയ്യാറാക്കുക.

ശ്രദ്ധിക്കേണ്ട കാര്യങ്ങൾ:
- ഇതൊരു ക്വിസ്/കൗണ്ട്ഡൗൺ വീഡിയോ അല്ല. ആദ്യം തന്നെ ചോദ്യവും ഉത്തരവും പറഞ്ഞ ശേഷം അതിന്റെ കാരണങ്ങളും പശ്ചാത്തലവും പഠിപ്പിച്ചു കൊടുക്കുകയാണ് വേണ്ടത്.
- മുൻപ് ഉപയോഗിച്ച ഈ വിഷയങ്ങൾ ഒഴിവാക്കുക: {avoid_str}
- കൃത്യമായി 5 സീനുകൾ ഉണ്ടായിരിക്കണം (ആകെ വോയ്‌സ് ഓവർ വായിക്കാൻ ഏകദേശം 50-60 സെക്കൻഡ് എടുക്കണം).

താഴെ പറയുന്ന JSON ഘടനയിൽ മാത്രം ഉത്തരം നൽകുക:
{{
  "topic": "വിഷയത്തിന്റെ പേര് (Malayalam)",
  "instagram_caption": "ഇൻസ്റ്റാഗ്രാമിൽ പോസ്റ്റ് ചെയ്യാനുള്ള ക്യാപ്ഷനും ഹാഷ്ടാഗുകളും (#keralapsc #psctips)",
  "scenes": [
    {{
      "section_tag": "ഇന്നത്തെ PSC ചോദ്യം",
      "headline": "ചോദ്യം (ചുരുക്കത്തിൽ)",
      "highlight_answer": "പ്രധാന ഉത്തരം (1-4 വാക്കുകൾ)",
      "bullet_points": ["പ്രധാന പോയിന്റ് 1", "പ്രധാന പോയിന്റ് 2"],
      "voiceover": "ആദ്യത്തെ 8-10 സെക്കൻഡ് വായിക്കാനുള്ള മലയാളം വിശദീകരണം."
    }},
    {{
      "section_tag": "എന്തുകൊണ്ട് ഇങ്ങനെ സംഭവിച്ചു?",
      "headline": "പ്രധാന കാരണം / പശ്ചാത്തലം",
      "highlight_answer": "പ്രധാന വർഷം / വ്യക്തി",
      "bullet_points": ["காரണം 1 ലളിതമായി", "കാരണം 2 ലളിതമായി"],
      "voiceover": "അടുത്ത 12-15 സെക്കൻഡ് വായിക്കാനുള്ള വിശദീകരണം."
    }},
    {{
      "section_tag": "ചരിത്രപരമായ വസ്തുതകൾ",
      "headline": "പ്രധാന സംഭവങ്ങൾ",
      "highlight_answer": "ഓർത്തിരിക്കേണ്ട പേര്/തീയതി",
      "bullet_points": ["വസ്തുത 1", "വസ്തുത 2"],
      "voiceover": "അടുത്ത 12-15 സെക്കൻഡ് വായിക്കാനുള്ള വിശദീകരണം."
    }},
    {{
      "section_tag": "PSC പരീക്ഷാ പോയിന്റുകൾ",
      "headline": "അനുബന്ധ ചോദ്യങ്ങൾ",
      "highlight_answer": "പരീക്ഷാ ടിപ്പ്",
      "bullet_points": ["അനുബന്ധ ചോദ്യം & ഉത്തരം 1", "അനുബന്ധ ചോദ്യം & ഉത്തരം 2"],
      "voiceover": "അടുത്ത 12-15 സെക്കൻഡ് വായിക്കാനുള്ള വിശദീകരണം."
    }},
    {{
      "section_tag": "റിവിഷൻ & ഫോളോ",
      "headline": "ദിവസവും ഒരു PSC അറിവ്!",
      "highlight_answer": "Follow & Save",
      "bullet_points": ["വീഡിയോ സേവ് ചെയ്യുക", "കൂട്ടുകാർക്ക് ഷെയർ ചെയ്യുക"],
      "voiceover": "അവസാന 5-7 സെക്കൻഡ് വായിക്കാനുള്ള ഔട്രോ."
    }}
  ]
}}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )

    data = json.loads(response.text)
    if "topic" in data:
        save_used_topic(data["topic"])
    return data


async def synthesize_scene_audio(text: str, out_mp3: Path) -> float:
    communicate = edge_tts.Communicate(text=text, voice=VOICE_NAME, rate="-2%")
    await communicate.save(str(out_mp3))
    return get_audio_duration(out_mp3)


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return max(3.0, float(res.stdout.strip()))


def find_malayalam_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/smc/Manjari-Bold.ttf" if bold else "/usr/share/fonts/truetype/smc/Manjari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def create_vertical_gradient() -> Image.Image:
    base = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(base)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return base


def draw_wrapped_text(draw, text, font, x, y, max_chars, fill, line_spacing=16) -> int:
    lines = textwrap.wrap(text, width=max_chars)
    curr_y = y
    for line in lines:
        draw.text((x, curr_y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, curr_y), line, font=font)
        curr_y += (bbox[3] - bbox[1]) + line_spacing
    return curr_y


def render_scene_clip(scene, scene_idx, total_scenes, duration, audio_path, out_mp4, bg_template) -> None:
    total_frames = int(math.ceil(duration * FPS))
    frames_dir = TEMP_DIR / f"frames_{scene_idx}"
    frames_dir.mkdir(parents=True, exist_ok=True)

    font_tag = find_malayalam_font(38, bold=True)
    font_head = find_malayalam_font(54, bold=True)
    font_ans = find_malayalam_font(62, bold=True)
    font_bullet = find_malayalam_font(42, bold=False)
    font_sub = find_malayalam_font(36, bold=False)

    for f in range(total_frames):
        t = f / FPS
        progress = min(1.0, t / 0.45)
        ease = 1 - (1 - progress) ** 3
        slide_offset = int((1 - ease) * 70)

        img = bg_template.copy().convert("RGBA")
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        tag_y = 140 + slide_offset
        draw.rounded_rectangle([(70, tag_y), (WIDTH - 70, tag_y + 85)], radius=24, fill=(56, 189, 248, int(45 * ease)), outline=ACCENT_CYAN, width=3)
        draw.text((110, tag_y + 18), f"#{scene_idx + 1}  {scene.get('section_tag', 'PSC Explainer')}", font=font_tag, fill=ACCENT_CYAN)

        card_top = 270 + slide_offset
        card_bottom = 1320 + slide_offset
        draw.rounded_rectangle([(70, card_top), (WIDTH - 70, card_bottom)], radius=36, fill=CARD_BG, outline=(255, 255, 255, 45), width=2)

        curr_y = card_top + 60
        curr_y = draw_wrapped_text(draw, scene.get("headline", ""), font_head, 120, curr_y, 24, TEXT_WHITE, 20)

        ans_progress = max(0.0, min(1.0, (t - 0.25) / 0.4))
        if ans_progress > 0:
            curr_y += 30
            box_h = 130
            draw.rounded_rectangle([(115, curr_y), (WIDTH - 115, curr_y + box_h)], radius=24, fill=(255, 204, 0, int(35 * ans_progress)), outline=ACCENT_GOLD, width=4)
            draw.text((150, curr_y + 30), str(scene.get("highlight_answer", "")), font=font_ans, fill=ACCENT_GOLD)
            curr_y += box_h + 55

        for b_idx, b_text in enumerate(scene.get("bullet_points", [])):
            if t >= 0.5 + b_idx * 0.35:
                curr_y = draw_wrapped_text(draw, f"• {b_text}", font_bullet, 125, curr_y, 28, ACCENT_GREEN if b_idx % 2 == 0 else TEXT_WHITE, 18)
                curr_y += 25

        sub_top = 1380
        draw.rounded_rectangle([(70, sub_top), (WIDTH - 70, 1740)], radius=28, fill=(15, 23, 42, 220))
        draw_wrapped_text(draw, scene.get("voiceover", ""), font_sub, 105, sub_top + 40, 32, TEXT_MUTED, 14)

        overall_progress = (scene_idx + (f / total_frames)) / total_scenes
        bar_width = int((WIDTH - 140) * overall_progress)
        draw.rounded_rectangle([(70, 1810), (WIDTH - 70, 1826)], radius=8, fill=(255, 255, 255, 50))
        draw.rounded_rectangle([(70, 1810), (70 + max(16, bar_width), 1826)], radius=8, fill=ACCENT_GOLD)

        combined = Image.alpha_composite(img, overlay).convert("RGB")
        combined.save(frames_dir / f"frame_{f:04d}.jpg", quality=92)

    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", str(frames_dir / "frame_%04d.jpg"),
        "-i", str(audio_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_mp4),
    ]
    subprocess.run(cmd, check=True)


def concat_scene_videos(scene_files: List[Path], final_mp4: Path) -> None:
    concat_list = TEMP_DIR / "concat_list.txt"
    concat_list.write_text("\n".join([f"file '{p.resolve()}'" for p in scene_files]), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(final_mp4)], check=True)


def send_to_telegram(video_path: Path, caption: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, "rb") as vf:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1000]}, files={"video": vf}, timeout=120).raise_for_status()


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    script_data = generate_psc_script()
    date_str = datetime.date.today().isoformat()
    bg_template = create_vertical_gradient()
    scenes = script_data.get("scenes", [])
    scene_mp4s: List[Path] = []

    for idx, scene in enumerate(scenes):
        audio_file = TEMP_DIR / f"scene_{idx}.mp3"
        scene_mp4 = TEMP_DIR / f"scene_{idx}.mp4"
        duration = await synthesize_scene_audio(scene["voiceover"], audio_file)
        render_scene_clip(scene, idx, len(scenes), duration + 0.3, audio_file, scene_mp4, bg_template)
        scene_mp4s.append(scene_mp4)

    final_video = OUTPUT_DIR / f"malayalam_psc_reel_{date_str}.mp4"
    concat_scene_videos(scene_mp4s, final_video)
    caption = f"📌 {script_data.get('topic', 'PSC Explainer')}\n\n{script_data.get('instagram_caption', '#keralapsc')}"
    send_to_telegram(final_video, caption)


if __name__ == "__main__":
    asyncio.run(main())
