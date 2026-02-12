import os
import asyncio
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

# --- EL DISEÑO DEL JUEGO (HTML) ---
HTML_JUEGO = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background: #1a1a1a; color: white; text-align: center; font-family: sans-serif; margin: 0; padding: 0; }
        .puntos { font-size: 40px; color: #ffd700; font-weight: bold; margin-top: 50px; }
        .chest { width: 220px; margin-top: 40px; cursor: pointer; transition: transform 0.1s; }
        .chest:active { transform: scale(0.9); }
    </style>
</head>
<body>
    <div class="puntos">💰 <span id="puntos">0</span></div>
    <img id="cofre" src="https://i.imgur.com/8Y3XqG2.png" class="chest">
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let puntos = 0;
        document.getElementById('cofre').onclick = () => {
            puntos++;
            document.getElementById('puntos').innerText = puntos;
            tg.HapticFeedback.impactOccurred('medium');
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        user = update.effective_user
        try:
            db.table("jugadores").upsert({"user_id": user.id, "nombre": user.first_name}).execute()
        except: pass
        
        # El botón apunta a la URL principal (/) donde está el HTML_JUEGO
        url_app = f"https://{request.host}/"
        keyboard = [[InlineKeyboardButton("🎁 ABRIR COFRE", web_app=WebAppInfo(url=url_app))]]
        await update.message.reply_text(f"¡Hola {user.first_name}! 🏴‍☠️\\n\\n¡Tu cofre te espera!", reply_markup=InlineKeyboardMarkup(keyboard))

    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)
    return "ok", 200
