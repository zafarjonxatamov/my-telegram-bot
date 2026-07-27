import logging, os, asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_HOLDER
from ai_handler import get_ai_slides, create_pptx
from database import init_db, get_balance, update_balance, get_language, set_language, create_payment, set_payment_status

logging.basicConfig(level=logging.INFO)

PRICES = {
    "Standart taqdimot (6-8 slayd)": {"price": 3500, "count": 8, "type": "ai"},
    "Standart + taqdimot (9-12 slayd)": {"price": 4000, "count": 12, "type": "ai"},
    "Standart pro taqdimot (9-15 slayd)": {"price": 4500, "count": 15, "type": "ai"},
    "Premium taqdimot (8-10 slayd)": {"price": 5000, "count": 10, "type": "ai_text"},
    "Premium + taqdimot (9-12 slayd)": {"price": 6000, "count": 12, "type": "ai_text"},
    "Premium pro taqdimot (10-15 slayd)": {"price": 8000, "count": 15, "type": "ai_text"},
    "BMI uchun taqdimot (14-16 slayd)": {"price": 20000, "count": 16, "type": "manual"},
    "Magistrlik dissertatsiyasi taqdimoti (16-18 slayd)": {"price": 30000, "count": 18, "type": "manual"},
    "PhD taqdimoti": {"price": 100000, "count": 15, "type": "manual"}
}

