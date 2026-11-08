#!/usr/bin/env python3
import asyncio
import datetime
import json
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
      "bullet_points": ["കാരണം 1 ലളിതമായി", "കാരണം 2 ലളിതമായി"],
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

    candidate_models = ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"]
    try:
    for m in client.models.list():
        name = getattr(m, "name", "")
            if "gemini" in name and ("flash" in name or "pro" in name) and not any(x in name for x in ["tts", "image", "embedding", "vision", "audio", "live"]):
            short_name = name.replace("models/", "")
            if short_name not in candidate_models and short_name != "gemini-2.5-flash":
                candidate_models.insert(0, short_name)
                except Exception as e:
         print(f"Warning listing models: {e}")
                
    response = None
    for model_name in candidate_models:
       try:
           print(f"Trying model: {model_name}")
           response = client.models.generate_content(
              model=model_name,
              contents=prompt,
              config=types.GenerateContentConfig(
                  response_mime_type="application/json",
                  temperature=0.7,
              ),
           )
           if response and response.text:
              break
       except Exception as e:
           print(f"Model {model_name} failed: {e}")
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
