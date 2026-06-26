# STB Bot Monitor

Bot Telegram untuk monitoring server STB (Set-Top Box) via SSH.

## Fitur

- Monitoring status STB: CPU temperature, RAM usage, storage usage, uptime, load average
- Cek koneksi STB
- Ping test ke target tertentu
- Speedtest internet (via speedtest-cli)
- Reboot STB dari jarak jauh
- Tombol interaktif untuk refresh data
- Filter user berdasarkan ID Telegram (opsional)
- Multi-STB dalam satu bot

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
| `/status <nama>` | Menampilkan status lengkap STB |
| `/cpu <nama>` | Menampilkan temperature CPU |
| `/ram <nama>` | Menampilkan penggunaan RAM |
| `/storage <nama>` | Menampilkan penggunaan storage |
| `/uptime <nama>` | Menampilkan uptime |
| `/ping <nama> [target]` | Ping test (default: 8.8.8.8) |
| `/speedtest <nama>` | Menjalankan speedtest (butuh speedtest-cli di STB) |
| `/reboot <nama>` | Mereset STB (konfirmasi via `/reboot_confirm`) |
| `/reboot_confirm <nama>` | Konfirmasi reboot STB |

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

- **Speedtest**: Pastikan `speedtest-cli` sudah terinstall di STB (`apt install speedtest-cli`)
- **Reboot**: User SSH harus memiliki akses `sudo reboot` tanpa password. Tambahkan ke `/etc/sudoers`:
  ```
  username ALL=(ALL) NOPASSWD: /sbin/reboot
  ```
- Pastikan port SSH (22) dapat diakses dari server tempat bot dijalankan
- Untuk produksi, sebaiknya gunakan SSH key authentication daripada password

## Lisensi

MIT
