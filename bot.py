# main.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import asyncio

TOKEN = "8735617587:AAG7bXUY4gjHWK0vxoyJnz-AFExodXp3B5s"

app = ApplicationBuilder().token("TOKEN").build()
# Текст та документи як у нашому робочому варіанті
base_text = """Будь ласка, з метою захисту персональних даних надішліть електронною поштою на адресу i.ponomarchuk@adigestore.it необхідну інформацію:

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

def main_menu_keyboard():
    return InlineKeyboardMarkup([
    [InlineKeyboardButton("СТРАХУВАННЯ", callback_data="insurance")],
    [InlineKeyboardButton("ЗАХИСТ МАЙБУТНЬОГО", callback_data="future")],
    [InlineKeyboardButton("ЕКОНОМІЯ LUCE/GAS", callback_data="energy")]
    ])

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
        kb.append([InlineKeyboardButton("Назад", callback_data="back")])
        await query.edit_message_text("Оберіть вид страхування:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif query.data == "future":
        kb = [[InlineKeyboardButton(name, callback_data=name)] for name in ["VITA","PENSIONE"]]
        kb.append([InlineKeyboardButton("Назад", callback_data="back")])
        await query.edit_message_text("Оберіть програму:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif query.data == "energy":
        kb = [[InlineKeyboardButton("LUCE/GAS", callback_data="LUCE/GAS")]]
        kb.append([InlineKeyboardButton("Назад", callback_data="back")])
        await query.edit_message_text("Оберіть тему:", reply_markup=InlineKeyboardMarkup(kb))
    
    else:
        docs = docs_map.get(query.data, "Документи не визначені")
        kb = [[InlineKeyboardButton("Назад", callback_data="back")]]
        await query.edit_message_text(
        f"Тема: {query.data}\n\n" + base_text.format(docs=docs),
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    "Дякую за звернення. Після відправки листа я зв'яжусь із Вами телефоном для персональної консультації з Вашого питання.\nІрина Гертнер"
    )
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

app.run_polling()