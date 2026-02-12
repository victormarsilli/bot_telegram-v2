import os
import asyncio
from flask import Flask, request
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

# Variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
db = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Operativo 🏴‍☠️"

@app.route('/api/index', methods=['POST'])
async def bot_handler():  # Mantenemos el async aquí porque ya pusimos flask[async]
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        user = update.effective_user
        try:
            db.table("jugadores").upsert({"user_id": user.id, "nombre": user.first_name}).execute()
        except: pass
        
        url_app = f"https://{request.host}/"
        keyboard = [[InlineKeyboardButton("🎁 ABRIR COFRE", web_app=WebAppInfo(url=url_app))]]
        await update.message.reply_text(f"¡Hola {user.first_name}! 🏴‍☠️", reply_markup=InlineKeyboardMarkup(keyboard))

    bot_app.add_handler(CommandHandler("start", start))
    
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)
        
    return "ok", 200
