import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_HOLDER

logging.basicConfig(level=logging.INFO)

# Narxlar va bajarilish muddatlari
PRICES = {
    "Kurs ishi": {"price": 60000, "time": "48 soat"},
    "Diplom ishi": {"price": 700000, "time": "120 soat (5 kun)"},
    "Slayd (1 list)": {"price": 1500, "time": "24 soat"},
    "Dars ishlanmasi Ma'ruza": {"price": 8000, "time": "24 soat"},
    "Dars ishlanmasi Seminar": {"price": 6000, "time": "24 soat"},
    "Dars ishlanmasi Laboratoriya": {"price": 6000, "time": "24 soat"},
    "Dars ishlanmasi Amaliy": {"price": 5000, "time": "24 soat"},
    "Maqola yozish": {"price": 50000, "time": "72 soat (3 kun)"},
    "Tezis": {"price": 30000, "time": "48 soat"},
    "Magistrlik dissertatsiyasi": {"price": 0, "time": "Kelishilgan holda"}
}

def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service TEXT,
            topic TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

def main_keyboard():
    return ReplyKeyboardMarkup([
        ["📝 Buyurtma berish"],
        ["ℹ️ Biz haqimizda / Aloqa"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    context.user_data.clear()
    
    welcome_text = (
        "Assalomu alaykum aziz izlanuvchi. Sizga quyidagi xizmatlarni tavsiya qilaman.\n\n"
        "🚀 <b>O'QITUVCHI VA TALABALAR UCHUN ENG SIFATli XIZMAT!</b>\n\n"
        "📝 <b>Kurs ishi</b>\n"
        "🎓 <b>Diplom ishi</b>\n"
        "📊 <b>Slayd</b>\n"
        "📖 <b>Dars ishlanmasi:</b> Ma'ruza\n"
        "📖 <b>Dars ishlanmasi:</b> Seminar\n"
        "📖 <b>Dars ishlanmasi:</b> Laboratoriya\n"
        "📖 <b>Dars ishlanmasi:</b> Amaliy\n"
        "📰 <b>Maqola</b>\n"
        "📌 <b>Tezis</b>\n"
        "🎓 <b>Magistrlik dissertatsiyasi</b>\n\n"
        "✔️ Sifatli xizmat\n"
        "✔️ Natija kafolatlanadi\n"
        "✔️ Hamyonbop narxlar\n\n"
        "📲 <b>Hoziroq buyurtma bering:</b>"
    )
    
    await update.message.reply_text(
        welcome_text, 
        reply_markup=main_keyboard(), 
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    state = context.user_data.get('state')

    if text == "ℹ️ Biz haqimizda / Aloqa":
        await update.message.reply_text("Barcha buyurtmalar mutaxassislar tomonidan individual tarzda va yuqori sifatda bajariladi.")
        return

    if text == "📝 Buyurtma berish":
        buttons = []
        for service_name, info in PRICES.items():
            price_str = f"{info['price']} so'm" if info['price'] > 0 else "Kelishiladi"
            buttons.append([InlineKeyboardButton(f"{service_name} — {price_str}", callback_data=f"srv_{service_name}")])
        
        await update.message.reply_text("🎓 Kerakli xizmat turini tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if state == 'waiting_topic':
        context.user_data['topic'] = text
        service = context.user_data['selected_service']
        price = PRICES[service]['price']
        time_limit = PRICES[service]['time']

        context.user_data['state'] = 'waiting_payment'
        
        confirmation_text = (
            f"📋 <b>Buyurtma tafsilotlari:</b>\n\n"
            f"• <b>Xizmat:</b> {service}\n"
            f"• <b>Mavzu/Talab:</b> {text}\n"
            f"• <b>Belgilangan vaqt:</b> {time_limit}\n"
            f"• <b>Narxi:</b> {price if price > 0 else 'Kelishiladi'} so'm\n\n"
            f"💳 To'lov uchun karta: <code>{CARD_NUMBER}</code> ({CARD_HOLDER})\n\n"
            f"Iltimos, to'lovni amalga oshirib, <b>chek rasmini</b> shu yerga yuboring:"
        )
        await update.message.reply_text(confirmation_text, parse_mode="HTML")
        return

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("srv_"):
        service_name = data.replace("srv_", "")
        context.user_data['selected_service'] = service_name
        context.user_data['state'] = 'waiting_topic'
        
        time_limit = PRICES[service_name]['time']
        await query.message.edit_text(
            f"Siz tanladingiz: <b>{service_name}</b>\n"
            f"⏱ Ushbu xizmat uchun ajratilgan vaqt: <b>{time_limit}</b>\n\n"
            f"✍️ Endi buyurtma mavzusini yoki batafsil talablaringizni yozib yuboring:",
            parse_mode="HTML"
        )
        return

    if data.startswith("pay_"):
        parts = data.split("_")
        action = parts[1]
        target_uid = int(parts[2])
        
        if action == "yes":
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ <b>To'lov tasdiqlandi! Ish boshlandi.</b>", parse_mode="HTML")
            await context.bot.send_message(chat_id=target_uid, text="✅ To'lovingiz admin tomonidan tasdiqlandi! Mutaxassis ishni boshladi, tayyor bo'lgach sizga yuboriladi.")
            
            service = context.user_data.get('selected_service', 'Nomaqbul')
            topic = context.user_data.get('topic', 'Kiritilmagan')
            admin_msg = (
                f"🚨 <b>Yangi tasdiqlangan buyurtma!</b>\n\n"
                f"👤 Mijoz ID: <code>{target_uid}</code>\n"
                f"📚 Xizmat: {service}\n"
                f"📝 Mavzu: {topic}\n\n"
                f"<i>(Ishni bajarib bo'lgach, tayyor faylni to'g'ridan-to'g'ri shu mijozga yuborishingiz mumkin)</i>"
            )
            await context.bot.send_message(chat_id=int(ADMIN_ID), text=admin_msg, parse_mode="HTML")
        else:
            await query.edit_message_caption(caption=query.message.caption + "\n\n❌ <b>To'lov rad etildi.</b>", parse_mode="HTML")
            await context.bot.send_message(chat_id=target_uid, text="❌ To'lov cheki yaroqsiz deb topildi. Iltimos, qaytadan urinib ko'ring.")
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    username = update.message.from_user.username or "Noma'lum"
    file_id = update.message.photo[-1].file_id
    service = context.user_data.get('selected_service', 'Nomaqbul')
    topic = context.user_data.get('topic', 'Kiritilmagan')

    caption = (
        f"💳 <b>Yangi to'lov cheki keldi!</b>\n\n"
        f"👤 Foydalanuvchi: @{username} (ID: <code>{uid}</code>)\n"
        f"📚 Xizmat: {service}\n"
        f"📝 Mavzu: {topic}"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay_yes_{uid}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"pay_no_{uid}")
    ]])

    if ADMIN_ID:
        await context.bot.send_photo(chat_id=int(ADMIN_ID), photo=file_id, caption=caption, reply_markup=keyboard, parse_mode="HTML")
        await update.message.reply_text("✅ Chek admingacha yuborildi. Admin tasdiqlashini kuting!")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()
