import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- QUESTIONS TEXT ---
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
    "AUTO": "https://docs.google.com/forms/d/e/1FAIpQLSfMBJRW42yIYxjdxT0tICiQTptlykHze6z2aZWgPjFq27g9Qw/viewform?usp=header",
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
    await update.message.reply_text(
        "Мене звуть Ірина Гертнер.\n"
        "Я вітаю Вас в офісі фінансових рішень для українців в Італії\n\n"
        "Чим можу Вам допомогти?",
        reply_markup=main_menu_keyboard()
    )

# --- BUTTON HANDLER ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back":
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

        await query.edit_message_text(
            "Оберіть категорію:",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    # topic selected
    topic = query.data
    required_docs = docs_map.get(topic, "")
    form_link = form_links.get(topic, "https://forms.gle/default")

    await query.edit_message_text(
        f"📌 Тема: {topic}\n\n"
        f"{questions_text}\n\n"
        f"{required_docs}\n\n"
        f"📝 Заповніть форму:\n{form_link}\n\n"
        "❗ Після заповнення форми підготуйте документи — з вами зв'яжуться."
    )

# --- HANDLE RANDOM TEXT ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Будь ласка, скористайтесь меню 👇",
        reply_markup=main_menu_keyboard()
    )

# --- MAIN ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("Bot is running...")
app.run_polling()


"""while True:
    try:
        app.run_polling()
    except Exception as e:
        print(f"Error: {e}")"""
