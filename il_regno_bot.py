import logging
import os
import json
import random
import asyncio
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import( ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, JobQueue

)

from config import TOKEN, GEMINI_API_KEY, GROUP_CHAT_ID
GROUP_CHAT_ID = None
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)


STATE_FILE = "regno.json"
EVENTI_POSSIBILI = ["carestia", "guerra", "festa", "epidemia", "miracolo"]
regno = {
    "soddisfazione": 75,
    "tasse": 10,
    "oro": 1000,
    "popolazione": 500,
    "eventi": [],
    "costruzioni": [],
    "discorsi": [],
    "re": {"id": None, "nome": None},
    "regina": {"id": None, "nome": None}
}
votazioni_attive = {}

def salva_stato():
    with open(STATE_FILE, "w") as f:
        json.dump(regno, f, indent=2)

def carica_stato():
    global regno
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            regno = json.load(f)

def chiedi_a_gemini(prompt):
    try:
        model = genai.GenerativeModel("gemma-3-27b-it")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("❌ Errore Gemini:", e, flush=True)
        return f"[Errore risposta Gemini: {e}]"


def is_sovrano(user_id):
    return user_id == regno["re"]["id"] or user_id == regno["regina"]["id"]

async def nomina_re(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # ✅ 1. Se rispondi a un messaggio
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        regno["re"] = {"id": user.id, "nome": user.full_name}
        salva_stato()
        await update.message.reply_text(f"👑 {user.full_name} è stato nominato Re!")
        return

    # ✅ 2. Se usi @username
    if context.args:
        username = context.args[0].lstrip("@").lower()
        try:
            members = await context.bot.get_chat_administrators(chat.id)
            for m in members:
                if m.user.username and m.user.username.lower() == username:
                    regno["re"] = {"id": m.user.id, "nome": m.user.full_name}
                    salva_stato()
                    await update.message.reply_text(f"🤴 {m.user.full_name} è stato nominato Re!")
                    return
            await update.message.reply_text("❌ Utente non trovato nel gruppo.")
        except Exception as e:
            await update.message.reply_text("❌ Errore durante la nomina.")
            print(f"Errore nomina_re: {e}", flush=True)
        return
       
    # ⛔ Nessun argomento e nessuna risposta
    await update.message.reply_text("❗ Usa il comando rispondendo a un messaggio o scrivi: /nomina_re @username")


async def nomina_regina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # ✅ 1. Se rispondi a un messaggio
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        regno["regina"] = {"id": user.id, "nome": user.full_name}
        salva_stato()
        await update.message.reply_text(f"👸 {user.full_name} è stata nominata Regina!")
        return

    # ✅ 2. Se usi @username
    if context.args:
        username = context.args[0].lstrip("@").lower()
        try:
            members = await context.bot.get_chat_administrators(chat.id)
            for m in members:
                if m.user.username and m.user.username.lower() == username:
                    regno["regina"] = {"id": m.user.id, "nome": m.user.full_name}
                    salva_stato()
                    await update.message.reply_text(f"👸 {m.user.full_name} è stata nominata Regina!")
                    return
            await update.message.reply_text("❌ Utente non trovato nel gruppo.")
        except Exception as e:
            await update.message.reply_text("❌ Errore durante la nomina.")
            print(f"Errore nomina_regina: {e}", flush=True)
        return
        
    # ⛔ Nessun argomento e nessuna risposta
    await update.message.reply_text("❗ Usa il comando rispondendo a un messaggio o scrivi: /nomina_regina @username")


async def chi_comanda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    re = regno["re"]["nome"] or "Nessuno"
    regina = regno["regina"]["nome"] or "Nessuna"
    await update.message.reply_text(f"👑 Re: {re}\n👸 Regina: {regina}")

async def statistiche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stato = (
        f"📊 *Statistiche del Regno*\n"
        f"👑 Soddisfazione: {regno['soddisfazione']}/100\n"
        f"💰 Oro: {regno['oro']}\n"
        f"📈 Tasse: {regno['tasse']}%\n"
        f"🧍‍♂️ Popolazione: {regno['popolazione']}\n"
        f"🏗 Costruzioni: {', '.join(regno['costruzioni']) or 'Nessuna'}\n"
        f"⚔️ Eventi recenti: {', '.join(regno['eventi'][-3:]) or 'Nessuno'}"
    )
    await update.message.reply_markdown(stato)

async def tasse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_sovrano(user_id):
        await update.message.reply_text("Solo il Re o la Regina possono cambiare le tasse.")
        return
    try:
        livello = int(context.args[0])
        regno['tasse'] = max(0, min(livello, 100))
        regno['soddisfazione'] -= int(livello / 10)
        salva_stato()
        await update.message.reply_text(f"Tasse impostate al {livello}%.")
    except:
        await update.message.reply_text("Uso corretto: /tasse [livello]")

async def discorso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_sovrano(user_id):
        await update.message.reply_text("Solo il Re o la Regina possono fare discorsi.")
        return
    mood = "felice" if regno["soddisfazione"] >= 70 else "neutrale" if regno["soddisfazione"] >= 40 else "rivolta"
    prompt = f"Genera direttamente un discorso regale ambientato in un regno medievale, senza introduzioni o saluti. La soddisfazione è {regno['soddisfazione']} ({mood})."
    testo = chiedi_a_gemini(prompt)
    regno["discorsi"].append(testo)
    salva_stato()
    await update.message.reply_markdown(f"🎙 *Discorso:*\n\n{testo}")

from telegram import Chat
from telegram.ext import MessageHandler, filters

chat_id_rilevato = False

async def rileva_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GROUP_CHAT_ID, chat_id_rilevato

    if not chat_id_rilevato:
        GROUP_CHAT_ID = update.effective_chat.id
        print(f"Chat ID Rilevato: {GROUP_CHAT_ID}", flush=True)
        chat_id_rilevato = True

async def evento_automatico(context: ContextTypes.DEFAULT_TYPE):
    evento = random.choice(["guerra", "carestia", "festa", "miracolo"])
    impatto = random.randint(-20, 20)
    regno["soddisfazione"] = max(1, min(100, regno["soddisfazione"] + impatto))
    prompt = f"Scrivi solo l'evento medievale di tipo {evento}, senza introduzioni o conclusioni. Soddisfazione: {regno['soddisfazione']}."
    testo = chiedi_a_gemini(prompt) # ✅ testo generato
    regno["eventi"].append(f"{evento} (auto)")
    salva_stato()
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=f"📜 *Evento automatico: {evento.title()}*\n\n{testo}",  # ✅ lo usi qui
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/statistiche - Mostra le statistiche del Regno\n"
        "/tasse - Modifica le tasse\n"
        "/discorso - Fai un discorso regale\n"
        "/nomina_re - Nomina un Re\n"
        "/nomina_regina - Nomina una Regina\n"
        "/chi_comanda - Mostra Re e Regina\n"
        "/help - Mostra questo messaggio"
    )
    await update.message.reply_text(help_text)

