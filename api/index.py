import os
import requests
from flask import Flask, request, render_template_string, jsonify
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

# --- CONFIGURACIÓN DE VARIABLES (Leídas desde Vercel) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MI_ID_TELEGRAM = os.getenv("MI_ID_TELEGRAM")
# Si en Vercel la llamaste "TU_DIRECCION_DE_BILLETERA_TON", usá ese nombre aquí:
MI_BILLETERA_RECIBO = os.getenv("TU_DIRECCION_DE_BILLETERA_TON") 
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY")

db = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# --- MANIFIESTO DINÁMICO ---
@app.route('/tonconnect-manifest.json')
def serve_manifest():
    response = jsonify({
        "url": "https://bot-telegram-v2-gmny.vercel.app",
        "name": "vIcmAr Platinum",
        "iconUrl": "https://bot-telegram-v2-gmny.vercel.app/icon.png"
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# --- FRONTEND ---
HTML_JUEGO = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vIcmAr Platinum</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
    <style>
        body {{ background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; margin: 0; padding-bottom: 50px; }}
        .card {{ background: #1e1e1e; margin: 15px; padding: 20px; border-radius: 15px; border: 1px solid #333; }}
        .balance {{ font-size: 38px; color: #0088cc; font-weight: bold; margin: 10px 0; }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 15px; border-radius: 12px; font-weight: bold; width: 90%; margin: 10px 0; cursor: pointer; font-size: 16px; }}
    </style>
</head>
<body>
    <div id="ton-connect-button"></div>
    <div class="card">
        <span style="color: #888; font-size: 12px;">BALANCE ESTIMADO</span>
        <div class="balance"><span id="puntos">0.0000</span> TON</div>
        <p style="color: #aaa; font-size: 14px;">Staking: <span id="stake">0.00</span> TON</p>
    </div>
    <div class="card">
        <h3>🏦 vIcmAr PLATINUM</h3>
        <button class="btn" onclick="ejecutarStake()">ACTIVAR STAKING</button>
    </div>
    <div class="card">
        <h3>💳 MOVIMIENTOS</h3>
        <button class="btn" style="background: #2ecc71;" onclick="enviarDeposito()">DEPOSITAR (0.10 TON)</button>
        <button class="btn" style="background: #282828; border: 1px solid #444;" onclick="solicitarRetiro()">RETIRAR (Mín. 5 TON)</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: 'https://bot-telegram-v2-gmny.vercel.app/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        }});

        async function actualizarSaldo() {{
            if (!userId) return;
            const res = await fetch(`/api/get_balance?user_id=${{userId}}`);
            const data = await res.json();
            if (data.puntos_totales !== undefined) {{
                document.getElementById('puntos').innerText = data.puntos_totales.toFixed(6);
                document.getElementById('stake').innerText = data.puntos_staking.toFixed(2);
            }}
        }}

        async function enviarDeposito() {{
            if (!tonConnectUI.connected) {{ alert("Conectá tu billetera."); return; }}
            const transaction = {{
                validUntil: Math.floor(Date.now() / 1000) + 300,
                messages: [{{ address: "{MI_BILLETERA_RECIBO}", amount: "100000000" }}]
            }};
            try {{
                const result = await tonConnectUI.sendTransaction(transaction);
                alert("Verificando... Esperá unos segundos.");
                await fetch('/api/verificar_pago', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ user_id: userId, boc: result.boc }})
                }});
                actualizarSaldo();
            }} catch (e) {{ alert("Cancelado."); }}
        }}

        async function solicitarRetiro() {{
            const monto = prompt("Monto (Min 5):");
            if (!monto) return;
            const res = await fetch('/api/solicitar_retiro', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId, nombre: tg.initDataUnsafe.user.first_name, cantidad: parseFloat(monto) }})
            }});
            const data = await res.json();
            alert(data.message || data.error);
        }}

        async function ejecutarStake() {{
            const res = await fetch('/api/stake_now', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId }})
            }});
            if (res.ok) alert("¡Staking Activado!");
            actualizarSaldo();
        }}

        if (userId) {{ actualizarSaldo(); setInterval(actualizarSaldo, 10000); }}
    </script>
</body>
</html>
"""

# --- RUTAS API ---
@app.route('/')
def home(): return render_template_string(HTML_JUEGO)

@app.route('/api/get_balance')
def get_balance():
    u_id = request.args.get('user_id')
    try:
        res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
        res_stk = db.table("jugadores").select("puntos_staking").eq("user_id", u_id).single().execute()
        return {"puntos_totales": float(res_bal.data or 0), "puntos_staking": float(res_stk.data['puntos_staking'] or 0)}
    except: return {"error": "Error"}, 500

@app.route('/api/stake_now', methods=['POST'])
def stake_now():
    u_id = request.get_json().get('user_id')
    res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
    db.table("jugadores").update({"puntos": 0, "puntos_staking": float(res_bal.data), "ultimo_reclamo": "now()"}).eq("user_id", u_id).execute()
    return {"success": True}

@app.route('/api/verificar_pago', methods=['POST'])
def verificar_pago():
    data = request.get_json()
    u_id = data.get('user_id')
    url = f"https://toncenter.com/api/v2/getTransactions?address={MI_BILLETERA_RECIBO}&limit=5&api_key={TONCENTER_API_KEY}"
    try:
        resp = requests.get(url).json()
        if resp.get("ok"):
            for tx in resp.get("result", []):
                tx_hash = tx["transaction_id"]["hash"]
                check = db.table("pagos_procesados").select("hash").eq("hash", tx_hash).execute()
                if not check.data and "in_msg" in tx:
                    val = int(tx["in_msg"]["value"]) / 1e9
                    if val >= 0.09:
                        db.table("pagos_procesados").insert({"hash": tx_hash, "user_id": u_id, "monto": val}).execute()
                        db.rpc('acreditar_puntos', {'id_usuario': u_id, 'cantidad': val}).execute()
                        return {"success": True}
    except: pass
    return {"success": False}

@app.route('/api/solicitar_retiro', methods=['POST'])
async def solicitar_retiro():
    data = request.get_json()
    u_id, nombre, cantidad = data.get('user_id'), data.get('nombre'), data.get('cantidad')
    try:
        bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
        async with bot_app:
            msg = f"🔔 **RETIRO vIcmAr**\nUsuario: {nombre}\nCant: {cantidad} TON"
            await bot_app.bot.send_message(chat_id=MI_ID_TELEGRAM, text=msg)
        return {"message": "Aviso enviado al administrador."}
    except: return {"error": "Error de aviso."}

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    async def start(update, context):
        u = update.effective_user
        db.table("jugadores").upsert({"user_id": u.id, "nombre": u.first_name}).execute()
        kb = [[InlineKeyboardButton("💎 MI BILLETERA vIcmAr", web_app=WebAppInfo(url=f"https://{request.host}/"))]]
        await update.message.reply_text(f"¡Hola {u.first_name}! 🏴‍☠️\\nMultiplica tus TON en vIcmAr Platinum.", reply_markup=InlineKeyboardMarkup(kb))
    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app: await bot_app.process_update(update)
    return "ok", 200