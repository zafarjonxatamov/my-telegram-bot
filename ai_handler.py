import os
import requests
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from config import (
    AI_MODEL,
    OPENAI_API_KEY,
    CLAUDE_API_KEY,
    GEMINI_API_KEY,
)

# Pexels kaliti to'g'ridan-to'g'ri shu yerda (config.py'ga qo'shish shart emas)
PEXELS_API_KEY = "EwSRENDIIVaujdEYjtp5WNAr26n67yI5GIJF7oK8gUR1b1yln3z3uSw3"

# ==========================================================
#  QO'LLAB-QUVVATLANADIGAN TILLAR
# ==========================================================

LANGUAGE_NAMES = {
    "uz": "o'zbek",
    "ru": "rus (Русский)",
    "en": "ingliz (English)",
    "kaa": "qoraqalpoq (Qaraqalpaqsha)",
    "kg": "qirg'iz (Кыргызcha)",
    "kk": "qozoq (Қазақша)",
    "tg": "tojik (Тоҷикӣ)",
}


def get_language_name(lang_code):
    return LANGUAGE_NAMES.get(lang_code, "o'zbek")

# ==========================================================
#  UCH XIL AI PROVAYDER: OpenAI -> Claude -> Gemini (fallback)
#  Birinchisi ishlamasa (masalan kredit tugasa), avtomatik
#  keyingisiga o'tadi.
# ==========================================================

def _try_openai(system_prompt, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(model=AI_MODEL, messages=messages)
    return response.choices[0].message.content


def _try_claude(system_prompt, prompt):
    # To'g'ridan-to'g'ri REST API orqali (kutubxona bilan bog'liq muammolarni oldini olish uchun)
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": [{"role": "user", "content": prompt}]
    }
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers, json=payload, timeout=60
    )
    data = resp.json()
    if "content" in data:
        return data["content"][0]["text"]
    raise Exception(data.get("error", {}).get("message", str(data)))


def _try_gemini(system_prompt, prompt):
    # To'g'ridan-to'g'ri REST API orqali (Windows'dagi DLL muammosini oldini olish uchun)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192}
    }
    resp = requests.post(url, json=payload, timeout=60)
    data = resp.json()
    if "candidates" in data:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    raise Exception(data.get("error", {}).get("message", str(data)))


# ==========================================================
#  HAR BIR HUJJAT TURI UCHUN AKADEMIK YOZISH TARTIBI (ANDOZA)
# ==========================================================

