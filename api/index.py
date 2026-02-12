import os
from flask import Flask, request, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

app = Flask(__name__)

# Configuración (Se cargan desde las variables de entorno de Vercel)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Conexión a la base de datos
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- EL DISEÑO DEL JUEGO (HTML) ---
# Aquí es donde el usuario verá el cofre.
HTML_JUEGO = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { background: #1a1a1a; color: white; text-align: center; font-family: sans-serif; overflow: hidden; }
        .chest { width: 180px; margin-top: 60px; cursor: pointer; transition: 0.1s; }
        .chest:active { transform: scale(0.9); }
        .puntos { font-size: 32px; color: #ffd700; font-weight: bold; margin-top: 20px; }
        .btn-tienda { background: #ffd700; color: black; border: none; padding: 15px 30px; border-radius: 10px; font-weight: bold; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="puntos">💰 <span id="puntos">0</span></div>
    <img id="cofre" src="https://i.imgur.com/8Y3XqG2.png" class="chest">
    <br>
    <button class="btn-tienda">🛒 TIENDA DE MEJORAS</button>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand(); // Abre la app a pantalla completa

        let puntos = 0;
        const cofre = document.getElementById('cofre');
        const puntosText = document.getElementById('puntos');

        cofre.onclick = () => {
            puntos++;
            puntosText.innerText = puntos;
            tg.HapticFeedback.impactOccurred('medium'); // Vibra al tocar (solo en celus)
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)

# --- LÓGICA DEL BOT ---
async def start(update: Update, context):
    user = update.effective_user
    
    # Registramos al usuario en Supabase si no existe
    # (Upsert: si existe lo ignora, si no existe lo crea)
    db.table("jugadores").upsert({
        "user_id": user.id,
        "nombre": user.first_name
    }).execute()

    # Botón para abrir la Mini App
    url_app = f"https://{request.host}/"
    keyboard = [[InlineKeyboardButton("🎁 ABRIR MI COFRE", web_app=WebAppInfo(url=url_app))]]
    
    await update.message.reply_text(
        f"¡Hola {user.first_name}! 🏴‍☠️\n\nBienvenido a tu imperio. Tocá el botón de abajo para empezar a recolectar oro.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.route('/api/index', methods=['POST'])
async def main():
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.initialize()
    await bot_app.process_update(update)
    await bot_app.shutdown()
    return "ok", 200