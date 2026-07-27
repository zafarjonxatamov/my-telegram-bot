import logging, os, asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_HOLDER
from ai_handler import get_ai_response, create_word, create_pptx, generate_plans
from database import (
    init_db, get_balance, update_balance, get_language, set_language,
    create_payment, get_payment, set_payment_status
)

logging.basicConfig(level=logging.INFO)

PRICES = {
    "Dars ishlanmasi": 4000, "Maqola": 19999, "Tezis": 9999,
    "Mavzu bo'yicha slayd": 4999, "Mustaqil ish": 9999, "Kurs ishi": 29999
}

DARS_TURI_PRICES = {"Amaliy mashg'ulot": 5000, "Seminar": 6000, "Laboratoriya mashg'uloti": 6000}
SUBTYPE_CATEGORIES = ["Dars ishlanmasi"]
DARS_TURI_MAP = {"🛠 Amaliy mashg'ulot": "Amaliy mashg'ulot", "💬 Seminar": "Seminar", "🔬 Laboratoriya mashg'uloti": "Laboratoriya mashg'uloti"}
DARS_TURI_KEYBOARD_ROWS = [["🛠 Amaliy mashg'ulot", "💬 Seminar"], ["🔬 Laboratoriya mashg'uloti"]]

def build_categories_keyboard():
    return ReplyKeyboardMarkup([
        ["Dars ishlanmasi", "Maqola"], ["Tezis", "Mustaqil ish"],
        ["Kurs ishi", "Mavzu bo'yicha slayd"], ["🌐 Tilni o'zgartirish"]
    ], resize_keyboard=True)