STRUCTURE_GUIDES = {
    "Dars ishlanmasi": """
Quyidagi tuzilishda, to'liq dars ishlanmasi (konspekt) yozing:
1. Mavzu
2. Darsning maqsadlari:
   - Ta'limiy maqsad
   - Tarbiyaviy maqsad
   - Rivojlantiruvchi maqsad
3. Dars turi va metodi (masalan: aralash dars, muammoli ta'lim, klaster va h.k.)
4. Kerakli jihoz va vositalar
5. Darsning borishi:
   a) Tashkiliy qism (2-3 daqiqa)
   b) O'tilgan mavzuni so'rash / uy vazifasini tekshirish
   c) Yangi mavzu bayoni (asosiy qism, to'liq va tushunarli tarzda)
   d) Mustahkamlash (savol-javob yoki mashqlar)
   e) Uyga vazifa
   f) Baholash va yakunlash
Har bir bo'limni aniq sarlavha bilan ajratib yozing.
""",

    "Maqola": """
Ilmiy maqola uchun quyidagi akademik tuzilishda yozing:
1. Sarlavha (mavzuga mos, qisqa va aniq)
2. Annotatsiya (5-7 gap, ishning mohiyatini qisqacha ifodalovchi)
3. Kalit so'zlar (5-7 ta)
4. Kirish (dolzarbligi, muammoning qo'yilishi, maqsad)
5. Asosiy qism (tahlil, mavjud yondashuvlar, muallifning fikri va argumentlari)
6. Natijalar va muhokama
7. Xulosa
8. Foydalanilgan adabiyotlar ro'yxati (kamida 5 ta manba, namunaviy shaklda)
""",

    "Tezis": """
Qisqa ilmiy tezis uchun quyidagi tuzilishda yozing:
1. Sarlavha
2. Kirish (muammoning dolzarbligi)
3. Asosiy g'oyalar (aniq va lo'nda, punktlar bilan)
4. Xulosa
5. Foydalanilgan adabiyotlar (3-5 ta manba)
""",

    "Mustaqil ish": """
Mustaqil ish uchun quyidagi tuzilishda yozing:
1. Kirish (mavzuning ahamiyati, ishning maqsadi)
2. Asosiy qism (mavzuni bo'limlarga bo'lib, chuqur va tushunarli tarzda yoritish)
3. Xulosa (asosiy fikrlarning qisqacha yakuni)
4. Foydalanilgan adabiyotlar ro'yxati
""",

    "Kurs ishi": """
Kurs ishi uchun quyidagi to'liq akademik tuzilishda yozing (hajmi 30-35 betga mo'ljallangan, 
shuning uchun har bir qismni imkon qadar batafsil yoriting):
1. Mundarija
2. Kirish (mavzuning dolzarbligi, ishning maqsadi va vazifalari, tadqiqot ob'ekti/predmeti)
3. I BOB — Nazariy qism (mavzu bo'yicha ilmiy adabiyotlar tahlili, asosiy tushunchalar)
4. II BOB — Amaliy/tahliliy qism (masala yechimi, misollar, tahlil, statistik yoki amaliy ma'lumotlar)
5. Xulosa va takliflar
6. Foydalanilgan adabiyotlar ro'yxati (kamida 10-15 ta manba)
""",

    "Bitiruv malakaviy ishi": """
Bitiruv malakaviy ishi (BMI) uchun quyidagi rasmiy OAK talablariga mos, TO'LIQ va BATAFSIL 
akademik tuzilishda yozing (umumiy hajmi 70-80 betga mo'ljallangan):

MUNDARIJA (I, II, III bob asosida)
KIRISH (dolzarblik, maqsad, ob'ekt/predmet)

I BOB (nazariy-metodologik asoslar)
  1.1, 1.2, 1.3 (kichik mavzular)
  I bob bo'yicha xulosa

II BOB (amaliy tahlil)
  2.1, 2.2, 2.3 (kichik mavzular)
  II bob bo'yicha xulosa

III BOB (takomillashtirish yo'llari)
  3.1, 3.2, 3.3 (kichik mavzular)
  III bob bo'yicha xulosa

UMUMIY XULOSA
FOYDALANILGAN ADABIYOTLAR RO'YXATI (kamida 20-30 ta manba)
GLOSSARIY (asosiy atamalar)
""",

    "Magistrlik dissertatsiyasi": """
Magistrlik dissertatsiyasi uchun yuqori ilmiy darajadagi, TO'LIQ va JUDA BATAFSIL akademik 
tuzilishda yozing (125-130 ta manba asosida):

MUNDARIJA (I, II, III bob asosida)
KIRISH (dolzarblik, maqsad, ilmiy yangilik, metodologiya, ob'ekt/predmet)

I BOB (ilmiy-nazariy tahlil)
  1.1, 1.2, 1.3 (kichik mavzular)
  I bob bo'yicha xulosa

II BOB (metodologiya va empirik tahlil)
  2.1, 2.2, 2.3 (kichik mavzular)
  II bob bo'yicha xulosa

III BOB (natijalar va tavsiyalar)
  3.1, 3.2, 3.3 (kichik mavzular)
  III bob bo'yicha xulosa

UMUMIY XULOSA
FOYDALANILGAN ADABIYOTLAR RO'YXATI (125-130 ta manba)
GLOSSARIY
""",

    "PhD dissertatsiya": """
PhD (falsafa doktori) dissertatsiyasi uchun eng yuqori ilmiy standartlarga mos, TO'LIQ va 
ENG BATAFSIL akademik tuzilishda yozing (hajmi 130-140 bet):

MUNDARIJA (I, II, III, IV bob asosida)
KIRISH (dolzarblik, maqsad, ilmiy yangilik, metodologiya, ob'ekt/predmet)
Gipoteza va himoyaga chiqariladigan holatlar

I BOB, II BOB, III BOB (3.1 dan 3.6 gacha), IV BOB (4.1 dan 4.3 gacha)
Har bir bob yakunida "Bob bo'yicha xulosa" bo'lishi shart.

UMUMIY XULOSA
FOYDALANILGAN ADABIYOTLAR RO'YXATI (130-140 ta manba)
GLOSSARIY
""",

    "O'quv qo'llanma": """
O'quv qo'llanma uchun (4-8 bob, hajmi 170-240 bet):
1. Mundarija
2. Kirish
3. Har bir BOB uchun: Nazariya (1.1, 1.2, 1.3), Bob bo'yicha xulosa, Nazorat savollari va Testlar.
4. Yakuniy xulosa, Adabiyotlar va Glossariy.
""",

    "Darslik": """
To'liq darslik uchun (6-14 bob, hajmi 170-440 bet):
1. Muqaddima va Mundarija
2. Har bir BOB uchun: Nazariya (1.1, 1.2, 1.3), Bob bo'yicha xulosa, Nazorat savollari va Testlar.
3. Umumiy xulosa, Adabiyotlar va Glossariy.
""",
}

DEFAULT_STRUCTURE = """
Mavzuni aniq, tushunarli va professional tarzda, kirish, asosiy qism va xulosadan 
iborat tuzilishda yoriting.
"""


def get_structure_guide(context):
    """Bo'lim nomiga mos akademik tuzilma (andoza) qaytaradi."""
    return STRUCTURE_GUIDES.get(context, DEFAULT_STRUCTURE)


