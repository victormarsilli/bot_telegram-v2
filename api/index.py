import os
import requests
from flask import Flask, request, render_template_string, jsonify
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler
from supabase import create_client

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MI_ID_TELEGRAM = os.getenv("MI_ID_TELEGRAM")
MI_BILLETERA_RECIBO = os.getenv("TU_DIRECCION_DE_BILLETERA_TON") 
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # <--- La de nuestro primer proyecto

db = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# --- RUTA PARA LA IA (GROQ) ---
@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    pregunta = request.get_json().get('pregunta')
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Eres el experto cripto de vIcmAr Platinum. Responde de forma breve, canchera y ayuda a los novatos a entender TON y el staking. No uses más de 3 frases."},
            {"role": "user", "content": pregunta}
        ]
    }
    try:
        resp = requests.post(url, json=payload, headers=headers).json()
        respuesta = resp['choices'][0]['message']['content']
        return jsonify({"respuesta": respuesta})
    except:
        return jsonify({"respuesta": "El gurú está meditando. Reintentá en un toque."})

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
        body {{ background: #121212; color: white; font-family: 'Segoe UI', sans-serif; text-align: center; margin: 0; }}
        
        /* Pantalla de Carga */
        #splash {{ 
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: #121212; display: flex; flex-direction: column; 
            justify-content: center; align-items: center; z-index: 9999; 
            transition: opacity 0.8s ease;
        }}
        .logo-anim {{ font-size: 40px; font-weight: bold; color: #0088cc; margin-bottom: 20px; letter-spacing: 5px; animation: pulse 1.5s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 0.5; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.5; }} }}

        .card {{ background: #1e1e1e; margin: 15px; padding: 20px; border-radius: 15px; border: 1px solid #333; }}
        .balance {{ font-size: 35px; color: #0088cc; font-weight: bold; }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 12px; border-radius: 10px; font-weight: bold; width: 90%; margin: 5px; }}

        /* Chat IA Style */
        #ai-box {{ background: #1a1a1a; border-radius: 15px; margin: 15px; padding: 15px; border: 1px solid #0088cc55; text-align: left; }}
        #ai-msg {{ font-size: 14px; color: #ccc; min-height: 30px; margin-bottom: 10px; border-left: 3px solid #0088cc; padding-left: 10px; }}
        .ai-input-group {{ display: flex; gap: 5px; }}
        input {{ flex-grow: 1; background: #222; border: 1px solid #444; color: white; padding: 8px; border-radius: 8px; }}
    </style>
</head>
<body>
    <div id="splash">
        <div class="logo-anim">vIcmAr</div>
        <p style="color: #666; letter-spacing: 2px;">PLATINUM SYSTEM</p>
    </div>

    <div id="main-content" style="display:none;">
        <div id="ton-connect-button" style="display:flex; justify-content:center; padding: 20px 0;"></div>
        
        <div class="card">
            <span style="font-size: 12px; color: #888;">SALDO TOTAL</span>
            <div class="balance"><span id="puntos">0.0000</span> TON</div>
            <p style="font-size: 13px; color: #aaa;">En Staking: <span id="stake">0.00</span></p>
        </div>

        <div id="ai-box">
            <div style="font-weight: bold; color: #0088cc; font-size: 12px; margin-bottom: 5px;">GURÚ CRIPTO vIcmAr</div>
            <div id="ai-msg">¡Hola! Tirame cualquier duda sobre TON o el Staking.</div>
            <div class="ai-input-group">
                <input type="text" id="ai-input" placeholder="¿Cómo retiro?">
                <button onclick="preguntarIA()" style="background:#0088cc; border:none; border-radius:8px; padding:0 15px; color:white;">→</button>
            </div>
        </div>

        <div class="card">
            <button class="btn" onclick="ejecutarStake()">ACTIVAR STAKING</button>
            <button class="btn" style="background:#2ecc71;" onclick="enviarDeposito()">DEPOSITAR (0.10)</button>
            <button class="btn" style="background:#222; border: 1px solid #444;" onclick="solicitarRetiro()">RETIRAR</button>
        </div>
    </div>

    <script>
        // Lógica Splash
        setTimeout(() => {{
            const splash = document.getElementById('splash');
            splash.style.opacity = '0';
            setTimeout(() => {{
                splash.style.display = 'none';
                document.getElementById('main-content').style.display = 'block';
            }}, 800);
        }}, 2500);

        const tg = window.Telegram.WebApp;
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : null;
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: 'https://bot-telegram-v2-gmny.vercel.app/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        }});

        async function preguntarIA() {{
            const input = document.getElementById('ai-input');
            const msg = document.getElementById('ai-msg');
            if (!input.value) return;
            msg.innerText = "Consultando a la red...";
            const res = await fetch('/api/ask_ai', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ pregunta: input.value }})
            }});
            const data = await res.json();
            msg.innerText = data.respuesta;
            input.value = "";
        }}

        async function actualizarSaldo() {{
            if (!userId) return;
            const res = await fetch(`/api/get_balance?user_id=${{userId}}`);
            const data = await res.json();
            if (data.puntos_totales !== undefined) {{
                document.getElementById('puntos').innerText = data.puntos_totales.toFixed(6);
                document.getElementById('stake').innerText = data.puntos_staking.toFixed(2);
            }}
        }}

        // (Funciones de pago y retiro se mantienen igual que la versión estable anterior)
        async function enviarDeposito() {{
            if (!tonConnectUI.connected) {{ alert("Conectá la wallet."); return; }}
            const transaction = {{
                validUntil: Math.floor(Date.now() / 1000) + 300,
                messages: [{{ address: "{MI_BILLETERA_RECIBO}", amount: "100000000" }}]
            }};
            try {{
                const result = await tonConnectUI.sendTransaction(transaction);
                await fetch('/api/verificar_pago', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ user_id: userId, boc: result.boc }})
                }});
                actualizarSaldo();
            }} catch (e) {{ alert("Cancelado."); }}
        }}

        async function solicitarRetiro() {{
            const monto = prompt("Monto a retirar:");
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
            await fetch('/api/stake_now', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId }})
            }});
            actualizarSaldo();
        }}

        if (userId) {{ actualizarSaldo(); setInterval(actualizarSaldo, 10000); }}
    </script>
