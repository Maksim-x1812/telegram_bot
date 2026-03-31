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
#ADMIN_ID = 

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE ---
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS user_files (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    topic TEXT,
    file_path TEXT,
    created_at TIMESTAMP
)
""")
conn.commit()

# --- TEXT ---
base_text = """Будь ласка, надішліть на email i.ponomarchuk@adigestore.it:

1. Cognome Nome
2. Indirizzo di residenza
3. Numero di telefono italiano
4. WhatsApp
5. Stato della familia
6. Professione
7. Note

📎 Документи:
{docs}

⬇️ Або надішліть документи прямо тут.
"""

docs_map = {
    "AUTO": "Carta d'identità\nPatente\nLibretto",
    "CASA": "Carta d'identità",
    "SALUTE": "Carta d'identità",
    "ALTRO": "Carta d'identità",
    "VITA": "Carta d'identità",
    "PENSIONE": "Carta d'identità",
    "LUCE/GAS": "Carta d'identità\nBollette"
}

# --- KEYBOARD ---
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
        "Я вітаю Вас в офісі фінансових рішень.\n"
        "Чим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

# --- BUTTON HANDLER ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        context.user_data.clear()
        await query.edit_message_text(
            "Чим можу Вам допомогти?",
            reply_markup=main_menu_keyboard()
        )
        return

    if query.data in ["insurance", "future", "energy"]:
        if query.data == "insurance":
            options = ["AUTO","CASA","SALUTE","ALTRO"]
        elif query.data == "future":
            options = ["VITA","PENSIONE"]
        else:
            options = ["LUCE/GAS"]

        kb = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options]
        kb.append([InlineKeyboardButton("Назад", callback_data="back")])

        await query.edit_message_text("Оберіть:", reply_markup=InlineKeyboardMarkup(kb))
        return

    # --- FINAL SELECTION ---
    topic = query.data
    context.user_data["state"] = "WAITING_FOR_FILES"
    context.user_data["topic"] = topic
    context.user_data["files"] = []

    docs = docs_map.get(topic, "Документи не визначені")

    kb = [
        [InlineKeyboardButton("✅ Завершити", callback_data="done")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]

    await query.edit_message_text(
        f"📌 Тема: {topic}\n\n"
        + base_text.format(docs=docs)
        + "\n\n📎 Надішліть файли тут.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# --- FILE HANDLER ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "WAITING_FOR_FILES":
        await update.message.reply_text("❗ Спочатку оберіть послугу.")
        return

    user = update.message.from_user
    doc = update.message.document
    topic = context.user_data["topic"]

    file = await context.bot.get_file(doc.file_id)

    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{user.id}_{topic}_{doc.file_name}"

    await file.download_to_drive(file_path)

    # Save to DB
    cur.execute(
        """INSERT INTO user_files 
        (user_id, username, topic, file_path, created_at)
        VALUES (%s, %s, %s, %s, %s)""",
        (user.id, user.username, topic, file_path, datetime.now())
    )
    conn.commit()

    context.user_data["files"].append(file_path)

    await update.message.reply_text(
        f"✅ Файл отримано ({len(context.user_data['files'])})\n"
        "Надішліть ще або натисніть «Завершити»."
    )

# --- FINISH ---
async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data != "done":
        return

    user = query.from_user
    topic = context.user_data.get("topic")
    files = context.user_data.get("files", [])

    if not files:
        await query.answer("❗ Ви не надіслали файли", show_alert=True)
        return

    # Notify admin
    msg = (
        f"📥 Новий клієнт\n"
        f"👤 @{user.username}\n"
        f"🆔 {user.id}\n"
        f"📂 {topic}\n"
        f"📎 {len(files)} файлів"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

    # Send files to admin
    for f in files:
        try:
            await context.bot.send_document(chat_id=ADMIN_ID, document=open(f, "rb"))
        except Exception as e:
            print("Error sending file:", e)

    context.user_data.clear()

    await query.edit_message_text(
        "✅ Дякую! Я зв'яжусь з Вами 📞",
        reply_markup=main_menu_keyboard()
    )

# --- TEXT REPLY ---
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "WAITING_FOR_FILES":
        await update.message.reply_text(
            "📎 Будь ласка, надішліть документи або натисніть «Завершити»."
        )
    else:
        await update.message.reply_text(
            "Будь ласка, скористайтесь меню 👇",
            reply_markup=main_menu_keyboard()
        )

# --- MAIN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(finish, pattern="^done$"))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

print("🤖 Bot is running...")
app.run_polling()
"""while True:
    try:
        app.run_polling()
    except Exception as e:
        print(f"Error: {e}")"""
