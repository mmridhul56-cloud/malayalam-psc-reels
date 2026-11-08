import asyncio, base64, datetime, json, os, subprocess, time
from pathlib import Path
from typing import Any, Dict, List
import edge_tts, requests
from google import genai
from google.genai import types

VOICE = os.getenv("MALAYALAM_VOICE", "ml-IN-MidhunNeural")
KEY = os.getenv("GEMINI_API_KEY", "")
OMNI_MODEL = os.getenv("OMNI_VIDEO_MODEL", "gemini-omni-1.2-flash")
OMNI_RESOLUTION = os.getenv("OMNI_RESOLUTION", "720p")
OUT, TMP, HIST = Path("output"), Path("temp_build"), Path("used_topics.json")

FALLBACK_STORYBOARD = {
    "topic": "വൈക്കം സത്യഗ്രഹം (1924-1925)",
    "psc_question": "വൈക്കം സത്യഗ്രഹം ആരംഭിച്ച വർഷവും തീയതിയും എന്നാണ്?",
    "psc_answer": "1924 മാർച്ച് 30 (603 ദിവസങ്ങൾ)",
    "instagram_caption": "വൈക്കം സത്യഗ്രഹം (1924–1925) — സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള കേരളത്തിലെ ആദ്യ സംഘടിത സമരം 📌 #keralapsc #psctips #malayalampsc",
    "scenes": [
        {
            "scene_number": 1, "duration_sec": 15, "step_badge": "ചോദ്യവും ഉത്തരവും",
            "headline_ml": "വൈക്കം സത്യഗ്രഹം: 1924 മാർച്ച് 30",
            "key_fact_ml": "സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള ആദ്യ സംഘടിത സമരം",
            "omni_prompt": "Vertical 9:16 cinematic 3D tilt-shift living historical miniature diorama of Vaikom Mahadeva Temple in 1924 Kerala, warm golden morning sunlight filtering through coconut palms and monsoon mist, miniature freedom fighters in white khadi walking peacefully along the temple road, smooth FPV camera flythrough pushing in from above, glowing golden time-portal particles in the air, photorealistic textures, 24fps, no text.",
            "voiceover": "കേരള പി എസ് സി പരീക്ഷകളിൽ സ്ഥിരമായി ചോദിക്കുന്ന ചോദ്യമാണ് വൈക്കം സത്യഗ്രഹം ആരംഭിച്ചത് എന്നാണെന്ന്. 1924 മാർച്ച് 30-നാണ് സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള ഈ ഐതിഹാസിക സമരം ആരംഭിച്ചത്."
        },
        {
            "scene_number": 2, "duration_sec": 15, "step_badge": "എന്തുകൊണ്ട് സംഭവിച്ചു?",
            "headline_ml": "വഴിനടക്കാനുള്ള അവകാശം",
            "key_fact_ml": "1923 കാക്കിനഡ സമ്മേളനത്തിൽ ടി.കെ. മാധവൻ പ്രമേയം അവതരിപ്പിച്ചു",
            "omni_prompt": "Vertical 9:16 cinematic 3D tilt-shift living historical diorama of a 1920s Kerala village road beside a traditional temple wall under dramatic monsoon clouds, warm vintage lantern glow, awooden barrier across the muddy road, slow orbital camera movement around miniature figures holding scrolls, photorealistic, 24fps, no text.",
            "voiceover": "വൈക്കം ക്ഷേത്രത്തിന് ചുറ്റുമുള്ള പൊതുവഴികളിലൂടെ അവർണ്ണർക്ക് നടക്കാൻ അന്ന് വിലക്കുണ്ടായിരുന്നു. 1923-ലെ കാക്കിനഡ കോൺഗ്രസ് സമ്മേളനത്തിൽ ടി.കെ. മാധവൻ അവതരിപ്പിച്ച പ്രമേയമാണ് ഈ സമരത്തിന് തുടക്കമിട്ടത്."
        },
        {
            "scene_number": 3, "duration_sec": 15, "step_badge": "പ്രധാന സംഭവങ്ങൾ",
            "headline_ml": "സവർണ്ണ ജാഥയും ഗാന്ധിജിയും",
            "key_fact_ml": "മന്നത്ത് പത്മനാഭൻ നയിച്ച സവർണ്ണ ജാഥ • 1925-ൽ ഗാന്ധിജി വൈക്കത്ത്",
            "omni_prompt": "Vertical 9:16 cinematic 3D tilt-shift living historical diorama of a grand procession of hundreds of miniature figures in white khadi marching with torches along a misty Kerala highway towards Trivandrum palace, golden time-portal light rays breaking through clouds, smooth tracking camera shot, 24fps, no text.",
            "voiceover": "ടി.കെ. മാധവൻ, കെ.പി. കേശവമേനോൻ എന്നിവർ സമരത്തിന് നേതൃത്വം നൽകി. സമരത്തിന് പിന്തുണയുമായി മന്നത്ത് പത്മനാഭൻ തിരുവനന്തപുരത്തേക്ക് സവർണ്ണ ജാഥ നയിച്ചു. 1925 മാർച്ചിൽ ഗാന്ധിജിയും വൈക്കം സന്ദർശിച്ചു."
        },
        {
            "scene_number": 4, "duration_sec": 15, "step_badge": "PSC പരീക്ഷാ പോയിന്റ്",
            "headline_ml": "603 ദിവസത്തെ സമരവിജയം!",
            "key_fact_ml": "1925 നവംബർ 23 • റാണി സേതു ലക്ഷ്മി ഭായി വഴികൾ തുറന്നുകൊടുത്തു",
            "omni_prompt": "Vertical 9:16 cinematic 3D tilt-shift living historical diorama of temple gates and roads opening in 1925 Kerala at sunrise, warm golden sunbeams illuminating lush green palm trees and backwaters, joyful miniature crowd walking freely together, gentle drone pull-back camera movement, 24fps, no text.",
            "voiceover": "ഒടുവിൽ 603 ദിവസത്തെ സമരത്തിനൊടുവിൽ 1925 നവംബർ 23-ന് തിരുവിതാംകൂർ റീജന്റ് റാണി സേതു ലക്ഷ്മി ഭായി വഴികൾ തുറന്നുകൊടുത്തതോടെ സമരം വിജയിച്ചു. തുടർന്നും പി എസ് സി അറിവുകൾക്കായി ഫോളോ ചെയ്യൂ!"
        }
    ]
}

