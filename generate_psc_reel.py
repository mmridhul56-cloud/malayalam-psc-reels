import asyncio, datetime, io, json, math, os, subprocess, textwrap, urllib.parse, wave
from pathlib import Path
import edge_tts, numpy as np, requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 24
VOICE = os.getenv("MALAYALAM_VOICE", "ml-IN-MidhunNeural")
KEY = os.getenv("GEMINI_API_KEY", "")
OUT, TMP, HIST = Path("output"), Path("temp_build"), Path("used_topics.json")

FALLBACK = {
    "topic": "വൈക്കം സത്യഗ്രഹം (1924-1925)",
    "scenes": [
        {"step_badge": "ചോദ്യവും ഉത്തരവും", "year_tag": "1924 മാർച്ച് 30", "headline_ml": "വൈക്കം സത്യഗ്രഹം!", "key_fact_ml": "സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള ആദ്യ സംഘടിത സമരം (603 ദിവസം)", "omni_prompt": "Vertical 9:16 cinematic 3D tilt-shift miniature diorama of Vaikom Temple in 1924 Kerala, golden morning sunlight, coconut palms, miniature freedom fighters in white khadi, photorealistic, no text", "voiceover": "കേരള പി എസ് സി പരീക്ഷകളിൽ സ്ഥിരമായി ചോദിക്കുന്ന ചോദ്യമാണ് വൈക്കം സത്യഗ്രഹം ആരംഭിച്ചത് എന്നാണെന്ന്. 1924 മാർച്ച് 30-നാണ് സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള ഈ ഐതിഹാസിക സമരം ആരംഭിച്ചത്."},
        {"step_badge": "എന്തുകൊണ്ട് സംഭവിച്ചു?", "year_tag": "1923 കാക്കിനഡ", "headline_ml": "വഴിനടക്കാനുള്ള അവകാശം", "key_fact_ml": "1923 കാക്കിനഡ കോൺഗ്രസ് സമ്മേളനത്തിൽ ടി.കെ. മാധവൻ പ്രമേയം അവതരിപ്പിച്ചു", "omni_prompt": "Vertical 9:16 cinematic 3D miniature diorama of 1920s Kerala village road beside temple wall under monsoon clouds, warm lantern glow, wooden barrier, photorealistic, no text", "voiceover": "വൈക്കം ക്ഷേത്രത്തിന് ചുറ്റുമുള്ള പൊതുവഴികളിലൂടെ അവർണ്ണർക്ക് നടക്കാൻ അന്ന് വിലക്കുണ്ടായിരുന്നു. 1923-ലെ കാക്കിനഡ കോൺഗ്രസ് സമ്മേളനത്തിൽ ടി.കെ. മാധവൻ അവതരിപ്പിച്ച പ്രമേയമാണ് ഈ സമരത്തിന് തുടക്കമിട്ടത്."},
        {"step_badge": "പ്രധാന സംഭവങ്ങൾ", "year_tag": "1924 - 1925", "headline_ml": "സവർണ്ണ ജാഥയും ഗാന്ധിജിയും", "key_fact_ml": "മന്നത്ത് പത്മനാഭൻ നയിച്ച സവർണ്ണ ജാഥ • 1925 മാർച്ചിൽ ഗാന്ധിജി വൈക്കത്ത്", "omni_prompt": "Vertical 9:16 cinematic 3D miniature diorama of grand peaceful procession in white khadi marching along misty Kerala palm highway towards palace, golden rays, no text", "voiceover": "ടി.കെ. മാധവൻ, കെ.പി. കേശവമേനോൻ എന്നിവർ സമരത്തിന് നേതൃത്വം നൽകി. സമരത്തിന് പിന്തുണയുമായി മന്നത്ത് പത്മനാഭൻ തിരുവനന്തപുരത്തേക്ക് സവർണ്ണ ജാഥ നയിച്ചു. 1925 മാർച്ചിൽ ഗാന്ധിജിയും വൈക്കം സന്ദർശിച്ചു."},
        {"step_badge": "PSC പരീക്ഷാ പോയിന്റ്", "year_tag": "1925 നവംബർ 23", "headline_ml": "603 ദിവസത്തെ സമരവിജയം!", "key_fact_ml": "റാണി സേതു ലക്ഷ്മി ഭായി വഴികൾ തുറന്നുകൊടുത്തു • വൈക്കം വീരർ: ഇ.വി. രാമസ്വാമി", "omni_prompt": "Vertical 9:16 cinematic 3D miniature diorama of temple gates opening in 1925 Kerala at sunrise, golden sunbeams over palm trees and backwaters, joyful crowd, no text", "voiceover": "ഒടുവിൽ 603 ദിവസത്തെ സമരത്തിനൊടുവിൽ 1925 നവംബർ 23-ന് തിരുവിതാംകൂർ റീജന്റ് റാണി സേതു ലക്ഷ്മി ഭായി വഴികൾ തുറന്നുകൊടുത്തതോടെ സമരം വിജയിച്ചു. തുടർന്നും പി എസ് സി അറിവുകൾക്കായി ഫോളോ ചെയ്യൂ!"}
    ]
}

