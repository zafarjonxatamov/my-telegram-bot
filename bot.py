# -*- coding: utf-8 -*-
import logging, os, asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from config import TELEGRAM_TOKEN, ADMIN_ID, CARD_NUMBER, CARD_HOLDER
from ai_handler import get_ai_response, create_word, create_pptx, is_long_document, generate_long_document
from database import (
    init_db, get_balance, update_balance,
    create_payment, get_payment, set_payment_status,
    get_language, set_language
)

logging.basicConfig(level=logging.INFO)

PRICES = {
    "Dars ishlanmasi": 2999, "Maqola": 19999, "Tezis": 9999,
    "Mavzu bo'yicha slayd": 4999, "Mustaqil ish": 9999, "Kurs ishi": 29999,
    "Bitiruv malakaviy ishi": 199999, "Magistrlik dissertatsiyasi": 799999,
    "PhD dissertatsiya": 11000000, "Uslubiy qo'llanma": 599999,
    "O'quv qo'llanma": 999999, "Darslik": 2999999
}

CATEGORIES = [
    ["Dars ishlanmasi", "Maqola"], ["Tezis", "Uslubiy qo'llanma"],
    ["O'quv qo'llanma", "Darslik"], ["Mustaqil ish", "Mavzu bo'yicha slayd"],
    ["Kurs ishi", "Bitiruv malakaviy ishi"], ["Magistrlik dissertatsiyasi", "PhD dissertatsiya"],
    ["🌐 Til / Language"],
    ["💳 Balansni to'ldirish", "Balansni tekshirish"]
]

# --- TIL TANLASH TUGMALARI ---
LANGUAGE_OPTIONS = {
    "O'zbek 🇺🇿": "uz",
    "Русский 🇷🇺": "ru",
    "English 🇬🇧": "en",
    "Qaraqalpaqsha 🇺🇿": "kaa",
    "Кыргызча 🇰🇬": "kg",
    "Қазақша 🇰🇿": "kk",
    "Тоҷикӣ 🇹🇯": "tg",
}

LANGUAGE_KEYBOARD = [
    ["O'zbek 🇺🇿", "Русский 🇷🇺"],
    ["English 🇬🇧", "Qaraqalpaqsha 🇺🇿"],
    ["Кыргызча 🇰🇬", "Қазақша 🇰🇿"],
    ["Тоҷикӣ 🇹🇯"],
    ["⬅️ Orqaga"],
]

# ==========================================================
#  MENYU TUGMALARI TARJIMASI (7 TIL)
#  Kalit — har doim o'zbekcha (kanonik) nom, u PRICES va
#  ai_handler.py bilan mos kelishi shart.
# ==========================================================

CATEGORY_TRANSLATIONS = {
    "Dars ishlanmasi": {
        "ru": "Разработка урока", "en": "Lesson Plan",
        "kaa": "Sabaq islanbesi", "kg": "Сабак иштелмеси",
        "kk": "Сабақ жоспары", "tg": "Тарҳи дарс",
    },
    "Maqola": {
        "ru": "Статья", "en": "Article",
        "kaa": "Maqala", "kg": "Макала",
        "kk": "Мақала", "tg": "Мақола",
    },
    "Tezis": {
        "ru": "Тезис", "en": "Thesis",
        "kaa": "Tezis", "kg": "Тезис",
        "kk": "Тезис", "tg": "Тезис",
    },
    "Mavzu bo'yicha slayd": {
        "ru": "Слайд по теме", "en": "Presentation Slides",
        "kaa": "Tema boyınsha slayd", "kg": "Тема боюнча слайд",
        "kk": "Тақырып бойынша слайд", "tg": "Слайд оид ба мавзӯъ",
    },
    "Mustaqil ish": {
        "ru": "Самостоятельная работа", "en": "Independent Work",
        "kaa": "Ózbetinshe jumıs", "kg": "Өз алдынча иш",
        "kk": "Өздік жұмыс", "tg": "Кори мустақилона",
    },
    "Kurs ishi": {
        "ru": "Курсовая работа", "en": "Course Paper",
        "kaa": "Kurs jumısı", "kg": "Курстук иш",
        "kk": "Курстық жұмыс", "tg": "Кори курсӣ",
    },
    "Bitiruv malakaviy ishi": {
        "ru": "Выпускная квалификационная работа", "en": "Bachelor's Thesis",
        "kaa": "Bitiriw maliymlik jumısı", "kg": "Бүтүрүү квалификациялык иши",
        "kk": "Бітіру біліктілік жұмысы", "tg": "Кори квалификатсионии хатм",
    },
    "Magistrlik dissertatsiyasi": {
        "ru": "Магистерская диссертация", "en": "Master's Dissertation",
        "kaa": "Magistrlik dissertaciyası", "kg": "Магистрдик диссертация",
        "kk": "Магистрлік диссертация", "tg": "Диссертатсияи магистрӣ",
    },
    "PhD dissertatsiya": {
        "ru": "Докторская диссертация (PhD)", "en": "PhD Dissertation",
        "kaa": "PhD dissertaciya", "kg": "PhD диссертация",
        "kk": "PhD диссертациясы", "tg": "Диссертатсияи PhD",
    },
    "Uslubiy qo'llanma": {
        "ru": "Методическое пособие", "en": "Methodological Guide",
        "kaa": "Ádistemelik qollanba", "kg": "Усулдук колдонмо",
        "kk": "Әдістемелік құрал", "tg": "Дастури методӣ",
    },
    "O'quv qo'llanma": {
        "ru": "Учебное пособие", "en": "Study Guide",
        "kaa": "Oqıw qollanba", "kg": "Окуу колдонмосу",
        "kk": "Оқу құралы", "tg": "Дастури таълимӣ",
    },
    "Darslik": {
        "ru": "Учебник", "en": "Textbook",
        "kaa": "Sabaqlıq", "kg": "Окуу китеби",
        "kk": "Оқулық", "tg": "Китоби дарсӣ",
    },
    "💳 Balansni to'ldirish": {
        "ru": "💳 Пополнить баланс", "en": "💳 Top Up Balance",
        "kaa": "💳 Balanstı tolıqtırıw", "kg": "💳 Балансты толуктоо",
        "kk": "💳 Балансты толтыру", "tg": "💳 Пур кардани баланс",
    },
    "Balansni tekshirish": {
        "ru": "Проверить баланс", "en": "Check Balance",
        "kaa": "Balanstı tekseriw", "kg": "Балансты текшерүү",
        "kk": "Балансты тексеру", "tg": "Санҷиши баланс",
    },
}

