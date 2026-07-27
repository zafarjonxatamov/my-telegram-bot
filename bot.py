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
    init_db, create_payment, get_payment, set_payment_status,
    get_language, set_language
)

logging.basicConfig(level=logging.INFO)

PRICES = {
    "Dars ishlanmasi": 4000, "Maqola": 19999, "Tezis": 9999,
    "Mavzu bo'yicha slayd": 4999, "Mustaqil ish": 9999, "Kurs ishi": 29999,
    "Bitiruv malakaviy ishi": 199999, "Magistrlik dissertatsiyasi": 799999,
    "Uslubiy qo'llanma": 599999
}

CATEGORIES = [
    ["Dars ishlanmasi", "Maqola"], ["Tezis", "Uslubiy qo'llanma"],
    ["Mustaqil ish", "Mavzu bo'yicha slayd"],
    ["Kurs ishi", "Bitiruv malakaviy ishi"], ["Magistrlik dissertatsiyasi"],
    ["🌐 Til / Language"],
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

# --- DARS ISHLANMASI TURLARI VA NARXLARI ---
SUBTYPE_CATEGORIES = ["Dars ishlanmasi", "Mavzu bo'yicha slayd"]

DARS_TURI_MAP = {
    "📖 Ma'ruza": "Ma'ruza",
    "🛠 Amaliy mashg'ulot": "Amaliy mashg'ulot",
    "💬 Seminar": "Seminar",
    "🔬 Laboratoriya mashg'uloti": "Laboratoriya mashg'uloti",
}

DARS_TURI_PRICES = {
    "Ma'ruza": 6000,
    "Amaliy mashg'ulot": 4000,
    "Seminar": 5000,
    "Laboratoriya mashg'uloti": 5000
}

DARS_TURI_KEYBOARD_ROWS = [
    ["📖 Ma'ruza"],
    ["🛠 Amaliy mashg'ulot"],
    ["💬 Seminar"],
    ["🔬 Laboratoriya mashg'uloti"],
    ["⬅️ Orqaga"],
]

# ==========================================================
#  MENYU TUGMALARI TARJIMASI (7 TIL)
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
    "Uslubiy qo'llanma": {
        "ru": "Методическое пособие", "en": "Methodological Guide",
        "kaa": "Ádistemelik qollanba", "kg": "Усулдук колдонмо",
        "kk": "Әдістемелік құрал", "tg": "Дастури методӣ",
    },
    "📖 Ma'ruza": {
        "ru": "📖 Лекция", "en": "📖 Lecture",
        "kaa": "📖 Lekciya", "kg": "📖 Лекция",
        "kk": "📖 Дәріс", "tg": "📖 Лексия",
    },
    "🛠 Amaliy mashg'ulot": {
        "ru": "🛠 Практическое занятие", "en": "🛠 Practical Session",
        "kaa": "🛠 Ámeliy sabaq", "kg": "🛠 Практикалык сабак",
        "kk": "🛠 Тәжірибелік сабақ", "tg": "🛠 Машғулоти амалӣ",
    },
    "💬 Seminar": {
        "ru": "💬 Семинар", "en": "💬 Seminar",
        "kaa": "💬 Seminar", "kg": "💬 Семинар",
        "kk": "💬 Семинар", "tg": "💬 Семинар",
    },
    "🔬 Laboratoriya mashg'uloti": {
        "ru": "🔬 Лабораторное занятие", "en": "🔬 Laboratory Session",
        "kaa": "🔬 Laboratoriya sabaǵı", "kg": "🔬 Лабораториялык сабак",
        "kk": "🔬 Зертханалық сабақ", "tg": "🔬 Машғулоти лабораторӣ",
    },
}

REVERSE_TRANSLATIONS = {}
for _canonical, _langs in CATEGORY_TRANSLATIONS.items():
    REVERSE_TRANSLATIONS[_canonical] = _canonical
    for _lang_code, _translated in _langs.items():
        REVERSE_TRANSLATIONS[_translated] = _canonical


def tr(canonical_text, lang_code):
    return CATEGORY_TRANSLATIONS.get(canonical_text, {}).get(lang_code, canonical_text)


CATEGORY_EMOJIS = {
    "Dars ishlanmasi": "📝",
    "Maqola": "📄",
    "Tezis": "📃",
    "Uslubiy qo'llanma": "📘",
    "Mustaqil ish": "✍️",
    "Mavzu bo'yicha slayd": "🖥️",
    "Kurs ishi": "📑",
    "Bitiruv malakaviy ishi": "🎓",
    "Magistrlik dissertatsiyasi": "🎖️",
}


