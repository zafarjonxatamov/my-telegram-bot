import os
import requests
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from config import AI_MODEL, OPENAI_API_KEY

PEXELS_API_KEY = "EwSRENDIIVaujdEYjtp5WNAr26n67yI5GIJF7oK8gUR1b1yln3z3uSw3"

def _try_openai(system_prompt, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=90.0)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response = client.chat.completions.create(model=AI_MODEL, messages=messages, timeout=90.0)
    return response.choices[0].message.content

def generate_plans(topic, language="uz"):
    system_prompt = "Siz tajribali professor sifatida ilmiy mavzular uchun 4 ta mukammal taqdimot rejasini tuzib berasiz."
    prompt = f"'{topic}' mavzusi uchun 4 ta asosiy reja tuzib bering. Faqat rejalarni matn ko'rinishida yozing."
    return _try_openai(system_prompt, prompt)

def get_ai_slides(prompt, slide_count=8, language="uz"):
    system_prompt = (
        f"Siz professional akademik taqdimot yaratuvchisiz. Barcha javoblar O'zbek tilida bo'lsin. "
        f"Aniq {slide_count} ta slayd tayyorlang. "
        f"Har bir slaydni quyidagi qat'iy formatda yozing:\n"
        f"[Slayd 1]\nSarlavha: ...\nMatn: ...\nRasm: (Faqat bitta aniq inglizcha kalit so'z: education, science, university, technology, business)"
    )
    return _try_openai(system_prompt, prompt)

def _search_pexels_image(query, save_path="temp_slide_image.jpg"):
    if not PEXELS_API_KEY: return None
    search_query = query.replace("Rasm:", "").strip().lower()
    if len(search_query) < 3: search_query = "education"
        
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

def create_pptx(title, content, color_scheme="klassik"):
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    # Ranglar sxemasi
    if color_scheme == "qora":
        bg_color, title_color, text_color, card_bg = RGBColor(15, 23, 42), RGBColor(255, 255, 255), RGBColor(203, 213, 225), RGBColor(30, 41, 59)
    elif color_scheme == "kok":
        bg_color, title_color, text_color, card_bg = RGBColor(239, 246, 255), RGBColor(30, 58, 138), RGBColor(30, 41, 59), RGBColor(255, 255, 255)
    else: # klassik oq/kulrang
        bg_color, title_color, text_color, card_bg = RGBColor(241, 245, 249), RGBColor(15, 23, 42), RGBColor(51, 65, 85), RGBColor(255, 255, 255)

    slides_data = content.split('[Slayd')
    for s_data in slides_data:
        if not s_data.strip(): continue
        lines = [ln.strip() for ln in s_data.split('\n') if ln.strip()]
        if len(lines) < 2: continue
        if lines[0].endswith(']'): lines = lines[1:] 
        if not lines: continue
            
        slide_title = "Sarlavha"
        body_text_lines = []
        image_keyword = "education"
        
        for line in lines:
            if line.startswith("Sarlavha:"):
                slide_title = line.replace("Sarlavha:", "").strip()
            elif line.startswith("Matn:"):
                body_text_lines.append(line.replace("Matn:", "").strip())
            elif line.startswith("Rasm:"):
                image_keyword = line.replace("Rasm:", "").strip()
            elif line and not line.startswith("[") and not line.startswith("Sarlavha"):
                body_text_lines.append(line)
                
        body_text = '\n'.join(body_text_lines)
        
        slide = prs.slides.add_slide(blank_layout)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg_color
        
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.0))
        p_title = title_box.text_frame.paragraphs[0]
        p_title.text = slide_title
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.color.rgb = title_color
        
        card = slide.shapes.add_shape(1, Inches(0.8), Inches(1.8), Inches(7.0), Inches(5.0))
        card.fill.solid()
        card.fill.fore_color.rgb = card_bg
        card.line.color.rgb = RGBColor(203, 213, 225)
        
        text_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(6.6), Inches(4.4))
        p_body = text_box.text_frame.paragraphs[0]
        p_body.text = body_text if body_text else "Ma'lumot mavjud emas."
        p_body.font.size = Pt(18)
        p_body.font.color.rgb = text_color
        
        image_path = _search_pexels_image(image_keyword)
        if image_path and os.path.exists(image_path):
            try:
                slide.shapes.add_picture(image_path, Inches(8.1), Inches(1.8), width=Inches(4.4), height=Inches(5.0))
            except: pass
            finally: os.remove(image_path)
            
    file_path = "Tayyor_Taqdimot.pptx"
    prs.save(file_path)
    return file_path