def get_data():
    used = json.loads(HIST.read_text("utf-8")) if HIST.exists() else []
    if not KEY: return FALLBACK
    client = genai.Client(api_key=KEY)
    prompt = f"നിങ്ങൾ കേരള PSC അദ്ധ്യാപകനാണ്. മുൻപ് ഉപയോഗിച്ചവ ഒഴിവാക്കുക: {', '.join(used[-25:]) or 'None'}. ഒരു പ്രധാന PSC ചോദ്യം എടുത്ത് അതിന്റെ ഉത്തരവും കാരണങ്ങളും പഠിപ്പിക്കുന്ന 4 സീനുകളുള്ള (60s) സ്ക്രിപ്റ്റ് ഉണ്ടാക്കുക. JSON format only: " + '{"topic":"വിഷയം","scenes":[{"step_badge":"ചോദ്യവും ഉത്തരവും","year_tag":"1924","headline_ml":"മലയാളം തലക്കെട്ട്","key_fact_ml":"പ്രധാന PSC പോയിന്റ്","omni_prompt":"Vertical 9:16 cinematic 3D tilt-shift miniature diorama of ..., warm golden volumetric light, photorealistic, no text","voiceover":"13-15 സെക്കൻഡ് മലയാളം വിവരണം."}]}'
    for m in ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"]:
        try:
            r = client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7))
            if r and r.text:
                d = json.loads(r.text)
                if isinstance(d, list): d = d[0]
                if d.get("scenes"):
                    if d.get("topic") and d["topic"] not in used:
                        used.append(d["topic"])
                        HIST.write_text(json.dumps(used[-200:], ensure_ascii=False), "utf-8")
                    return d
        except Exception as e:
            print("Model note:", m, e)
    return FALLBACK

def make_art(idx, sub):
    np.random.seed(100 + idx * 10 + sub)
    yy, xx = np.mgrid[0:H, 0:W]
    yn, xn = yy / H, xx / W
    pals = [((18,12,34),(165,88,28),(255,195,75)), ((10,24,38),(28,82,105),(245,165,55)), ((24,10,22),(135,38,42),(255,180,45)), ((8,26,28),(22,98,82),(250,210,95))]
    tc, mc, gc = pals[(idx + sub) % 4]
    sx, sy = 0.5 + (0.12 if sub == 0 else -0.12), 0.42
    ds = np.sqrt((xn - sx)**2 + ((yn - sy)*1.35)**2)
    rays = ((0.5 + 0.5 * np.sin(np.arctan2(yn - sy, xn - sx) * 18.0 + idx))**3) * np.exp(-ds * 2.2) * 0.45
    gl = np.clip(np.exp(-ds * 3.2) + rays, 0, 1)
    rgb = np.zeros((H, W, 3), dtype=np.uint8)
    for c in range(3):
        b = tc[c]*(1 - yn) + mc[c]*yn
        rgb[:, :, c] = np.clip(b + (gc[c] - b)*gl, 0, 255).astype(np.uint8)
    im = Image.fromarray(rgb, "RGB").convert("RGBA")
    dr = ImageDraw.Draw(im)
    hy, cx = 1120, W // 2 + (40 if sub == 0 else -40)
    for tw, th, ty in [(260, 75, hy - 90), (200, 70, hy - 155), (140, 65, hy - 215)]:
        dr.polygon([(cx-tw, ty+th), (cx-tw+35, ty), (cx+tw-35, ty), (cx+tw, ty+th)], fill=(14, 10, 20, 250), outline=(*gc, 170), width=2)
    dr.rectangle([(0, hy), (W, H)], fill=(8, 10, 18, 245))
    return im

