# STB Bot Monitor

Bot Telegram untuk monitoring server STB (Set-Top Box) via SSH.

## Fitur

<img width="382" height="687" alt="Screenshot 2026-06-27 131312" src="https://github.com/user-attachments/assets/e866bac6-fdcf-4288-9591-5145a998eb09" />
<img width="382" height="687" alt="Screenshot 2026-06-27 134205" src="https://github.com/user-attachments/assets/a9577342-c2fa-4c7d-82d4-86dd63516e78" />

- Monitoring status STB: CPU temperature, RAM usage, storage usage, uptime, load average
- Cek koneksi STB (SSH)
- Ping test ke target tertentu (default 8.8.8.8)
- Speedtest internet (mendukung speedtest-cli & speedtest Ookla)
- Reboot STB dari jarak jauh
- Tombol interaktif untuk refresh data
- Filter user berdasarkan ID Telegram (opsional)
- Multi-STB dalam satu bot
- **Notifikasi otomatis** via Telegram:
  - Power On / Power Off STB
  - Internet hilang / kembali
  - CPU Overheating (>90°C) dan pulih normal
- Update script via Telegram (`/script_update`)
- Hapus bot dari server via Telegram (`/delete_bot`)

## Persyaratan

- Python 3.8+
- STB dengan SSH server aktif
- Token bot Telegram dari [@BotFather](https://t.me/BotFather)

## Instalasi

1. Clone repositori:

```bash
git clone https://github.com/budijoi/stb-bot-monitor.git
cd stb-bot-monitor
```

2. Install Python dan pip (khusus Armbian/Debian/Ubuntu):

```bash
apt update && apt install -y python3 python3-pip
```

3. Install dependencies — pilih salah satu metode:

   > **Catatan:** Script cukup diinstall di **satu perangkat saja** (VPS, PC, atau salah satu STB).
   > Bot akan SSH ke semua STB yang terdaftar di `stb_list.json` dari satu tempat tersebut.
   > Pastikan perangkat tempat bot berjalan bisa mengakses port SSH semua STB.

   **Metode A — Virtual environment (disarankan):**

   ```bash
   apt install -y python3-venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   **Metode B — Bypass system package protection:**

   ```bash
   pip install --break-system-packages -r requirements.txt
   ```

4. Edit file `stb_list.json`:

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "allowed_users": [123456789],
  "stb_list": [
    {
      "name": "stb-ruang-tamu",
      "host": "192.168.1.100",
      "port": 22,
      "username": "root",
      "password": "password123"
    }
  ]
}
```

| Field | Keterangan |
|---|---|
| `bot_token` | Token bot dari BotFather |
| `allowed_users` | Array ID Telegram yang diizinkan (kosongkan jika ingin publik) |
| `stb_list` | Daftar STB yang akan dimonitor |
| `name` | Nama unik STB (digunakan di command) |
| `host` | Alamat IP atau domain STB |
| `port` | Port SSH (default: 22) |
| `username` | Username SSH |
| `password` | Password SSH |

5. Jalankan bot:

   ```bash
   python bot.py
   ```

   > Jika menggunakan virtual environment, aktifkan dulu: `source venv/bin/activate`

## Command Bot

| Perintah | Deskripsi |
|---|---|
| `/start` | Menampilkan menu bantuan |
| `/list` | Menampilkan daftar STB dengan tombol interaktif |
| `/status [nama]` | Status lengkap STB (tanpa arg = pilih dari tombol) |
| `/cpu <nama>` | Temperature CPU |
| `/ram <nama>` | Penggunaan RAM |
| `/storage <nama>` | Penggunaan storage |
| `/uptime <nama>` | Uptime |
| `/ping [nama] [target]` | Ping test (tanpa arg = pilih dari tombol, default target 8.8.8.8) |
| `/speedtest [nama]` | Speedtest (tanpa arg = pilih dari tombol) |
| `/reboot [nama]` | Reboot STB (tanpa arg = pilih dari tombol, konfirmasi `ya`/`tidak`) |
| `/cancel` | Batalkan proses reboot |
| `/restart` | Restart bot Telegram |
| `/test_notif` | Kirim test notifikasi ke pengguna |
| `/check_update` | Cek update script dari git remote |
| `/script_update` | Update script (git pull) lalu restart |
| `/delete_bot` | Hapus bot dari server (konfirmasi via `/delete_bot_confirm`) |
| `/delete_bot_confirm` | Konfirmasi hapus bot |
| `/monitor on/off` | Aktifkan/nonaktifkan notifikasi monitoring otomatis |

## Notifikasi Otomatis (Background Monitoring)

Bot akan mengirim notifikasi ke Telegram secara otomatis untuk event berikut:

| Event | Notifikasi | Keterangan |
|---|---|---|
| ✅ Power On | STB menyala dan SSH dapat diakses | Deteksi perubahan dari offline ke online |
| ⚠️ Power Off | STB tidak merespons SSH | Deteksi perubahan dari online ke offline |
| 🌐 Internet Hilang | STB tidak bisa ping ke 8.8.8.8 | Deteksi perubahan koneksi internet |
| 🌐 Internet Kembali | STB bisa ping ke 8.8.8.8 kembali | Deteksi perubahan |
| 🔥 CPU Overheating | Suhu CPU > 90°C selama ~10 detik | Peringatan berkelanjutan |
| ✅ CPU Normal | Suhu CPU turun kembali di bawah 90°C | Notifikasi pemulihan |

Monitoring berjalan setiap 10 detik. Untuk mengaktifkan/menonaktifkan:

```
/monitor on    → Aktifkan notifikasi
/monitor off   → Nonaktifkan notifikasi
```

## Auto-start (Bot Aktif Setelah Reboot)

Bot tidak otomatis aktif saat STB reboot. Gunakan salah satu metode berikut:

### Opsi 1 — Systemd Service (disarankan)

```bash
cat > /etc/systemd/system/stb-bot.service << 'EOF'
[Unit]
Description=STB Bot Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/stb-bot-monitor
ExecStart=/root/stb-bot-monitor/venv/bin/python /root/stb-bot-monitor/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable stb-bot
systemctl start stb-bot
```

### Opsi 2 — Crontab

```bash
crontab -e
# Tambah baris berikut:
@reboot cd /root/stb-bot-monitor && /root/stb-bot-monitor/venv/bin/python bot.py &
```

> Sesuaikan path `venv/bin/python` jika tidak menggunakan virtual environment atau lokasi direktori berbeda.

## Manajemen Bot (Start / Stop / Restart)

Jika menggunakan systemd service:

```bash
systemctl start stb-bot      # Start bot
systemctl stop stb-bot       # Stop bot
systemctl restart stb-bot    # Restart bot
systemctl status stb-bot     # Cek status bot
journalctl -u stb-bot -f     # Lihat log bot real-time
```

Jika menjalankan manual via terminal:
```bash
# Start
cd /root/stb-bot-monitor
source venv/bin/activate
python bot.py

# Stop: tekan Ctrl+C
# Restart: Ctrl+C lalu jalankan ulang
```

## Catatan

- **Notifications**: Fitur notifikasi otomatis hanya berfungsi jika `allowed_users` diisi dengan ID Telegram yang valid
- **Speedtest**: Pastikan `speedtest-cli` sudah terinstall di STB (`apt install speedtest-cli`)
- **Reboot**: User SSH harus memiliki akses `sudo reboot` tanpa password. Tambahkan ke `/etc/sudoers`:
  ```
  username ALL=(ALL) NOPASSWD: /sbin/reboot
  ```
- Pastikan port SSH (22) dapat diakses dari server tempat bot dijalankan
- Untuk produksi, sebaiknya gunakan SSH key authentication daripada password

## Lisensi

MIT