async def imposta_comandi(app):
    await app.bot.set_my_commands([
        ("statistiche", "Mostra le statistiche del Regno"),
        ("tasse", "Modifica le tasse"),
        ("discorso", "Fai un discorso regale"),
        ("nomina_re", "Nomina un Re"),
        ("nomina_regina", "Nomina una Regina"),
        ("chi_comanda", "Chi comanda nel Regno"),
        ("help", "Mostra l'elenco dei comandi")
    ])

def main():
    print("✅ Entrato in main()", flush=True)

    logging.basicConfig(level=logging.INFO)
    carica_stato()

    app = ApplicationBuilder().token(TOKEN).post_init(imposta_comandi).build()  # ✅ QUI

    print("✅ Costruita l'applicazione Telegram", flush=True)

    app.add_handler(CommandHandler("statistiche", statistiche))
    app.add_handler(CommandHandler("tasse", tasse))
    app.add_handler(CommandHandler("discorso", discorso))
    app.add_handler(CommandHandler("nomina_re", nomina_re))
    app.add_handler(CommandHandler("nomina_regina", nomina_regina))
    app.add_handler(CommandHandler("chi_comanda", chi_comanda))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.ALL, rileva_chat))

    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(evento_automatico, interval=900, first=30)

    print("🤖 Il Regno è attivo.", flush=True)

    app.run_polling()

if __name__ == "__main__":
    main()