def get_img(prompt_en, idx, sub):
    try:
        q = urllib.parse.quote(prompt_en[:340])
        r = requests.get(f"https://image.pollinations.ai/prompt/{q}?width=1080&height=1920&seed={2026+idx*17+sub}&nologo=true&model=flux", timeout=22)
        if r.status_code == 200 and len(r.content) > 15000:
            return Image.open(io.BytesIO(r.content)).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
    except Exception:
        pass
    return make_art(idx, sub)

def fnt(txt, sz):
    ml = any("\u0d00" <= c <= "\u0d7f" for c in str(txt))
    for p in (["/usr/share/fonts/truetype/smc/Manjari-Bold.ttf", "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Bold.ttf"] if ml else ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]):
        if os.path.exists(p): return ImageFont.truetype(p, size=sz)
    return ImageFont.load_default()

def make_bgm(dur, wav_p):
    sr = 44100
    t = np.linspace(0, dur, int(dur * sr), endpoint=False)
    dr = 0.35 * np.sin(2 * np.pi * 73.42 * t) + 0.22 * np.sin(2 * np.pi * 110.0 * t)
    pe = 0.5 + 0.5 * np.sin(2 * np.pi * (100.0 / 60.0) * t - np.pi / 2) ** 4
    ch = 0.25 * np.sin(2 * np.pi * 587.33 * t) * np.exp(-np.maximum(0, t - 0.35) * 6.5) * (t >= 0.35)
    pcm = np.clip((dr * (0.6 + 0.4 * pe) + ch) * 0.11 * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(wav_p), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())

