from flask import Flask, request, jsonify
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import os
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- INITIALIZE FIREBASE ---
if not firebase_admin._apps:
    private_key = os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key": private_key,
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred)

db = firestore.client()
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")

JADWAL_WILAYAH = {
    "Tier 1: Balenos/Serendia": {"Sunday": 30, "Monday": 25, "Tuesday": 30, "Wednesday": 25, "Thursday": 30, "Friday": 25},
    "Tier 2: Calpheon/Ulukita": {"Sunday": 50, "Monday": 40, "Tuesday": 40, "Wednesday": 40, "Thursday": 40, "Friday": 50},
    "Tier 3: Valencia/Edania": {"Sunday": 75, "Monday": 55, "Tuesday": 55, "Wednesday": 75, "Thursday": 55, "Friday": 75}
}

def verify_signature(req):
    if not PUBLIC_KEY: return False
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    signature = req.headers.get("X-Signature-Ed25519")
    timestamp = req.headers.get("X-Signature-Timestamp")
    if not signature or not timestamp: return False
    body = req.data.decode("utf-8")
    try:
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except BadSignatureError:
        return False

def parse_cap(field_name):
    """Mengambil angka kapasitas maksimum dari nama Field (contoh: Mainball (0/25) -> 25)"""
    try:
        return int(field_name.split('/')[-1].split(')')[0].strip())
    except:
        return 30

