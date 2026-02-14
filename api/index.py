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
            {"role": "system", "content": "Eres el Gurú Cripto de vIcmAr Platinum. Ayuda a novatos. Sé breve y usa emojis."},
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
        body {{ background: #121212; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; overflow: hidden; }}
        .top-bar {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: #1a1a1a; border-bottom: 1px solid #333; }}
        .screen {{ display: none; height: calc(100vh - 120px); overflow-y: auto; padding: 20px; box-sizing: border-box; }}
        .active {{ display: block; }}
        .card {{ background: #1e1e1e; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #333; position: relative; }}
        .tier-tag {{ position: absolute; top: 10px; right: 10px; background: #0088cc; padding: 2px 8px; border-radius: 5px; font-size: 10px; font-weight: bold; }}
        .locked {{ opacity: 0.4; filter: grayscale(1); }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 12px; border-radius: 10px; width: 100%; font-weight: bold; margin-top: 5px; cursor: pointer; }}
        .nav-bar {{ position: fixed; bottom: 0; width: 100%; height: 60px; background: #1a1a1a; display: flex; border-top: 1px solid #333; }}
        .nav-item {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 12px; color: #888; }}
        .active-tab {{ color: #0088cc; }}
        #chat-history {{ height: 250px; overflow-y: auto; text-align: left; margin-bottom: 10px; }}
        .bubble {{ background: #222; padding: 10px; border-radius: 10px; margin-bottom: 8px; border-left: 3px solid #0088cc; font-size: 14px; }}
        #ref-link {{ background: #111; padding: 8px; border-radius: 5px; font-size: 10px; color: #0088cc; border: 1px dashed #444; margin-top: 5px; word-break: break-all; }}
    </style>
</head>
<body>
    <div class="top-bar">
        <div style="font-size: 14px; color: #0088cc; font-weight: bold;">vIcmAr: <span id="val-top">0.00</span></div>
        <div id="ton-connect-button"></div>
    </div>

    <div id="home-screen" class="screen active">
        <div id="chat-history">
            <div class="bubble">Bienvenido a vIcmAr Platinum. ¿En qué puedo ayudarte hoy? 🚀</div>
        </div>
        <div style="display:flex; gap:5px;">
            <input type="text" id="ai-input" style="flex-grow:1; background:#222; border:1px solid #444; color:white; padding:10px; border-radius:10px;" placeholder="Duda sobre TON...">
            <button onclick="preguntarIA()" style="background:#0088cc; border:none; padding:10px 15px; border-radius:10px; color:white;">→</button>
        </div>
    </div>

    <div id="wallet-screen" class="screen">
        <div class="card">
            <span class="tier-tag">NIVEL 1%</span>
            <div style="font-size: 12px; color: #888;">SALDO DISPONIBLE</div>
            <div style="font-size: 24px; font-weight: bold;"><span id="puntos">0.0000</span> TON</div>
            <p style="color:#2ecc71; font-size:12px; margin:5px 0;">Generando 1% diario automáticamente.</p>
        </div>

        <div class="card">
            <span class="tier-tag" style="background:#f1c40f; color:black;">STAKE 5%</span>
            <div style="font-size: 12px; color: #888;">EN STAKING</div>
            <div style="font-size: 24px; font-weight: bold;"><span id="stake">0.0000</span> TON</div>
            <button class="btn" onclick="ejecutarStake()">PASAR TODO A STAKE (5%)</button>
        </div>

        <div id="card-vip" class="card locked">
            <span class="tier-tag" style="background:#e74c3c;">VIP 20%</span>
            <div style="color:#e74c3c; font-weight:bold;">MODO VIRAL ACTIVADO</div>
            <div id="ref-status" style="font-size: 12px; margin: 5px 0;">Referidos: 0 / 5</div>
            <div id="ref-link">Cargando...</div>
            <button class="btn" onclick="compartir()">INVITAR AMIGOS</button>
        </div>

        <button class="btn" style="background:#2ecc71; margin-top:10px;" onclick="enviarDeposito()">DEPOSITAR (0.10 TON)</button>
        <button class="btn" style="background:#222; border:1px solid #444;" onclick="solicitarRetiro()">RETIRAR</button>
    </div>

    <div class="nav-bar">
        <div class="nav-item active-tab" onclick="switchTab('home')"><span>🤖</span><span>Asistente</span></div>
        <div class="nav-item" onclick="switchTab('wallet')"><span>💳</span><span>Inversión</span></div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : 123;
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: 'https://bot-telegram-v2-gmny.vercel.app/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        }});

        // Link de Referido
        const botUsername = "DeposiTon"; // <-- CAMBIA ESTO
        const refLink = `https://t.me/${{botUsername}}?start=${{userId}}`;
        document.getElementById('ref-link').innerText = refLink;

        function switchTab(t) {{
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active-tab'));
            if(t==='home') {{ document.getElementById('home-screen').classList.add('active'); document.querySelectorAll('.nav-item')[0].classList.add('active-tab'); }}
            else {{ document.getElementById('wallet-screen').classList.add('active'); document.querySelectorAll('.nav-item')[1].classList.add('active-tab'); }}
        }}

        async function preguntarIA() {{
            const inp = document.getElementById('ai-input');
            const hist = document.getElementById('chat-history');
            if(!inp.value) return;
            const q = inp.value; inp.value = "";
            hist.innerHTML += `<div class="bubble" style="border-left-color:#2ecc71;">${{q}}</div>`;
            const res = await fetch('/api/ask_ai', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ pregunta: q }}) }});
            const data = await res.json();
            hist.innerHTML += `<div class="bubble">${{data.respuesta}}</div>`;
            hist.scrollTop = hist.scrollHeight;
        }}

        async function actualizarSaldo() {{
            const res = await fetch(`/api/get_balance?user_id=${{userId}}`);
            const data = await res.json();
            document.getElementById('puntos').innerText = data.puntos_totales.toFixed(6);
            document.getElementById('val-top').innerText = data.puntos_totales.toFixed(2);
            document.getElementById('stake').innerText = data.puntos_staking.toFixed(4);
            document.getElementById('ref-status').innerText = `Referidos: ${{data.referidos_count}} / 5`;
            if(data.referidos_count >= 5) document.getElementById('card-vip').classList.remove('locked');
        }}

        function compartir() {{
            const text = "💎 Sumate a vIcmAr Platinum y ganá un 20% diario. Entrá acá: ";
            window.open(`https://t.me/share/url?url=${{encodeURIComponent(refLink)}}&text=${{encodeURIComponent(text)}}`);
        }}

        async function enviarDeposito() {{
            if (!tonConnectUI.connected) {{ alert("Wallet no conectada."); return; }}
            const tx = {{ validUntil: Math.floor(Date.now()/1000)+300, messages: [{{ address: "{MI_BILLETERA_RECIBO}", amount: "100000000" }}] }};
            try {{
                const result = await tonConnectUI.sendTransaction(tx);
                await fetch('/api/verificar_pago', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ user_id: userId, boc: result.boc }}) }});
                actualizarSaldo();
            }} catch(e) {{ alert("Cancelado"); }}
        }}

        async function ejecutarStake() {{
            await fetch('/api/stake_now', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ user_id: userId }}) }});
            actualizarSaldo();
        }}

        async function solicitarRetiro() {{
            const m = prompt("Monto a retirar:");
            if(m) await fetch('/api/solicitar_retiro', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ user_id: userId, nombre: tg.initDataUnsafe.user.first_name, cantidad: m }}) }});
        }}

        setInterval(actualizarSaldo, 10000);
        actualizarSaldo();
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
    res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
    res_data = db.table("jugadores").select("puntos_staking, referidos_count").eq("user_id", u_id).single().execute()
    return {
        "puntos_totales": float(res_bal.data or 0), 
        "puntos_staking": float(res_data.data['puntos_staking'] or 0),
        "referidos_count": int(res_data.data['referidos_count'] or 0)
    }

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

@app.route('/api/index', methods=['POST'])
async def bot_handler():
    update_data = request.get_json(force=True)
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    async def start(update, context):
        u = update.effective_user
        # Lógica de Referidos
        if context.args and context.args[0].isdigit():
            referrer_id = int(context.args[0])
            if referrer_id != u.id:
                db.rpc('sumar_referido', {'id_padre': referrer_id}).execute()
        
        db.table("jugadores").upsert({"user_id": u.id, "nombre": u.first_name}).execute()
        kb = [[InlineKeyboardButton("💎 vIcmAr Platinum", web_app=WebAppInfo(url=f"https://{request.host}/"))]]
        await update.message.reply_text(f"Hola {u.first_name}! 🏴‍☠️ Bienvenido al sistema Platinum.", reply_markup=InlineKeyboardMarkup(kb))
    
    bot_app.add_handler(CommandHandler("start", start))
    update = Update.de_json(update_data, bot_app.bot)
    async with bot_app: await bot_app.process_update(update)
    return "ok", 200
``` 🏴‍☠️💎🔥