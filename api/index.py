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

HTML_JUEGO = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
    <style>
        body { background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; margin: 0; }
        .card { background: #1e1e1e; margin: 15px; padding: 20px; border-radius: 15px; border: 1px solid #333; }
        .balance { font-size: 35px; color: #0088cc; font-weight: bold; }
        .btn { background: #0088cc; color: white; border: none; padding: 12px 20px; border-radius: 10px; font-weight: bold; width: 80%; margin: 10px 0; cursor: pointer; }
        #ton-connect-button { display: flex; justify-content: center; margin: 20px 0; }
    </style>
</head>
<body>
    <div id="ton-connect-button"></div>

    <div class="card">
        <div class="balance"><span id="puntos">0.00</span> TON</div>
        <p style="color: #888;">Saldo en Stake: <span id="stake">0.00</span></p>
    </div>

    <div class="card">
        <h3>🏦 SISTEMA DE STAKE</h3>
        <p>Ganá el 1% diario sobre tus TON depositados.</p>
        <button class="btn" onclick="alert('Próximamente: Stake On-chain')">PONER EN STAKE</button>
    </div>

    <div class="card">
        <h3>💳 BILLETERA</h3>
        <button class="btn" style="background: #2ecc71;">DEPOSITAR</button>
        <button class="btn" style="background: #e74c3c;">RETIRAR</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        // 1. Obtener el ID del usuario de Telegram
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;

        // 2. Función para pedir el saldo al servidor (Flask -> Supabase)
        async function actualizarSaldo() {
            if (!userId) return;
            try {
                const response = await fetch(`/api/get_balance?user_id=${userId}`);
                const data = await response.json();
                
                if (data.puntos_totales !== undefined) {
                    // Actualizamos los números en la pantalla
                    document.getElementById('puntos').innerText = data.puntos_totales.toFixed(4);
                    document.getElementById('stake').innerText = data.puntos_staking.toFixed(2);
                }
            } catch (e) {
                console.error("Error al obtener saldo:", e);
            }
        }

        // 3. Ejecutar la actualización al abrir y cada 10 segundos
        if (userId) {
            actualizarSaldo();
            setInterval(actualizarSaldo, 10000); 
        }

        // 4. Configuración de TON Connect
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({
            manifestUrl: 'https://' + window.location.host + '/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)
@app.route('/api/get_balance')
def get_balance():
    user_id = request.args.get('user_id')
    if not user_id:
        return {"error": "Falta user_id"}, 400

    try:
        # Llamamos a la función inteligente que creamos en Supabase (RPC)
        result = db.rpc('calcular_saldo_total', {'jugador_id': int(user_id)}).execute()
        
        # También traemos el valor de puntos_staking por separado
        user_data = db.table("jugadores").select("puntos_staking").eq("user_id", user_id).single().execute()
        
        return {
            "puntos_totales": float(result.data) if result.data else 0.0,
            "puntos_staking": float(user_data.data['puntos_staking']) if user_data.data else 0.0
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        user = update.effective_user
        # Registramos al usuario con los nuevos campos
        try:
            db.table("jugadores").upsert({
                "user_id": user.id, 
                "nombre": user.first_name
            }).execute()
        except: pass
        
        url_app = f"https://{request.host}/"
        keyboard = [[InlineKeyboardButton("💎 ABRIR BILLETERA TON", web_app=WebAppInfo(url=url_app))]]
        await update.message.reply_text(
            f"¡Bienvenido {user.first_name}! 🏴‍☠️\\n\\nAcá podés gestionar tus TON y ganar intereses por Stake.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)
    return "ok", 200