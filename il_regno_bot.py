import logging
import os
import json
import random
import asyncio
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import( ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, JobQueue

)

from config import TOKEN, DEEPSEEK_API_KEY, GROUP_CHAT_ID

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
def chiedi_a_deepseek(prompt):
    try:
        res = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            }
        )

        print("✅ DeepSeek status:", res.status_code, flush=True)
        print("📦 DeepSeek response:", res.text, flush=True)

        return res.json().get("choices", [{}])[0].get("message", {}).get("content", "[Errore risposta DeepSeek]")
    except Exception as e:
        print("❌ DeepSeek Exception:", e, flush=True)
        return f"[Errore DeepSeek: {e}]"


def is_sovrano(user_id):
    return user_id == regno["re"]["id"] or user_id == regno["regina"]["id"]

async def nomina_re(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    regno["re"] = {"id": user.id, "nome": user.full_name}
    salva_stato()
    await update.message.reply_text(f"👑 {user.full_name} è stato nominato Re!")

async def nomina_regina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    regno["regina"] = {"id": user.id, "nome": user.full_name}
    salva_stato()
    await update.message.reply_text(f"👸 {user.full_name} è stata nominata Regina!")

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
    prompt = f"Scrivi un discorso regale in un regno medievale. La soddisfazione è {regno['soddisfazione']} ({mood})."
    testo = chiedi_a_deepseek(prompt)
    regno["discorsi"].append(testo)
    salva_stato()
    await update.message.reply_markdown(f"🎙 *Discorso:*\n\n{testo}")

from telegram import Chat
from telegram.ext import MessageHandler, filters

async def rileva_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat: Chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        await update.message.reply_text(
            f"🤖 Chat ID rilevato: `{chat.id}`",
            parse_mode="Markdown"
        )

async def evento_automatico(context: ContextTypes.DEFAULT_TYPE):
    evento = random.choice(["guerra", "carestia", "festa", "miracolo"])
    impatto = random.randint(-20, 20)
    regno["soddisfazione"] = max(1, min(100, regno["soddisfazione"] + impatto))
    prompt = f"Scrivi un evento medievale di tipo {evento}. Soddisfazione: {regno['soddisfazione']}."
    testo = chiedi_a_deepseek(prompt)  # ✅ testo generato
    regno["eventi"].append(f"{evento} (auto)")
    salva_stato()
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=f"📜 *Evento automatico: {evento.title()}*\n\n{testo}",  # ✅ lo usi qui
        parse_mode="Markdown"
    )


def main():
    print("✅ Entrato in main()", flush=True)

    logging.basicConfig(level=logging.INFO)
    carica_stato()
    
    app = ApplicationBuilder().token(TOKEN).build()
    print("✅ Costruita l'applicazione Telegram", flush=True)

    app.add_handler(CommandHandler("statistiche", statistiche))
    app.add_handler(CommandHandler("tasse", tasse))
    app.add_handler(CommandHandler("discorso", discorso))
    app.add_handler(CommandHandler("nomina_re", nomina_re))
    app.add_handler(CommandHandler("nomina_regina", nomina_regina))
    app.add_handler(CommandHandler("chi_comanda", chi_comanda))
    app.add_handler(MessageHandler(filters.ALL, rileva_chat))

    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(evento_automatico, interval=900, first=30)

    print("🤖 Il Regno è attivo.", flush=True)

    app.run_polling()

if __name__ == "__main__":
    main()

