import os
import requests
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from config import AI_MODEL, OPENAI_API_KEY

LANGUAGE_NAMES = {
    "uz": "O'zbek (Uzbek)", "ru": "Rus (Русский)", "en": "Ingliz (English)",
    "kaa": "Qoraqalpoq (Qaraqalpaqsha)", "kg": "Qirg'iz (Кыргызcha)",
    "kk": "Qozoq (Қазақша)", "tg": "Tojik (Тоҷикӣ)",
}

def get_language_name(lang_code):
    return LANGUAGE_NAMES.get(lang_code, "O'zbek")

def _try_openai(system_prompt, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=90.0) # Vaqtni uzaytirdik
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response = client.chat.completions.create(model=AI_MODEL, messages=messages, timeout=90.0)
    return response.choices[0].message.content

def generate_plans(topic, language="uz"):
    lang_name = get_language_name(language)
    system_prompt = f"Siz tajribali professor sifatida {lang_name} tilida ilmiy mavzular uchun 4 ta mukammal reja tuzib berasiz."
    prompt = f"'{topic}' mavzusi uchun 4 ta asosiy reja tuzib bering. Faqat rejalarni matn ko'rinishida yozing."
    return _try_openai(system_prompt, prompt)

def get_ai_response(prompt, context="", language="uz"):
    lang_name = get_language_name(language)
    system_prompt = (
        f"Siz professional akademik taqdimot yaratuvchisiz. Barcha javoblar FAKAT {lang_name} tilida bo'lsin. "
        f"Aniq 8 ta slayd tayyorlang. "
        f"Har bir slaydni quyidagi qat'iy formatda yozing:\n"
        f"[Slayd 1]\nSarlavha: ...\nMatn: ..."
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

def create_pptx(title, content):
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    slides_data = content.split('[Slayd')
    
    for s_data in slides_data:
        if not s_data.strip(): continue
        lines = [ln.strip() for ln in s_data.split('\n') if ln.strip()]
        if len(lines) < 2: continue
        if lines[0].endswith(']'): lines = lines[1:] 
        if not lines: continue
            
        slide_title = "Sarlavha yo'q"
        body_text = ""
        
        for line in lines:
            if line.startswith("Sarlavha:"):
                slide_title = line.replace("Sarlavha:", "").strip()
            elif line.startswith("Matn:"):
                body_text = line.replace("Matn:", "").strip()
            elif not line.startswith("Rasm:") and not body_text:
                body_text += line + "\n"
                
        slide = prs.slides.add_slide(blank_layout)
        
        # Orqa fon rangi (Zamonaviy och kulrang)
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(241, 245, 249)
        
        # Sarlavha qutisi
        title_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.3), Inches(1.0))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = slide_title
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.color.rgb = RGBColor(15, 23, 42)
        
        # Asosiy kontent uchun zamonaviy oq quti (Card)
        card = slide.shapes.add_shape(1, Inches(1.0), Inches(2.0), Inches(11.3), Inches(4.8))
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(203, 213, 225)
        card.line.width = Pt(1.5)
        
        # Matn joylash
        text_box = slide.shapes.add_textbox(Inches(1.3), Inches(2.3), Inches(10.7), Inches(4.2))
        tf_body = text_box.text_frame
        tf_body.word_wrap = True
        p_body = tf_body.paragraphs[0]
        p_body.text = body_text if body_text else "Ma'lumot mavjud emas."
        p_body.font.size = Pt(20)
        p_body.font.color.rgb = RGBColor(51, 65, 85)
            
    file_path = "Zamonaviy_Slayd.pptx"
    prs.save(file_path)
    return file_path
