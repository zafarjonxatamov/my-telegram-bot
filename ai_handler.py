import os
import re
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from config import OPENAI_API_KEY, AI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def clean_text(text: str) -> str:
    """Markdown belgilarini (**, --- kabilarni) tozalab tashlash"""
    text = re.sub(r'\*\*', '', text)  # ** larni olib tashlash
    text = re.sub(r'---', '', text)    # --- larni olib tashlash
    return text.strip()

def get_ai_slides(prompt: str, count: int = 8) -> str:
    """OpenAI orqali taqdimot matnini generatsiya qilish"""
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "Siz professional taqdimot matnlarini tuzuvchi mutaxassissiz. Hech qanday markdown belgilari (**, ---) ishlatmang, faqat toza matn yozing."},
            {"role": "user", "content": f"Mavzu bo'yicha {count} ta slayddan iborat taqdimot matnini tuzib ber.\nHar bir slayd sarlavhasi 'Sarlavha:' bilan, matni esa 'Matn:' bilan boshlansin.\n\n{prompt}"}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def create_pptx(title: str, slides_text: str, color_theme: str = "klassik") -> str:
    """PowerPoint faylini toza va chiroyli tarzda yaratish"""
    prs = Presentation()
    
    # 1. Asosiy sarlavha slaydi
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    if slide.shapes.title:
        slide.shapes.title.text = clean_text(title)

    # AI matnini slaydlarga bo'lib chiqish
    slides_data = slides_text.split("Sarlavha:")
    
    for s_data in slides_data:
        if not s_data.strip():
            continue
        
        parts = s_data.split("Matn:")
        s_title = clean_text(parts[0])
        s_content = clean_text(parts[1]) if len(parts) > 1 else ""

        # Agar sarlavha ichida ortiqcha "Slayd X" so'zlari bo'lsa tozalaymiz
        s_title = re.sub(r'Slayd\s*\d+', '', s_title).strip()
        if not s_title:
            continue

        slide_layout = prs.slide_layouts[1] # Sarlavha va matn layouti
        slide = prs.slides.add_slide(slide_layout)
        
        # Sarlavha
        if slide.shapes.title:
            slide.shapes.title.text = s_title
        
        # Matn (body) qismi
        if len(slide.placeholders) > 1:
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.text = s_content

    filename = f"presentation_{os.urandom(4).hex()}.pptx"
    prs.save(filename)
    return filename
