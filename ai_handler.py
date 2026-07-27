import os
import requests
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from config import AI_MODEL, OPENAI_API_KEY, CLAUDE_API_KEY, GEMINI_API_KEY

PEXELS_API_KEY = "EwSRENDIIVaujdEYjtp5WNAr26n67yI5GIJF7oK8gUR1b1yln3z3uSw3"

# 7 TA TIL QAYTARILDI
LANGUAGE_NAMES = {
    "uz": "o'zbek", "ru": "rus (Русский)", "en": "ingliz (English)",
    "kaa": "qoraqalpoq (Qaraqalpaqsha)", "kg": "qirg'iz (Кыргызcha)",
    "kk": "qozoq (Қазақша)", "tg": "tojik (Тоҷикӣ)",
}

def get_language_name(lang_code):
    return LANGUAGE_NAMES.get(lang_code, "o'zbek")

def _try_openai(system_prompt, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response = client.chat.completions.create(model=AI_MODEL, messages=messages)
    return response.choices[0].message.content

def _try_gemini(system_prompt, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"system_instruction": {"parts": [{"text": system_prompt}]}, "contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 8192}}
    resp = requests.post(url, json=payload, timeout=60)
    data = resp.json()
    if "candidates" in data: return data["candidates"][0]["content"]["parts"][0]["text"]
    raise Exception(data.get("error", {}).get("message", str(data)))

STRUCTURE_GUIDES = {
    "Dars ishlanmasi - Amaliy mashg'ulot": """AMALIY MASHGʻULOT
MAVZU: [Mavzu nomi]
Mashgʻulotning maqsadi: (aynan 50 ta so’zdan iborat matn yarating)
Topshiriqlar: (aynan 3 ta topshiriq)
Mashgʻulotning borishi:
1-bosqich: (aynan 50 ta so’zdan iborat matn)
2-bosqich: (aynan 25 ta so’zdan iborat matn)
3-bosqich: (aynan 25 ta so’zdan iborat matn)

AMALIY TOPSHIRIQLAR VA METODIK OʻYINLAR
Topshiriq: (mavzuga oid sport va harakatli o’yinlar bo'yicha ma'lumot)
Yakuniy xulosa: (aynan 25 ta so’zdan iborat matn)
Nazorat savollari: (aynan 6 ta nazorat savoli)
TAVSIYA ETILGAN ADABIYOTLAR: (Mavzuga oid mahalliy olimlar tomonidan yaratilgan adabiyotlar bo’lsin, 4 yoki 5 ta)
Ilova: (Mavzuga oid rasmlar yoki texnologik xaritani matnli ta'rifi)
""",

    "Dars ishlanmasi - Seminar": """SEMINAR MASHG’ULOTI
MAVZU: [Mavzu nomi]
Reja:
1. [1-reja]
2. [2-reja]
3. [3-reja]
4. [4-reja]
Mashg‘ulotning maqsadi: (aynan 60 ta so’zdan iborat matn)
Mashg‘ulot turi: (mashg'ulot turini yozing)
Mashg‘ulot muammosi: (aynan 30 ta so’zdan iborat matn)
O‘quv maqsadlari: (maqsadlarni sanab yozing)
Seminar reja: (batafsil yozing)
Asosiy tushunchalar: (qisqacha ta'riflari bilan)
Guruh topshiriqlari: (aniq topshiriqlar bering)
Seminar metodlari: (sanab o'ting)
Uyga vazifa: Mini-insho yozish (1-1.5 sahifa)
Seminarlarda muhokama qilish uchun qo’shimcha savollar: (aynan 5 ta savol)
TAVSIYA ETILGAN ADABIYOTLAR: (Mavzuga oid mahalliy olimlar tomonidan yaratilgan adabiyotlar bo’lsin, 4 yoki 5 ta)
""",

    "Dars ishlanmasi - Laboratoriya mashg'uloti": """LABORATORIYA MASHG’ULOTI
MAVZU: [Mavzu nomi]
Reja:
1. [1-reja]
2. [2-reja]
3. [3-reja]
4. [4-reja]
Mashg‘ulotning maqsadi: (aynan 60 ta so’zdan iborat matn)
Mashg‘ulot turi: (mashg'ulot turini yozing)
Mashg‘ulot muammosi: (aynan 30 ta so’zdan iborat matn)
O‘quv maqsadlari: (maqsadlarni sanab yozing)
Laboratoriya reja: (batafsil yozing)
Asosiy tushunchalar: (qisqacha ta'riflari bilan)
Guruh topshiriqlari: (aniq topshiriqlar bering)
Laboratoriya metodlari: (sanab o'ting)
Uyga vazifa: Mini-insho yozish (1-1.5 sahifa)
Laboratoriyalarda muhokama qilish uchun qo’shimcha savollar: (aynan 5 ta savol)
TAVSIYA ETILGAN ADABIYOTLAR: (Mavzuga oid mahalliy olimlar tomonidan yaratilgan adabiyotlar bo’lsin, 4 yoki 5 ta)
""",

    "Mavzu bo'yicha slayd": """Slayd (Taqdimot) uchun ma'lumotlarni juda sodda, toza va chiroyli dizaynda matnlar tekisligi bilan yoriting.
Zarur joylarda ma'lumotlarni jadvallar (Markdown ustunlari) va chiroyli ro'yxatlar shaklida keltiring. 
Matnlar mavzuga aynan mos, aniq va ortiqcha gaplarsiz bo'lsin. Kamida 10 ta, ko'pi bilan 15 ta slayd chiqaring.
Har bir slaydni [Slayd 1], [Slayd 2] deb boshlang va Sarlavha hamda Asosiy matn (jadval/ro'yxat)ni kiriting.
"""
}

def get_structure_guide(context):
    return STRUCTURE_GUIDES.get(context, "Mavzuni ilmiy, professional tarzda aniq yoriting. Matn tushunarli bo'lsin.")

def _call_ai(system_prompt, prompt):
    for name, func in [("OpenAI", _try_openai), ("Gemini", _try_gemini)]:
        try: return func(system_prompt, prompt)
        except: continue
    raise Exception("AI provayder javob qaytarmadi, birozdan so'ng urinib ko'ring.")

def get_ai_response(prompt, context="", language="uz"):
    structure = get_structure_guide(context)
    lang_name = get_language_name(language)
    system_prompt = (
        f"Siz akademik AI yordamchisiz. Bo'lim: {context}. "
        f"Barcha ma'lumotni {lang_name} tilida yozing.\n"
        f"Qat'iy yozish qoidasi:\n{structure}"
    )
    return _call_ai(system_prompt, prompt)

def create_word(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    for line in content.split('\n'):
        if line.strip(): doc.add_paragraph(line)
    file_path = "Tayyor_Hujjat.docx"
    doc.save(file_path)
    return file_path

def _search_pexels_image(query, save_path="temp_slide_image.jpg"):
    if not PEXELS_API_KEY: return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY}, 
            params={"query": query, "per_page": 1, "orientation": "landscape"}, 
            timeout=10
        )
        photos = resp.json().get("photos", [])
        if not photos: return None
        img_resp = requests.get(photos[0]["src"]["large"], timeout=10)
        with open(save_path, "wb") as f: f.write(img_resp.content)
        return save_path
    except: return None

def create_pptx(title, content):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]
    paragraphs = [p for p in content.split('\n\n') if len(p.strip()) > 10]
    
    for p in paragraphs[:15]:
        lines = [ln for ln in p.strip().split('\n') if ln.strip()]
        if not lines: continue
        slide_title = lines[0].strip().replace("[Slayd", "").replace("]", "").strip()
        body_text = '\n'.join(lines[1:])
        
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = slide_title
        
        text_placeholder = slide.placeholders[1]
        text_placeholder.text = body_text
        text_placeholder.left, text_placeholder.top = Inches(0.5), Inches(1.5)
        text_placeholder.width, text_placeholder.height = Inches(5.5), Inches(5)
        
        image_query = slide_title if len(slide_title) > 5 else title
        image_path = _search_pexels_image(image_query)
        if image_path and os.path.exists(image_path):
            try: slide.shapes.add_picture(image_path, Inches(6.3), Inches(1.8), width=Inches(3.2))
            except: pass
            finally: os.remove(image_path)
            
    file_path = "Tayyor_Slayd.pptx"
    prs.save(file_path)
    return file_path
