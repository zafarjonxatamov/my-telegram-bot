import os
import requests
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from config import AI_MODEL, OPENAI_API_KEY

PEXELS_API_KEY = "EwSRENDIIVaujdEYjtp5WNAr26n67yI5GIJF7oK8gUR1b1yln3z3uSw3"

LANGUAGE_NAMES = {
    "uz": "O'zbek (Uzbek)", "ru": "Rus (Русский)", "en": "Ingliz (English)",
    "kaa": "Qoraqalpoq (Qaraqalpaqsha)", "kg": "Qirg'iz (Кыргызcha)",
    "kk": "Qozoq (Қазақша)", "tg": "Tojik (Тоҷикӣ)",
}

def get_language_name(lang_code):
    return LANGUAGE_NAMES.get(lang_code, "O'zbek")

def _try_openai(system_prompt, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response = client.chat.completions.create(model=AI_MODEL, messages=messages)
    return response.choices[0].message.content

STRUCTURE_GUIDES = {
    "Dars ishlanmasi - Amaliy mashg'ulot": """AMALIY MASHGʻULOT ISHLANMASI
Mavzuni to'liq ilmiy, akademik va pedagogik uslubda yoriting. Hech qanday uydirma faktlar, mantiqsiz so'zlar yoki boshqa tillarni aralashtirmang.
Quyidagi tuzilmaga qat'iy amal qiling:
1. MAVZU: [Mavzu nomi]
2. Mashgʻulotning maqsadi: (Talabalar nima o'rganishi haqida batafsil va mantiqiy asoslangan maqsad).
3. Mashg'ulot vazifalari: (3-4 ta aniq ta'limiy vazifalar).
4. Asosiy tushunchalar: (Mavzuga oid kamida 3 ta terminning ilmiy izohi).
5. Mashgʻulotning borishi (Bosqichlar): 
   - Kirish qismi (tashkiliy qism va mavzuga kirish).
   - Asosiy qism (Amaliy topshiriqlar, mashqlar va ularning ilmiy tahlili).
   - Yakuniy qism (Xulosa va baholash).
6. Mustaqil bajarish uchun topshiriqlar.
7. Nazorat savollari (Mavzu yuzasidan 5 ta mantiqiy savol).
8. Tavsiya etilgan asosiy adabiyotlar (Haqiqiy olimlar va kitoblar nomlari).
""",

    "Dars ishlanmasi - Seminar": """SEMINAR MASHG’ULOTI ISHLANMASI
Mavzuni to'liq ilmiy, akademik va pedagogik uslubda yoriting. Barcha ma'lumotlar 100% to'g'ri, mantiqiy bog'langan va xatosiz bo'lishi shart.
Quyidagi tuzilmaga qat'iy amal qiling:
1. MAVZU: [Mavzu nomi]
2. Mashg‘ulotning maqsadi va vazifalari: (Batafsil va ilmiy asoslangan).
3. O'quv rejalari: (Mavzuni ochib beruvchi 3-4 ta asosiy reja).
4. Asosiy qism (Rejalarning batafsil bayoni): Har bir reja bo'yicha ilmiy dalillar, faktlar va qoidalar bilan asoslangan kengaytirilgan matn.
5. Seminar uchun munozara savollari: (Guruh bo'lib ishlash uchun 5 ta o'ylantiradigan savol).
6. Tahliliy topshiriqlar (Keys-stadi): Talabalar yechishi kerak bo'lgan bitta kichik amaliy muammo.
7. Foydalanilgan adabiyotlar.
""",

    "Dars ishlanmasi - Laboratoriya mashg'uloti": """LABORATORIYA MASHG’ULOTI ISHLANMASI
Mavzuni ilmiy, aniq va texnik/metodik jihatdan to'g'ri yoriting. Tajriba yoki mashg'ulot jarayoni ketma-ketligini aniq tushuntiring.
1. MAVZU: [Mavzu nomi]
2. Laboratoriya mashg'ulotining maqsadi.
3. Kerakli jihozlar va uskunalar.
4. Xavfsizlik texnikasi qoidalari.
5. Mashg'ulotni bajarish tartibi (Qadam-baqadam aniq ko'rsatmalar, mantiqiy ketma-ketlikda).
6. Olingan natijalarni tahlil qilish usullari.
7. Xulosa va topshiriqlar.
""",

    "Mavzu bo'yicha slayd": """Siz professional prezentatsiya (Slayd) yaratuvchisiz.
Matnlar juda qisqa, aniq, ilmiy asoslangan va dizaynga mos bo'lishi kerak.
Mavzuga umuman aloqasi yo'q so'zlarni ISHLATMANG! Faqat haqiqiy sport va akademik faktlarni yozing.
Kamida 8 ta, ko'pi bilan 12 ta slayd tayyorlang.

Har bir slaydni quyidagi formatda qat'iy yozing:
[Slayd 1]
Sarlavha: (Mavzuga oid aniq sarlavha)
Matn: (2-3 ta qisqa, tushunarli bullet point yoki faktlar).
Rasm: (Faqatgina ingliz tilida BITTA SO'Z yozing. Masalan: handball, goalkeeper, sport, stadium, training, team)
"""
}

def get_structure_guide(context):
    return STRUCTURE_GUIDES.get(context, "Mavzuni to'liq ilmiy, akademik va grammatik jihatdan xatosiz yoriting. Uydirma faktlar ishlatmang.")

def get_ai_response(prompt, context="", language="uz"):
    structure = get_structure_guide(context)
    lang_name = get_language_name(language)
    
    system_prompt = (
        f"Siz O'zbekistonning eng tajribali professori va fan nomzodisiz. "
        f"Sizning vazifangiz universitet talabalari va o'qituvchilari uchun yuqori sifatli, ilmiy materiallar tayyorlash. "
        f"Barcha javoblarni FAKAT VA FAKAT {lang_name} tilida yozing. Boshqa tillarni aralashtirmang. "
        f"Faktlar 100% to'g'ri, mantiqli va ilmiy tilda bo'lishi shart. Hech qachon mavjud bo'lmagan so'zlarni, g'ayritabiiy qoidalarni yoki mantiqsiz ro'yxatlarni o'ylab topmang.\n\n"
        f"Bo'lim: {context}.\n"
        f"Qat'iy yozish qoidasi:\n{structure}"
    )
    return _try_openai(system_prompt, prompt)

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
    search_query = query.replace("Rasm:", "").strip().lower()
    if len(search_query) < 3 or "qoraqo'l" in search_query or "serang" in search_query:
        search_query = "handball goalkeeper"
        
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY}, 
            params={"query": search_query, "per_page": 1, "orientation": "landscape"}, 
            timeout=10
        )
        photos = resp.json().get("photos", [])
        if not photos: 
            resp = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": PEXELS_API_KEY}, params={"query": "sport training", "per_page": 1}, timeout=10)
            photos = resp.json().get("photos", [])
            if not photos: return None
            
        img_resp = requests.get(photos[0]["src"]["large"], timeout=10)
        with open(save_path, "wb") as f: f.write(img_resp.content)
        return save_path
    except: 
        return None

