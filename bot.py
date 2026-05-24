import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta

# --- CONFIGURATION & JADWAL DATA ---
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

class Group:
    def __init__(self, name, group_type, capacity):
        self.name = name
        self.type = group_type  # 'Main', 'Secondary', 'None'
        self.capacity = capacity
        self.members = []

class AttendanceView(discord.ui.View):
    def __init__(self, title, description, time_str, groups):
        super().__init__(timeout=None)
        self.event_title = title
        self.event_desc = description
        self.event_time = time_str
        self.groups = groups
        
        for i, group in enumerate(self.groups):
            style = discord.ButtonStyle.success if group.type == 'Main' else \
                    discord.ButtonStyle.primary if group.type == 'Secondary' else \
                    discord.ButtonStyle.secondary
            
            button = discord.ui.Button(label=f"Join {group.name}", style=style, custom_id=f"btn_{i}")
            button.callback = self.make_callback(group)
            self.add_item(button)

    def make_callback(self, clicked_group):
        async def button_callback(interaction: discord.Interaction):
            user = interaction.user
            current_group = None

            # 1. Cek apakah user sudah ada di grup mana pun
            for g in self.groups:
                if user in g.members:
                    current_group = g
                    break

            # 2. Jika user mengklik grup yang SAMA (Mencabut status / Leave)
            if current_group == clicked_group:
                current_group.members.remove(user)
                if current_group.type == 'Main':
                    self.promote_secondary_to_main(current_group)
                await interaction.response.send_message(f"Kamu keluar dari {current_group.name}.", ephemeral=True)
            
            # 3. Jika user mengklik grup BARU (Join / Pindah)
            else:
                # EDIT LOGIKA DI SINI: Jika tipe grup BUKAN Secondary, baru cek kapasitas maksimumnya
                if clicked_group.type != 'Secondary' and len(clicked_group.members) >= clicked_group.capacity:
                    await interaction.response.send_message(f"Maaf, {clicked_group.name} sudah penuh!", ephemeral=True)
                    return
                
                # Jika sebelumnya ada di grup lain, hapus dulu dari grup lama
                if current_group:
                    current_group.members.remove(user)
                    if current_group.type == 'Main':
                        self.promote_secondary_to_main(current_group)

                # Masukkan ke grup baru
                clicked_group.members.append(user)
                await interaction.response.send_message(f"Kamu berhasil masuk ke {clicked_group.name}.", ephemeral=True)

            # 4. Update tampilan Embed
            await interaction.message.edit(embed=self.generate_embed())
        return button_callback

    def promote_secondary_to_main(self, main_group):
        secondary_group = next((g for g in self.groups if g.type == 'Secondary'), None)
        if secondary_group and len(secondary_group.members) > 0:
            if len(main_group.members) < main_group.capacity:
                promoted_user = secondary_group.members.pop(0)
                main_group.members.append(promoted_user)

    def generate_embed(self):
        embed = discord.Embed(title=self.event_title, description=self.event_desc, color=discord.Color.dark_orange())
        embed.add_field(name="Waktu Pelaksanaan", value=f"⏰ {self.event_time}", inline=False)
        
        for group in self.groups:
            member_list = "\n".join([f"{i+1}. {m.display_name}" for i, m in enumerate(group.members)])
            if not member_list:
                member_list = "_Kosong_"
            
            # EDIT DI SINI: Jika tipe grup Secondary, ubah teks kapasitas menjadi simbol ∞
            cap_text = "∞" if group.type == "Secondary" else str(group.capacity)
            cap_text = "∞" if group.type == "None" else str(group.capacity)
                
            embed.add_field(
                name=f"{group.name} ({len(group.members)}/{cap_text})", 
                value=member_list, 
                inline=False
            )
        return embed

# --- CORE BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # Menggunakan global sync otomatis saat bot menyala tanpa perlu menulis Guild ID
    try:
        synced = await bot.tree.sync()
        print(f"Berhasil menyinkronkan {len(synced)} global command(s).")
    except Exception as e:
        print(f"Gagal melakukan sinkronisasi: {e}")
    print(f'Bot {bot.user} siap digunakan!')

# --- MODERN SLASH COMMAND WITH CHOICES ---
@bot.tree.command(name="create_event", description="Membuat absensi event berdasarkan region dan hari (Jam otomatis 20:00 GMT+7)")
@app_commands.describe(
    wilayah="Pilih region wilayah pertandingan",
    hari="Pilih hari pelaksanaan untuk menentukan kapasitas sesuai tabel"
)
@app_commands.choices(wilayah=[
    app_commands.Choice(name="Tier 1: Balenos/Serendia", value="Tier 1: Balenos/Serendia"),
    app_commands.Choice(name="Tier 2: Calpheon/Ulukita", value="Tier 2: Calpheon/Ulukita"),
    app_commands.Choice(name="Tier 3: Valencia/Edania", value="Tier 3: Valencia/Edania"),
])
@app_commands.choices(hari=[
    app_commands.Choice(name="Sunday", value="Sunday"),
    app_commands.Choice(name="Monday", value="Monday"),
    app_commands.Choice(name="Tuesday", value="Tuesday"),
    app_commands.Choice(name="Wednesday", value="Wednesday"),
    app_commands.Choice(name="Thursday", value="Thursday"),
    app_commands.Choice(name="Friday", value="Friday"),
])
async def create_event(interaction: discord.Interaction, wilayah: str, hari: str):
    # 1. Ambil kapasitas secara otomatis dari database dictionary
    max_capacity = JADWAL_WILAYAH[wilayah][hari]
    
    # 2. LOGIKA BARU: Hitung tanggal otomatis berdasarkan hari yang dipilih
    hari_target_map = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    
    hari_ini = datetime.now()
    hari_ini_idx = hari_ini.weekday() # Mengembalikan angka 0 (Monday) - 6 (Sunday)
    hari_target_idx = hari_target_map[hari]
    
    # Hitung selisih hari dari hari ini ke hari target
    selisih_hari = (hari_target_idx - hari_ini_idx) % 7
    
    # Jika hari yang dipilih adalah HARI INI, selisihnya 0. 
    # Jika admin ingin membuat untuk minggu depan padahal harinya sama, logika % 7 ini bisa disesuaikan.
    
    tanggal_target = hari_ini + timedelta(days=selisih_hari)
    waktu_lengkap = f"{tanggal_target.strftime('%d/%m/%y')} ({hari}), 20:00 GMT+7"
    
    title = f"⚔️ NODE WAR: {wilayah.upper()}"
    description = f"Pendaftaran Node War wilayah **{wilayah}** untuk hari **{hari}**. Kuota otomatis disesuaikan dengan regulasi tabel."

    # 3. Setup Group
    groups = [
        Group(name="Mainball", group_type="Main", capacity=max_capacity-5),
        Group(name="Team Defense", group_type="Secondary", capacity=max_capacity-max_capacity+5),
        Group(name="Waitlist", group_type="None", capacity=9999),
        Group(name="Absen", group_type="None", capacity=9999)
    ]
    
    view = AttendanceView(title, description, waktu_lengkap, groups)
    embed = view.generate_embed()
    
    await interaction.response.send_message(embed=embed, view=view)

import os
from dotenv import load_dotenv
load_dotenv()
bot.run(os.getenv('DISCORD_TOKEN'))