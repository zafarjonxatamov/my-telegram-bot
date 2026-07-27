import logging, os, asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_HOLDER
from ai_handler import get_ai_response, create_word, create_pptx
from database import (
    init_db, get_balance, update_balance, get_language, set_language,
    create_payment, get_payment, set_payment_status
)

logging.basicConfig(level=logging.INFO)

PRICES = {
    "Dars ishlanmasi": 4000, "Maqola": 19999, "Tezis": 9999,
    "Mavzu bo'yicha slayd": 4999, "Mustaqil ish": 9999, "Kurs ishi": 29999
}

DARS_TURI_PRICES = {
    "Amaliy mashg'ulot": 5000,
    "Seminar": 6000,
    "Laboratoriya mashg'uloti": 6000
}

SUBTYPE_CATEGORIES = ["Dars ishlanmasi"]
DARS_TURI_MAP = {
    "🛠 Amaliy mashg'ulot": "Amaliy mashg'ulot",
    "💬 Seminar": "Seminar", 
    "🔬 Laboratoriya mashg'uloti": "Laboratoriya mashg'uloti"
}
DARS_TURI_KEYBOARD_ROWS = [["🛠 Amaliy mashg'ulot", "💬 Seminar"], ["🔬 Laboratoriya mashg'uloti"]]

def build_categories_keyboard():
    return ReplyKeyboardMarkup([
        ["Dars ishlanmasi", "Maqola"], 
        ["Tezis", "Mustaqil ish"],
        ["Kurs ishi", "Mavzu bo'yicha slayd"],
        ["🌐 Tilni o'zgartirish"] 
    ], resize_keyboard=True)

def build_language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"), InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kk")],
        [InlineKeyboardButton("🇰🇬 Кыргызча", callback_data="lang_kg"), InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang_tg")],
        [InlineKeyboardButton("🇺🇿 Qaraqalpaqsha", callback_data="lang_kaa")]
    ])

