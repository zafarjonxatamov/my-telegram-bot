import os
import re
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches, Pt
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
    """Mavzuga mos keluvchi to'g'ri shablonni tanlab PowerPoint yaratish"""
    
    template_files = [f for f in os.listdir('.') if f.endswith('.pptx') and not f.startswith('presentation_')]
    
    selected_template = None
    
    # Agar mavzuga mos keluvchi kalit so'zlar bo'lsa, fayl nomlaridan qidiramiz
    title_lower = title.lower()
    for tf in template_files:
        tf_lower = tf.lower()
        # Mavzurdagi biron bir so'z fayl nomida qatnashgan bo'lsa, o'shani olamiz
        words = title_lower.split()
        if any(word in tf_lower for word in words if len(word) > 3):
            selected_template = tf
            break

    # Agar mos keladigani topilmasa va shablonlar ko'p bo'lsa, AI orqali aniqlaymiz yoki birinchisini olamiz
    if not selected_template and template_files:
        try:
            prompt_text = f"Quyidagi shablon fayllar ro'yxati bor: {template_files[:30]}.\nFoydalanuvchi kiritgan mavzu: '{title}'.\nShu mavzuga eng mos keladigan bitta fayl nomini yoz. Faqat fayl nomini yoz."
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.1
            )
            suggested = response.choices[0].message.content.strip()
            if suggested in template_files:
                selected_template = suggested
        except:
            pass

    prs = None
    if selected_template:
        try:
            prs = Presentation(selected_template)
        except Exception as e:
            print(f"Shablonni ochib bo'lmadi: {e}")
            
    # Agar shablon ochilmasa yoki mos kelmasa, xatolik chiqarmaslik uchun toza taqdimot ochamiz
    if prs is None:
        prs = Presentation()

    # 1. Sarlavha slaydi
    if len(prs.slides) > 0:
        slide = prs.slides[0]
        for shape in slide.shapes:
            if shape.has_text_frame:
                shape.text_frame.text = clean_text(title)
                for paragraph in shape.text_frame.paragraphs:
                    paragraph.font.size = Pt(28)
                break
    else:
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        if slide.shapes.title:
            slide.shapes.title.text = clean_text(title)

    # Matnni qismlarga bo'lish va slaydlarni qo'shish
    chunks = slides_text.split("Sarlavha:")
    
    for chunk in chunks:
        if not chunk.strip():
            continue
            
        parts = chunk.split("Matn:")
        s_title = clean_text(parts[0])
        s_content = clean_text(parts[1]) if len(parts) > 1 else ""

        if not s_title or not s_content:
            continue

        slide_layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        
        if slide.shapes.title:
            slide.shapes.title.text = s_title
            for paragraph in slide.shapes.title.text_frame.paragraphs:
                paragraph.font.size = Pt(24)
            
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
