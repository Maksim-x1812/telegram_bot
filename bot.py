import os
import asyncio
import logging
import psycopg2
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

#python -m pip install --upgrade pip
# pip install python-telegram-bot==20.7
# pip3 install python-telegram-bot==20.7
#$env:BOT_TOKEN="123456:ABC..."
#python main.py

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

print("ALL ENV:", os.environ)

BOT_TOKEN = os.getenv("BOT_TOKEN")
#BOT_TOKEN = "8735617587:AAEc6beNLSR7joTPA51IaPrhw__Rw2xyXSM"

#print("DEBUG TOKEN:", BOT_TOKEN)
"""if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")"""

DATABASE_URL = os.getenv("DATABASE_URL")

print("DEBUG DB:", DATABASE_URL)
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found")



conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS user_files (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    file_id TEXT,
    file_name TEXT,
    created_at TIMESTAMP
)
""")
conn.commit()

# --- TEXT ---
base_text = """Будь ласка, з метою захисту персональних данихнадішліть електронною поштою на адресу i.ponomarchuk@adigestore.it необхідну інформацію:

1. Cognome Nome
2. Indirizzo di residenza
3. Numero di telefono italiano
4. WhatsApp
5. Stato della familia
6. Professione
7. Note

Долучіть необхідні документи:
{docs}

Для пришвидшення обробки інформації зазначте тему звернення в назві листа.
"""

docs_map = {
    "AUTO": "Carta d'identità fronte/retro\nPatente fronte/retro\nLibretto fronte/retro\nCertificato Ucraino MTSBU o Libretto della macchina italiana",
    "CASA": "Carta d'identità fronte/retro",
    "SALUTE": "Carta d'identità fronte/retro",
    "ALTRO": "Carta d'identità fronte/retro",
    "VITA": "Carta d'identità fronte/retro",
    "PENSIONE": "Carta d'identità fronte/retro",
    "LUCE/GAS": "Carta d'identità fronte/retro\nBolletto LUCE\nBolletto GAS"
}

# --- KEYBOARD ---
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("СТРАХУВАННЯ", callback_data="insurance")],
        [InlineKeyboardButton("ЗАХИСТ МАЙБУТНЬОГО", callback_data="future")],
        [InlineKeyboardButton("ЕКОНОМІЯ LUCE/GAS", callback_data="energy")]
    ])

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Мене звуть Ірина Гертнер.\nЯ вітаю Вас в офісі фінансових рішень для українців в Італії.\nЧим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        await query.edit_message_text(
            "Мене звуть Ірина Гертнер.\nЯ вітаю Вас в офісі фінансових рішень для українців в Італії.\nЧим можу Вам допомогти?",
            reply_markup=main_menu_keyboard()
        )
        return

    if query.data == "insurance":
        kb = [[InlineKeyboardButton(name, callback_data=name)] for name in ["AUTO","CASA","SALUTE","ALTRO"]]
    elif query.data == "future":
        kb = [[InlineKeyboardButton(name, callback_data=name)] for name in ["VITA","PENSIONE"]]
    elif query.data == "energy":
        kb = [[InlineKeyboardButton("LUCE/GAS", callback_data="LUCE/GAS")]]
    else:
        docs = docs_map.get(query.data, "Документи не визначені")
        kb = [[InlineKeyboardButton("Назад", callback_data="back")]]
        await query.edit_message_text(
            f"Тема: {query.data}\n\n" + base_text.format(docs=docs),
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    kb.append([InlineKeyboardButton("Назад", callback_data="back")])
    await query.edit_message_text("Оберіть:", reply_markup=InlineKeyboardMarkup(kb))

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Дякую за звернення. Після відправки листа я зв'яжусь із Вами телефоном для персональної консультації з Вашого питання.\nІрина Гертнер"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Надсилаючи файли, ви погоджуєтесь на обробку персональних даних.\nВаші дані використовуються лише для обробки запиту.")
    user = update.message.from_user
    doc = update.message.document

    user_id = user.id
    username = user.username
    file_id = doc.file_id
    file_name = doc.file_name

    file = await context.bot.get_file(file_id)

    os.makedirs("downloads", exist_ok=True)

    await file.download_to_drive(f"downloads/{file_name}")

    
    # Save to DB
    cur.execute(
        "INSERT INTO user_files (user_id, username, file_id, file_name, created_at) VALUES (%s, %s, %s, %s, %s)",
        (user_id, username, file_id, file_name, datetime.now())
    )
    conn.commit()

    await update.message.reply_text("Файл отримано та збережено ✅")

async def download_file(context, file_id, file_name):
    file = await context.bot.get_file(file_id)
    await file.download_to_drive(file_name)

# --- MAIN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

app.run_polling()
"""while True:
    try:
        app.run_polling()
    except Exception as e:
        print(f"Error: {e}")"""