def build_categories_keyboard(lang_code):
    rows = [
        ["Dars ishlanmasi", "Maqola"],
        ["Tezis", "Uslubiy qo'llanma"],
        ["Mustaqil ish", "Mavzu bo'yicha slayd"],
        ["Kurs ishi", "Bitiruv malakaviy ishi"],
        ["Magistrlik dissertatsiyasi"],
        ["🌐 Til / Language"],
    ]

    def _label(item):
        translated = tr(item, lang_code)
        emoji = CATEGORY_EMOJIS.get(item)
        return f"{emoji} {translated}" if emoji else translated

    translated_rows = [[_label(item) for item in row] for row in rows]
    return ReplyKeyboardMarkup(translated_rows, resize_keyboard=True)


_ALL_LANGS = ["uz", "ru", "en", "kaa", "kg", "kk", "tg"]
for _canonical, _emoji in CATEGORY_EMOJIS.items():
    for _lc in _ALL_LANGS:
        _translated = tr(_canonical, _lc)
        _labeled = f"{_emoji} {_translated}"
        REVERSE_TRANSLATIONS[_labeled] = _canonical


def build_dars_turi_keyboard(lang_code):
    translated_rows = [[tr(item, lang_code) for item in row] for row in DARS_TURI_KEYBOARD_ROWS]
    return ReplyKeyboardMarkup(translated_rows, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    uid = update.message.from_user.id
    user_lang = get_language(uid)
    context.user_data.clear()
    reply_markup = build_categories_keyboard(user_lang)
    await update.message.reply_text(
        "Assalomu alaykum! Men sizning AI yordamchingizman. Bo'limni tanlang:",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

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
        context.user_data.clear()
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

    # --- Dars ishlanmasi yoki Mavzu bo'yicha slayd tanlanganda — avval turi so'raladi ---
    if text in SUBTYPE_CATEGORIES:
        context.user_data.clear()
        context.user_data['awaiting_dars_turi'] = True
        context.user_data['pending_cat'] = text
        display_cat = tr(text, user_lang)
        await update.message.reply_text(
            f"📚 {display_cat} turini tanlang:",
            reply_markup=build_dars_turi_keyboard(user_lang)
        )
        return

    # --- Foydalanuvchi turini tanladi (Dars ishlanmasi yoki Slayd uchun) ---
    if context.user_data.get('awaiting_dars_turi') and text in DARS_TURI_MAP:
        context.user_data['awaiting_dars_turi'] = False
        pending_cat = context.user_data.get('pending_cat', "Dars ishlanmasi")
        context.user_data['cat'] = pending_cat
        dars_turi_key = DARS_TURI_MAP[text]
        context.user_data['dars_turi'] = dars_turi_key
        context.user_data['custom_price'] = DARS_TURI_PRICES.get(dars_turi_key, PRICES[pending_cat])

        await update.message.reply_text(
            "📝 Mavzuni kiriting:",
            reply_markup=build_categories_keyboard(user_lang)
        )
        return

    # --- Oddiy bo'lim (Maqola, Tezis va h.k.) tanlanganda ---
    if text in PRICES:
        context.user_data.clear()
        context.user_data['cat'] = text
        context.user_data['dars_turi'] = None
        context.user_data['custom_price'] = None
        await update.message.reply_text("📝 Mavzuni kiriting:")
        return

    cat = context.user_data.get('cat')

    # --- Agar to'lov chekini kutayotgan bo'lsak, lekin foydalanuvchi matn yozsa ---
    if context.user_data.get('awaiting_payment_screenshot'):
        await update.message.reply_text(
            "📸 Iltimos, avval to'lov chekining rasmini (screenshot) yuboring."
        )
        return

    if not cat:
        await update.message.reply_text("⚠️ Avval bo'limni tanlang!")
        return

    # --- Mavzu birinchi marta kiritilganda — narx va to'lov ma'lumotlarini beramiz ---
    if not context.user_data.get('pending_topic'):
        price = context.user_data.get('custom_price') or PRICES.get(cat, 0)
        context.user_data['pending_topic'] = text
        context.user_data['awaiting_payment_screenshot'] = True

        await update.message.reply_text(
            f"💳 Kerakli mablag': {price} so'm\n\n"
            f"Karta raqami: {CARD_NUMBER}\n"
            f"Egasi: {CARD_HOLDER}\n\n"
            f"✅ To'lovni amalga oshirib, chek (rasm) yuboring."
        )
        return


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    if not context.user_data.get('awaiting_payment_screenshot'):
        return

    cat = context.user_data.get('cat')
    dars_turi = context.user_data.get('dars_turi')
    topic = context.user_data.get('pending_topic')
    price = context.user_data.get('custom_price') or PRICES.get(cat, 0)
    user_lang = get_language(uid)

    file_id = update.message.photo[-1].file_id

    payment_id = create_payment(
        uid, price, file_id,
        category=cat, dars_turi=dars_turi, topic=topic, language=user_lang
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Chekingiz qabul qilindi va admin tekshiruviga yuborildi.\n"
        "Tasdiqlangach, hujjatingiz tayyorlanib, sizga yuboriladi."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{payment_id}")
        ]
    ])

    username = update.message.from_user.username or "yo'q"
    display_cat = tr(cat, user_lang)
    display_turi = tr_dars_turi_by_key(dars_turi, user_lang) if dars_turi else ""
    turi_line = f"\nTuri: {display_turi}" if display_turi else ""

    caption = (
        f"🆕 Yangi buyurtma\n"
        f"ID: {payment_id}\n"
        f"Foydalanuvchi: {uid} (@{username})\n"
        f"Bo'lim: {display_cat}{turi_line}\n"
        f"Mavzu: {topic}\n"
        f"Summa: {price} so'm"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=caption,
        reply_markup=keyboard
    )


