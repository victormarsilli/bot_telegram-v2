import os
import asyncio
import json
from flask import Flask, request, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

# Configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
db = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# --- EL JUEGO (HTML) ---
HTML_JUEGO = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background: #1a1a1a; color: white; text-align: center; font-family: sans-serif; }
        .puntos { font-size: 40px; color: #ffd700; margin-top: 50px; }
        .chest { width: 200px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="puntos">💰 <span id="puntos">0</span></div>
    <img id="cofre" src="https://i.imgur.com/8Y3XqG2.png" class="chest">
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let p = 0;
        document.getElementById('cofre').onclick = () => {
            p++;
            document.getElementById('puntos').innerText = p;
            tg.HapticFeedback.impactOccurred('light');
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)

# --- FUNCIÓN DE TELEGRAM (SIN DECORADOR DE FLASK) ---
async def process_telegram_update(json_data, host):
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        user = update.effective_user
        try:
            db.table("jugadores").upsert({"user_id": user.id, "nombre": user.first_name}).execute()
        except: pass
        
        url_app = f"https://{host}/"
        keyboard = [[InlineKeyboardButton("🎁 ABRIR COFRE", web_app=WebAppInfo(url=url_app))]]
        await update.message.reply_text(f"¡Hola {user.first_name}! 🏴‍☠️", reply_markup=InlineKeyboardMarkup(keyboard))

    bot_app.add_handler(CommandHandler("start", start))
    
    update = Update.de_json(json_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)

# --- LA ENTRADA PRINCIPAL (Aquí es donde evitamos a Flask) ---
@app.route('/api/index', methods=['POST'])
def handler():
    # En lugar de dejar que Flask maneje la función asincrónica, 
    # la ejecutamos nosotros manualmente con asyncio.run
    update_data = request.get_json(force=True)
    host = request.host
    
    try:
        asyncio.run(process_telegram_update(update_data, host))
    except Exception as e:
        print(f"Error: {e}")
        
    return "ok", 200
