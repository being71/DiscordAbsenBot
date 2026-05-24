from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Mengambil Public Key dari Environment Variables Vercel
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")

# --- DATABASE JADWAL ---
JADWAL_WILAYAH = {
    "Tier 1: Balenos/Serendia": {
        "Sunday": 30, "Monday": 25, "Tuesday": 30, "Wednesday": 25, "Thursday": 30, "Friday": 25
    },
    "Tier 2: Calpheon/Ulukita": {
        "Sunday": 50, "Monday": 40, "Tuesday": 40, "Wednesday": 40, "Thursday": 40, "Friday": 50
    },
    "Tier 3: Valencia/Edania": {
        "Sunday": 75, "Monday": 55, "Tuesday": 55, "Wednesday": 75, "Thursday": 55, "Friday": 75
    }
}

def verify_signature(req):
    """Fungsi wajib verifikasi keamanan Discord"""
    if not PUBLIC_KEY:
        return False
        
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    signature = req.headers.get("X-Signature-Ed25519")
    timestamp = req.headers.get("X-Signature-Timestamp")
    
    if not signature or not timestamp:
        return False
        
    body = req.data.decode("utf-8")
    try:
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except BadSignatureError:
        return False

@app.route('/api/interactions', methods=['POST'])
def interactions():
    # 1. Verifikasi Keamanan
    if not verify_signature(request):
        return "Invalid request signature", 401
    
    data = request.json
    
    # 2. Handle PING dari Discord (Setup Awal)
    if data.get("type") == 1:
        return jsonify({"type": 1})
    
    # 3. Handle Slash Command (/create_event)
    if data.get("type") == 2 and data["data"]["name"] == "create_event":
        
        # Ekstrak input opsi dari pengguna (Wilayah & Hari)
        options = data["data"].get("options", [])
        wilayah = next((opt["value"] for opt in options if opt["name"] == "wilayah"), "Tier 1: Balenos/Serendia")
        hari = next((opt["value"] for opt in options if opt["name"] == "hari"), "Sunday")

        # --- LOGIKA TANGGAL & KAPASITAS (Sama persis dengan kode Anda) ---
        max_capacity = JADWAL_WILAYAH[wilayah][hari]
        
        hari_target_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        hari_ini = datetime.now()
        hari_ini_idx = hari_ini.weekday()
        hari_target_idx = hari_target_map[hari]
        
        selisih_hari = (hari_target_idx - hari_ini_idx) % 7
        tanggal_target = hari_ini + timedelta(days=selisih_hari)
        waktu_lengkap = f"{tanggal_target.strftime('%d/%m/%y')} ({hari}), 20:00 GMT+7"
        
        # --- PERHITUNGAN SLOT (Sama persis dengan kode Anda) ---
        mainball_cap = max_capacity - 5
        defense_cap = 5 # (max_capacity - max_capacity + 5)
        
        # --- MERAKIT JSON UNTUK TAMPILAN DISCORD ---
        response_payload = {
            "type": 4, 
            "data": {
                "embeds": [{
                    "title": f"⚔️ NODE WAR: {wilayah.upper()}",
                    "description": f"Pendaftaran Node War wilayah **{wilayah}** untuk hari **{hari}**. Kuota otomatis disesuaikan dengan regulasi tabel.",
                    "color": 15105570, # Equivalent dari discord.Color.dark_orange()
                    "fields": [
                        {
                            "name": "Waktu Pelaksanaan", 
                            "value": f"⏰ {waktu_lengkap}"
                        },
                        {
                            "name": f"Mainball (0/{mainball_cap})", 
                            "value": "_Kosong_"
                        },
                        {
                            "name": f"Team Defense (0/{defense_cap})", 
                            "value": "_Kosong_"
                        },
                        {
                            "name": "Waitlist (0/∞)", 
                            "value": "_Kosong_"
                        },
                        {
                            "name": "Absen (0/∞)", 
                            "value": "_Kosong_"
                        }
                    ]
                }],
                "components": [{
                    "type": 1, # Action Row (Wajib untuk menampung tombol)
                    "components": [
                        {
                            "type": 2, "label": "Join Mainball", "style": 3, "custom_id": "btn_mainball"
                        },
                        {
                            "type": 2, "label": "Join Team Defense", "style": 1, "custom_id": "btn_defense"
                        },
                        {
                            "type": 2, "label": "Join Waitlist", "style": 2, "custom_id": "btn_waitlist"
                        },
                        {
                            "type": 2, "label": "Join Absen", "style": 2, "custom_id": "btn_absen"
                        }
                    ]
                }]
            }
        }
        return jsonify(response_payload)

    # 4. Handle Interaksi Saat Tombol Diklik
    if data.get("type") == 3:
        user_name = data["member"]["user"]["username"]
        button_id = data["data"]["custom_id"]
        
        # Tombol akan merespons, tetapi teks Embed belum berubah karena butuh Database
        return jsonify({
            "type": 4, 
            "data": {
                "content": f"Sip {user_name}, command klik diterima! (Fitur update teks sedang dalam pengembangan)",
                "flags": 64 # Ephemeral
            }
        })

    return jsonify({"error": "Unknown type"}), 400