def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🎨 Taqdimot Yaratish"],
        ["💰 Balansni Tekshirish", "🌐 Tilni O'zgartirish"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    context.user_data.clear()
    await update.message.reply_text("Assalomu alaykum! Tilni tanlang:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    if data.startswith("lang_"):
        set_language(uid, data.split("_")[1])
        await query.edit_message_text("✅ Til saqlandi! Asosiy menyu:")
        await context.bot.send_message(chat_id=uid, text="Kerakli bo'limni tanlang:", reply_markup=main_keyboard())
        return

    if data.startswith("pay_yes_") or data.startswith("pay_no_"):
        parts = data.split("_")
        action = parts[1]
        pay_id = int(parts[2])
        target_uid = int(parts[3])
        amount = int(parts[4])
        
        if action == "yes":
            set_payment_status(pay_id, "approved")
            update_balance(target_uid, amount)
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **Tasdiqlandi! Balans to'ldirildi.**", parse_mode="Markdown")
            await context.bot.send_message(chat_id=target_uid, text="✅ To'lovingiz tasdiqlandi! Davom etishingiz mumkin.", reply_markup=main_keyboard())
        else:
            set_payment_status(pay_id, "rejected")
            await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **Rad etildi.**", parse_mode="Markdown")
            await context.bot.send_message(chat_id=target_uid, text="❌ To'lov rad etildi.")
        return

    if data.startswith("cat_"):
        cat_name = data.replace("cat_", "")
        context.user_data['selected_cat'] = cat_name
        p_info = PRICES[cat_name]
        context.user_data['price_info'] = p_info
        
        bal = get_balance(uid)
        price = p_info['price']
        
        if bal < price:
            await query.message.reply_text(
                f"⚠️ Mablag' yetarli emas!\nNarx: **{price} so'm**.\n"
                f"💳 Karta: `{CARD_NUMBER}` ({CARD_HOLDER})\n\n"
                f"Iltimos, to'lovni qilib chek rasmini shu yerga yuboring.", parse_mode="Markdown"
            )
            context.user_data['awaiting_payment'] = True
            return

        update_balance(uid, -price)
        await proceed_after_payment(query.message, context, uid)
        return

    if data.startswith("color_"):
        color = data.replace("color_", "")
        await query.edit_message_text("⏳ Taqdimot yaratilmoqda, iltimos kuting...")
        
        uid = query.from_user.id
        topic = context.user_data.get('topic')
        r1 = context.user_data.get('reja_1', '')
        r2 = context.user_data.get('reja_2', '')
        r3 = context.user_data.get('reja_3', '')
        r4 = context.user_data.get('reja_4', '')
        p_info = context.user_data.get('price_info')
        
        full_prompt = f"Mavzu: {topic}\nRejalar:\n1. {r1}\n2. {r2}\n3. {r3}\n4. {r4}"
        
        try:
            slides_text = get_ai_slides(full_prompt, p_info['count'])
            file_path = create_pptx(topic[:30], slides_text, color)
            
            with open(file_path, 'rb') as f:
                await context.bot.send_document(chat_id=uid, document=f, caption="✅ Marhamat, slaydingiz tayyor!", reply_markup=main_keyboard())
            os.remove(file_path)
            context.user_data.clear()
        except Exception as e:
            await context.bot.send_message(chat_id=uid, text=f"❌ Xatolik: {e}", reply_markup=main_keyboard())
        return

async def proceed_after_payment(message, context, uid):
    p_info = context.user_data.get('price_info')
    if p_info['type'] == 'manual':
        context.user_data['state'] = 'manual_source'
        await message.reply_text("📥 To'lov qabul qilindi! Iltimos, ushbu ilmiy ish / manba hujjatini yuboring. Admin uni shaxsan o'zi tayyorlab beradi.")
    elif p_info['type'] == 'ai_text':
        context.user_data['state'] = 'waiting_source_text'
        await message.reply_text("📄 Premium turdagi taqdimot uchun asosiy matnni yoki faylni yuboring:")
    else:
        context.user_data['state'] = 'waiting_topic'
        await message.reply_text("✏️ Taqdimot mavzusini kiriting:", reply_markup=ReplyKeyboardRemove())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    username = update.message.from_user.username or "Noma'lum"
    file_id = update.message.photo[-1].file_id
    
    p_info = context.user_data.get('price_info', {"price": 5000})
    price = p_info['price']
    
    payment_id = create_payment(uid, price, file_id)
    caption = f"💳 **Yangi to'lov cheki!**\n\n👤 Foydalanuvchi: @{username} (ID: `{uid}`)\n💵 Summa: {price} so'm\n🆔 ID: `{payment_id}`"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay_yes_{payment_id}_{uid}_{price}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"pay_no_{payment_id}_{uid}_{price}")
    ]])
    
    if ADMIN_ID:
        await context.bot.send_photo(chat_id=int(ADMIN_ID), photo=file_id, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        await update.message.reply_text("✅ Chek admingacha yuborildi. Tasdiqlanishini kuting!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text
    state = context.user_data.get('state')

    if text == "💰 Balansni Tekshirish":
        bal = get_balance(uid)
        await update.message.reply_text(f"💳 Sizning balansingiz: **{bal} so'm**", parse_mode="Markdown")
        return

    if text == "🌐 Tilni O'zgartirish":
        await update.message.reply_text("Tilni tanlang:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]))
        return

    if text == "🎨 Taqdimot Yaratish":
        buttons = []
        for cat_name in PRICES.keys():
            buttons.append([InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_name}")])
        await update.message.reply_text("🎓 Taqdimot turini tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if state == 'manual_source':
        cat_name = context.user_data.get('selected_cat', 'BMI')
        caption = f"🎓 **Yangi maxsus buyurtma (Admin uchun)!**\n\n👤 Foydalanuvchi ID: `{uid}`\n📚 Turi: {cat_name}\n\nManba quyida yuborildi:"
        if ADMIN_ID:
            await context.bot.send_message(chat_id=int(ADMIN_ID), text=caption, parse_mode="Markdown")
            if update.message.document:
                await context.bot.send_document(chat_id=int(ADMIN_ID), document=update.message.document.file_id)
            else:
                await context.bot.send_message(chat_id=int(ADMIN_ID), text=f"Manba matni:\n{text}")
        await update.message.reply_text("✅ Manbangiz adminga yuborildi! Admin tayyorlab shaxsiy akkauntingizga yuboradi.", reply_markup=main_keyboard())
        context.user_data.clear()
        return

    if state == 'waiting_topic':
        context.user_data['topic'] = text
        context.user_data['state'] = 'waiting_reja_1'
        await update.message.reply_text("✍️ 1-rejani kiriting:")
        return

    if state == 'waiting_reja_1':
        context.user_data['reja_1'] = text
        context.user_data['state'] = 'waiting_reja_2'
        await update.message.reply_text("✍️ 2-rejani kiriting:")
        return

    if state == 'waiting_reja_2':
        context.user_data['reja_2'] = text
        context.user_data['state'] = 'waiting_reja_3'
        await update.message.reply_text("✍️ 3-rejani kiriting:")
        return

    if state == 'waiting_reja_3':
        context.user_data['reja_3'] = text
        context.user_data['state'] = 'waiting_reja_4'
        await update.message.reply_text("✍️ 4-rejani kiriting:")
        return

    if state == 'waiting_reja_4':
        context.user_data['reja_4'] = text
        context.user_data['state'] = 'waiting_color'
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬜ Klassik (Oq/Kulrang)", callback_data="color_klassik")],
            [InlineKeyboardButton("⬛ Qora stil", callback_data="color_qora")],
            [InlineKeyboardButton("🟦 Ko'k akademik", callback_data="color_kok")]
        ])
        await update.message.reply_text("🎨 Taqdimot dizayn va rangini tanlang:", reply_markup=keyboard)
        return

    await update.message.reply_text("⚠️ Kerakli bo'limni tanlang:", reply_markup=main_keyboard())

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()
