import os
import requests
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

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

# 1. REJALARNI TUZISH FUNKSIYASI
def generate_plans(topic, language="uz"):
    lang_name = get_language_name(language)
    system_prompt = f"Siz tajribali professor va akademik sifatida {lang_name} tilida ilmiy mavzular uchun 4 ta mukammal reja tuzib berasiz."
    prompt = f"'{topic}' mavzusi uchun 4 ta asosiy reja tuzib bering. Har bir reja ilmiy va mantiqiy ketma-ketlikda bo'lsin. Faqat rejalarni matn ko'rinishida yozing."
    return _try_openai(system_prompt, prompt)

# 2. SLAYD UCHUN MATN VA MAZMUN YARATISH
def get_ai_response(prompt, context="", language="uz"):
    lang_name = get_language_name(language)
    system_prompt = (
        f"Siz professional taqdimot va slayd yaratuvchisiz. Barcha javoblar FAKAT {lang_name} tilida bo'lsin. "
        f"Kamida 8 ta, ko'pi bilan 12 ta slayd tayyorlang. "
        f"Har bir slaydni quyidagi qat'iy formatda yozing:\n"
        f"[Slayd 1]\nSarlavha: ...\nMatn: ...\nRasm: (ingliz tilida bitta so'z, masalan: sport, education, technology)"
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
    if len(search_query) < 3: search_query = "presentation design"
        
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY}, 
            params={"query": search_query, "per_page": 1, "orientation": "landscape"}, 
            timeout=10
        )
        photos = resp.json().get("photos", [])
        if not photos: return None
        img_resp = requests.get(photos[0]["src"]["large"], timeout=10)
        with open(save_path, "wb") as f: f.write(img_resp.content)
        return save_path
    except: return None

# 3. ZAMONAVIY QUTILI VA DIZAYNLI POWERPOINT YARATISH
def create_pptx(title, content):
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # Bo'sh slayd
    
    slides_data = content.split('[Slayd')
    
    for s_data in slides_data:
        if not s_data.strip(): continue
        lines = [ln.strip() for ln in s_data.split('\n') if ln.strip()]
        if len(lines) < 2: continue
        if lines[0].endswith(']'): lines = lines[1:] 
        if not lines: continue
            
        slide_title = "Sarlavha yo'q"
        body_text = ""
        image_keyword = "education" 
        
        for line in lines:
            if line.startswith("Sarlavha:"):
                slide_title = line.replace("Sarlavha:", "").strip()
            elif line.startswith("Matn:"):
                body_text = line.replace("Matn:", "").strip()
            elif line.startswith("Rasm:"):
                image_keyword = line.replace("Rasm:", "").strip()
                
        slide = prs.slides.add_slide(blank_layout)
        
        # Orqa fon rangi (Oq/Havoriy zamonaviy)
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(248, 250, 252)
        
        # Yuqori sarlavha qutisi
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.0))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = slide_title
        p_title.font.size = Pt(32)
        p_title.font.bold = True
        p_title.font.color.rgb = RGBColor(15, 23, 42)
        
        # Matn uchun zamonaviy quti (Card Box)
        card = slide.shapes.add_shape(1, Inches(0.8), Inches(1.8), Inches(7.2), Inches(5.0)) # 1 = Manger (Rectangle)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(226, 232, 240)
        card.line.width = Pt(1.5)
        
        # Matnni quti ichiga joylash
        text_box = slide.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(6.6), Inches(4.4))
        tf_body = text_box.text_frame
        tf_body.word_wrap = True
        p_body = tf_body.paragraphs[0]
        p_body.text = body_text
        p_body.font.size = Pt(20)
        p_body.font.color.rgb = RGBColor(51, 65, 85)
        
        # Rasmni joylash
        image_path = _search_pexels_image(image_keyword)
        if image_path and os.path.exists(image_path):
            try:
                slide.shapes.add_picture(image_path, Inches(8.3), Inches(1.8), width=Inches(4.2), height=Inches(5.0))
            except: pass
            finally: os.remove(image_path)
            
    file_path = "Zamonaviy_Slayd.pptx"
    prs.save(file_path)
    return file_path
