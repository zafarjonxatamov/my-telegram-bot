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
    """OpenAI orqali aniq va to'liq taqdimot matnini olish"""
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "Siz professional taqdimot matnlarini tuzuvchi mutaxassissiz. Hech qanday markdown belgilari (**, ---) ishlatmang. Har bir slaydni aniq formatda yozing."},
            {"role": "user", "content": f"Mavzu bo'yicha {count} ta slayddan iborat taqdimot matnini tuzib ber.\nFormat quyidagicha bo'lsin:\nSarlavha: [Sarlavha matni]\nMatn: [Asosiy tushuntirish va ma'lumotlar]\n\n{prompt}"}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def create_pptx(title: str, slides_text: str, color_theme: str = "klassik") -> str:
    """PowerPoint faylini mukammal dizayn va ranglar bilan yaratish"""
    prs = Presentation()
    
    # 1. Asosiy Sarlavha Slaydi
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    if slide.shapes.title:
        slide.shapes.title.text = clean_text(title)
    if len(slide.placeholders) > 1:
        slide.placeholders[1].text = "Avtomatik tayyorlangan ilmiy taqdimot"

    # Matnni qismlarga to'g'ri ajratish uchun regex yoki split ishlatamiz
    # "Sarlavha:" so'zi bo'yicha bo'lamiz
    chunks = slides_text.split("Sarlavha:")
    
    for chunk in chunks:
        if not chunk.strip():
            continue
            
        # Har bir chunk ichidan Sarlavha va Matnni ajratib olamiz
        parts = chunk.split("Matn:")
        s_title = clean_text(parts[0])
        s_content = clean_text(parts[1]) if len(parts) > 1 else ""

        if not s_title or not s_content:
            continue

        # Sarlavha va matn slaydi
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        
        # Sarlavha matnini yozish
        if slide.shapes.title:
            slide.shapes.title.text = s_title
            
        # Asosiy matnni joylash va shriftni o'qishga qulay qilish
        if len(slide.placeholders) > 1:
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.text = s_content
            
            for paragraph in tf.paragraphs:
                paragraph.font.size = Pt(16)
                paragraph.font.name = "Arial"

    filename = f"presentation_{os.urandom(4).hex()}.pptx"
    prs.save(filename)
    return filename