# Har bir tarjimadan kanonik (o'zbekcha) nomga qaytadigan teskari lug'at
REVERSE_TRANSLATIONS = {}
for _canonical, _langs in CATEGORY_TRANSLATIONS.items():
    REVERSE_TRANSLATIONS[_canonical] = _canonical
    for _lang_code, _translated in _langs.items():
        REVERSE_TRANSLATIONS[_translated] = _canonical


def tr(canonical_text, lang_code):
    """Kanonik (o'zbekcha) matnni tanlangan tilga tarjima qiladi."""
    return CATEGORY_TRANSLATIONS.get(canonical_text, {}).get(lang_code, canonical_text)


def build_categories_keyboard(lang_code):
    """Foydalanuvchi tiliga mos tarjima qilingan asosiy menyuni quradi."""
    rows = [
        ["Dars ishlanmasi", "Maqola"],
        ["Tezis", "Uslubiy qo'llanma"],
        ["O'quv qo'llanma", "Darslik"],
        ["Mustaqil ish", "Mavzu bo'yicha slayd"],
        ["Kurs ishi", "Bitiruv malakaviy ishi"],
        ["Magistrlik dissertatsiyasi", "PhD dissertatsiya"],
        ["🌐 Til / Language"],
        ["💳 Balansni to'ldirish", "Balansni tekshirish"],
    ]
    translated_rows = [[tr(item, lang_code) for item in row] for row in rows]
    return ReplyKeyboardMarkup(translated_rows, resize_keyboard=True)


