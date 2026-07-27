import os
import glob
import pypdf
from docx import Document
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from config import AI_MODEL, OPENAI_API_KEY

def _try_openai(system_prompt, prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=90.0)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response = client.chat.completions.create(model=AI_MODEL, messages=messages, timeout=90.0)
    return response.choices[0].message.content

def search_books_content(topic, plans):
    """
    'books/' papkasidagi barcha PDF va Word kitoblarini o'qib,
    kiritilgan mavzu va 4 ta rejaga mos keladigan qismlarni qidirib topadi.
    """
    books_dir = "books"
    if not os.path.exists(books_dir):
        os.makedirs(books_dir)
        return "Kitoblar bazasi bo'sh."

    extracted_texts = []
    
    # PDF fayllarni o'qish
    for pdf_path in glob.glob(os.path.join(books_dir, "*.pdf")):
        try:
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages[:30]: # Har bir kitobdan dastlabki sahifalar
                txt = page.extract_text()
                if txt and any(word.lower() in txt.lower() for word in topic.split()):
                    extracted_texts.append(txt[:1000])
        except: continue

    # Word fayllarni o'qish
    for docx_path in glob.glob(os.path.join(books_dir, "*.docx")):
        try:
            doc = Document(docx_path)
            full_doc_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            if any(word.lower() in full_doc_text.lower() for word in topic.split()):
                extracted_texts.append(full_doc_text[:2000])
        except: continue

    if not extracted_texts:
        return f"Mavzu bo'yicha maxsus kitob topilmadi, umumiy ilmiy asosda tuzilsin. Mavzu: {topic}, Rejalar: {plans}"
    
    return "\n---\n".join(extracted_texts[:3]) # Topilgan eng mos 3 ta parcha

def get_ai_slides_from_books(topic, plans, slide_count=8):
    # Kitoblardan tegishli manba matnlarini qidirib olamiz
    source_material = search_books_content(topic, plans)
    
    system_prompt = (
        f"Siz professional akademik taqdimot yaratuvchisiz. Quyida keltirilgan kitob manbalari va matnlariga asoslanib, "
        f"aniq {slide_count} ta slayd matnini tuzib bering. Barcha javoblar O'zbek tilida bo'lsin.\n"
        f"Har bir slaydni qat'iy quyidagi formatda yozing:\n"
        f"[Slayd 1]\nSarlavha: ...\nMatn: ...\n"
    )
    prompt = f"Mavzu: {topic}\nRejalar:\n{plans}\n\nKitobdan olingan manbalar:\n{source_material}"
    return _try_openai(system_prompt, prompt)

def create_pptx(title, content, color_scheme="klassik"):
    """
    'templates/' papkasida shablon bo'lsa o'shandan foydalanadi, 
    bo'lmasa mukammal dizayn asosida noldan slayd quradi.
    """
    templates_dir = "templates"
    template_files = glob.glob(os.path.join(templates_dir, "*.pptx"))
    
    if template_files:
        prs = Presentation(template_files[0]) # Siz tashlagan tayyor shablon dizayni
    else:
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)
        
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
    
    # Ranglar sxemasi
    if color_scheme == "qora":
        bg_color, title_color, text_color, card_bg = RGBColor(15, 23, 42), RGBColor(255, 255, 255), RGBColor(203, 213, 225), RGBColor(30, 41, 59)
    elif color_scheme == "kok":
        bg_color, title_color, text_color, card_bg = RGBColor(239, 246, 255), RGBColor(30, 58, 138), RGBColor(30, 41, 59), RGBColor(255, 255, 255)
    else: 
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
        
        for line in lines:
            if line.startswith("Sarlavha:"):
                slide_title = line.replace("Sarlavha:", "").strip()
            elif line.startswith("Matn:"):
                body_text_lines.append(line.replace("Matn:", "").strip())
            elif line and not line.startswith("[") and not line.startswith("Sarlavha"):
                body_text_lines.append(line)
                
        body_text = '\n'.join(body_text_lines)
        
        slide = prs.slides.add_slide(blank_layout)
        try:
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = bg_color
        except: pass
        
        # Sarlavha qutisi
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.0))
        p_title = title_box.text_frame.paragraphs[0]
        p_title.text = slide_title
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = title_color
        
        # Matn uchun chiroyli card (fon blok)
        card = slide.shapes.add_shape(1, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0))
        card.fill.solid()
        card.fill.fore_color.rgb = card_bg
        card.line.color.rgb = RGBColor(203, 213, 225)
        
        text_box = slide.shapes.add_textbox(Inches(1.1), Inches(2.1), Inches(11.1), Inches(4.4))
        p_body = text_box.text_frame.paragraphs[0]
        p_body.text = body_text if body_text else "Ma'lumot mavjud emas."
        p_body.font.size = Pt(18)
        p_body.font.color.rgb = text_color
            
    file_path = "Tayyor_Taqdimot.pptx"
    prs.save(file_path)
    return file_path
