import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

#python -m pip install --upgrade pip
# pip install python-telegram-bot==20.7
# pip3 install python-telegram-bot==20.7


BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- TEXT ---
base_text = """Будь ласка, з метою захисту персональних даних...
{docs}
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
        "Мене звуть Ірина Гертнер...\nЧим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        await query.edit_message_text(
            "Мене звуть Ірина Гертнер...\nЧим можу Вам допомогти?",
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
        "Дякую за звернення..."
    )

# --- MAIN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

app.run_polling()