@app.route('/api/interactions', methods=['POST'])
def interactions():
    if not verify_signature(request):
        return "Invalid request signature", 401
    
    data = request.json
    if data.get("type") == 1:
        return jsonify({"type": 1})
    
    # === HANDLE SLASH COMMAND (/create_event) ===
    if data.get("type") == 2 and data["data"]["name"] == "create_event":
        options = data["data"].get("options", [])
        wilayah = next((opt["value"] for opt in options if opt["name"] == "wilayah"), "Tier 1: Balenos/Serendia")
        hari = next((opt["value"] for opt in options if opt["name"] == "hari"), "Sunday")

        max_capacity = JADWAL_WILAYAH[wilayah][hari]
        
        hari_target_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        hari_ini = datetime.now()
        selisih_hari = (hari_target_map[hari] - hari_ini.weekday()) % 7
        tanggal_target = hari_ini + timedelta(days=selisih_hari)
        waktu_lengkap = f"{tanggal_target.strftime('%d/%m/%y')} ({hari}), 20:00 GMT+7"
        
        mainball_cap = max_capacity - 5
        defense_cap = 5
        event_id = data["id"] # Menggunakan ID interaksi unik sebagai ID Event
        
        return jsonify({
            "type": 4, 
            "data": {
                "embeds": [{
                    "title": f"⚔️ NODE WAR: {wilayah.upper()}",
                    "description": f"Pendaftaran Node War wilayah **{wilayah}** untuk hari **{hari}**. Kuota otomatis disesuaikan dengan regulasi tabel.",
                    "color": 15105570,
                    "fields": [
                        {"name": "Waktu Pelaksanaan", "value": f"⏰ {waktu_lengkap}"},
                        {"name": f"Mainball (0/{mainball_cap})", "value": "_Kosong_"},
                        {"name": f"Team Defense (0/{defense_cap})", "value": "_Kosong_"},
                        {"name": "Waitlist (0/∞)", "value": "_Kosong_"},
                        {"name": "Absen (0/∞)", "value": "_Kosong_"}
                    ]
                }],
                "components": [{
                    "type": 1,
                    "components": [
                        {"type": 2, "label": "Join Mainball", "style": 3, "custom_id": f"mainball:{event_id}"},
                        {"type": 2, "label": "Join Team Defense", "style": 1, "custom_id": f"defense:{event_id}"},
                        {"type": 2, "label": "Join Waitlist", "style": 2, "custom_id": f"waitlist:{event_id}"},
                        {"type": 2, "label": "Join Absen", "style": 2, "custom_id": f"absen:{event_id}"}
                    ]
                }]
            }
        })

    # === HANDLE INTERAKSI TOMBOL (Join / Leave / Switch / Auto-Promotion) ===
    if data.get("type") == 3:
        custom_id = data["data"]["custom_id"]
        action, event_id = custom_id.split(":")
        
        member = data["member"]
        user_id = member["user"]["id"]
        display_name = member.get("nick") or member["user"].get("global_name") or member["user"]["username"]
        
        # Ambil data lama dari Embed asli Discord
        old_embed = data["message"]["embeds"][0]
        fields = old_embed["fields"]
        
        mainball_cap = parse_cap(fields[1]["name"])
        defense_cap = parse_cap(fields[2]["name"])
        
        # Tarik data dari Firebase Firestore
        doc_ref = db.collection("events").document(event_id)
        doc = doc_ref.get()
        
        if doc.exists:
            doc_data = doc.to_dict()
        else:
            doc_data = {"mainball": [], "defense": [], "waitlist": [], "absen": [], "names": {}}
            
        doc_data["names"][user_id] = display_name
        
        # Cari user saat ini ada di grup mana
        current_group = None
        for g in ["mainball", "defense", "waitlist", "absen"]:
            if user_id in doc_data.get(g, []):
                current_group = g
                break
                
        target_group = action

        # ======================================================================
        # FIX: AUTO-ROUTING (Jika klik Waitlist tapi Mainball kosong/belum penuh)
        # ======================================================================
        if target_group == "waitlist" and len(doc_data.get("mainball", [])) < mainball_cap:
            target_group = "mainball"
        # ======================================================================
        
        # Logika KELUAR (Klik tombol yang sama)
        if current_group == target_group:
            doc_data[current_group].remove(user_id)
            
            # Auto-promotion dari Waitlist HANYA boleh masuk ke Mainball!
            if current_group == "mainball" and doc_data.get("waitlist"):
                promoted_id = doc_data["waitlist"].pop(0)
                doc_data["mainball"].append(promoted_id)
        
        # Logika MASUK / PINDAH GRUP
        else:
            # Cek kapasitas jika targetnya grup terbatas (mainball / defense)
            if target_group in ["mainball", "defense"]:
                cap_limit = mainball_cap if target_group == "mainball" else defense_cap
                if len(doc_data.get(target_group, [])) >= cap_limit:
                    return jsonify({
                        "type": 4, "data": {"content": "❌ Maaf, slot kategori ini sudah penuh!", "flags": 64}
                    })
            
            # Hapus dari grup lama jika ada
            if current_group:
                doc_data[current_group].remove(user_id)
                
                # Auto-promotion dari Waitlist HANYA aktif jika grup yang ditinggalkan adalah Mainball
                if current_group == "mainball" and doc_data.get("waitlist"):
                    promoted_id = doc_data["waitlist"].pop(0)
                    doc_data["mainball"].append(promoted_id)
            
            # Masukkan ke grup baru
            if target_group not in doc_data: doc_data[target_group] = []
            doc_data[target_group].append(user_id)
            
        # Simpan perubahan state kembali ke Firebase Firestore
        doc_ref.set(doc_data)
        
        # Fungsi pembantu untuk menyusun daftar nama string di Embed
        def make_list_str(g_key):
            u_ids = doc_data.get(g_key, [])
            if not u_ids: return "_Kosong_"
            return "\n".join([f"{i+1}. {doc_data['names'].get(uid, 'Unknown')}" for i, uid in enumerate(u_ids)])
            
        # Rakit Embed baru dengan data terbaru dari Database
        new_fields = [
            {"name": "Waktu Pelaksanaan", "value": fields[0]["value"]},
            {"name": f"Mainball ({len(doc_data.get('mainball', []))}/{mainball_cap})", "value": make_list_str("mainball")},
            {"name": f"Team Defense ({len(doc_data.get('defense', []))}/{defense_cap})", "value": make_list_str("defense")},
            {"name": f"Waitlist ({len(doc_data.get('waitlist', []))}/∞)", "value": make_list_str("waitlist")},
            {"name": f"Absen ({len(doc_data.get('absen', []))}/∞)", "value": make_list_str("absen")}
        ]
        
        # type 7 = Mengedit pesan asli tempat tombol berada secara instan
        return jsonify({
            "type": 7,
            "data": {
                "embeds": [{
                    "title": old_embed["title"],
                    "description": old_embed["description"],
                    "color": old_embed["color"],
                    "fields": new_fields
                }],
                "components": data["message"]["components"] # Mempertahankan tombol yang sama
            }
        })

    return jsonify({"error": "Unknown type"}), 400