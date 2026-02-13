import os
import asyncio
import requests
from flask import Flask, request, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración TON (Para verificación automática)
TONCENTER_API_KEY = "TU_API_KEY_DE_TONCENTER"  # Obtenla en @tonapibot
MI_BILLETERA_RECIBO = "TU_DIRECCION_DE_BILLETERA_AQUI"

app = Flask(__name__)

# --- DISEÑO DEL FRONTEND (HTML/JS) ---
HTML_JUEGO = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
    <style>
        body { background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; margin: 0; padding-bottom: 50px; }
        .card { background: #1e1e1e; margin: 15px; padding: 20px; border-radius: 15px; border: 1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .balance { font-size: 38px; color: #0088cc; font-weight: bold; margin: 10px 0; }
        .btn { background: #0088cc; color: white; border: none; padding: 15px; border-radius: 12px; font-weight: bold; width: 90%; margin: 10px 0; cursor: pointer; font-size: 16px; }
        .btn-alt { background: #282828; border: 1px solid #444; }
        #ton-connect-button { display: flex; justify-content: center; margin: 20px 0; }
        .label { color: #888; font-size: 14px; text-transform: uppercase; }
    </style>
</head>
<body>
    <div id="ton-connect-button"></div>

    <div class="card">
        <span class="label">Balance Total (con Interés)</span>
        <div class="balance"><span id="puntos">0.0000</span> TON</div>
        <p style="color: #aaa;">En Staking: <span id="stake">0.00</span> TON</p>
    </div>

    <div class="card">
        <h3>🏦 STAKING</h3>
        <p style="font-size: 14px; color: #ccc;">Generando 1% de interés diario</p>
        <button class="btn" onclick="ejecutarStake()">PONER SALDO EN STAKE</button>
    </div>

    <div class="card">
        <h3>💳 BILLETERA</h3>
        <button class="btn" style="background: #2ecc71;" onclick="enviarDeposito()">DEPOSITAR 1 TON</button>
        <button class="btn btn-alt" onclick="solicitarRetiro()">RETIRAR FONDOS</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;

        // 1. Inicializar TON Connect
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({
            manifestUrl: 'https://' + window.location.host + '/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        });

        // 2. Actualizar Saldo desde la API
        async function actualizarSaldo() {
            if (!userId) return;
            try {
                const response = await fetch(`/api/get_balance?user_id=${userId}`);
                const data = await response.json();
                if (data.puntos_totales !== undefined) {
                    document.getElementById('puntos').innerText = data.puntos_totales.toFixed(6);
                    document.getElementById('stake').innerText = data.puntos_staking.toFixed(2);
                }
            } catch (e) { console.error(e); }
        }

        // 3. Función de Depósito
        async function enviarDeposito() {
            if (!tonConnectUI.connected) { alert("Conectá tu wallet primero"); return; }
            const transaction = {
                validUntil: Math.floor(Date.now() / 1000) + 300,
                messages: [{ address: " """ + MI_BILLETERA_RECIBO + """ ", amount: "1000000000" }]
            };
            try {
                const result = await tonConnectUI.sendTransaction(transaction);
                alert("Pago enviado. Verificando en la blockchain...");
                // Enviamos el BOC (base64 de la transacción) para verificar
                fetch('/api/verificar_pago', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ user_id: userId, boc: result.boc })
                });
            } catch (e) { alert("Transacción cancelada"); }
        }

        // 4. Función de Stake
        async function ejecutarStake() {
            if (!confirm("¿Mover saldo disponible a Staking?")) return;
            const response = await fetch('/api/stake_now', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId })
            });
            const res = await response.json();
            if (res.success) { alert("¡Stake activado!"); actualizarSaldo(); }
            else { alert("Error: " + res.error); }
        }

        function solicitarRetiro() { alert("Solicitud enviada al administrador."); }

        if (userId) {
            actualizarSaldo();
            setInterval(actualizarSaldo, 10000);
        }
    </script>
</body>
</html>
"""

# --- RUTAS DE LA API ---

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)

@app.route('/api/get_balance')
def get_balance():
    user_id = request.args.get('user_id')
    try:
        res_total = db.rpc('calcular_saldo_total', {'jugador_id': int(user_id)}).execute()
        res_user = db.table("jugadores").select("puntos_staking").eq("user_id", user_id).single().execute()
        return {
            "puntos_totales": float(res_total.data) if res_total.data else 0.0,
            "puntos_staking": float(res_user.data['puntos_staking']) if res_user.data else 0.0
        }
    except: return {"error": "Error de base de datos"}, 500

@app.route('/api/stake_now', methods=['POST'])
def stake_now():
    user_id = request.get_json().get('user_id')
    try:
        res_saldo = db.rpc('calcular_saldo_total', {'jugador_id': int(user_id)}).execute()
        nuevo_total = float(res_saldo.data)
        db.table("jugadores").update({
            "puntos": 0, "puntos_staking": nuevo_total, "ultimo_reclamo": "now()"
        }).eq("user_id", user_id).execute()
        return {"success": True}
    except Exception as e: return {"error": str(e)}, 500

@app.route('/api/verificar_pago', methods=['POST'])
def verificar_pago():
    data = request.get_json()
    user_id = data.get('user_id')
    boc = data.get('boc') # El mensaje de la transacción

    # 1. Consultamos las últimas transacciones de tu billetera
    url = f"https://toncenter.com/api/v2/getTransactions?address={MI_BILLETERA_RECIBO}&limit=5&api_key={TONCENTER_API_KEY}"
    
    try:
        response = requests.get(url).json()
        if response.get("ok"):
            transacciones = response.get("result", [])
            for tx in transacciones:
                # Verificamos si el mensaje coincide o si el hash es reciente
                # (Simplificado: verificamos que entró un pago de 1 TON)
                valor = int(tx["in_msg"]["value"]) / 1e9
                if valor >= 0.99: # Por si hay comisiones
                    # Acreditamos en Supabase
                    db.rpc('acreditar_puntos', {'id_usuario': user_id, 'cantidad': valor}).execute()
                    return {"success": True, "mensaje": "¡Pago verificado!"}
                    
    except Exception as e:
        return {"error": str(e)}, 500
    
    return {"success": False, "error": "No se encontró el pago todavía"}

# --- MANEJADOR DEL BOT DE TELEGRAM ---

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        user = update.effective_user
        db.table("jugadores").upsert({"user_id": user.id, "nombre": user.first_name}).execute()
        
        url_app = f"https://{request.host}/"
        keyboard = [[InlineKeyboardButton("💎 MI BILLETERA vIcmAr", web_app=WebAppInfo(url=url_app))]]
        await update.message.reply_text(
            f"¡Hola {user.first_name}! 🏴‍☠️\\n\\nBienvenido a tu centro de control de TON.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)
    return "ok", 200