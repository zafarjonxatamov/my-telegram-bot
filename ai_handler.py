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
    """Markdown belgilarini tozalash"""
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'---', '', text)
    return text.strip()

def get_ai_slides(prompt: str, count: int = 8) -> str:
    """OpenAI orqali sifatli va tuzilimli taqdimot matnini olish"""
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "Siz professional taqdimot matnlarini tuzuvchi mutaxassissiz. Hech qanday markdown belgilari (**, ---) ishlatmang. Qisti-baqti so'zlarsiz, aniq ilmiy matn yozing."},
            {"role": "user", "content": f"Mavzu bo'yicha {count} ta slayddan iborat taqdimot matnini tuzib ber.\nHar bir slayd sarlavhasi 'Sarlavha:' bilan, asosiy mazmuni esa 'Matn:' bilan boshlansin.\n\n{prompt}"}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def create_pptx(title: str, slides_text: str, color_theme: str = "klassik") -> str:
    """PowerPoint faylini professional formatda yaratish"""
    prs = Presentation()
    
    # 1. Sarlavha slaydi (Asosiy sahifa)
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    if slide.shapes.title:
        slide.shapes.title.text = clean_text(title)
        
    # Tagiga kichik yozuv qo'shish uchun subtitle
    if len(slide.placeholders) > 1:
        slide.placeholders[1].text = "Taqdimot avtomatik ravishda tayyorlandi"

    # AI matnini slaydlarga bo'lish
    slides_data = slides_text.split("Sarlavha:")
    
    for s_data in slides_data:
        if not s_data.strip():
            continue
        
        parts = s_data.split("Matn:")
        s_title = clean_text(parts[0])
        s_content = clean_text(parts[1]) if len(parts) > 1 else ""

        # Ortiqcha "Slayd X" so'zlarini tozalash
        s_title = re.sub(r'Slayd\s*\d+', '', s_title).strip()
        if not s_title:
            continue

        # Sarlavha va matn slaydi layouti (1-indeks)
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        
        # Sarlavhani joylash
        if slide.shapes.title:
            slide.shapes.title.text = s_title
        
        # Matnni toza va o'qishga qulay qilib joylash
        if len(slide.placeholders) > 1:
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.text = s_content
            
            # Matn shrift o'lchamini chiroyli ko'rinishga keltirish
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(18)
                paragraph.font.name = "Arial"

    filename = f"presentation_{os.urandom(4).hex()}.pptx"
    prs.save(filename)
    return filename
