from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import os

app = Flask(__name__)

# Mengambil Public Key dari Environment Variables (Bukan Bot Token)
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")

def verify_signature(req):
    """Fungsi wajib untuk memverifikasi bahwa request benar-benar dari Discord"""
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
    # 1. Verifikasi Keamanan (WAJIB)
    if not verify_signature(request):
        return "Invalid request signature", 401
    
    data = request.json
    
    # 2. Handle PING dari Discord (Saat pertama kali setup URL di portal)
    if data.get("type") == 1:
        return jsonify({"type": 1})
    
    # 3. Handle Slash Command (/create_event)
    if data.get("type") == 2:
        command_name = data["data"]["name"]
        
        if command_name == "create_event":
            # Merakit UI Embed & Tombol secara manual menggunakan JSON
            response_payload = {
                "type": 4, # 4 = Mengirim pesan balasan
                "data": {
                    "embeds": [{
                        "title": "⚔️ NODE WAR",
                        "description": "Klik tombol di bawah untuk mendaftar.",
                        "color": 16753920, # Warna dalam format Decimal
                        "fields": [
                            {"name": "Tim Utama (0/30)", "value": "_Kosong_"},
                            {"name": "Cadangan (0/∞)", "value": "_Kosong_"}
                        ]
                    }],
                    "components": [{
                        "type": 1, # Action Row (Wajib untuk menampung tombol)
                        "components": [
                            {
                                "type": 2, # Tombol
                                "label": "Join Tim Utama",
                                "style": 3, # Hijau
                                "custom_id": "join_main"
                            },
                            {
                                "type": 2,
                                "label": "Join Cadangan",
                                "style": 1, # Biru
                                "custom_id": "join_secondary"
                            }
                        ]
                    }]
                }
            }
            return jsonify(response_payload)

    # 4. Handle Interaksi Tombol Diklik
    if data.get("type") == 3:
        button_id = data["data"]["custom_id"]
        user_name = data["member"]["user"]["username"]
        
        # PENTING: Karena Vercel stateless, proses modifikasi array (CRUD antrean) 
        # harus Anda hubungkan ke Database eksternal di sini sebelum membalas interaksi.
        
        return jsonify({
            "type": 4, 
            "data": {
                "content": f"Halo {user_name}, kamu mengklik {button_id}! (Logika database belum terpasang)",
                "flags": 64 # Ephemeral (Hanya dilihat oleh user yang klik)
            }
        })

    return jsonify({"error": "Unknown type"}), 400