def generate_psc_omni_storyboard() -> Dict[str, Any]:
    used = json.loads(HIST.read_text("utf-8")) if HIST.exists() else []
    client = genai.Client(api_key=KEY)
    prompt = (
        "നിങ്ങൾ കേരള PSC പരീക്ഷകൾക്കായി 1-മിനിറ്റ് (4 സീനുകൾ x 15 സെക്കൻഡ് = 60 സെക്കൻഡ്) ദൈർഘ്യമുള്ള 'ലിവിങ് ഹിസ്റ്ററി എക്സ്പ്ലെയ്നർ' വീഡിയോ സ്ക്രിപ്റ്റ് തയ്യാറാക്കുന്ന അദ്ധ്യാപകനാണ്. "
        f"മുൻപ് ഉപയോഗിച്ചവ ഒഴിവാക്കുക: {', '.join(used[-30:]) or 'None'}. "
        "മറ്റുള്ളവരുടെ മാപ്പ് വീഡിയോകൾ കോപ്പി ചെയ്യാതെ, നമ്മുടെ സ്വന്തം 'Cinematic 3D Tilt-Shift Living Historical Diorama & Time-Portal' ശൈലിയിലാണ് ഓരോ സീനിന്റെയും `omni_prompt` ഇംഗ്ലീഷിൽ നൽകേണ്ടത് (Google Flow Omni 1.2 Flash മോഡലിന് 15s 9:16 വീഡിയോ ഉണ്ടാക്കാൻ). "
        'JSON format only (4 scenes): {"topic":"വിഷയം","psc_question":"ചോദ്യം","psc_answer":"ഉത്തരം","instagram_caption":"ക്യാപ്ഷൻ #keralapsc","scenes":[{"scene_number":1,"duration_sec":15,"step_badge":"ചോദ്യവും ഉത്തരവും","headline_ml":"തലക്കെട്ട്","key_fact_ml":"പ്രധാന പോയിന്റ്","omni_prompt":"Vertical 9:16 cinematic 3D tilt-shift living historical diorama of ..., smooth FPV camera movement, golden volumetric light, 24fps, no text.","voiceover":"13-15 സെക്കൻഡ് മലയാളം വിവരണം."}]}'
    )
    models = ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"]
    resp = None
    for m in models:
        for attempt in range(2):
            try:
                resp = client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7))
                if resp and resp.text:
                    break
            except Exception as e:
                print(f"Model {m} note: {e}")
                time.sleep(3)
        if resp and resp.text:
            break
    if resp and resp.text:
        try:
            data = json.loads(resp.text)
            if isinstance(data, list):
                data = data[0]
            if data.get("scenes"):
                if "topic" in data and data["topic"] not in used:
                    used.append(data["topic"])
                    HIST.write_text(json.dumps(used[-200:], ensure_ascii=False, indent=2), "utf-8")
                return data
        except Exception as e:
            print("JSON fallback:", e)
    return FALLBACK_STORYBOARD