WELCOME_TEXT = """Assalomu alaykum! Slayd va Hujjatlar yaratuvchi AI yordamchingizga xush kelibsiz. 🎓

📝 Quyidagi menyudan kerakli bo'limni tanlang va mavzuni kiriting."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    context.user_data.clear()
    await update.message.reply_text(WELCOME_TEXT, reply_markup=build_categories_keyboard())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    username = update.message.from_user.username or "Noma'lum"
    file_id = update.message.photo[-1].file_id
    
    cat = context.user_data.get('cat', "Mavzu bo'yicha slayd")
    dars_turi = context.user_data.get('dars_turi')
    price = DARS_TURI_PRICES[dars_turi] if cat == "Dars ishlanmasi" and dars_turi in DARS_TURI_PRICES else PRICES.get(cat, 5000)

    payment_id = create_payment(uid, price, file_id)
    
    caption = (
        f"💳 **Yangi to'lov cheki keldi!**\n\n"
        f"👤 Foydalanuvchi: @{username} (ID: `{uid}`)\n"
        f"💵 Summa: {price} so'm\n"
        f"🆔 To'lov ID: `{payment_id}`"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay_yes_{payment_id}_{uid}_{price}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"pay_no_{payment_id}_{uid}")
        ]
    ])
    
    if ADMIN_ID:
        try:
            await context.bot.send_photo(
                chat_id=int(ADMIN_ID),
                photo=file_id,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Chekingiz adminga yuborildi. Tez orada balansingiz to'ldiriladi, kuting!")
        except Exception as e:
            await update.message.reply_text(f"❌ Chekni yuborishda xatolik: {e}")
    else:
        await update.message.reply_text("⚠️ Admin ID sozlanmagan!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text
    user_lang = get_language(uid)

    if text == "🌐 Tilni o'zgartirish":
        await update.message.reply_text(
            "Iltimos, o'zingizga qulay tilni tanlang:\n"
            "Пожалуйста, выберите язык:\n"
            "Please select a language:", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
                [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"), InlineKeyboardButton(" Karakalpak", callback_data="lang_kaa")],
                [InlineKeyboardButton("🇰🇬 Кыргызcha", callback_data="lang_kg"), InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kk")],
                [InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang_tg")]
            ])
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
        await update.message.reply_text("✏️ Mavzuni batafsil kiriting:", reply_markup=ReplyKeyboardRemove())
        return

    if text in PRICES and text not in SUBTYPE_CATEGORIES:
        context.user_data['cat'] = text
        context.user_data['dars_turi'] = None
        await update.message.reply_text("✏️ Mavzuni batafsil kiriting:", reply_markup=ReplyKeyboardRemove())
        return

    cat = context.user_data.get('cat')
    if not cat:
        await update.message.reply_text("⚠️ Avval pastdagi menyudan bo'limni tanlang.", reply_markup=build_categories_keyboard())
        return

    topic = text
    context.user_data['topic'] = topic
    
    dars_turi = context.user_data.get('dars_turi')
    price = DARS_TURI_PRICES[dars_turi] if cat == "Dars ishlanmasi" and dars_turi in DARS_TURI_PRICES else PRICES.get(cat, 0)
    bal = get_balance(uid)

    if bal < price:
        await update.message.reply_text(
            f"⚠️ Mablag' yetarli emas! Narx: {price} so'm.\n"
            f"💳 Karta: {CARD_NUMBER} ({CARD_HOLDER})\n\n"
            f"Iltimos, to'lovni qilib chek rasmini shu yerga yuboring."
        )
        return

    msg = await update.message.reply_text("⏳ Sun'iy intellekt reja tuzmoqda, biroz kuting...")
    
    try:
        plans = await asyncio.to_thread(generate_plans, topic, user_lang)
        context.user_data['plans'] = plans
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Reja ma'qul, davom etish", callback_data="approve_plan")],
            [InlineKeyboardButton("🔄 Boshqa reja yaratish", callback_data="regenerate_plan")]
        ])
        
        await context.bot.edit_message_text(
            chat_id=uid, message_id=msg.message_id,
            text=f"📋 **Taklif etilgan rejalar:**\n\n{plans}\n\nUshbu reja sizga ma'qulmi?",
            reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.edit_message_text(chat_id=uid, message_id=msg.message_id, text=f"❌ Xatolik: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    user_lang = get_language(uid)

    if data.startswith("lang_"):
        set_language(uid, data.split("_")[1])
        await query.edit_message_text("✅ Til muvaffaqiyatli o'zgartirildi!", reply_markup=None)
        await context.bot.send_message(chat_id=uid, text="Asosiy menyu:", reply_markup=build_categories_keyboard())
        return

    if data.startswith("pay_yes_") or data.startswith("pay_no_"):
        parts = data.split("_")
        action = parts[1]
        pay_id = int(parts[2])
        target_uid = int(parts[3])
        
        if action == "yes":
            amount = int(parts[4]) if len(parts) > 4 else 5000
            set_payment_status(pay_id, "approved")
            update_balance(target_uid, amount)
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **Tasdiqlandi! Balans qo'shildi.**", parse_mode="Markdown")
            try:
                await context.bot.send_message(chat_id=target_uid, text="✅ To'lovingiz tasdiqlandi! Balansingizga mablag' qo'shildi. Endi mavzuni yuborishingiz mumkin.", reply_markup=build_categories_keyboard())
            except: pass
        else:
            set_payment_status(pay_id, "rejected")
            await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **Rad etildi.**", parse_mode="Markdown")
            try:
                await context.bot.send_message(chat_id=target_uid, text="❌ To'lov cheki rad etildi. Administrator bilan bog'laning.")
            except: pass
        return

    if data == "regenerate_plan":
        topic = context.user_data.get('topic', 'Mavzu')
        await query.edit_message_text("⏳ Yangi rejalar tuzilmoqda...")
        try:
            plans = await asyncio.to_thread(generate_plans, topic, user_lang)
            context.user_data['plans'] = plans
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Reja ma'qul, davom etish", callback_data="approve_plan")],
                [InlineKeyboardButton("🔄 Boshqa reja yaratish", callback_data="regenerate_plan")]
            ])
            await query.message.reply_text(f"📋 **Yangi rejalar:**\n\n{plans}", reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            await query.message.reply_text(f"Xatolik: {e}")
        return

    if data == "approve_plan":
        await query.edit_message_text("✅ Reja tasdiqlandi! Fayl tayyorlanmoqda, kuting...")
        
        cat = context.user_data.get('cat')
        topic = context.user_data.get('topic')
        dars_turi = context.user_data.get('dars_turi')
        plans = context.user_data.get('plans', '')
        
        price = DARS_TURI_PRICES[dars_turi] if cat == "Dars ishlanmasi" and dars_turi in DARS_TURI_PRICES else PRICES.get(cat, 0)
        update_balance(uid, -price)
        
        ai_context = f"{cat} - {dars_turi}" if dars_turi else cat
        prompt = f"Mavzu: {topic}\nTasdiqlangan rejalar:\n{plans}"

        try:
            resp = await asyncio.to_thread(get_ai_response, prompt, ai_context, user_lang)
            if "slayd" in cat.lower():
                p = await asyncio.to_thread(create_pptx, topic[:30], resp)
            else:
                p = await asyncio.to_thread(create_word, topic[:30], resp)
            
            with open(p, 'rb') as f:
                await context.bot.send_document(chat_id=uid, document=f, caption="✅ Marhamat, faylingiz tayyor!", reply_markup=build_categories_keyboard())
            os.remove(p)
            context.user_data.clear()
        except Exception as e:
            update_balance(uid, price)
            await context.bot.send_message(chat_id=uid, text=f"❌ Xato: {e}", reply_markup=build_categories_keyboard())

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot xatosiz va mukammal holatda ishga tushdi...")
    app.run_polling()
