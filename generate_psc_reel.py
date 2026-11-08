import asyncio, datetime, json, math, os, subprocess, textwrap, time, wave
from pathlib import Path
from typing import Any, Dict, List, Tuple
import edge_tts, numpy as np, requests
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("MALAYALAM_VOICE", "ml-IN-MidhunNeural")
KEY = os.getenv("GEMINI_API_KEY", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
OUT, TMP, HIST = Path("output"), Path("temp_build"), Path("used_topics.json")

PLACES: Dict[str, Tuple[float, float]] = {
    "Kochi": (9.96, 76.24), "Mattancherry": (9.95, 76.26), "Fort Kochi": (9.965, 76.242),
    "Kodungallur": (10.22, 76.20), "Mahodayapuram": (10.23, 76.21), "Ponnani": (10.77, 75.92),
    "Perumpadappu": (10.72, 75.96), "Kozhikode": (11.25, 75.78), "Kappad": (11.38, 75.72),
    "Vaikom": (9.75, 76.39), "Kottayam": (9.59, 76.52), "Thrissur": (10.52, 76.21),
    "Tripunithura": (9.94, 76.35), "Thiruvananthapuram": (8.52, 76.93), "Venganoor": (8.41, 77.02),
    "Sivagiri": (8.74, 76.72), "Aruvippuram": (8.46, 77.05), "Chempazhanthy": (8.59, 76.91),
    "Attingal": (8.69, 76.81), "Colachel": (8.18, 77.25), "Kayamkulam": (9.17, 76.50),
    "Alappuzha": (9.49, 76.33), "Punnapra": (9.44, 76.34), "Vayalar": (9.68, 76.35),
    "Channar": (8.35, 77.15), "Periyar": (10.12, 76.48), "Kalady": (10.16, 76.44),
    "Aluva": (10.11, 76.35), "Guruvayur": (10.59, 76.04), "Palakkad": (10.78, 76.65),
    "Silent Valley": (11.13, 76.43), "Manjeri": (11.12, 76.12), "Tirur": (10.91, 75.92),
    "Chavakkad": (10.53, 76.01), "Thalassery": (11.75, 75.49), "Pazhassi": (11.89, 75.56),
    "Kannur": (11.87, 75.37), "Payyannur": (12.10, 75.20), "Kayyur": (12.26, 75.18),
    "Kasaragod": (12.50, 74.99), "Bekal": (12.39, 75.03), "Wayanad": (11.68, 76.13),
    "Idukki": (9.85, 76.97), "Munnar": (10.08, 77.06), "Pathanamthitta": (9.26, 76.78),
    "Kollam": (8.89, 76.61), "Kundara": (8.96, 76.68),
}

KERALA_DISTRICTS_RAW = {
    "Kasaragod": [(12.78,74.88),(12.75,75.25),(12.60,75.42),(12.35,75.40),(12.15,75.32),(12.12,75.10),(12.45,74.96)],
    "Kannur": [(12.12,75.10),(12.15,75.32),(12.12,75.65),(11.95,75.85),(11.75,75.88),(11.70,75.53),(11.88,75.35)],
    "Wayanad": [(11.95,75.85),(11.92,76.15),(11.85,76.40),(11.60,76.38),(11.50,75.95),(11.75,75.88)],
    "Kozhikode": [(11.70,75.53),(11.75,75.88),(11.50,75.95),(11.42,76.08),(11.22,75.98),(11.18,75.78),(11.45,75.65)],
    "Malappuram": [(11.18,75.78),(11.22,75.98),(11.42,76.08),(11.42,76.38),(11.15,76.50),(10.88,76.35),(10.72,76.05),(10.75,75.92)],
    "Palakkad": [(10.88,76.35),(11.15,76.50),(11.20,76.72),(10.95,76.92),(10.55,76.88),(10.45,76.65),(10.55,76.25),(10.72,76.05)],
    "Thrissur": [(10.75,75.92),(10.72,76.05),(10.55,76.25),(10.45,76.65),(10.28,76.75),(10.18,76.15),(10.45,76.02)],
    "Ernakulam": [(10.18,76.15),(10.28,76.75),(10.05,76.82),(9.82,76.60),(9.80,76.42),(9.82,76.24),(9.98,76.22)],
    "Idukki": [(10.28,76.75),(10.22,77.15),(10.05,77.32),(9.65,77.25),(9.45,77.15),(9.48,76.90),(9.82,76.60),(10.05,76.82)],
    "Kottayam": [(9.82,76.40),(9.82,76.60),(9.48,76.90),(9.42,76.55),(9.55,76.38),(9.70,76.37)],
    "Alappuzha": [(9.82,76.24),(9.82,76.40),(9.70,76.37),(9.55,76.38),(9.42,76.55),(9.15,76.60),(9.12,76.43),(9.48,76.32)],
    "Pathanamthitta": [(9.48,76.90),(9.45,77.15),(9.25,77.22),(9.12,77.10),(9.15,76.60),(9.42,76.55)],
    "Kollam": [(9.12,76.43),(9.15,76.60),(9.12,77.10),(8.92,77.20),(8.78,77.08),(8.78,76.65),(8.95,76.53)],
    "Thiruvananthapuram": [(8.78,76.65),(8.78,77.08),(8.55,77.25),(8.32,77.22),(8.28,77.05),(8.52,76.85)],
}

COASTLINE_WEST_RAW = [
    (14.0, 74.40), (13.2, 74.72), (12.78, 74.88), (12.45, 74.96), (12.12, 75.10),
    (11.88, 75.35), (11.70, 75.53), (11.45, 75.65), (11.18, 75.78), (10.75, 75.92),
    (10.45, 76.02), (10.18, 76.15), (9.98, 76.22), (9.82, 76.24), (9.48, 76.32),
    (9.12, 76.43), (8.95, 76.53), (8.78, 76.65), (8.52, 76.85), (8.28, 77.05),
    (8.08, 77.55), (8.50, 78.15), (9.28, 79.15), (10.30, 79.85), (11.80, 79.85), (14.0, 80.30)
]

def subdivide_organic_polygon(pts, closed=True, iterations=4, roughness=0.12):
    curr = list(pts)
    for it in range(iterations):
        nxt = []
        n = len(curr)
        limit = n if closed else n - 1
        scale = roughness * (0.52 ** it)
        for i in range(limit):
            p1, p2 = curr[i], curr[(i + 1) % n]
            nxt.append(p1)
            a, b = (p1, p2) if p1 < p2 else (p2, p1)
            h = math.sin(a[0] * 127.1 + a[1] * 311.7 + b[0] * 269.5 + b[1] * 183.3 + it * 17.0)
            dx, dy = b[1] - a[1], -(b[0] - a[0])
            nxt.append((0.5 * (a[0] + b[0]) + h * scale * dx, 0.5 * (a[1] + b[1]) + h * scale * dy))
        if not closed:
            nxt.append(curr[-1])
        curr = nxt
    return curr

def load_kerala_districts() -> Dict[str, List[List[Tuple[float, float]]]]:
    geojson_cache = TMP / "kerala_districts.geojson"
    try:
        if not geojson_cache.exists():
            TMP.mkdir(parents=True, exist_ok=True)
            r = requests.get("https://raw.githubusercontent.com/geohacker/kerala/master/geojsons/district.geojson", timeout=12)
            if r.status_code == 200:
                geojson_cache.write_text(r.text, encoding="utf-8")
        if geojson_cache.exists():
            gj = json.loads(geojson_cache.read_text(encoding="utf-8"))
            out: Dict[str, List[List[Tuple[float, float]]]] = {}
            for feat in gj.get("features", []):
                props = feat.get("properties", {})
                dname = props.get("DISTRICT") or props.get("district") or props.get("NAME_2") or ""
                geom = feat.get("geometry", {})
                gtype = geom.get("type", "")
                coords = geom.get("coordinates", [])
                polys = []
                if gtype == "Polygon":
                    for ring in coords[:1]:
                        polys.append([(pt[1], pt[0]) for pt in ring])
                elif gtype == "MultiPolygon":
                    for poly in coords:
                        for ring in poly[:1]:
                            polys.append([(pt[1], pt[0]) for pt in ring])
                if dname and polys:
                    out[dname] = polys
            if len(out) >= 10:
                return out
    except Exception as e:
        print("GeoJSON fallback:", e)
    return {k: [subdivide_organic_polygon(v, closed=True, iterations=4, roughness=0.12)] for k, v in KERALA_DISTRICTS_RAW.items()}

MAP_W, MAP_H = 2200, 3600
LAT_MIN, LAT_MAX = 7.6, 13.4
LON_MIN, LON_MAX = 73.6, 78.4

def latlon_to_xy(lat: float, lon: float) -> Tuple[float, float]:
    return ((lon - LON_MIN) / (LON_MAX - LON_MIN) * MAP_W, (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * MAP_H)

def build_master_dark_map(districts_map: Dict[str, List[List[Tuple[float, float]]]]) -> Image.Image:
    np.random.seed(42)
    yy, xx = np.mgrid[0:MAP_H, 0:MAP_W]
    lat_grid = LAT_MAX - (yy / MAP_H) * (LAT_MAX - LAT_MIN)
    lon_grid = LON_MIN + (xx / MAP_W) * (LON_MAX - LON_MIN)
    ghats_lon = 77.2 - (lat_grid - 8.2) * 0.36
    ridge = np.exp(-((lon_grid - ghats_lon) ** 2) / (2 * 0.22 ** 2))
    noise1 = gaussian_filter(np.random.randn(MAP_H // 4, MAP_W // 4), sigma=5)
    noise2 = gaussian_filter(np.random.randn(MAP_H // 4, MAP_W // 4), sigma=16)
    terrain_small = ridge[::4, ::4] * (0.65 + 0.85 * noise1) + 0.4 * noise2
    dy, dx = np.gradient(terrain_small)
    shade_small = np.clip(0.5 + (-dx * 2.1 - dy * 1.4), 0.12, 0.96)
    shade = np.array(Image.fromarray((shade_small * 255).astype(np.uint8)).resize((MAP_W, MAP_H), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0

    land_mask_img = Image.new("L", (MAP_W, MAP_H), 0)
    ldraw = ImageDraw.Draw(land_mask_img)
    coast_pts = [latlon_to_xy(lat, lon) for lat, lon in subdivide_organic_polygon(COASTLINE_WEST_RAW, closed=False, iterations=5, roughness=0.08)]
    ldraw.polygon(coast_pts + [(MAP_W, MAP_H), (MAP_W, 0)], fill=255)
    for polys in districts_map.values():
        for ring in polys:
            if len(ring) >= 3:
                ldraw.polygon([latlon_to_xy(lat, lon) for lat, lon in ring], fill=255)

    land_mask = np.array(land_mask_img, dtype=np.float32) / 255.0
    coastal_glow = gaussian_filter(land_mask, sigma=24)
    rgb = np.zeros((MAP_H, MAP_W, 3), dtype=np.uint8)
    for c, (sc, lc) in enumerate([
        (5 + coastal_glow * 14 + shade * 3, 36 + shade * 52),
        (21 + coastal_glow * 28 + shade * 5, 41 + shade * 56),
        (35 + coastal_glow * 42 + shade * 7, 48 + shade * 62),
    ]):
        rgb[:, :, c] = np.clip(sc * (1 - land_mask) + lc * land_mask, 0, 255).astype(np.uint8)

    base_map = Image.fromarray(rgb, mode="RGB").convert("RGBA")
    draw = ImageDraw.Draw(base_map)
    for polys in districts_map.values():
        for ring in polys:
            pts = [latlon_to_xy(lat, lon) for lat, lon in ring]
            if len(pts) >= 3:
                draw.line(pts + [pts[0]], fill=(102, 114, 128, 130), width=2)
    return base_map

FALLBACK_SCRIPT = {
    "topic": "വൈക്കം സത്യഗ്രഹം (1924-1925)",
    "series_tag": "KERALA PSC  •  RENAISSANCE SERIES",
    "instagram_caption": "വൈക്കം സത്യഗ്രഹം (1924–1925) — സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടിയുള്ള കേരളത്തിലെ ആദ്യ സംഘടിത സമരം 📌 #keralapsc #psctips #malayalampsc",
    "scenes": [
        {
            "year_big": "1924", "title_ml": "വൈക്കം സത്യഗ്രഹം!", "subtitle_en": "MARCH 30, 1924  •  FREEDOM OF MOVEMENT",
            "color_theme": "gold", "highlight_districts": ["Kottayam", "Ernakulam", "Alappuzha"],
            "pins": [{"name": "Vaikom", "lat": 9.75, "lon": 76.39, "icon": "temple", "side": "left"}, {"name": "Kottayam", "lat": 9.59, "lon": 76.52, "icon": "none", "side": "right"}],
            "bottom_pill": "603 DAYS  •  FIRST ORGANIZED SATYAGRAHA",
            "voiceover": "കേരള ചരിത്രത്തിൽ സഞ്ചാര സ്വാതന്ത്ര്യത്തിന് വേണ്ടി നടന്ന ആദ്യത്തെ സംഘടിത സമരമായിരുന്നു 1924 മാർച്ച് 30-ന് ആരംഭിച്ച വൈക്കം സത്യഗ്രഹം."
        },
        {
            "year_big": "1923", "title_ml": "കാക്കിനഡ സമ്മേളനം", "subtitle_en": "T.K. MADHAVAN'S HISTORIC RESOLUTION",
            "color_theme": "cyan", "highlight_districts": ["Kottayam", "Alappuzha"],
            "pins": [{"name": "Vaikom", "lat": 9.75, "lon": 76.39, "icon": "torch", "side": "left"}, {"name": "Kayamkulam", "lat": 9.17, "lon": 76.50, "icon": "star", "side": "right"}],
            "route": {"from": "Kayamkulam", "to": "Vaikom"},
            "bottom_pill": "MAIN LEADERS: T.K. MADHAVAN & K.P. KESAVA MENON",
            "voiceover": "വൈക്കം മഹാദേവ ക്ഷേത്രത്തിന് ചുറ്റുമുള്ള പൊതുവഴികളിലൂടെ അവർണ്ണർക്ക് നടക്കാൻ വിലക്കുണ്ടായിരുന്നു. 1923-ലെ കാക്കിനഡ കോൺഗ്രസ് സമ്മേളനത്തിൽ ടി.കെ. മാധവൻ ഇതിനെതിരെ പ്രമേയം അവതരിപ്പിച്ചു."
        },
        {
            "year_big": "", "title_ml": "സവർണ്ണ ജാഥ!", "subtitle_en": "LED BY MANNATHU PADMANABHAN",
            "color_theme": "red", "highlight_districts": ["Kottayam", "Alappuzha", "Kollam", "Thiruvananthapuram"],
            "pins": [{"name": "Vaikom", "lat": 9.75, "lon": 76.39, "icon": "torch", "side": "left"}, {"name": "Thiruvananthapuram", "lat": 8.52, "lon": 76.93, "icon": "crown", "side": "left"}],
            "route": {"from": "Vaikom", "to": "Thiruvananthapuram"},
            "bottom_pill": "VAIKOM TO TRIVANDRUM  •  SAVARNA JATHA",
            "voiceover": "സമരത്തിന് പിന്തുണ പ്രഖ്യാപിച്ചുകൊണ്ട് മന്നത്ത് പത്മനാഭന്റെ നേതൃത്വത്തിൽ വൈക്കത്ത് നിന്ന് തിരുവനന്തപുരത്തേക്ക് ചരിത്രപ്രസിദ്ധമായ സവർണ്ണ ജാഥ നടത്തി."
        },
        {
            "year_big": "1925", "title_ml": "ഗാന്ധിജി വൈക്കത്ത്!", "subtitle_en": "PERIYAR E.V. RAMASAMY  •  'VAIKOM VEERAR'",
            "color_theme": "gold", "highlight_districts": ["Kottayam", "Ernakulam", "Idukki"],
            "pins": [{"name": "Vaikom", "lat": 9.75, "lon": 76.39, "icon": "star", "side": "left"}, {"name": "Aluva", "lat": 10.11, "lon": 76.35, "icon": "none", "side": "right"}],
            "route": {"from": "Aluva", "to": "Vaikom"},
            "bottom_pill": "MARCH 1925  •  GANDHIJI VISITS VAIKOM",
            "voiceover": "തമിഴ്നാട്ടിൽ നിന്ന് സമരത്തിനെത്തിയ ഇ.വി. രാമസ്വാമി നായ്ക്കർ വൈക്കം വീരർ എന്നറിയപ്പെട്ടു. 1925 മാർച്ചിൽ മഹാത്മാഗാന്ധി വൈക്കം സന്ദർശിച്ച് ചർച്ചകൾ നടത്തി."
        },
        {
            "year_big": "1925", "title_ml": "ചരിത്ര വിജയം!", "subtitle_en": "NOVEMBER 23, 1925  •  ROADS OPENED",
            "color_theme": "cyan", "highlight_districts": ["Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam", "Idukki"],
            "pins": [{"name": "Vaikom", "lat": 9.75, "lon": 76.39, "icon": "crown", "side": "left"}, {"name": "Thiruvananthapuram", "lat": 8.52, "lon": 76.93, "icon": "star", "side": "left"}],
            "bottom_pill": "RANI SETHU LAKSHMI BAYI  •  603 DAYS",
            "voiceover": "ഒടുവിൽ 603 ദിവസത്തെ സമരത്തിനൊടുവിൽ 1925 നവംബർ 23-ന് തിരുവിതാംകൂർ റീജന്റ് റാണി സേതു ലക്ഷ്മി ഭായി ക്ഷേത്രത്തിന് ചുറ്റുമുള്ള വഴികൾ തുറന്നുകൊടുത്തു. തുടർന്നും പി എസ് സി അറിവുകൾക്കായി ഫോളോ ചെയ്യൂ!"
        }
    ]
}

def get_script() -> Dict[str, Any]:
    used = json.loads(HIST.read_text("utf-8")) if HIST.exists() else []
    if not KEY:
        return FALLBACK_SCRIPT
    client = genai.Client(api_key=KEY)
    known_places = ", ".join(list(PLACES.keys()))
    prompt = (
        "നിങ്ങൾ '@bhoomikadha' ശൈലിയിലുള്ള കേരള PSC വിഷ്വൽ ഡോക്യുമെന്ററി റീൽസ് നിർമ്മിക്കുന്ന അദ്ധ്യാപകനാണ്. "
        "PSC പരീക്ഷകളിൽ ആവർത്തിച്ചു ചോദിക്കുന്ന ഒരു ചരിത്ര/ഭൂമിശാസ്ത്ര/നവോത്ഥാന ചോദ്യം എടുത്ത് അതിന്റെ ഉത്തരവും കാരണങ്ങളും മാപ്പിലൂടെ വിശദീകരിക്കുന്ന 5 സീനുകളുള്ള (60 സെക്കൻഡ്) സ്ക്രിപ്റ്റ് തയ്യാറാക്കുക. "
        f"മുൻപ് ഉപയോഗിച്ചവ ഒഴിവാക്കുക: {', '.join(used[-30:]) or 'None'}. "
        f"ലഭ്യമായ പ്രധാന സ്ഥലങ്ങൾ: {known_places}. "
        "ലഭ്യമായ ജില്ലകൾ: Kasaragod, Kannur, Wayanad, Kozhikode, Malappuram, Palakkad, Thrissur, Ernakulam, Idukki, Kottayam, Alappuzha, Pathanamthitta, Kollam, Thiruvananthapuram. "
        'ലഭ്യമായ ഐക്കണുകൾ: "crown", "temple", "fort", "ship", "torch", "waves", "star", "none". color_theme: "gold", "cyan", or "red". '
        'JSON format only: {"topic":"വിഷയം","series_tag":"KERALA PSC • VISUAL HISTORY","instagram_caption":"ക്യാപ്ഷൻ #keralapsc","scenes":[{"year_big":"1924","title_ml":"മലയാളം തലക്കെട്ട്","subtitle_en":"ENGLISH SUBTITLE","color_theme":"gold","highlight_districts":["Kottayam"],"pins":[{"name":"Vaikom","lat":9.75,"lon":76.39,"icon":"temple","side":"left"}],"route":{"from":"Vaikom","to":"Kottayam"},"bottom_pill":"KEY FACT IN ENGLISH","voiceover":"10-12 സെക്കൻഡ് മലയാളം വിവരണം."}]}'
    )
    models = ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.0-flash"]
    try:
        for m in client.models.list():
            n = getattr(m, "name", "").replace("models/", "")
            if "gemini" in n and ("flash" in n or "pro" in n) and not any(x in n for x in ["tts", "image", "embedding", "vision", "audio", "live", "2.5-flash"]):
                if n not in models:
                    models.append(n)
    except Exception as e:
        print("Model list note:", e)
    resp = None
    for m in models:
        for attempt in range(2):
            try:
                print(f"Trying model {m} (attempt {attempt+1})...")
                resp = client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7))
                if resp and resp.text:
                    break
            except Exception as e:
                print("Model attempt error:", m, e)
                time.sleep(4)
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
    return FALLBACK_SCRIPT

def get_font_for_text(text: str, sz: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    has_ml = any("\u0d00" <= ch <= "\u0d7f" for ch in str(text))
    candidates = [
        f"/usr/share/fonts/truetype/smc/Manjari-{'Bold' if bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/noto/NotoSansMalayalam-{'Bold' if bold else 'Regular'}.ttf",
    ] if has_ml else [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=sz)
    return ImageFont.load_default()

def draw_vector_icon(draw: ImageDraw.ImageDraw, icon: str, cx: int, cy: int, scale: float = 1.0) -> None:
    if scale <= 0.05 or not icon or icon == "none":
        return
    s = scale
    if icon == "crown":
        pts = [(cx-int(34*s),cy+int(16*s)),(cx-int(40*s),cy-int(20*s)),(cx-int(16*s),cy-int(4*s)),(cx,cy-int(30*s)),(cx+int(16*s),cy-int(4*s)),(cx+int(40*s),cy-int(20*s)),(cx+int(34*s),cy+int(16*s))]
        draw.polygon(pts, fill=(255, 204, 0, 255))
        draw.rectangle([(cx - int(34*s), cy + int(20*s)), (cx + int(34*s), cy + int(28*s))], fill=(230, 175, 0, 255))
    elif icon == "fort":
        w, h = int(32*s), int(26*s)
        draw.rectangle([(cx - w, cy - h//2), (cx + w, cy + h)], fill=(255, 204, 0, 255))
        for bx in range(-w, w, max(8, int(16*s))):
            draw.rectangle([(cx + bx, cy - h), (cx + bx + int(10*s), cy - h//2)], fill=(255, 204, 0, 255))
        draw.rectangle([(cx - int(8*s), cy + int(2*s)), (cx + int(8*s), cy + h)], fill=(20, 26, 36, 255))
    elif icon == "temple":
        draw.polygon([(cx, cy - int(34*s)), (cx - int(34*s), cy - int(4*s)), (cx + int(34*s), cy - int(4*s))], fill=(255, 204, 0, 255))
        draw.rectangle([(cx - int(24*s), cy - int(4*s)), (cx + int(24*s), cy + int(22*s))], fill=(240, 185, 0, 255))
        draw.rectangle([(cx - int(6*s), cy + int(4*s)), (cx + int(6*s), cy + int(22*s))], fill=(20, 26, 36, 255))
    elif icon == "ship":
        draw.polygon([(cx - int(34*s), cy + int(4*s)), (cx + int(34*s), cy + int(4*s)), (cx + int(22*s), cy + int(22*s)), (cx - int(22*s), cy + int(22*s))], fill=(245, 190, 0, 255))
        draw.polygon([(cx, cy - int(32*s)), (cx, cy), (cx + int(26*s), cy - int(4*s))], fill=(255, 255, 255, 245))
    elif icon == "waves":
        for row in range(3):
            wy = cy - int(10*s) + row * int(13*s)
            pts = [(cx + dx, wy + int(5 * s * math.sin(dx * 0.2))) for dx in range(-36, 38, 6)]
            draw.line(pts, fill=(56, 189, 248, 255), width=max(2, int(4*s)))
    else:
        r1, r2 = int(26*s), int(12*s)
        pts = [(cx + int((r1 if i%2==0 else r2) * math.cos(-math.pi/2 + i*math.pi/5)), cy + int((r1 if i%2==0 else r2) * math.sin(-math.pi/2 + i*math.pi/5))) for i in range(10)]
        draw.polygon(pts, fill=(255, 204, 0, 255))

def get_place_latlon(pin: Dict[str, Any]) -> Tuple[float, float]:
    name = pin.get("name", "")
    if name in PLACES:
        return PLACES[name]
    for k, v in PLACES.items():
        if k.lower() in name.lower() or name.lower() in k.lower():
            return v
    return (float(pin.get("lat", 10.15)), float(pin.get("lon", 76.35)))

def compute_scene_camera(scene: Dict[str, Any], districts_map: Dict[str, List[List[Tuple[float, float]]]]) -> Tuple[float, float, float]:
    lats, lons = [], []
    for p in scene.get("pins", []):
        lat, lon = get_place_latlon(p)
        lats.append(lat)
        lons.append(lon)
    for dname in scene.get("highlight_districts", []):
        for k, polys in districts_map.items():
            if k.lower() == dname.lower():
                for ring in polys:
                    for lat, lon in ring[::4]:
                        lats.append(lat)
                        lons.append(lon)
    if not lats:
        return (10.2, 76.3, 1.35)
    min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
    span_lat = max(0.55, (max_lat - min_lat) * 2.35)
    zoom = max(1.15, min(2.35, (LAT_MAX - LAT_MIN) / span_lat * 0.55))
    return ((min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0, zoom)

def generate_documentary_bgm(duration_sec: float, out_wav: Path) -> None:
    sr = 44100
    n_samples = int(duration_sec * sr)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    drone = 0.35 * np.sin(2 * np.pi * 73.42 * t) + 0.22 * np.sin(2 * np.pi * 110.0 * t) + 0.12 * np.sin(2 * np.pi * 146.83 * t)
    pulse_env = 0.5 + 0.5 * np.sin(2 * np.pi * (100.0 / 60.0) * t - np.pi / 2) ** 4
    shimmer = 0.08 * np.sin(2 * np.pi * 220.0 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t))
    chime_env = np.exp(-np.maximum(0, t - 0.35) * 6.5) * (t >= 0.35)
    chime = 0.28 * np.sin(2 * np.pi * 587.33 * t) * chime_env + 0.18 * np.sin(2 * np.pi * 880.0 * t) * chime_env
    audio = (drone * (0.6 + 0.4 * pulse_env) + shimmer + chime) * 0.11
    pcm = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

THEME_COLORS = {"gold": (255, 204, 0), "cyan": (56, 189, 248), "red": (239, 68, 68)}

def render_scene_video(master_map, districts_map, scene, scene_idx, cam_prev, cam_target, duration, voice_mp3, out_mp4, series_tag):
    n_frames = int(math.ceil(duration * FPS))
    fdir = TMP / f"f_{scene_idx}"
    fdir.mkdir(parents=True, exist_ok=True)
    theme_rgb = THEME_COLORS.get(scene.get("color_theme", "gold"), (255, 204, 0))
    pins = scene.get("pins", [])
    route = scene.get("route")

    for f in range(n_frames):
        t = f / FPS
        cam_p = min(1.0, t / 1.1)
        cam_ease = 3 * cam_p ** 2 - 2 * cam_p ** 3
        drift = 1.0 + 0.08 * (t / max(1.0, duration))
        clat = cam_prev[0] + (cam_target[0] - cam_prev[0]) * cam_ease
        clon = cam_prev[1] + (cam_target[1] - cam_prev[1]) * cam_ease
        czoom = (cam_prev[2] + (cam_target[2] - cam_prev[2]) * cam_ease) * drift

        cx, cy = latlon_to_xy(clat, clon)
        crop_w, crop_h = W / czoom, H / czoom
        x1 = max(0.0, min(MAP_W - crop_w, cx - crop_w * 0.52))
        y1 = max(0.0, min(MAP_H - crop_h, cy - crop_h * 0.50))

        def to_screen(lat: float, lon: float) -> Tuple[int, int]:
            mx, my = latlon_to_xy(lat, lon)
            return (int((mx - x1) * czoom), int((my - y1) * czoom))

        cropped = master_map.crop((int(x1), int(y1), int(x1 + crop_w), int(y1 + crop_h))).resize((W, H), Image.Resampling.BICUBIC)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        poly_alpha = min(1.0, max(0.0, (t - 0.15) / 0.55))
        if poly_alpha > 0:
            for dname in scene.get("highlight_districts", []):
                for k, polys in districts_map.items():
                    if k.lower() == dname.lower():
                        for ring in polys:
                            pts = [to_screen(lat, lon) for lat, lon in ring]
                            if len(pts) >= 3:
                                draw.polygon(pts, fill=(*theme_rgb, int(68 * poly_alpha)))
                                draw.line(pts + [pts[0]], fill=(*theme_rgb, int(235 * poly_alpha)), width=4)

        if route and isinstance(route, dict):
            p_from, p_to = route.get("from", ""), route.get("to", "")
            if p_from in PLACES and p_to in PLACES and t >= 0.75:
                route_prog = min(1.0, (t - 0.75) / 1.25)
                x_a, y_a = to_screen(*PLACES[p_from])
                x_b, y_b = to_screen(*PLACES[p_to])
                ctrl_x, ctrl_y = (x_a + x_b) / 2 - 55, (y_a + y_b) / 2
                steps = 44
                max_step = int(steps * route_prog)
                curve_pts = [((1 - i/steps)**2 * x_a + 2*(1 - i/steps)*(i/steps)*ctrl_x + (i/steps)**2 * x_b, (1 - i/steps)**2 * y_a + 2*(1 - i/steps)*(i/steps)*ctrl_y + (i/steps)**2 * y_b) for i in range(max_step + 1)]
                for i in range(0, len(curve_pts) - 1, 2):
                    draw.line([curve_pts[i], curve_pts[i + 1]], fill=(255, 204, 0, 245), width=6)

        f_pin = get_font_for_text("VAIKOM", 22, bold=True)
        for p_idx, p in enumerate(pins):
            appear_t = 0.45 + p_idx * 0.45
            if t < appear_t:
                continue
            pin_p = min(1.0, (t - appear_t) / 0.38)
            pin_scale = 1.0 - (1.0 - pin_p) ** 3
            px, py = to_screen(*get_place_latlon(p))
            pin_col = (255, 204, 0) if p_idx == 0 else (56, 189, 248)
            pulse_phase = ((t - appear_t) * 1.4) % 1.0
            pulse_r = int(14 + 28 * pulse_phase)
            draw.ellipse([(px - pulse_r, py - pulse_r), (px + pulse_r, py + pulse_r)], outline=(*pin_col, int(160 * (1.0 - pulse_phase))), width=3)
            r_dot = int(14 * pin_scale)
            draw.ellipse([(px - r_dot, py - r_dot), (px + r_dot, py + r_dot)], fill=(*pin_col, 255), outline=(15, 20, 28, 255), width=4)
            draw.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=(15, 20, 28, 255))
            draw_vector_icon(draw, p.get("icon", "none"), px, py - 52, scale=pin_scale)

            label_txt = str(p.get("name", "PLACE")).upper()
            bb = draw.textbbox((0, 0), label_txt, font=f_pin)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            pad_x, pad_y = 20, 11
            bx1 = max(24, px - tw - pad_x * 2 - 22) if p.get("side", "left") == "left" else min(W - tw - pad_x * 2 - 24, px + 22)
            by1 = py - (th + pad_y * 2) // 2
            draw.rounded_rectangle([(bx1, by1), (bx1 + tw + pad_x * 2, by1 + th + pad_y * 2)], radius=14, fill=(18, 24, 34, int(238 * pin_scale)), outline=(130, 142, 158, int(210 * pin_scale)), width=2)
            draw.text((bx1 + pad_x, by1 + pad_y - 2), label_txt, font=f_pin, fill=(248, 250, 252, int(255 * pin_scale)))

        for y in range(440):
            draw.line([(0, y), (W, y)], fill=(6, 14, 24, int(180 * (1 - y / 440) ** 1.5)))
        for y in range(H - 390, H):
            draw.line([(0, y), (W, y)], fill=(6, 14, 24, int(190 * ((y - (H - 390)) / 390) ** 1.5)))

        draw.ellipse([(48, 82), (122, 156)], fill=(14, 28, 46, 240), outline=(56, 189, 248, 220), width=3)
        f_ep = get_font_for_text("PSC", 21, bold=True)
        draw.text((63, 107), "PSC", font=f_ep, fill=(255, 204, 0, 255))
        bb_ep = draw.textbbox((0, 0), series_tag, font=f_ep)
        draw.rounded_rectangle([(134, 92), (182 + (bb_ep[2] - bb_ep[0]), 146)], radius=24, fill=(22, 32, 46, 228), outline=(85, 100, 120, 190), width=2)
        draw.text((158, 107), series_tag, font=f_ep, fill=(225, 232, 240, 255))

        head_p = min(1.0, max(0.0, (t - 0.1) / 0.45))
        head_off = int((1.0 - (1.0 - (1.0 - head_p) ** 3)) * 35)
        head_a = int(255 * head_p)
        cy = 205 + head_off

        yr_txt = str(scene.get("year_big", "")).strip()
        if yr_txt:
            f_yr = get_font_for_text(yr_txt, 112, bold=True)
            bb = draw.textbbox((0, 0), yr_txt, font=f_yr)
            tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2 + 4, cy + 4), yr_txt, font=f_yr, fill=(0, 0, 0, int(175 * head_p)))
            draw.text(((W - tw) // 2, cy), yr_txt, font=f_yr, fill=(255, 204, 0, head_a))
            cy += 132

        tml = str(scene.get("title_ml", "")).strip()
        if tml:
            f_tml = get_font_for_text(tml, 58, bold=True)
            bb = draw.textbbox((0, 0), tml, font=f_tml)
            tw = bb[2] - bb[0]
            draw.text(((W - tw) // 2 + 3, cy + 3), tml, font=f_tml, fill=(0, 0, 0, int(190 * head_p)))
            draw.text(((W - tw) // 2, cy), tml, font=f_tml, fill=(255, 255, 255, head_a))
            cy += 84

        sub_txt = str(scene.get("subtitle_en", "")).strip().upper()
        if sub_txt:
            f_sub_en = get_font_for_text(sub_txt, 25, bold=True)
            bb = draw.textbbox((0, 0), sub_txt, font=f_sub_en)
            tw = bb[2] - bb[0]
            draw.rounded_rectangle([((W - tw) // 2 - 24, cy - 6), ((W + tw) // 2 + 24, cy + 40)], radius=14, fill=(22, 30, 42, int(230 * head_p)), outline=(95, 110, 130, int(185 * head_p)), width=2)
            draw.text(((W - tw) // 2, cy + 5), sub_txt, font=f_sub_en, fill=(*theme_rgb, head_a))

        bp_txt = str(scene.get("bottom_pill", "")).strip().upper()
        if bp_txt and t >= 0.9:
            bp_p = min(1.0, (t - 0.9) / 0.35)
            f_bp = get_font_for_text(bp_txt, 22, bold=True)
            bb = draw.textbbox((0, 0), bp_txt, font=f_bp)
            tw = bb[2] - bb[0]
            draw.rounded_rectangle([((W - tw) // 2 - 26, 1515), ((W + tw) // 2 + 26, 1570)], radius=14, fill=(14, 116, 180, int(242 * bp_p)))
            draw.text(((W - tw) // 2, 1530), bp_txt, font=f_bp, fill=(255, 255, 255, int(255 * bp_p)))

        vo_txt = str(scene.get("voiceover", "")).strip()
        if vo_txt:
            cap_lines = textwrap.wrap(vo_txt, width=32)
            f_cap = get_font_for_text(vo_txt, 33, bold=True)
            box_h = 30 + len(cap_lines) * 44
            draw.rounded_rectangle([(56, 1595), (W - 56, 1595 + box_h)], radius=20, fill=(10, 16, 26, 224), outline=(255, 204, 0, 145), width=2)
            ly = 1610
            for ln in cap_lines:
                bb = draw.textbbox((0, 0), ln, font=f_cap)
                draw.text(((W - (bb[2] - bb[0])) // 2, ly), ln, font=f_cap, fill=(255, 242, 190, 255))
                ly += 44

        Image.alpha_composite(cropped, overlay).convert("RGB").save(fdir / f"frame_{f:04d}.jpg", quality=92)

    bgm_wav = TMP / f"bgm_{scene_idx}.wav"
    generate_documentary_bgm(duration, bgm_wav)
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", str(fdir / "frame_%04d.jpg"), "-i", str(voice_mp3), "-i", str(bgm_wav),
        "-filter_complex", "[1:a]volume=1.35[vo];[2:a]volume=0.85[bg];[vo][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_mp4),
    ]
    subprocess.run(cmd, check=True)

async def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    districts_map = load_kerala_districts()
    master_map = build_master_dark_map(districts_map)
    data = get_script()
    dt = datetime.date.today().isoformat()
    (OUT / f"psc_script_{dt}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    scenes = data.get("scenes", [])
    series_tag = str(data.get("series_tag", "KERALA PSC  •  VISUAL HISTORY")).upper()
    clips: List[Path] = []
    cam_prev = (10.35, 76.25, 1.25)

    for idx, sc in enumerate(scenes):
        mp3, mp4 = TMP / f"s_{idx}.mp3", TMP / f"s_{idx}.mp4"
        await edge_tts.Communicate(text=sc["voiceover"], voice=VOICE, rate="-2%").save(str(mp3))
        res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)], capture_output=True, text=True, check=True)
        dur = max(3.5, float(res.stdout.strip())) + 0.35
        cam_target = compute_scene_camera(sc, districts_map)
        render_scene_video(master_map, districts_map, sc, idx, cam_prev, cam_target, dur, mp3, mp4, series_tag)
        cam_prev = cam_target
        clips.append(mp4)

    lst = TMP / "list.txt"
    lst.write_text("\n".join([f"file '{p.resolve()}'" for p in clips]), "utf-8")
    final_mp4 = OUT / f"malayalam_psc_reel_{dt}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final_mp4)], check=True)
    if TG_TOKEN and TG_CHAT:
        with open(final_mp4, "rb") as vf:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={"chat_id": TG_CHAT, "caption": f"📌 {data.get('topic','')}\n\n{data.get('instagram_caption','')}"[:1000]}, files={"video": vf}, timeout=120).raise_for_status()
    print("Bhoomikadha-style video ready:", final_mp4)

if __name__ == "__main__":
    asyncio.run(build())