TOPUP_WAITING_AMOUNT = "waiting_amount"
TOPUP_WAITING_SCREENSHOT = "waiting_screenshot"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    uid = update.message.from_user.id
    user_lang = get_language(uid)
    reply_markup = build_categories_keyboard(user_lang)
    await update.message.reply_text("V3.0 Balans tizimi ishga tushdi! Bo'limni tanlang:", reply_markup=reply_markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    # Foydalanuvchi tilida ko'rsatilgan tugma matnini kanonik (o'zbekcha) nomga aylantiramiz
    text = REVERSE_TRANSLATIONS.get(text, text)

    user_lang = get_language(uid)

    # --- Til tanlash menyusini ochish ---
    if text == "🌐 Til / Language":
        await update.message.reply_text(
            "🌐 Tilni tanlang / Выберите язык / Choose a language:",
            reply_markup=ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True)
        )
        return

    # --- Orqaga qaytish ---
    if text == "⬅️ Orqaga":
        await update.message.reply_text(
            "Bosh menyu:",
            reply_markup=build_categories_keyboard(user_lang)
        )
        return

    # --- Foydalanuvchi tilni tanladi ---
    if text in LANGUAGE_OPTIONS:
        lang_code = LANGUAGE_OPTIONS[text]
        set_language(uid, lang_code)
        await update.message.reply_text(
            f"✅ Til tanlandi: {text}\nEndi barcha hujjatlar shu tilda yaratiladi.",
            reply_markup=build_categories_keyboard(lang_code)
        )
        return

    # --- Balansni to'ldirish tugmasi bosilganda ---
    if text == "💳 Balansni to'ldirish":
        context.user_data['topup_state'] = TOPUP_WAITING_AMOUNT
        await update.message.reply_text(
            "💳 Necha so'mlik balans to'ldirmoqchisiz?\nFaqat raqam kiriting (masalan: 50000)"
        )
        return

    # --- Foydalanuvchi to'ldirish summasini kiritmoqda ---
    if context.user_data.get('topup_state') == TOPUP_WAITING_AMOUNT:
        if not text.isdigit():
            await update.message.reply_text("⚠️ Iltimos, faqat raqam kiriting (masalan: 50000)")
            return
        amount = int(text)
        context.user_data['topup_amount'] = amount
        context.user_data['topup_state'] = TOPUP_WAITING_SCREENSHOT
        await update.message.reply_text(
            f"💳 {amount} so'mni quyidagi kartaga o'tkazing:\n\n"
            f"Karta raqami: {CARD_NUMBER}\n"
            f"Egasi: {CARD_HOLDER}\n\n"
            f"✅ To'lovni amalga oshirgach, chek (screenshot) rasmini shu yerga yuboring."
        )
        return

    if text == "Balansni tekshirish":
        b = get_balance(uid)
        await update.message.reply_text(f"💰 ID: {uid}\n💰 Balans: {b} so'm")
        return

    if text in PRICES:
        context.user_data['cat'] = text
        display_name = tr(text, user_lang)
        await update.message.reply_text(f"✅ {display_name} tanlandi. Narxi: {PRICES[text]} so'm. Mavzuni yozing:")
        return

    cat = context.user_data.get('cat')
    if not cat:
        await update.message.reply_text("⚠️ Avval bo'limni tanlang!")
        return

    bal = get_balance(uid)
    price = PRICES.get(cat, 0)

    if bal < price:
        await update.message.reply_text(f"❌ Mablag' yetarli emas! Sizda: {bal} so'm. Kerak: {price} so'm.")
        return

    if is_long_document(cat):
        # Katta hajmli hujjat — bo'lim-bo'lim (bob-bob) generatsiya qilinadi
        status_msg = await update.message.reply_text(
            "⏳ Bu turdagi hujjat bir necha bo'limdan iborat va bo'lim-bo'lim "
            "yaratiladi. Bu biroz vaqt olishi mumkin (bir necha daqiqa)...\n\n"
            "Boshlanmoqda: 0%"
        )

        progress = {"idx": 0, "total": 0, "section": ""}

        def _progress_callback(idx, total, section_title):
            progress["idx"] = idx
            progress["total"] = total
            progress["section"] = section_title

        task = asyncio.create_task(
            asyncio.to_thread(generate_long_document, text, cat, _progress_callback, user_lang)
        )

        while not task.done():
            await asyncio.sleep(4)
            if progress["total"]:
                pct = int(progress["idx"] / progress["total"] * 100)
                try:
                    await status_msg.edit_text(
                        f"⏳ Yaratilmoqda: {progress['idx']}/{progress['total']} bo'lim ({pct}%)\n"
                        f"Hozirgi: {progress['section'][:60]}"
                    )
                except Exception:
                    pass

        resp = await task
        try:
            await status_msg.edit_text("✅ Barcha bo'limlar tayyor! Fayl shakllantirilmoqda...")
        except Exception:
            pass
    else:
        await update.message.reply_text("⏳ AI ishlamoqda...")
        resp = get_ai_response(text, context=cat, language=user_lang)

    update_balance(uid, -price)
    await update.message.reply_text(resp[:4000])

    try:
        if "slayd" in cat.lower():
            p = create_pptx(text[:20], resp)
        else:
            p = create_word(text[:20], resp)
        with open(p, 'rb') as f:
            await update.message.reply_document(document=f)
        os.remove(p)
    except Exception as e:
        await update.message.reply_text(f"Fayl xatosi: {e}")


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi to'lov chekini (rasm) yuborganda ishlaydi."""
    uid = update.message.from_user.id

    if context.user_data.get('topup_state') != TOPUP_WAITING_SCREENSHOT:
        return  # Kutilmagan rasm, e'tiborsiz qoldiramiz

    amount = context.user_data.get('topup_amount', 0)
    file_id = update.message.photo[-1].file_id

    payment_id = create_payment(uid, amount, file_id)

    context.user_data['topup_state'] = None
    context.user_data['topup_amount'] = None

    await update.message.reply_text(
        "✅ Chekingiz qabul qilindi va admin tekshiruviga yuborildi.\n"
        "Tasdiqlangach, balansingizga mablag' qo'shiladi."
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
        f"Summa: {amount} so'm"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        reply_markup=keyboard
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin 'Tasdiqlash' yoki 'Rad etish' tugmasini bosganda ishlaydi."""
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
            text=f"✅ To'lovingiz tasdiqlandi! Balansingizga {amount} so'm qo'shildi."
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
    print("V3.0 BOT ISHGA TUSHDI...")
    app.run_polling()
