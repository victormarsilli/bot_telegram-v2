import os
import requests
from flask import Flask, request, render_template_string
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

# --- CONFIGURACIÓN DE VARIABLES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ⚠️ REEMPLAZAR CON TUS DATOS REALES:
TONCENTER_API_KEY = "TU_API_KEY_DE_TONCENTER"  
MI_BILLETERA_RECIBO = "TU_DIRECCION_DE_BILLETERA_TON" 
# Esta variable debe estar configurada en el panel de Vercel:
MI_ID_TELEGRAM = os.getenv("MI_ID_TELEGRAM") 

db = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# --- FRONTEND: HTML, CSS y JAVASCRIPT ---
HTML_JUEGO = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vIcmAr Staking</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
    <style>
        body {{ background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; margin: 0; padding-bottom: 50px; }}
        .card {{ background: #1e1e1e; margin: 15px; padding: 20px; border-radius: 15px; border: 1px solid #333; }}
        .balance {{ font-size: 38px; color: #0088cc; font-weight: bold; margin: 10px 0; }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 15px; border-radius: 12px; font-weight: bold; width: 90%; margin: 10px 0; cursor: pointer; font-size: 16px; transition: 0.3s; }}
        .btn:active {{ transform: scale(0.98); opacity: 0.8; }}
        #ton-connect-button {{ display: flex; justify-content: center; margin: 20px 0; }}
        .label {{ color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
        .info {{ font-size: 12px; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    <div id="ton-connect-button"></div>

    <div class="card">
        <span class="label">Balance Total Estimado</span>
        <div class="balance"><span id="puntos">0.0000</span> TON</div>
        <p style="color: #aaa; font-size: 14px;">Staking Activo: <span id="stake">0.00</span> TON</p>
    </div>

    <div class="card">
        <h3>🏦 vIcmAr PLATINUM STAKE</h3>
        <p style="font-size: 14px; color: #ccc;">Gana 1% diario acumulado</p>
        <button class="btn" onclick="ejecutarStake()">PASAR TODO A STAKE</button>
    </div>

    <div class="card">
        <h3>💳 MOVIMIENTOS</h3>
        <button class="btn" style="background: #2ecc71;" onclick="enviarDeposito()">DEPOSITAR (0.10 TON)</button>
        <button class="btn" style="background: #282828; border: 1px solid #444;" onclick="solicitarRetiro()">RETIRAR (Mín. 5 TON)</button>
        <p class="info">Retiros procesados manualmente por seguridad.</p>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;
        const userName = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.first_name : "Usuario";

        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: 'https://' + window.location.host + '/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        }});

        async function actualizarSaldo() {{
            if (!userId) return;
            try {{
                const res = await fetch(`/api/get_balance?user_id=${{userId}}`);
                const data = await res.json();
                if (data.puntos_totales !== undefined) {{
                    document.getElementById('puntos').innerText = data.puntos_totales.toFixed(6);
                    document.getElementById('stake').innerText = data.puntos_staking.toFixed(2);
                }}
            }} catch (e) {{ console.error("Error al actualizar saldo:", e); }}
        }}

        async function enviarDeposito() {{
            if (!tonConnectUI.connected) {{ alert("Conectá tu billetera primero."); return; }}
            
            // 0.10 TON = 100,000,000 nanoton (Enviado como string)
            const transaction = {{
                validUntil: Math.floor(Date.now() / 1000) + 300,
                messages: [{{ 
                    address: "{MI_BILLETERA_RECIBO}", 
                    amount: "100000000" 
                }}]
            }};
            
            try {{
                const result = await tonConnectUI.sendTransaction(transaction);
                alert("Pago enviado. Verificando en la blockchain...");
                
                const response = await fetch('/api/verificar_pago', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ user_id: userId, boc: result.boc }})
                }});
                
                const data = await response.json();
                if (data.success) alert("¡Depósito acreditado!");
                else alert("El pago se está procesando en la red.");
                actualizarSaldo();
            }} catch (e) {{ 
                console.error(e);
                alert("Operación cancelada o error de red."); 
            }}
        }}

        async function solicitarRetiro() {{
            const monto = prompt("¿Cuánto querés retirar? (Mínimo 5 TON):");
            if (!monto) return;
            
            const numMonto = parseFloat(monto);
            if (numMonto < 5) {{
                alert("El mínimo es de 5 TON.");
                return;
            }}

            const response = await fetch('/api/solicitar_retiro', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId, nombre: userName, cantidad: numMonto }})
            }});
            
            const data = await response.json();
            alert(data.message || data.error);
        }}

        async function ejecutarStake() {{
            if (!confirm("¿Mover todo tu saldo a Staking para ganar interés?")) return;
            const res = await fetch('/api/stake_now', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId }})
            }});
            const data = await res.json();
            if (data.success) alert("¡Capital puesto en Staking!");
            actualizarSaldo();
        }}

        if (userId) {{
            actualizarSaldo();
            setInterval(actualizarSaldo, 10000);
        }}
    </script>
