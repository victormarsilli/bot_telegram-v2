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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

db = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# --- IA (GROQ) ---
@app.route('/api/ask_ai', methods=['POST'])
def ask_ai():
    pregunta = request.get_json().get('pregunta')
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Eres el Gurú Cripto de vIcmAr Platinum. Ayuda a novatos. Sé breve (máximo 2 frases) y usa emojis."},
            {"role": "user", "content": pregunta}
        ]
    }
    try:
        resp = requests.post(url, json=payload, headers=headers).json()
        return jsonify({"respuesta": resp['choices'][0]['message']['content']})
    except: return jsonify({"respuesta": "Gurú fuera de línea 🧘"}), 500

@app.route('/tonconnect-manifest.json')
def serve_manifest():
    res = jsonify({"url": "https://bot-telegram-v2-gmny.vercel.app","name": "vIcmAr Platinum","iconUrl": "https://bot-telegram-v2-gmny.vercel.app/icon.png"})
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res

# --- FRONTEND REDISEÑADO ---
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
        body {{ background: #121212; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; overflow: hidden; }}
        
        /* Header Superior */
        .top-bar {{ 
            display: flex; justify-content: space-between; align-items: center; 
            padding: 10px 20px; background: #1a1a1a; border-bottom: 1px solid #333;
        }}
        .mini-balance {{ font-size: 14px; color: #0088cc; font-weight: bold; }}

        /* Pantallas */
        .screen {{ display: none; height: calc(100vh - 60px); overflow-y: auto; padding: 20px; box-sizing: border-box; }}
        .active {{ display: block; }}

        /* Chat UI */
        #chat-container {{ display: flex; flex-direction: column; height: 80%; }}
        #chat-history {{ flex-grow: 1; overflow-y: auto; text-align: left; padding: 10px; }}
        .bubble {{ background: #222; padding: 10px; border-radius: 10px; margin-bottom: 10px; border-left: 3px solid #0088cc; }}
        .user-bubble {{ border-left: 3px solid #2ecc71; }}

        /* Botonera de Navegación */
        .nav-bar {{ 
            position: fixed; bottom: 0; width: 100%; height: 60px; 
            background: #1a1a1a; display: flex; border-top: 1px solid #333;
        }}
        .nav-item {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 12px; cursor: pointer; color: #888; }}
        .nav-item.active-tab {{ color: #0088cc; }}

        /* Splash */
        #splash {{ position: fixed; top: 0; width: 100%; height: 100%; background: #121212; z-index: 10000; display: flex; justify-content: center; align-items: center; transition: 0.8s; }}
        
        .card {{ background: #1e1e1e; padding: 20px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #333; }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 15px; border-radius: 12px; width: 100%; font-weight: bold; margin-top: 10px; }}
        input {{ width: 80%; padding: 10px; border-radius: 10px; border: 1px solid #444; background: #222; color: white; }}
    </style>
</head>
<body>

    <div id="splash"><h1>vIcmAr</h1></div>

    <div class="top-bar">
        <div class="mini-balance">Saldo: <span id="val-top">0.00</span> TON</div>
        <div id="ton-connect-button"></div>
    </div>

    <div id="home-screen" class="screen active">
        <div id="chat-container">
            <div id="chat-history">
                <div class="bubble">¡Hola! Soy tu Gurú de vIcmAr. Preguntame lo que quieras sobre TON.</div>
            </div>
            <div style="display: flex; gap: 5px;">
                <input type="text" id="ai-input" placeholder="Escribe tu duda...">
                <button onclick="preguntarIA()" style="background:#0088cc; border:none; border-radius:10px; width:50px; color:white;">→</button>
            </div>
        </div>
    </div>

    <div id="wallet-screen" class="screen">
        <div class="card">
            <p style="color:#888; margin:0;">BALANCE DISPONIBLE</p>
            <h2 id="puntos">0.000000</h2>
            <p style="color:#0088cc; margin:0;">STAKING ACTIVO: <span id="stake">0.00</span> TON</p>
        </div>
        <div class="card">
            <h3>🏦 vIcmAr Stake</h3>
            <p style="font-size: 13px; color:#aaa;">Gana 1% diario acumulado sobre tu capital.</p>
            <button class="btn" onclick="ejecutarStake()">PASAR TODO A STAKE</button>
        </div>
        <button class="btn" style="background:#2ecc71;" onclick="enviarDeposito()">DEPOSITAR (0.10 TON)</button>
        <button class="btn" style="background:#222; border:1px solid #444;" onclick="solicitarRetiro()">RETIRAR</button>
    </div>

    <div class="nav-bar">
        <div class="nav-item active-tab" onclick="switchTab('home')">
            <span>🤖</span><span>Asistente</span>
        </div>
        <div class="nav-item" onclick="switchTab('wallet')">
            <span>💳</span><span>Wallet</span>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: 'https://bot-telegram-v2-gmny.vercel.app/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        }});

        function switchTab(tab) {{
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active-tab'));
            
            if(tab === 'home') {{
                document.getElementById('home-screen').classList.add('active');
                document.querySelectorAll('.nav-item')[0].classList.add('active-tab');
            }} else {{
                document.getElementById('wallet-screen').classList.add('active');
                document.querySelectorAll('.nav-item')[1].classList.add('active-tab');
            }}
        }}

        async function preguntarIA() {{
            const input = document.getElementById('ai-input');
            const history = document.getElementById('chat-history');
            if(!input.value) return;
            
            history.innerHTML += `<div class="bubble user-bubble">${{input.value}}</div>`;
            const val = input.value;
            input.value = "";
            
            const res = await fetch('/api/ask_ai', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ pregunta: val }})
            }});
            const data = await res.json();
            history.innerHTML += `<div class="bubble">${{data.respuesta}}</div>`;
            history.scrollTop = history.scrollHeight;
        }}

        async function actualizarSaldo() {{
            const res = await fetch(`/api/get_balance?user_id=${{tg.initDataUnsafe.user.id}}`);
            const data = await res.json();
            document.getElementById('puntos').innerText = data.puntos_totales.toFixed(6);
            document.getElementById('val-top').innerText = data.puntos_totales.toFixed(2);
            document.getElementById('stake').innerText = data.puntos_staking.toFixed(2);
        }}

        async function enviarDeposito() {{
            if (!tonConnectUI.connected) {{ alert("Conecta tu wallet."); return; }}
            const transaction = {{
                validUntil: Math.floor(Date.now() / 1000) + 300,
                messages: [{{ address: "{MI_BILLETERA_RECIBO}", amount: "100000000" }}]
            }};
            try {{
                const result = await tonConnectUI.sendTransaction(transaction);
                await fetch('/api/verificar_pago', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ user_id: tg.initDataUnsafe.user.id, boc: result.boc }})
                }});
                actualizarSaldo();
            }} catch (e) {{ alert("Cancelado."); }}
        }}

        async function solicitarRetiro() {{
            const m = prompt("Monto:");
            await fetch('/api/solicitar_retiro', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: tg.initDataUnsafe.user.id, nombre: tg.initDataUnsafe.user.first_name, cantidad: parseFloat(m) }})
            }});
        }}

        async function ejecutarStake() {{
            await fetch('/api/stake_now', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: tg.initDataUnsafe.user.id }})
            }});
            actualizarSaldo();
        }}

        setTimeout(() => {{ document.getElementById('splash').style.opacity = '0'; setTimeout(()=>{{document.getElementById('splash').style.display='none'}},800)}}, 2000);
        setInterval(actualizarSaldo, 10000);
        actualizarSaldo();
    </script>
