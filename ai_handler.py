import os
import google.generativeai as genai
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def get_ai_slides(prompt: str, count: int = 8) -> str:
    """Gemini AI orqali taqdimot matnini generatsiya qilish"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    full_prompt = (
        f"Mavzu bo'yicha {count} ta slayddan iborat taqdimot matnini tuzib ber.\n"
        f"Har bir slayd sarlavhasi 'Sarlavha:' bilan, matni esa 'Matn:' bilan boshlansin.\n"
        f"Ma'lumotlar aniq va ilmiy bo'lsin.\n\n{prompt}"
    )
    response = model.generate_content(full_prompt)
    return response.text

def create_pptx(title: str, slides_text: str, color_theme: str = "klassik") -> str:
    """PowerPoint faylini yaratish"""
    prs = Presentation()
    
    # Ranglar sxemasi
    if color_theme == "qora":
        bg_color = RGBColor(20, 20, 20)
        title_color = RGBColor(255, 255, 255)
        text_color = RGBColor(220, 220, 220)
    elif color_theme == "kok":
        bg_color = RGBColor(240, 244, 248)
        title_color = RGBColor(16, 42, 77)
        text_color = RGBColor(50, 50, 50)
    else:
        bg_color = RGBColor(255, 255, 255)
        title_color = RGBColor(30, 30, 30)
        text_color = RGBColor(60, 60, 60)

    # Asosiy sahifa (Sarlavha slaydi)
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title_box = slide.shapes.title
    title_box.text = title

    # AI matnini slaydlarga bo'lib chiqish
    slides_data = slides_text.split("Sarlavha:")
    
    for s_data in slides_data:
        if not s_data.strip():
            continue
        
        parts = s_data.split("Matn:")
        s_title = parts[0].strip()
        s_content = parts[1].strip() if len(parts) > 1 else ""

        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        
        if slide.shapes.title:
            slide.shapes.title.text = s_title
        
        if len(slide.placeholders) > 1:
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.text = s_content

    filename = f"presentation_{os.urandom(4).hex()}.pptx"
    prs.save(filename)
    return filename
