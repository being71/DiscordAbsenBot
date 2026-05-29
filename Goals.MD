# Goals

## Phase 1: Fondasi Arsitektur & Otentikasi (Minggu 1-2)
Fokus awal adalah menyiapkan infrastruktur web dan menghubungkannya dengan ekosistem yang sudah ada (Discord).

- **Setup Framework & Hosting**: Inisialisasi proyek web (disarankan Next.js) dan hubungkan repository ke Vercel untuk auto-deployment.
- **Integrasi Firebase**: Setup Firebase Firestore (untuk database statistik), Firebase Storage (untuk menyimpan gambar screenshot NW), dan Firebase Auth.
- **Discord SSO (Single Sign-On)**: Gunakan otentikasi Discord di Firebase Auth. Ini memungkinkan anggota guild login ke website menggunakan akun Discord mereka.
- **Sinkronisasi Database**: Buat koleksi di Firestore untuk menampung data pemain, mencakup: Discord_ID, Family_Name, Guild_Name (Blazing/Nostrae/Ducky), dan Default_Role.
- **Tips Role**: Buat klasifikasi class dari awal. Misalnya, pemain yang memegang class Dosa atau Musa otomatis masuk ke kategori Main DPS/Flanker, sementara Shai masuk ke Support.

## Phase 2: Mesin OCR & Validasi Data (Minggu 3-4)
Ini adalah inti dari backend Anda. Gambar yang diunggah harus bisa dibaca dengan akurat.

- **Sistem Upload Gambar**: Buat halaman dashboard admin (khusus officer) untuk mengunggah 3 screenshot (dari masing-masing guild). Gambar ini masuk ke Firebase Storage.
- **Integrasi Cloud Vision API**: Karena Anda menggunakan ekosistem Firebase (Google), menggunakan Google Cloud Vision API adalah pilihan OCR paling mulus untuk membaca teks pada gambar (Mendeteksi Family Name, Kills, DMG Dealt, Ally HP Healed, dll).
- **Dashboard Validasi (Krusial)**: OCR tidak selalu 100% akurat. Sebelum data permanen masuk ke Firestore, buat halaman preview berbentuk tabel yang menampilkan hasil bacaan mesin. Admin bisa mengedit angka yang salah ketik (misal: mesin membaca "8" sebagai "B") lalu menekan tombol "Save to Database".

## Phase 3: Pengembangan Fitur Bot Discord (Minggu 5)
Karena bot Discord Attendance Tracker Anda sudah berjalan, mari kita tingkatkan fungsinya agar tersinkronisasi dengan website Vercel/Firebase Anda.

- **Integrasi Database**: Hubungkan bot Discord secara langsung ke Firebase Firestore agar mereka membaca sumber data yang sama.
- **Perombakan Attendance**: Saat OCR selesai memproses data Node War di web, perintahkan mesin untuk otomatis memanggil webhook ke bot Discord. Bot akan mencentang otomatis daftar absensi berdasarkan Family Name yang terdeteksi di gambar. Officer tidak perlu lagi mengabsen manual!
- **Command Baru (/mystats & /nw_result)**:
  - Pemain bisa mengetik `/mystats` di Discord, dan bot akan menarik data dari Firestore untuk menampilkan ringkasan KDA dan kontribusi mereka di NW terakhir.
  - Setelah admin mengunggah hasil NW di web, bot otomatis mengirimkan pengumuman ke channel Discord: "Statistik Node War hari ini sudah diunggah! Cek performamu di [Link Vercel Anda]".

## Phase 4: Visualisasi Data & Dashboard (Minggu 6-7)
Membangun front-end yang interaktif untuk memberikan insight kepada pemain.

- **Halaman Overview NW (Harian)**: Menampilkan metrik Match (Tanggal, Lawan, Menang/Kalah). Buat Leaderboard terpisah berdasarkan peran (Top Kills untuk DPS, Top Heals untuk Support, Top Cannon/Structure DMG untuk tim Base).
- **Grafik Trajektori (7 Hari & 30 Hari)**: Gunakan library seperti Recharts atau Chart.js. Buat grafik garis (Line Chart) untuk melihat tren Damage Dealt dan Survivability aliansi secara keseluruhan.
- **Halaman Profil Pemain**: Pemain bisa mengklik nama mereka sendiri untuk melihat grafik performa pribadi dari waktu ke waktu. Di sinilah Impact Score (pembobotan kustom berdasarkan peran yang dibahas sebelumnya) divisualisasikan.

## Phase 5: Analitik Lanjutan & Evaluasi Strategi (Minggu 8+)
Fitur advanced untuk officer Guild.

- **Guild Contribution Pie Chart**: Membandingkan kontribusi Blazing, Nostrae, dan Ducky dalam satu Node War untuk melihat keseimbangan kekuatan aliansi.
- **Death Location / Time Tracker (Opsional)**: Menganalisis kolom "Time Dead". Jika rata-rata "Time Dead" aliansi sangat tinggi di menit-menit tertentu, officer bisa mengevaluasi apakah ada miskomunikasi saat regroup atau respawn.
- **Export to CSV**: Fitur bagi officer untuk mengunduh raw data ke Excel/Google Sheets jika ingin melakukan analisis mendalam (misalnya untuk evaluasi pembagian payout atau reward guild).