def create_pptx(title, content):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]
    
    slides_data = content.split('[Slayd')
    
    for s_data in slides_data:
        if not s_data.strip(): continue
        
        lines = [ln.strip() for ln in s_data.split('\n') if ln.strip()]
        if len(lines) < 2: continue
        
        if lines[0].endswith(']'): lines = lines[1:] 
        if not lines: continue
            
        slide_title = "Sarlavha yo'q"
        body_text_lines = []
        image_keyword = "sport training" 
        
        for line in lines:
            if line.startswith("Sarlavha:"):
                slide_title = line.replace("Sarlavha:", "").strip()
            elif line.startswith("Matn:"):
                body_text_lines.append(line.replace("Matn:", "").strip())
            elif line.startswith("Rasm:"):
                image_keyword = line.replace("Rasm:", "").strip()
            elif line and not line.startswith("[") and not line.startswith("Sarlavha") and not line.startswith("Rasm"):
                body_text_lines.append(line)
                
        body_text = '\n'.join(body_text_lines)
        
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = slide_title
        
        text_placeholder = slide.placeholders[1]
        text_placeholder.text = body_text
        text_placeholder.left, text_placeholder.top = Inches(0.5), Inches(1.5)
        text_placeholder.width, text_placeholder.height = Inches(5.5), Inches(5)
        
        image_path = _search_pexels_image(image_keyword)
        if image_path and os.path.exists(image_path):
            try: slide.shapes.add_picture(image_path, Inches(6.3), Inches(1.8), width=Inches(3.2))
            except: pass
            finally: os.remove(image_path)
            
    file_path = "Tayyor_Slayd.pptx"
    prs.save(file_path)
    return file_path