</body>
</html>
"""

# --- EL RESTO DE RUTAS IGUAL QUE LA VERSIÓN FUNCIONAL ---
@app.route('/')
def home(): return render_template_string(HTML_JUEGO)

@app.route('/api/get_balance')
def get_balance():
    u_id = request.args.get('user_id')
    try:
        res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
        res_stk = db.table("jugadores").select("puntos_staking").eq("user_id", u_id).single().execute()
        return {"puntos_totales": float(res_bal.data or 0), "puntos_staking": float(res_stk.data['puntos_staking'] or 0)}
    except: return {"error": "DB Error"}, 500

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
            msg = f"🔔 **RETIRO vIcmAr**\nUsuario: {nombre} ({u_id})\nCant: {cantidad} TON"
            await bot_app.bot.send_message(chat_id=MI_ID_TELEGRAM, text=msg)
        return {"message": "Solicitud enviada al admin."}
    except: return {"error": "Error de envío."}

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    async def start(update, context):
        u = update.effective_user
        db.table("jugadores").upsert({"user_id": u.id, "nombre": u.first_name}).execute()
        kb = [[InlineKeyboardButton("💎 MI BILLETERA vIcmAr", web_app=WebAppInfo(url=f"https://{request.host}/"))]]
        await update.message.reply_text(f"¡Hola {u.first_name}! 🏴‍☠️\\nBienvenido a vIcmAr Platinum.", reply_markup=InlineKeyboardMarkup(kb))
    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app: await bot_app.process_update(update)
    return "ok", 200