# YANGILANGAN, PROFESSIONAL XUSH KELIBSIZ XABARI
WELCOME_TEXT = """Assalomu alaykum! Slayd va Hujjatlar yaratuvchi AI yordamchingizga xush kelibsiz. 🎓

📝 Quyidagi menyudan kerakli bo'limni tanlang.

⚠️ Sifatli va aniq natija olish uchun quyidagi qoidalarga amal qiling:

• Mavzuni iloji boricha batafsil va to'liq yozing. 
  ❌ Noto'g'ri: "Tarix"
  ✅ To'g'ri: "Qo'qon xonligi asoschisi Shohruhbiy va Olimxon davri tarixi"
  
  ❌ Noto'g'ri: "Darvozabonlar"
  ✅ To'g'ri: "Gandbolchi darvozabonlarning mashg'ulot va musobaqa faoliyatida taktik tayyorgarligi"

• Har bir mavzuga umumiy bilimdondek qarayman. Tor doiradagi mavzularni kiritishda ularning qaysi fanga mansubligini ham qo'shib yozing (masalan: Sport pedagogikasi, Jismoniy tarbiya).
• Qisqartma yoki imloviy xatoli so'zlarga tushunmay qolishim mumkin. 
• Kiritilgan mavzuga tushunmagan holda, umuman boshqa mavzuga chalg'ib ketishim ehtimoli bor. 

❗️ Iltimos, mavzu yozishda e'tiborli bo'ling va to'liq nomini kiriting!"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=build_categories_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text
    user_lang = get_language(uid)

    if text == "🌐 Tilni o'zgartirish":
        await update.message.reply_text(
            "Iltimos, o'zingizga qulay tilni tanlang:\nВыберите язык:\nChoose your language:", 
            reply_markup=build_language_keyboard()
        )
        return

    if text in SUBTYPE_CATEGORIES:
        context.user_data['pending_cat'] = text
        context.user_data['awaiting_dars_turi'] = True
        await update.message.reply_text("📚 Dars turini tanlang:", reply_markup=ReplyKeyboardMarkup(DARS_TURI_KEYBOARD_ROWS, resize_keyboard=True))
        return

    if context.user_data.get('awaiting_dars_turi') and text in DARS_TURI_MAP:
        context.user_data['awaiting_dars_turi'] = False
        context.user_data['cat'] = context.user_data.get('pending_cat', "Dars ishlanmasi")
        context.user_data['dars_turi'] = DARS_TURI_MAP[text]
        await update.message.reply_text("✏️ Mavzuni batafsil va qoidalarga amal qilgan holda kiriting:", reply_markup=ReplyKeyboardRemove())
        return

    if text in PRICES and text not in SUBTYPE_CATEGORIES:
        context.user_data['cat'] = text
        context.user_data['dars_turi'] = None
        await update.message.reply_text("✏️ Mavzuni batafsil va qoidalarga amal qilgan holda kiriting:", reply_markup=ReplyKeyboardRemove())
        return

    cat = context.user_data.get('cat')
    if cat:
        topic = text
        dars_turi = context.user_data.get('dars_turi')
        
        if cat == "Dars ishlanmasi" and dars_turi in DARS_TURI_PRICES:
            price = DARS_TURI_PRICES[dars_turi]
        else:
            price = PRICES.get(cat, 0)
            
        bal = get_balance(uid)

        if bal < price:
            await update.message.reply_text(
                f"⚠️ Kerakli mablag'ni kiriting va to'lov rasmini yuboring.\n\n"
                f"💳 Karta raqami: {CARD_NUMBER}\n"
                f"👤 Karta egasi: {CARD_HOLDER}\n\n"
                f"Summa: {price} so'm"
            )
            return
        
        await update.message.reply_text("⏳ Fayl tayyorlanmoqda, iltimos kuting. (Bu jarayon 1-2 daqiqa vaqt olishi mumkin)...")
        update_balance(uid, -price)
        
        ai_context = f"{cat} - {dars_turi}" if dars_turi else cat
        
        try:
            resp = await asyncio.to_thread(get_ai_response, topic, ai_context, user_lang)

            if "slayd" in cat.lower():
                p = await asyncio.to_thread(create_pptx, topic[:30], resp)
            else:
                p = await asyncio.to_thread(create_word, topic[:30], resp)
            
            with open(p, 'rb') as f:
                await update.message.reply_document(document=f, reply_markup=build_categories_keyboard())
            os.remove(p)
            context.user_data['cat'] = None
            context.user_data['dars_turi'] = None
        except Exception as e:
            update_balance(uid, price) 
            await update.message.reply_text(f"Fayl saqlashda xatolik yuz berdi: {e}", reply_markup=build_categories_keyboard())
    else:
        await update.message.reply_text(
            "⚠️ Iltimos, avval pastdagi menyudan o'zingizga kerakli hujjat turini tanlang.",
            reply_markup=build_categories_keyboard()
        )

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    file_id = update.message.photo[-1].file_id
    
    cat = context.user_data.get('cat')
    dars_turi = context.user_data.get('dars_turi')
    
    if cat == "Dars ishlanmasi" and dars_turi in DARS_TURI_PRICES:
        amount = DARS_TURI_PRICES[dars_turi]
    else:
        amount = PRICES.get(cat, 0)
    
    payment_id = create_payment(uid, amount, file_id)

    await update.message.reply_text(
        "✅ To'lov chekingiz qabul qilindi va admin tekshiruviga yuborildi. Tasdiqlangach, botdan foydalanishda davom etishingiz mumkin.",
        reply_markup=build_categories_keyboard()
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{payment_id}")
        ]
    ])

    username = update.message.from_user.username or "yo'q"
    caption_text = f"{cat} - {dars_turi}" if dars_turi else cat
    caption = (
        f"🆕 Yangi to'lov so'rovi\n"
        f"ID: {payment_id}\n"
        f"Foydalanuvchi: {uid} (@{username})\n"
        f"Summa: {amount} so'm\n"
        f"Bo'lim: {caption_text or 'Noma`lum'}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        reply_markup=keyboard
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        set_language(query.from_user.id, lang_code)
        await query.edit_message_text("✅ Til muvaffaqiyatli tanlandi! Endi barcha ma'lumotlar shu tilda tayyorlanadi.")
        return

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Sizda ruxsat yo'q!", show_alert=True)
        return

    action, payment_id_str = data.split("_")
    payment_id = int(payment_id_str)

    payment = get_payment(payment_id)
    if not payment:
        await query.edit_message_caption(caption="⚠️ Bu to'lov so'rovi topilmadi.")
        return

    _, user_id, amount, file_id, status = payment

    if status != "pending":
        await query.edit_message_caption(caption=f"ℹ️ Bu so'rov allaqachon '{status}' holatida.")
        return

    if action == "approve":
        update_balance(user_id, amount)
        set_payment_status(payment_id, "approved")
        await query.edit_message_caption(caption=f"✅ Tasdiqlandi. {amount} so'm qo'shildi (ID: {payment_id}).")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ To'lovingiz tasdiqlandi! Balansingizga {amount} so'm qo'shildi. Endi mavzuni kiritib, ishingizni davom ettirishingiz mumkin."
        )
    elif action == "reject":
        set_payment_status(payment_id, "rejected")
        await query.edit_message_caption(caption=f"❌ Rad etildi (ID: {payment_id}).")
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ To'lovingiz rad etildi. Savol bo'lsa, admin bilan bog'laning."
        )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("Bot yangi xush kelibsiz xabari bilan ishga tushdi...")
    app.run_polling()