</body>
</html>
"""

# --- RUTAS DE API ---

@app.route('/')
def home():
    return render_template_string(HTML_JUEGO)

@app.route('/api/get_balance')
def get_balance():
    u_id = request.args.get('user_id')
    try:
        res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
        res_stk = db.table("jugadores").select("puntos_staking").eq("user_id", u_id).single().execute()
        return {
            "puntos_totales": float(res_bal.data) if res_bal.data else 0.0,
            "puntos_staking": float(res_stk.data['puntos_staking']) if res_stk.data else 0.0
        }
    except: return {"error": "Error DB"}, 500

@app.route('/api/stake_now', methods=['POST'])
def stake_now():
    u_id = request.get_json().get('user_id')
    try:
        res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
        db.table("jugadores").update({
            "puntos": 0, "puntos_staking": float(res_bal.data), "ultimo_reclamo": "now()"
        }).eq("user_id", u_id).execute()
        return {"success": True}
    except Exception as e: return {"error": str(e)}, 500

@app.route('/api/verificar_pago', methods=['POST'])
def verificar_pago():
    data = request.get_json()
    u_id, boc = data.get('user_id'), data.get('boc')
    url = f"https://toncenter.com/api/v2/getTransactions?address={MI_BILLETERA_RECIBO}&limit=10&api_key={TONCENTER_API_KEY}"
    try:
        resp = requests.get(url).json()
        if resp.get("ok"):
            for tx in resp.get("result", []):
                tx_hash = tx["transaction_id"]["hash"]
                check = db.table("pagos_procesados").select("hash").eq("hash", tx_hash).execute()
                if not check.data and "in_msg" in tx:
                    val = int(tx["in_msg"]["value"]) / 1e9
                    if val >= 0.09: # Margen por comisiones
                        db.table("pagos_procesados").insert({"hash": tx_hash, "user_id": u_id, "monto": val}).execute()
                        db.rpc('acreditar_puntos', {'id_usuario': u_id, 'cantidad': val}).execute()
                        return {"success": True}
    except: pass
    return {"success": False}, 400

@app.route('/api/solicitar_retiro', methods=['POST'])
async def solicitar_retiro():
    data = request.get_json()
    u_id, nombre, cantidad = data.get('user_id'), data.get('nombre'), data.get('cantidad')

    res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
    if float(res_bal.data) < cantidad:
        return {"error": "Saldo insuficiente."}, 400

    try:
        bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
        async with bot_app:
            msg = f"🔔 **SOLICITUD DE RETIRO**\\n\\nUsuario: {nombre} ({u_id})\\nCantidad: {cantidad} TON"
            await bot_app.bot.send_message(chat_id=MI_ID_TELEGRAM, text=msg, parse_mode='Markdown')
        return {"message": "Solicitud enviada al administrador."}
    except Exception as e:
        return {"error": "No se pudo enviar el aviso al admin."}, 500

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        u = update.effective_user
        db.table("jugadores").upsert({"user_id": u.id, "nombre": u.first_name}).execute()
        url_app = f"https://{request.host}/"
        kb = [[InlineKeyboardButton("💎 ABRIR vIcmAr PLATINUM", web_app=WebAppInfo(url=url_app))]]
        await update.message.reply_text(f"¡Hola {u.first_name}! 🏴‍☠️\\nMultiplica tus TON con un 1% diario.", reply_markup=InlineKeyboardMarkup(kb))

    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)
    return "ok", 200