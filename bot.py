import logging, os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, CARD_NUMBER, CARD_HOLDER
from ai_handler import get_ai_response, create_word, create_pptx
from database import init_db, get_balance, update_balance, get_language, set_language

logging.basicConfig(level=logging.INFO)

PRICES = {
    "Dars ishlanmasi": 4000, "Maqola": 19999, "Tezis": 9999,
    "Mavzu bo'yicha slayd": 4999, "Mustaqil ish": 9999, "Kurs ishi": 29999,
    "Bitiruv malakaviy ishi": 199999, "Magistrlik dissertatsiyasi": 799999,
    "Uslubiy qo'llanma": 599999
}

SUBTYPE_CATEGORIES = ["Dars ishlanmasi"]
DARS_TURI_MAP = {
    "📖 Ma'ruza": "Ma'ruza", "🛠 Amaliy mashg'ulot": "Amaliy mashg'ulot",
    "💬 Seminar": "Seminar", "🔬 Laboratoriya mashg'uloti": "Laboratoriya mashg'uloti"
}
DARS_TURI_KEYBOARD_ROWS = [["📖 Ma'ruza", "🛠 Amaliy mashg'ulot"], ["💬 Seminar", "🔬 Laboratoriya mashg'uloti"]]

def build_categories_keyboard():
    return ReplyKeyboardMarkup([
        ["Dars ishlanmasi", "Maqola"], ["Tezis", "Uslubiy qo'llanma"],
        ["Mustaqil ish", "Mavzu bo'yicha slayd"], ["Kurs ishi", "Bitiruv malakaviy ishi"],
        ["Magistrlik dissertatsiyasi"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    # 1. Start tugmasini bosgan insonga yozuv
    await update.message.reply_text(
        "Assalomu alaykum men sizning AI yordamchingizman, bo'limlarni tanlang",
        reply_markup=build_categories_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text
    user_lang = get_language(uid)

    if text in SUBTYPE_CATEGORIES:
        context.user_data['pending_cat'] = text
        context.user_data['awaiting_dars_turi'] = True
        await update.message.reply_text("📚 Dars turini tanlang:", reply_markup=ReplyKeyboardMarkup(DARS_TURI_KEYBOARD_ROWS, resize_keyboard=True))
        return

    if context.user_data.get('awaiting_dars_turi') and text in DARS_TURI_MAP:
        context.user_data['awaiting_dars_turi'] = False
        context.user_data['cat'] = context.user_data.get('pending_cat', "Dars ishlanmasi")
        context.user_data['dars_turi'] = DARS_TURI_MAP[text]
        # 2. Bo'lim tanlangandan so'ng yozuv
        await update.message.reply_text("Mavzuni kiriting", reply_markup=ReplyKeyboardRemove())
        return

    if text in PRICES and text not in SUBTYPE_CATEGORIES:
        context.user_data['cat'] = text
        context.user_data['dars_turi'] = None
        # 2. Bo'lim tanlangandan so'ng yozuv
        await update.message.reply_text("Mavzuni kiriting", reply_markup=ReplyKeyboardRemove())
        return

    cat = context.user_data.get('cat')
    if cat:
        topic = text
        price = PRICES.get(cat, 0)
        bal = get_balance(uid)

        # 3. Mavzuni yozganidan so'ng yozuv
        if bal < price:
            await update.message.reply_text(f"Kerakli mablag'ni kiriting va to'lov rasmini yuboring\nKarta: {CARD_NUMBER} ({CARD_HOLDER})")
            return
        
        # Agar to'lovi bo'lsa, davom etadi
        await update.message.reply_text("⏳ Fayl tayyorlanmoqda, iltimos kuting...")
        update_balance(uid, -price)
        
        ai_context = f"{cat} - {context.user_data.get('dars_turi')}" if context.user_data.get('dars_turi') else cat
        resp = get_ai_response(topic, context=ai_context, language=user_lang)

        # Matnli xabar chiqarilmaydi, faqat fayl yuboriladi
        try:
            if "slayd" in cat.lower():
                p = create_pptx(topic[:30], resp)
            else:
                p = create_word(topic[:30], resp)
            
            with open(p, 'rb') as f:
                await update.message.reply_document(document=f, reply_markup=build_categories_keyboard())
            os.remove(p)
            context.user_data['cat'] = None
            context.user_data['dars_turi'] = None
        except Exception as e:
            await update.message.reply_text(f"Fayl saqlashda xatolik yuz berdi: {e}", reply_markup=build_categories_keyboard())

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ To'lov chekingiz qabul qilindi va admin tekshiruviga yuborildi. Tasdiqlangach, botdan foydalanishda davom etishingiz mumkin.",
        reply_markup=build_categories_keyboard()
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    print("Yangi bot ishga tushdi...")
    app.run_polling()