def _call_ai(system_prompt, prompt):
    """
    Avval OpenAI'ni sinaydi, ishlamasa Claude'ga, u ham ishlamasa
    Gemini'ga o'tadi. Uchalasi ham ishlamasa xatolik ko'taradi.
    """
    providers = [
        ("OpenAI", _try_openai),
        ("Claude", _try_claude),
        ("Gemini", _try_gemini),
    ]

    errors = []
    for name, func in providers:
        try:
            return func(system_prompt, prompt)
        except Exception as e:
            errors.append(f"{name}: {str(e)}")
            continue

    raise Exception("Barcha provayderlar ishlamadi:\n" + "\n".join(errors))


def get_ai_response(prompt, context="", language="uz"):
    """
    Qisqa hujjatlar uchun — bitta so'rov bilan to'liq javob oladi.
    """
    structure = get_structure_guide(context)
    lang_name = get_language_name(language)

    system_prompt = (
        f"Siz akademik AI yordamchisiz. Bo'lim: {context}. "
        f"MUHIM: Butun javobni albatta {lang_name} tilida yozing.\n"
        "O'qituvchi va talabalar uchun professional, yaxshi tuzilgan javob bering.\n\n"
        f"YOZISH TARTIBI:\n{structure}"
    )

    try:
        return _call_ai(system_prompt, prompt)
    except Exception as e:
        return f"AI Xatolik yuz berdi. {str(e)}"


# ==========================================================
#  KATTA HAJMLI HUJJATLARNI BO'LIM-BO'LIM (BOB-BOB) YARATISH
# ==========================================================

def get_academic_plan(topic, work_type, language="uz"):
    """Ish turiga qarab batafsil mundarija (plan) yaratadi."""
    structure = get_structure_guide(work_type)
    lang_name = get_language_name(language)

    system_prompt = (
        f"Siz akademik reja tuzuvchisiz. Mavzu: {topic}. Ish turi: {work_type}.\n"
        f"Faqat va faqat {lang_name} tilida javob bering.\n"
        "Sizning vazifangiz — ushbu ish uchun juda batafsil mundarija (plan) tuzish.\n"
        "Har bir bob va uning ichidagi kichik bo'limlarni (1.1, 1.2 va h.k.) aniq ko'rsating.\n"
        "Faqat mundarija punktlarini qaytaring, ortiqcha matnsiz."
    )
    
    try:
        plan_text = _call_ai(system_prompt, f"'{topic}' mavzusi uchun {work_type} rejasini tuzing.")
        return [line.strip() for line in plan_text.split('\n') if line.strip() and (line[0].isdigit() or "BOB" in line.upper() or "KIRISH" in line.upper() or "XULOSA" in line.upper())]
    except Exception:
        return []


def generate_large_document(topic, work_type, language="uz", progress_callback=None):
    """Katta hujjatni bo'lim-bo'lim yaratib birlashtiradi."""
    plan = get_academic_plan(topic, work_type, language)
    if not plan:
        return "Reja tuzishda xatolik yuz berdi."

    lang_name = get_language_name(language)
    base_system_prompt = (
        f"Siz professional akademik yozuvchisiz. Ish turi: {work_type}.\n"
        f"MUHIM: Faqat {lang_name} tilida yozing.\n"
        "Sizga berilgan har bir bo'limni maksimal darajada batafsil, ilmiy va tushunarli yoritib bering."
    )

    total = len(plan)
    parts = []

    for idx, section_title in enumerate(plan, start=1):
        section_prompt = (
            f"Mavzu: '{topic}'\nBo'lim: '{section_title}'\n\n"
            "Ushbu bo'lim uchun kamida 500-1000 so'zdan iborat ilmiy matn yozing."
        )
        try:
            text = _call_ai(base_system_prompt, section_prompt)
            parts.append(f"\n\n{section_title.upper()}\n\n{text}")
        except Exception:
            parts.append(f"\n\n{section_title.upper()}\n\n[Xatolik yuz berdi]")

        if progress_callback:
            progress_callback(idx, total, section_title)

    return "".join(parts)


def create_word(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    file_path = "Akademik_Ish.docx"
    doc.save(file_path)
    return file_path


def _search_pexels_image(query, save_path="temp_slide_image.jpg"):
    if not PEXELS_API_KEY: return None
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": 1}
        resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
        photos = resp.json().get("photos", [])
        if not photos: return None
        img_resp = requests.get(photos[0]["src"]["large"], timeout=10)
        with open(save_path, "wb") as f: f.write(img_resp.content)
        return save_path
    except: return None


def create_pptx(title, content):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]
    paragraphs = [p for p in content.split('\n\n') if len(p.strip()) > 20]
    
    for p in paragraphs[:12]:
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = title
        tf = slide.placeholders[1]
        tf.text = p[:500] + "..." if len(p) > 500 else p
        
        image_path = _search_pexels_image(title)
        if image_path:
            try:
                slide.shapes.add_picture(image_path, Inches(6), Inches(1.5), width=Inches(3.5))
            except: pass
            finally: 
                if os.path.exists(image_path): os.remove(image_path)

    file_path = "Taqdimot.pptx"
    prs.save(file_path)
    return file_path
