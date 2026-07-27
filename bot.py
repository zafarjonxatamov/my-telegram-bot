import logging, os
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
        await update.message.reply_text("Mavzuni kiriting", reply_markup=ReplyKeyboardRemove())
        return

    if text in PRICES and text not in SUBTYPE_CATEGORIES:
        context.user_data['cat'] = text
        context.user_data['dars_turi'] = None
        await update.message.reply_text("Mavzuni kiriting", reply_markup=ReplyKeyboardRemove())
        return

    cat = context.user_data.get('cat')
    if cat:
        topic = text
        price = PRICES.get(cat, 0)
        bal = get_balance(uid)

        # Balans yetarli bo'lmaganda chiqadigan aniq xabar
        if bal < price:
            await update.message.reply_text(
                f"⚠️ Kerakli mablag'ni kiriting va to'lov rasmini yuboring.\n\n"
                f"💳 Karta raqami: {CARD_NUMBER}\n"
                f"👤 Karta egasi: {CARD_HOLDER}\n\n"
                f"Summa: {price} so'm"
            )
            return
        
        await update.message.reply_text("⏳ Fayl tayyorlanmoqda, iltimos kuting...")
        update_balance(uid, -price)
        
        ai_context = f"{cat} - {context.user_data.get('dars_turi')}" if context.user_data.get('dars_turi') else cat
        resp = get_ai_response(topic, context=ai_context, language=user_lang)

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
    else:
        # Bot jim qolmasligi uchun yo'naltiruvchi qism
        await update.message.reply_text(
            "⚠️ Iltimos, avval pastdagi menyudan o'zingizga kerakli bo'limni tanlang (Masalan: Dars ishlanmasi, Maqola va h.k).",
            reply_markup=build_categories_keyboard()
        )

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    file_id = update.message.photo[-1].file_id
    
    cat = context.user_data.get('cat')
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
    caption = (
        f"🆕 Yangi to'lov so'rovi\n"
        f"ID: {payment_id}\n"
        f"Foydalanuvchi: {uid} (@{username})\n"
        f"Summa: {amount} so'm\n"
        f"Bo'lim: {cat or 'Noma`lum'}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        reply_markup=keyboard
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Sizda ruxsat yo'q!", show_alert=True)
        return

    action, payment_id_str = query.data.split("_")
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
    app.add_handler(CallbackQueryHandler(handle_admin_callback))
    
    print("Yangi bot to'liq sozlangan holda ishga tushdi...")
    app.run_polling()