def generate_omni_video_clip(prompt_en: str, duration_sec: int, out_mp4: Path) -> bool:
    client = genai.Client(api_key=KEY)
    dur_str = f"{max(3, min(15, int(duration_sec)))}s"
    try:
        print(f"Calling {OMNI_MODEL} ({dur_str}, 9:16, {OMNI_RESOLUTION})...")
        interaction = client.interactions.create(
            model=OMNI_MODEL,
            input=prompt_en,
            response_format={"type": "video", "duration": dur_str, "aspect_ratio": "9:16", "resolution": OMNI_RESOLUTION},
            store=True,
        )
        if hasattr(interaction, "output_video") and getattr(interaction.output_video, "data", None):
            out_mp4.write_bytes(base64.b64decode(interaction.output_video.data))
            return True
    except Exception as e:
        print(f"Omni 1.2 API note (Paid Tier required for direct API video generation): {e}")
    return False

def export_google_flow_sheet(data: Dict[str, Any], out_txt: Path) -> None:
    lines = [
        "======================================================================",
        "GOOGLE FLOW (OMNI 1.2 FLASH) — 60s MALAYALAM PSC STORYBOARD",
        f"Topic   : {data.get('topic', '')}",
        f"Question: {data.get('psc_question', '')}",
        f"Answer  : {data.get('psc_answer', '')}",
        "======================================================================",
        "How to generate in Google Flow (https://flow.google.com/):",
        "1. Open https://flow.google.com/ -> New Project",
        "2. Select Model: 'Omni Flash (Omni 1.2)' -> Mode: 'Video'",
        "3. Set Aspect Ratio: '9:16' | Duration: '15s'",
        "4. Paste the 4 scene prompts below to generate your 4 clips,",
        "   connect them in Scenebuilder, and add the malayalam_psc_voiceover.mp3 file!",
        "----------------------------------------------------------------------\n",
    ]
    for sc in data.get("scenes", []):
        lines.extend([
            f"[SCENE {sc.get('scene_number', 1)} — 15s | {sc.get('step_badge', '')}]",
            f"Malayalam Title : {sc.get('headline_ml', '')}",
            f"Key PSC Fact    : {sc.get('key_fact_ml', '')}",
            f"Voiceover (ML)  : {sc.get('voiceover', '')}",
            f"Omni 1.2 Prompt : {sc.get('omni_prompt', '')}",
            "----------------------------------------------------------------------\n",
        ])
    out_txt.write_text("\n".join(lines), encoding="utf-8")

async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    dt = datetime.date.today().isoformat()
    data = generate_psc_omni_storyboard()
    (OUT / f"psc_omni_storyboard_{dt}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    export_google_flow_sheet(data, OUT / f"google_flow_omni_1_2_prompts_{dt}.txt")

    clips: List[Path] = []
    vo_parts: List[str] = []
    for idx, sc in enumerate(data.get("scenes", [])):
        vo_parts.append(sc.get("voiceover", ""))
        clip_mp4 = TMP / f"omni_scene_{idx+1}.mp4"
        if generate_omni_video_clip(sc.get("omni_prompt", ""), sc.get("duration_sec", 15), clip_mp4):
            clips.append(clip_mp4)

    vo_mp3 = OUT / f"malayalam_psc_voiceover_{dt}.mp3"
    await edge_tts.Communicate(text=" ... ".join(vo_parts), voice=VOICE, rate="-2%").save(str(vo_mp3))

    if clips:
        lst = TMP / "list.txt"
        lst.write_text("\n".join([f"file '{p.resolve()}'" for p in clips]), "utf-8")
        merged_v = TMP / "merged_omni.mp4"
        final_mp4 = OUT / f"malayalam_psc_omni_reel_{dt}.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(merged_v)], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(merged_v), "-i", str(vo_mp3), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final_mp4)], check=True)
        print("Final Omni 1.2 video ready:", final_mp4)

if __name__ == "__main__":
    asyncio.run(main())
