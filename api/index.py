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
            {"role": "system", "content": "Eres el Gurú Cripto de vIcmAr Platinum. Sé breve y usa emojis."},
            {"role": "user", "content": pregunta}
        ]
    }
    try:
        resp = requests.post(url, json=payload, headers=headers).json()
        return jsonify({"respuesta": resp['choices'][0]['message']['content']})
    except: return jsonify({"respuesta": "Gurú fuera de línea 🧘"}), 500

@app.route('/tonconnect-manifest.json')
def serve_manifest():
    res = jsonify({"url": f"https://{{request.host}}", "name": "vIcmAr Platinum", "iconUrl": f"https://{{request.host}}/icon.png"})
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
        .card {{ background: #1e1e1e; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #333; }}
        .btn {{ background: #0088cc; color: white; border: none; padding: 12px; border-radius: 10px; width: 100%; font-weight: bold; margin-top: 5px; cursor: pointer; }}
        
        /* Slider Custom */
        .slider-container {{ margin: 20px 0; }}
        input[type=range] {{ width: 100%; height: 8px; border-radius: 5px; background: #333; outline: none; -webkit-appearance: none; }}
        input[type=range]::-webkit-slider-thumb {{ -webkit-appearance: none; width: 20px; height: 20px; background: #0088cc; border-radius: 50%; cursor: pointer; }}

        /* Navigation */
        .nav-bar {{ position: fixed; bottom: 0; width: 100%; height: 60px; background: #1a1a1a; display: flex; border-top: 1px solid #333; }}
        .nav-item {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 11px; color: #888; }}
        .active-tab {{ color: #0088cc; }}
        
        #chat-history {{ height: 250px; overflow-y: auto; text-align: left; margin-bottom: 10px; }}
        .bubble {{ background: #222; padding: 10px; border-radius: 10px; margin-bottom: 8px; border-left: 3px solid #0088cc; font-size: 14px; }}
        #ref-link {{ background: #111; padding: 10px; border-radius: 8px; color: #0088cc; font-size: 11px; word-break: break-all; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="top-bar">
        <div style="font-size: 14px; color: #0088cc; font-weight: bold;">vIcmAr: <span id="val-top">0.00</span></div>
        <div id="ton-connect-button"></div>
    </div>

    <div id="screen-guru" class="screen active">
        <div id="chat-history"><div class="bubble">¡Hola! Soy tu Gurú Platinum. Preguntame lo que quieras. 🤖</div></div>
        <div style="display:flex; gap:5px;">
            <input type="text" id="ai-input" style="flex-grow:1; background:#222; border:1px solid #444; color:white; padding:10px; border-radius:10px;" placeholder="Duda sobre cripto...">
            <button onclick="preguntarIA()" style="background:#0088cc; border:none; padding:10px 15px; border-radius:10px; color:white;">→</button>
        </div>
    </div>

    <div id="screen-stake" class="screen">
        <div class="card">
            <div style="font-size: 12px; color: #888;">SALDO EN BILLETERA (1% Diarios)</div>
            <div style="font-size: 24px; font-weight: bold;"><span id="puntos">0.0000</span> TON</div>
        </div>

        <div class="card">
            <h3 style="margin-top:0;">Configurar Stake</h3>
            <p style="font-size: 12px; color:#aaa;">Deslizá para elegir el monto a pasar al 5% diario.</p>
            <div class="slider-container">
                <input type="range" id="stake-slider" min="0" max="0" step="0.0001" value="0" oninput="updateStakeLabel(this.value)">
                <div style="display:flex; justify-content:space-between; margin-top:10px;">
                    <span>0 TON</span>
                    <span id="stake-value" style="color:#0088cc; font-weight:bold;">0.0000 TON</span>
                </div>
            </div>
            <button class="btn" onclick="enviarAlStake()">INVERTIR EN STAKE</button>
        </div>

        <div class="card">
            <div style="font-size: 12px; color: #888;">TOTAL EN STAKE (5% o 20% Diarios)</div>
            <div style="font-size: 24px; font-weight: bold; color: #f1c40f;"><span id="stake-total">0.0000</span> TON</div>
        </div>
        
        <button class="btn" style="background:#2ecc71;" onclick="enviarDeposito()">DEPOSITAR (0.10 TON)</button>
        <button class="btn" style="background:#222; border:1px solid #444;" onclick="solicitarRetiro()">RETIRAR</button>
    </div>

    <div id="screen-ref" class="screen">
        <div class="card" style="text-align:center;">
            <h2 style="color:#e74c3c; margin:0;">VIP 20%</h2>
            <p id="ref-status">Referidos: 0 / 5</p>
            <p style="font-size: 12px; color:#888;">Invitá a 5 amigos para que tu sección de Stake rinda un 20% diario sobre el capital invertido.</p>
            <div id="ref-link">Generando link...</div>
            <button class="btn" onclick="compartir()">COMPARTIR LINK</button>
        </div>
    </div>

    <div class="nav-bar">
        <div class="nav-item active-tab" onclick="switchTab('guru', 0)"><span>🤖</span><span>Gurú</span></div>
        <div class="nav-item" onclick="switchTab('stake', 1)"><span>📊</span><span>Inversión</span></div>
        <div class="nav-item" onclick="switchTab('ref', 2)"><span>👥</span><span>Referidos</span></div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        const userId = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : 123;
        const tonConnectUI = new TON_CONNECT_UI.TonConnectUI({{
            manifestUrl: 'https://' + window.location.host + '/tonconnect-manifest.json',
            buttonRootId: 'ton-connect-button'
        }});

        let saldoDisponible = 0;

        function switchTab(screenId, index) {{
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active-tab'));
            document.getElementById('screen-' + screenId).classList.add('active');
            document.querySelectorAll('.nav-item')[index].classList.add('active-tab');
        }}

        function updateStakeLabel(val) {{
            document.getElementById('stake-value').innerText = parseFloat(val).toFixed(4) + " TON";
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
            
            saldoDisponible = data.puntos_totales;
            document.getElementById('puntos').innerText = saldoDisponible.toFixed(6);
            document.getElementById('val-top').innerText = saldoDisponible.toFixed(2);
            document.getElementById('stake-total').innerText = data.puntos_staking.toFixed(4);
            document.getElementById('ref-status').innerText = `Referidos: ${{data.referidos_count}} / 5`;
            
            // Actualizar Slider
            const slider = document.getElementById('stake-slider');
            slider.max = saldoDisponible;
            
            // Link de Ref
            const botUser = "DeposiTon"; // <-- CAMBIAR
            document.getElementById('ref-link').innerText = `https://t.me/${{botUser}}?start=${{userId}}`;
        }}

        async function enviarAlStake() {{
            const monto = document.getElementById('stake-slider').value;
            if(monto <= 0) return alert("Elegí un monto.");
            const res = await fetch('/api/stake_amount', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ user_id: userId, cantidad: parseFloat(monto) }})
            }});
            if(res.ok) {{ alert("¡Inversión exitosa!"); actualizarSaldo(); }}
        }}

        async function enviarDeposito() {{
            if (!tonConnectUI.connected) return alert("Conectá tu wallet.");
            const tx = {{ validUntil: Math.floor(Date.now()/1000)+300, messages: [{{ address: "{MI_BILLETERA_RECIBO}", amount: "100000000" }}] }};
            try {{
                const result = await tonConnectUI.sendTransaction(tx);
                await fetch('/api/verificar_pago', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ user_id: userId, boc: result.boc }}) }});
                actualizarSaldo();
            }} catch(e) {{ alert("Cancelado"); }}
        }}

        function compartir() {{
            const url = document.getElementById('ref-link').innerText;
            window.open(`https://t.me/share/url?url=${{encodeURIComponent(url)}}&text=Sumate a vIcmAr!`);
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

@app.route('/api/stake_amount', methods=['POST'])
def stake_amount():
    data = request.get_json()
    u_id, cant = data.get('user_id'), data.get('cantidad')
    # Consolidamos intereses primero
    res_bal = db.rpc('calcular_saldo_total', {'jugador_id': int(u_id)}).execute()
    db.table("jugadores").update({
        "puntos": float(res_bal.data) - cant,
        "puntos_staking": db.table("jugadores").select("puntos_staking").eq("user_id", u_id).single().execute().data['puntos_staking'] + cant,
        "ultimo_reclamo": "now()"
    }).eq("user_id", u_id).execute()
    return {"success": True}

# (Mantener rutas /api/verificar_pago y /api/index iguales)