import os
import asyncio
from flask import Flask, request, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application
from supabase import create_client

app = Flask(__name__)

# Configuración
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- HTML (Igual que antes) ---
HTML_JUEGO = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background: #1a1a1a; color: white; text-align: center; font-family: sans-serif; overflow: hidden; margin: 0; padding: 0; }
        .puntos { font-size: 40px; color: #ffd700; font-weight: bold; margin-top: 50px; text-shadow: 2px 2px #000; }
        .chest { width: 220px; margin-top: 40px; cursor: pointer; transition: transform 0.1s; }
        .chest:active { transform: scale(0.9); }
        .btn-tienda { background: #ffd700; color: black; border: none; padding: 15px 40px; border-radius: 12px; font-weight: bold; margin-top: 50px; font-size: 18px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="puntos">💰 <span id="puntos">0</span></div>
    <img id="cofre" src="https://i.imgur.com/8Y3XqG2.png" class="chest" alt="Cofre">
    <br>
    <button class="btn-tienda">🛒 TIENDA</button>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand(); 
        let puntos = 0;
        const puntosText = document.getElementById('puntos');
        document.getElementById('cofre').onclick = () => {
            puntos++;
            puntosText.innerText = puntos;
            tg.HapticFeedback.impactOccurred('medium'); 
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)

# --- LA FUNCIÓN START AHORA ES SINCRÓNICA ---
def start_sync(update, context):
    user = update.effective_user
    try:
        db.table("jugadores").upsert({"user_id": user.id, "nombre": user.first_name}).execute()
    except:
        pass

    url_app = f"https://{request.host}/"
    keyboard = [[InlineKeyboardButton("🎁 ABRIR MI COFRE", web_app=WebAppInfo(url=url_app))]]
    
    # Usamos el bot directamente para enviar el mensaje (de forma asincrónica pero dentro del loop)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update.message.reply_text(
        f"¡Hola {user.first_name}! 🏴‍☠️\\n\\nBienvenido al imperio. Tocá abajo:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    ))

@app.route('/api/index', methods=['POST'])
def main():
    # Eliminamos cualquier rastro de 'async def' en las rutas de Flask
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    from telegram.ext import CommandHandler
    bot_app.add_handler(CommandHandler("start", start_sync))
    
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, bot_app.bot)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.process_update(update))
        loop.run_until_complete(bot_app.shutdown())
    finally:
        loop.close()
        
    return "ok", 200