</body>
</html>
"""

# --- RUTAS DE API (Igual que antes) ---
@app.route('/')
def home(): return render_template_string(HTML_JUEGO)

@app.route('/api/get_balance')
def get_balance():
    u_id = request.args.get('user_id')
    res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
    res_stk = db.table("jugadores").select("puntos_staking").eq("user_id", u_id).single().execute()
    return {"puntos_totales": float(res_bal.data or 0), "puntos_staking": float(res_stk.data['puntos_staking'] or 0)}

@app.route('/api/stake_now', methods=['POST'])
def stake_now():
    u_id = request.get_json().get('user_id')
    res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
    db.table("jugadores").update({"puntos": 0, "puntos_staking": float(res_bal.data), "ultimo_reclamo": "now()"}).eq("user_id", u_id).execute()
    return {"success": True}

@app.route('/api/verificar_pago', methods=['POST'])
def verificar_pago():
    data = request.get_json()
    url = f"https://toncenter.com/api/v2/getTransactions?address={MI_BILLETERA_RECIBO}&limit=5&api_key={TONCENTER_API_KEY}"
    resp = requests.get(url).json()
    if resp.get("ok"):
        for tx in resp.get("result", []):
            tx_hash = tx["transaction_id"]["hash"]
            check = db.table("pagos_procesados").select("hash").eq("hash", tx_hash).execute()
            if not check.data and "in_msg" in tx:
                val = int(tx["in_msg"]["value"]) / 1e9
                if val >= 0.09:
                    db.table("pagos_procesados").insert({"hash": tx_hash, "user_id": data.get('user_id'), "monto": val}).execute()
                    db.rpc('acreditar_puntos', {'id_usuario': data.get('user_id'), 'cantidad': val}).execute()
                    return {"success": True}
    return {"success": False}

@app.route('/api/solicitar_retiro', methods=['POST'])
async def solicitar_retiro():
    data = request.get_json()
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    async with bot_app:
        await bot_app.bot.send_message(chat_id=MI_ID_TELEGRAM, text=f"🔔 RETIRO: {data.get('nombre')} - {data.get('cantidad')} TON")
    return {"message": "Solicitud enviada."}

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    async def start(update, context):
        u = update.effective_user
        db.table("jugadores").upsert({"user_id": u.id, "nombre": u.first_name}).execute()
        kb = [[InlineKeyboardButton("💎 vIcmAr Platinum", web_app=WebAppInfo(url=f"https://{request.host}/"))]]
        await update.message.reply_text(f"Hola {u.first_name}! 🏴‍☠️ Bienvenido.", reply_markup=InlineKeyboardMarkup(kb))
    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app: await bot_app.process_update(update)
    return "ok", 200