async def main():
    OUT.mkdir(parents=True, exist_ok=True); TMP.mkdir(parents=True, exist_ok=True)
    dt = datetime.date.today().isoformat()
    data = get_data()
    scenes = data.get("scenes", [])
    clips = []
    for idx, sc in enumerate(scenes):
        mp3, mp4 = TMP / f"s_{idx}.mp3", TMP / f"s_{idx}.mp4"
        await edge_tts.Communicate(text=sc["voiceover"], voice=VOICE, rate="-2%").save(str(mp3))
        res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)], capture_output=True, text=True, check=True)
        dur = max(4.0, float(res.stdout.strip())) + 0.35
        im_a = get_img(sc.get("omni_prompt", "Kerala history 3D diorama"), idx, 0)
        im_b = get_img(sc.get("omni_prompt", "Kerala history") + " close up warm light", idx, 1)
        nf = int(math.ceil(dur * FPS))
        fdir = TMP / f"f_{idx}"
        fdir.mkdir(parents=True, exist_ok=True)
        for f in range(nf):
            t = f / FPS
            pr = t / dur
            za = 1.03 + 0.16 * min(1.0, pr * 1.4)
            cwa, cha = W / za, H / za
            pxa, pya = (W - cwa) * (0.35 + 0.25 * math.sin(pr * math.pi)), (H - cha) * (0.42 - 0.15 * pr)
            fa = im_a.crop((int(pxa), int(pya), int(pxa + cwa), int(pya + cha))).resize((W, H), Image.Resampling.BILINEAR)
            if pr < 0.48: frm = fa
            else:
                pb = (pr - 0.48) / 0.52
                zb = 1.18 - 0.14 * pb
                cwb, chb = W / zb, H / zb
                pxb, pyb = (W - cwb) * (0.60 - 0.25 * pb), (H - chb) * (0.30 + 0.12 * pb)
                fb = im_b.crop((int(pxb), int(pyb), int(pxb + cwb), int(pyb + chb))).resize((W, H), Image.Resampling.BILINEAR)
                frm = Image.blend(fa, fb, min(1.0, (pr - 0.48) / 0.12))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            for pi in range(24):
                px, py = int((pi * 197 + t * 30) % W), int(((pi * 311 - t * 45) % (H - 450)) + 220)
                d.ellipse([(px-3, py-3), (px+3, py+3)], fill=(255, 215, 90, 120))
            for y in range(340): d.line([(0, y), (W, y)], fill=(6, 10, 18, int(195 * (1 - y / 340))))
            for y in range(H - 600, H): d.line([(0, y), (W, y)], fill=(6, 10, 18, int(230 * ((y - (H - 600)) / 600))))
            d.rounded_rectangle([(48, 86), (640, 150)], radius=22, fill=(18, 28, 46, 228), outline=(56, 189, 248, 185), width=2)
            d.text((75, 100), sc.get("step_badge", "PSC"), font=fnt(sc.get("step_badge", "PSC"), 25), fill=(255, 255, 255, 255))
            if sc.get("year_tag"):
                d.rounded_rectangle([(W - 340, 86), (W - 48, 150)], radius=20, fill=(255, 204, 0, 245))
                d.text((W - 315, 99), str(sc["year_tag"])[:16], font=fnt(sc["year_tag"], 27), fill=(12, 16, 24, 255))
            d.rounded_rectangle([(48, 172), (W - 48, 278)], radius=24, fill=(14, 22, 36, 215), outline=(255, 204, 0, 175), width=2)
            hl = sc.get("headline_ml", "")
            fh = fnt(hl, 42)
            bb = d.textbbox((0, 0), hl, font=fh)
            d.text(((W - (bb[2] - bb[0])) // 2, 198), hl, font=fh, fill=(255, 215, 60, 255))
            d.rounded_rectangle([(52, 1335), (W - 52, 1483)], radius=22, fill=(16, 26, 42, 232), outline=(74, 222, 128, 185), width=2)
            d.rounded_rectangle([(52, 1335), (72, 1483)], radius=10, fill=(74, 222, 128, 255))
            d.text((94, 1351), "PSC EXAM POINT", font=fnt("PSC", 19), fill=(74, 222, 128, 255))
            fk = fnt(sc.get("key_fact_ml", ""), 28)
            for ki, kl in enumerate(textwrap.wrap(sc.get("key_fact_ml", ""), width=42)[:2]):
                d.text((94, 1383 + ki * 40), kl, font=fk, fill=(248, 250, 252, 255))
            vls = textwrap.wrap(sc.get("voiceover", ""), width=34)
            fv = fnt(sc.get("voiceover", ""), 31)
            act = min(len(vls) - 1, int(pr * len(vls))) if vls else 0
            d.rounded_rectangle([(52, 1502), (W - 52, 1536 + len(vls) * 42)], radius=22, fill=(8, 12, 20, 235), outline=(255, 255, 255, 65), width=2)
            for li, ln in enumerate(vls):
                bb = d.textbbox((0, 0), ln, font=fv)
                d.text(((W - (bb[2] - bb[0])) // 2, 1520 + li * 42), ln, font=fv, fill=(255, 215, 0, 255) if li == act else (215, 225, 238, 215))
            Image.alpha_composite(frm, ov).convert("RGB").save(fdir / f"frame_{f:04d}.jpg", quality=92)
        bgm = TMP / f"bgm_{idx}.wav"
        make_bgm(dur, bgm)
        subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(fdir / "frame_%04d.jpg"), "-i", str(mp3), "-i", str(bgm), "-filter_complex", "[1:a]volume=1.35[vo];[2:a]volume=0.85[bg];[vo][bg]amix=inputs=2:duration=first[aout]", "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-shortest", str(mp4)], check=True)
        clips.append(mp4)
    lst = TMP / "list.txt"
    lst.write_text("\n".join([f"file '{p.resolve()}'" for p in clips]), "utf-8")
    final_mp4 = OUT / f"malayalam_psc_chronolens_reel_{dt}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final_mp4)], check=True)

if __name__ == "__main__":
    asyncio.run(main())