def tr_dars_turi_by_key(dars_turi_key, lang_code):
    """Dars turi kalitidan (masalan 'Ma'ruza') tugma matnini topib, tarjima qiladi."""
    for label, key in DARS_TURI_MAP.items():
        if key == dars_turi_key:
            return tr(label, lang_code)
    return dars_turi_key


async def _generate_and_send(payment_id, admin_message):
    """To'lov tasdiqlangandan so'ng hujjatni generatsiya qilib, faqat fayl
    ko'rinishida foydalanuvchiga yuboradi."""
    payment = get_payment(payment_id)
    if not payment:
        return
    _, user_id, amount, file_id, status, category, dars_turi, topic, language = payment
    language = language or "uz"

    ai_context = f"{category} - {dars_turi}" if dars_turi else category

    bot = admin_message.get_bot()

    try:
        await bot.send_message(chat_id=user_id, text="⏳ Hujjatingiz tayyorlanmoqda, iltimos kuting...")
    except Exception:
        pass

    if is_long_document(category):
        progress = {"idx": 0, "total": 0, "section": ""}

        def _progress_callback(idx, total, section_title):
            progress["idx"] = idx
            progress["total"] = total
            progress["section"] = section_title

        task = asyncio.create_task(
            asyncio.to_thread(generate_long_document, topic, category, _progress_callback, language)
        )
        while not task.done():
            await asyncio.sleep(4)
            if progress["total"]:
                pct = int(progress["idx"] / progress["total"] * 100)
                try:
                    await admin_message.edit_caption(
                        caption=(
                            f"⏳ Tayyorlanmoqda (ID: {payment_id}): "
                            f"{progress['idx']}/{progress['total']} bo'lim ({pct}%)"
                        )
                    )
                except Exception:
                    pass
        resp = await task
    else:
        resp = await asyncio.to_thread(get_ai_response, topic, ai_context, language)

    try:
        if "slayd" in category.lower():
            p = create_pptx(topic[:20], resp)
        else:
            p = create_word(topic[:20], resp)
        with open(p, 'rb') as f:
            await bot.send_document(chat_id=user_id, document=f)
        os.remove(p)
        try:
            await admin_message.edit_caption(caption=f"✅ Tayyor va yuborildi (ID: {payment_id}).")
        except Exception:
            pass
    except Exception as e:
        try:
            await bot.send_message(chat_id=user_id, text=f"❌ Fayl yaratishda xatolik: {e}")
        except Exception:
            pass
        try:
            await admin_message.edit_caption(caption=f"❌ Xatolik yuz berdi (ID: {payment_id}): {e}")
        except Exception:
            pass


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
        await query.edit_message_caption(caption="⚠️ Bu buyurtma topilmadi.")
        return

    _, user_id, amount, file_id, status, category, dars_turi, topic, language = payment

    if status != "pending":
        await query.edit_message_caption(caption=f"ℹ️ Bu buyurtma allaqachon '{status}' holatida.")
        return

    if action == "approve":
        set_payment_status(payment_id, "approved")
        await query.edit_message_caption(
            caption=f"✅ Tasdiqlandi (ID: {payment_id}). Hujjat tayyorlanmoqda..."
        )
        asyncio.create_task(_generate_and_send(payment_id, query.message))

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
    print("V4.0 BOT ISHGA TUSHDI...")
    app.run_polling()
