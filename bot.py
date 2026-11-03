import os
import logging
from collections import defaultdict, deque
 
from openai import AsyncOpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
 
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agro-bot")
 
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
 
# Render avtomatik beradi
PORT = int(os.getenv("PORT", "10000"))
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "")
 
SYSTEM_PROMPT = (
    "Sen O'zbekiston qishloq xo'jaligi bo'yicha tajribali agronom-maslahatchisan. "
    "Paxta, makkajo'xori, bug'doy, sabzavot, bog'dorchilik, sug'orish, o'g'itlash, "
    "zararkunanda va kasalliklarga qarshi kurash, tuproq, hosildorlik haqida savollarga "
    "javob berasan. Foydalanuvchi qaysi tilda yozsa, shu tilda javob ber "
    "(asosan o'zbek tilida). Javoblar sodda, aniq va amaliy bo'lsin, qadamma-qadam "
    "tushuntir. Pestitsid va o'g'it dozalari haqida aniq raqam aytsang, mahsulot "
    "yorlig'idagi ko'rsatmaga amal qilish va mahalliy agronom bilan tekshirish "
    "kerakligini eslat. Qishloq xo'jaligiga aloqasi yo'q savollarga muloyimlik bilan "
    "'Men faqat agrar masalalarda yordam beraman' deb javob ber."
)
 
client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
 
# Har bir foydalanuvchi uchun oxirgi 6 ta xabar (suhbat xotirasi)
history = defaultdict(lambda: deque(maxlen=6))
 
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! 🌱 Men agrar yordamchi botman.\n\n"
        "Paxta, makkajo'xori, bug'doy, sabzavot va boshqa ekinlar haqida "
        "savolingizni yozing.\n\n"
        "/yangi - suhbatni yangidan boshlash"
    )
 
 
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history[update.effective_user.id].clear()
    await update.message.reply_text("Suhbat tozalandi. Yangi savol bering.")
 
 
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
 
    history[user_id].append({"role": "user", "content": text})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history[user_id]]
 
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=900,
            temperature=0.5,
        )
        reply = resp.choices[0].message.content or "Javob olinmadi, qayta urinib ko'ring."
    except Exception as e:
        log.exception("Groq xatosi: %s", e)
        history[user_id].pop()
        reply = "Kechirasiz, hozir javob bera olmadim. Birozdan keyin qayta urinib ko'ring."
 
    history[user_id].append({"role": "assistant", "content": reply})
 
    # Telegram limiti 4096 belgi
    for i in range(0, len(reply), 4000):
        await update.message.reply_text(reply[i : i + 4000])
 
 
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yangi", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
 
    if BASE_URL:
        # Render'da: webhook rejimi
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{BASE_URL}/{TELEGRAM_TOKEN}",
        )
    else:
        # Kompyuteringizda sinash uchun: polling rejimi
        app.run_polling()
 
 
if __name__ == "__main__":
    main()
 
