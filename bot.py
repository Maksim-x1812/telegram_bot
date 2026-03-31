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
ADMIN_ID = 464552562  # Your admin ID

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE ---
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Create tables
cur.execute("""
CREATE TABLE IF NOT EXISTS user_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    topic TEXT,
    cognome_nome TEXT,
    indirizzo TEXT,
    telefono TEXT,
    whatsapp TEXT,
    stato_familia TEXT,
    professione TEXT,
    note TEXT,
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

# --- QUESTIONS ---
questions = [
    ("cognome_nome", "1. Введіть ваше ім'я та прізвище:"),
    ("indirizzo", "2. Введіть вашу адресу проживання:"),
    ("telefono", "3. Введіть номер телефону італійський:"),
    ("whatsapp", "4. Введіть ваш WhatsApp:"),
    ("stato_familia", "5. Введіть ваш сімейний стан:"),
    ("professione", "6. Введіть вашу професію:"),
    ("note", "7. Будь-які додаткові нотатки:")
]

docs_map = {
    "AUTO": "📄 Потрібно надіслати:\n- Carta d'identità\n- Patente\n- Libretto",
    "CASA": "📄 Потрібно надіслати:\n- Carta d'identità",
    "SALUTE": "📄 Потрібно надіслати:\n- Carta d'identità",
    "ALTRO": "📄 Потрібно надіслати:\n- Carta d'identità",
    "VITA": "📄 Потрібно надіслати:\n- Carta d'identità",
    "PENSIONE": "📄 Потрібно надіслати:\n- Carta d'identità",
    "LUCE/GAS": "📄 Потрібно надіслати:\n- Carta d'identità\n- Bollette"
}

# --- MENUS ---
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
        "Мене звуть Ірина Гертнер.\nЧим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

# ---------------------------------------------------------
# FIXED: FINISH handler first so that button() does NOT eat it
# ---------------------------------------------------------
async def finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("state") != "WAITING_FOR_FILES":
        await query.answer("Спочатку завершіть форму.", show_alert=True)
        return

    user = query.from_user
    topic = context.user_data["topic"]
    answers = context.user_data.get("answers", {})
    files = context.user_data.get("files", [])

    # Save form
    cur.execute("""
        INSERT INTO user_requests
        (user_id, username, topic, cognome_nome, indirizzo, telefono, whatsapp, stato_familia, professione, note, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        user.id, user.username, topic,
        answers.get("cognome_nome"),
        answers.get("indirizzo"),
        answers.get("telefono"),
        answers.get("whatsapp"),
        answers.get("stato_familia"),
        answers.get("professione"),
        answers.get("note"),
        datetime.now()
    ))
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
        f"👤 @{user.username}\n🆔 {user.id}\n"
        f"📂 {topic}\n📎 {len(files)} файлів"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

    for f in files:
        try:
            await context.bot.send_document(chat_id=ADMIN_ID, document=open(f, "rb"))
        except:
            pass

    context.user_data.clear()

    await query.edit_message_text(
        "✅ Дякую! Дані та файли отримані.\n\nЧим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

# ---------------------------------------------------------
# BUTTON HANDLER — corrected so "finish" is ignored
# ---------------------------------------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # prevent finish from being processed here
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

    # final topic (AUTO, VITA etc)
    topic = query.data
    context.user_data["topic"] = topic
    context.user_data["answers"] = {}
    context.user_data["current_q"] = 0
    context.user_data["files"] = []
    context.user_data["state"] = "FILLING_FORM"

    required_docs = docs_map.get(topic, "Документи не потрібні.")

    await query.edit_message_text(
        f"📌 Тема: {topic}\n\n"
        f"{required_docs}\n\n"
        "Тепер введемо ваші дані."
    )

    await query.message.reply_text(questions[0][1])

# ---------------------------------------------------------
# HANDLE TEXT INPUT
# ---------------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")

    if state == "FILLING_FORM":
        idx = context.user_data["current_q"]
        key, _ = questions[idx]
        context.user_data["answers"][key] = update.message.text
        idx += 1

        if idx < len(questions):
            context.user_data["current_q"] = idx
            await update.message.reply_text(questions[idx][1])
        else:
            context.user_data["state"] = "WAITING_FOR_FILES"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Завершити", callback_data="finish")],
                [InlineKeyboardButton("Назад", callback_data="back")]
            ])
            await update.message.reply_text(
                "Дякую! Тепер надішліть документи (можна кілька файлів).",
                reply_markup=kb
            )

    elif state == "WAITING_FOR_FILES":
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

# ---------------------------------------------------------
# HANDLE DOCUMENTS
# ---------------------------------------------------------
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "WAITING_FOR_FILES":
        await update.message.reply_text("❗ Спочатку оберіть послугу та заповніть дані.")
        return

    user = update.message.from_user
    doc = update.message.document
    topic = context.user_data["topic"]

    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{user.id}_{topic}_{doc.file_name}"

    file = await update.bot.get_file(doc.file_id)
    await file.download_to_drive(file_path)

    context.user_data["files"].append(file_path)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Завершити", callback_data="finish")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ])
    await update.message.reply_text(f"✅ Файл отримано ({len(context.user_data['files'])})", reply_markup=kb)

# --- MAIN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

# IMPORTANT: finish goes FIRST
app.add_handler(CallbackQueryHandler(finish_callback, pattern="^finish$"), group=0)

# all other buttons
app.add_handler(CallbackQueryHandler(button), group=1)

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("Bot is running...")
app.run_polling()


"""while True:
    try:
        app.run_polling()
    except Exception as e:
        print(f"Error: {e}")"""
