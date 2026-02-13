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

# ⚠️ REEMPLAZAR ESTOS DOS VALORES:
TONCENTER_API_KEY = "TU_API_KEY_DE_TONCENTER"  
MI_BILLETERA_RECIBO = "TU_DIRECCION_DE_BILLETERA" 

db = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# --- FRONTEND: HTML, CSS y JAVASCRIPT ---
HTML_JUEGO = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js"></script>
    <style>
        body {{ background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; margin: 0; padding-bottom: 50px; }}
        .card {{ background: #1e1e1e; margin: 15px; padding: 20px; border-radius: 15px; border: 1px solid #333; }}
        .balance {{ font-size: 38px; color: #0088cc; font-weight: bold; margin: 10px 0; }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 15px; border-radius: 12px; font-weight: bold; width: 90%; margin: 10px 0; cursor: pointer; }}
        #ton-connect-button {{ display: flex; justify-content: center; margin: 20px 0; }}
        .label {{ color: #888; font-size: 14px; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div id="ton-connect-button"></div>

    <div class="card">
        <span class="label">Balance Total con Interés</span>
        <div class="balance"><span id="puntos">0.0000</span> TON</div>
        <p style="color: #aaa;">En Staking: <span id="stake">0.00</span> TON</p>
    </div>

    <div class="card">
        <h3>🏦 SISTEMA DE STAKING</h3>
        <p style="font-size: 14px; color: #ccc;">Gana 1% diario acumulado</p>
        <button class="btn" onclick="ejecutarStake()">PASAR SALDO A STAKE</button>
    </div>

    <div class="card">
        <h3>💳 BILLETERA</h3>
        <button class="btn" style="background: #2ecc71;" onclick="enviarDeposito()">DEPOSITAR 1 TON</button>
        <button class="btn" style="background: #282828; border: 1px solid #444;" onclick="solicitarRetiro()">RETIRAR</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;

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
            }} catch (e) {{ console.error(e); }}
        }}

        async function enviarDeposito() {{
            if (!tonConnectUI.connected) {{ alert("Conecta tu wallet primero"); return; }}
            const transaction = {{
                validUntil: Math.floor(Date.now() / 1000) + 300,
                messages: [{{ address: "{MI_BILLETERA_RECIBO}", amount: "1000000000" }}]
            }};
            try {{
                const result = await tonConnectUI.sendTransaction(transaction);
                alert("Verificando pago en la red...");
                const response = await fetch('/api/verificar_pago', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ user_id: userId, boc: result.boc }})
                }});
                const data = await response.json();
                if (data.success) {{
                    alert("¡Pago verificado!");
                }} else {{
                    alert("Aún no detectamos el pago. Intenta actualizar en unos segundos.");
                }}
                actualizarSaldo();
            }} catch (e) {{ alert("Error o transacción cancelada."); }}
        }}

        async function ejecutarStake() {{
            if (!confirm("¿Activar Staking sobre el saldo total?")) return;
            const res = await fetch('/api/stake_now', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId }})
            }});
            const data = await res.json();
            if (data.success) {{
                alert("¡Stake activado!");
            }}
            actualizarSaldo();
        }}

        function solicitarRetiro() {{ alert("Solicitud de retiro enviada al administrador."); }}

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
        # Llamada a la función RPC para calcular intereses en tiempo real
        res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
        res_stk = db.table("jugadores").select("puntos_staking").eq("user_id", u_id).single().execute()
        return {
            "puntos_totales": float(res_bal.data) if res_bal.data else 0.0,
            "puntos_staking": float(res_stk.data['puntos_staking']) if res_stk.data else 0.0
        }
    except: return {"error": "DB Error"}, 500

@app.route('/api/stake_now', methods=['POST'])
def stake_now():
    u_id = request.get_json().get('user_id')
    try:
        # Calculamos el saldo actual con intereses acumulados
        res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
        nuevo_monto_stake = float(res_bal.data)
        
        # Movemos todo a staking y reiniciamos el reloj de intereses
        db.table("jugadores").update({
            "puntos": 0, 
            "puntos_staking": nuevo_monto_stake, 
            "ultimo_reclamo": "now()"
        }).eq("user_id", u_id).execute()
        return {"success": True}
    except Exception as e: return {"error": str(e)}, 500

@app.route('/api/verificar_pago', methods=['POST'])
def verificar_pago():
    data = request.get_json()
    u_id, boc = data.get('user_id'), data.get('boc')
    
    # Consultamos Toncenter para ver las últimas transacciones
    url = f"https://toncenter.com/api/v2/getTransactions?address={MI_BILLETERA_RECIBO}&limit=10&api_key={TONCENTER_API_KEY}"
    
    try:
        resp = requests.get(url).json()
        if resp.get("ok"):
            for tx in resp.get("result", []):
                tx_hash = tx["transaction_id"]["hash"]
                
                # 1. Verificamos si este hash ya fue procesado
                check = db.table("pagos_procesados").select("hash").eq("hash", tx_hash).execute()
                
                if not check.data and "in_msg" in tx:
                    # 2. Verificamos el monto (1 TON = 1.000.000.000 nanoton)
                    val = int(tx["in_msg"]["value"]) / 1e9
                    if val >= 0.95: # Margen por comisiones
                        # Registramos el pago para evitar doble uso
                        db.table("pagos_procesados").insert({
                            "hash": tx_hash, 
                            "user_id": u_id, 
                            "monto": val
                        }).execute()
                        
                        # Acreditamos los puntos
                        db.rpc('acreditar_puntos', {'id_usuario': u_id, 'cantidad': val}).execute()
                        return {"success": True}
    except: pass
    return {"success": False, "error": "Transacción no encontrada"}, 400

# --- MANEJADOR DEL BOT ---

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    async def start(update, context):
        u = update.effective_user
        # Registramos al usuario si no existe
        db.table("jugadores").upsert({"user_id": u.id, "nombre": u.first_name}).execute()
        
        url_webapp = f"https://{request.host}/"
        kb = [[InlineKeyboardButton("💎 BILLETERA vIcmAr", web_app=WebAppInfo(url=url_webapp))]]
        
        await update.message.reply_text(
            f"¡Hola {u.first_name}! 🏴‍☠️\\n\\nTu sistema de Stake TON está activo.",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app:
        await bot_app.process_update(update)
    return "ok", 200