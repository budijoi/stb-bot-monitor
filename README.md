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

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Edit file `stb_list.json`:

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

4. Jalankan bot:

```bash
python bot.py
```

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
