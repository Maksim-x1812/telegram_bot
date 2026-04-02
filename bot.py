import os
import logging
import psycopg2
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 464552562

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE ---
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS user_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    topic TEXT,
    created_at TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS user_files (
    id SERIAL PRIMARY KEY,
    request_id INT,
    file_path TEXT,
    created_at TIMESTAMP
)
""")

conn.commit()

# --- QUESTIONS (NOW JUST DISPLAYED) ---
questions_text = """
📝 Дані, які потрібно заповнити у формі:

1. Ім'я та прізвище
2. Адреса проживання
3. Номер телефону (італійський)
4. WhatsApp
5. Сімейний стан
6. Професія
7. Додаткові нотатки
"""

# --- DOCUMENTS ---
docs_map = {
    "AUTO": "📄 Потрібно надіслати:\n- Carta d'identità\n- Patente\n- Libretto",
    "CASA": "📄 Потрібно надіслати:\n- Carta d'identità",
    "SALUTE": "📄 Потрібно надіслати:\n- Carta d'identità",
    "ALTRO": "📄 Потрібно надіслати:\n- Carta d'identità",
    "VITA": "📄 Потрібно надіслати:\n- Carta d'identità",
    "PENSIONE": "📄 Потрібно надіслати:\n- Carta d'identità",
    "LUCE/GAS": "📄 Потрібно надіслати:\n- Carta d'identità\n- Bollette"
}

# --- GOOGLE FORMS ---
form_links = {
    "AUTO": "https://forms.gle/your_auto_form",
    "CASA": "https://forms.gle/your_casa_form",
    "SALUTE": "https://forms.gle/your_salute_form",
    "ALTRO": "https://forms.gle/your_altro_form",
    "VITA": "https://forms.gle/your_vita_form",
    "PENSIONE": "https://forms.gle/your_pensione_form",
    "LUCE/GAS": "https://forms.gle/your_energy_form"
}

# --- MENU ---
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("СТРАХУВАННЯ", callback_data="insurance")],
        [InlineKeyboardButton("ЗАХИСТ МАЙБУТНЬОГО", callback_data="future")],
        [InlineKeyboardButton("ЕКОНОМІЯ LUCE/GAS", callback_data="energy")]
    ])

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Мене звуть Ірина Гертнер.\n"
        "Я вітаю Вас в офісі фінансових рішень для українців в Італії\n"
        "Чим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

# --- FINISH ---
async def finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("state") != "WAITING_FOR_FILES":
        await query.answer("Спочатку оберіть послугу.", show_alert=True)
        return

    user = query.from_user
    topic = context.user_data["topic"]
    files = context.user_data.get("files", [])

    # Save request
    cur.execute("""
        INSERT INTO user_requests (user_id, username, topic, created_at)
        VALUES (%s,%s,%s,%s)
        RETURNING id
    """, (user.id, user.username, topic, datetime.now()))
    request_id = cur.fetchone()[0]
    conn.commit()

    # Save files
    for f in files:
        cur.execute("""
        INSERT INTO user_files (request_id, file_path, created_at)
        VALUES (%s,%s,%s)
        """, (request_id, f, datetime.now()))
    conn.commit()

    # Notify admin
    msg = (
        f"📥 Новий клієнт\n"
        f"👤 @{user.username}\n"
        f"🆔 {user.id}\n"
        f"📂 {topic}\n"
        f"📎 {len(files)} файлів"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

    for f in files:
        try:
            await context.bot.send_document(chat_id=ADMIN_ID, document=open(f, "rb"))
        except:
            pass

    context.user_data.clear()

    await query.edit_message_text(
        "✅ Дякую! Дані отримані.\n\nЧим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

# --- BUTTONS ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "finish":
        return

    if query.data == "back":
        context.user_data.clear()
        await query.edit_message_text(
            "Чим можу Вам допомогти?",
            reply_markup=main_menu_keyboard()
        )
        return

    # categories
    if query.data in ["insurance", "future", "energy"]:
        if query.data == "insurance":
            options = ["AUTO", "CASA", "SALUTE", "ALTRO"]
        elif query.data == "future":
            options = ["VITA", "PENSIONE"]
        else:
            options = ["LUCE/GAS"]

        kb = [[InlineKeyboardButton(o, callback_data=o)] for o in options]
        kb.append([InlineKeyboardButton("Назад", callback_data="back")])

        await query.edit_message_text("Оберіть категорію:", reply_markup=InlineKeyboardMarkup(kb))
        return

    # topic selected
    topic = query.data
    context.user_data["topic"] = topic
    context.user_data["files"] = []
    context.user_data["state"] = "WAITING_FOR_FILES"

    required_docs = docs_map.get(topic, "")
    form_link = form_links.get(topic, "https://forms.gle/default")

    await query.edit_message_text(
        f"📌 Тема: {topic}\n\n"
        f"{questions_text}\n\n"
        f"📝 Заповніть форму:\n{form_link}\n\n"
        f"{required_docs}\n\n"
        "❗ Після заповнення форми надішліть документи тут."
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Завершити", callback_data="finish")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ])

    await query.message.reply_text(
        "📎 Очікую на ваші файли 👇",
        reply_markup=kb
    )

# --- HANDLE TEXT ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "WAITING_FOR_FILES":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Завершити", callback_data="finish")],
            [InlineKeyboardButton("Назад", callback_data="back")]
        ])
        await update.message.reply_text(
            "📎 Надішліть файли або натисніть «Завершити».",
            reply_markup=kb
        )
    else:
        await update.message.reply_text(
            "Будь ласка, скористайтесь меню 👇",
            reply_markup=main_menu_keyboard()
        )

# --- HANDLE DOCUMENTS ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "WAITING_FOR_FILES":
        await update.message.reply_text("❗ Спочатку оберіть послугу.")
        return

    user = update.message.from_user
    doc = update.message.document
    topic = context.user_data["topic"]

    await update.message.reply_text("⏳ Отримую файл...")

    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{user.id}_{topic}_{doc.file_name}"

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(file_path)

        context.user_data.setdefault("files", []).append(file_path)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Завершити", callback_data="finish")],
            [InlineKeyboardButton("Назад", callback_data="back")]
        ])

        await update.message.reply_text(
            f"✅ Файл збережено ({len(context.user_data['files'])})",
            reply_markup=kb
        )

    except Exception as e:
        logging.error(f"Download error: {e}")
        await update.message.reply_text("❌ Помилка при отриманні файлу.")

# --- MAIN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CallbackQueryHandler(finish_callback, pattern="^finish$"), group=0)
app.add_handler(CallbackQueryHandler(button), group=1)

app.add_handler(CommandHandler("start", start))

app.add_handler(MessageHandler(filters.Document.ALL, handle_document), group=0)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text), group=1)

print("Bot is running...")
app.run_polling()


"""while True:
    try:
        app.run_polling()
    except Exception as e:
        print(f"Error: {e}")"""
