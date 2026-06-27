import logging
import os
import sys
import asyncio
import subprocess
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler

from config import load_config
from stb_monitor import (
    get_cpu_temp, get_ram_usage, get_storage_usage, get_uptime,
    get_load_average, check_connection, ping_test, speedtest_result,
    reboot_stb, get_all_status, async_ssh
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

config = load_config()
stb_list = config.get("stb_list", [])
allowed_users = config.get("allowed_users", [])


def get_stb_by_name(name: str):
    for stb in stb_list:
        if stb["name"] == name:
            return stb
    return None


def auth_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if allowed_users and user_id not in allowed_users:
            await update.message.reply_text("⛔ Anda tidak memiliki izin untuk menggunakan bot ini.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        await update.message.reply_text("⛔ Anda tidak memiliki izin.")
        return

    text = (
        "🤖 *STB Monitor By Budijoi*\n\n"
        "Bot untuk monitoring server STB.\n\n"
        "*Commands:*\n"
        "/list - Lihat daftar STB\n"
        "/status <namastb> - Status lengkap STB\n"
        "/ping <namastn> - Ping test STB\n"
        "/speedtest <namastb> - Speedtest STB\n"
        "/reboot <nama> - Reboot STB (balas ya/tidak)\n"
        "/restart - Restart bot Telegram\n"
        "/check_update - Cek update script\n"
        "/script_update - Update script dari git\n"
        "/delete_bot - Hapus bot dari server\n"
        "/monitor on/off - Aktifkan/nonaktifkan notifikasi monitoring\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def list_stb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not stb_list:
        await update.message.reply_text("📭 Tidak ada STB terdaftar.")
        return

    keyboard = [
        [InlineKeyboardButton(f"🖥 {stb['name']} ({stb['host']})", callback_data=f"status_{stb['name']}")]
        for stb in stb_list
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 *Daftar STB:*\nKlik untuk melihat status:", reply_markup=reply_markup, parse_mode="Markdown")


def stb_selection_keyboard(action: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🖥 {stb['name']} ({stb['host']})", callback_data=f"{action}_{stb['name']}")]
        for stb in stb_list
    ])


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("status_"):
        name = data.replace("status_", "")
        await show_status(query, context, name)
    elif data.startswith("refresh_"):
        name = data.replace("refresh_", "")
        await show_status(query, context, name, edit=True)
    elif data.startswith("ping_"):
        name = data.replace("ping_", "")
        await cmd_ping_callback(query, context, name)
    elif data.startswith("speedtest_"):
        name = data.replace("speedtest_", "")
        await cmd_speedtest_callback(query, context, name)
    # reboot_ handled by ConversationHandler


async def show_status(query, context: ContextTypes.DEFAULT_TYPE, name: str, edit=False):
    stb = get_stb_by_name(name)
    if not stb:
        await query.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    msg = await query.message.reply_text(f"🔍 Mengambil data {name}...")

    results = await get_all_status(
        stb["host"], stb.get("port", 22), stb["username"], stb["password"]
    )

    text = (
        f"🖥 *Status STB: {name}*\n"
        f"├ 🌐 Host: `{stb['host']}`\n"
        f"├ 🔗 Koneksi: {results['connection']}\n"
        f"├ 🌡 CPU Temp: {results['cpu_temp']}\n"
        f"├ 🧠 RAM: {results['ram']}\n"
        f"├ 💾 Storage: {results['storage']}\n"
        f"├ ⏱ Uptime: {results['uptime']}\n"
        f"└ 📊 Load: {results['load']}"
    )

    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{name}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        if not stb_list:
            await update.message.reply_text("📭 Tidak ada STB terdaftar.")
            return
        await update.message.reply_text("📋 Pilih STB:", reply_markup=stb_selection_keyboard("status"))
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan. Gunakan /list untuk melihat daftar.")
        return

    msg = await update.message.reply_text(f"🔍 Mengambil data {name}...")

    results = await get_all_status(
        stb["host"], stb.get("port", 22), stb["username"], stb["password"]
    )

    text = (
        f"🖥 *Status STB: {name}*\n"
        f"├ 🌐 Host: `{stb['host']}`\n"
        f"├ 🔗 Koneksi: {results['connection']}\n"
        f"├ 🌡 CPU Temp: {results['cpu_temp']}\n"
        f"├ 🧠 RAM: {results['ram']}\n"
        f"├ 💾 Storage: {results['storage']}\n"
        f"├ ⏱ Uptime: {results['uptime']}\n"
        f"└ 📊 Load: {results['load']}"
    )

    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{name}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def cmd_cpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /cpu <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    result = await get_cpu_temp(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(f"🌡 *CPU Temperature {name}:*\n{result}", parse_mode="Markdown")


async def cmd_ram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /ram <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    result = await get_ram_usage(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(f"🧠 *RAM Usage {name}:*\n{result}", parse_mode="Markdown")


async def cmd_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /storage <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    result = await get_storage_usage(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(f"💾 *Storage Usage {name}:*\n{result}", parse_mode="Markdown")


async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /uptime <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    result = await get_uptime(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(f"⏱ *Uptime {name}:*\n{result}", parse_mode="Markdown")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        if not stb_list:
            await update.message.reply_text("📭 Tidak ada STB terdaftar.")
            return
        await update.message.reply_text("📋 Pilih STB untuk ping:", reply_markup=stb_selection_keyboard("ping"))
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    target = context.args[1] if len(context.args) > 1 else "8.8.8.8"
    await update.message.reply_text(f"📡 Ping {name} ke {target}...")
    result = await ping_test(stb["host"], stb.get("port", 22), stb["username"], stb["password"], target)
    await update.message.reply_text(f"📡 *Ping Result {name} ke {target}:*\n{result}", parse_mode="Markdown")


async def cmd_ping_callback(query, context: ContextTypes.DEFAULT_TYPE, name: str):
    stb = get_stb_by_name(name)
    if not stb:
        await query.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return
    await query.message.reply_text(f"📡 Ping {name} ke 8.8.8.8...")
    result = await ping_test(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await query.message.reply_text(f"📡 *Ping Result {name}:*\n{result}", parse_mode="Markdown")


async def cmd_speedtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        if not stb_list:
            await update.message.reply_text("📭 Tidak ada STB terdaftar.")
            return
        await update.message.reply_text("📋 Pilih STB untuk speedtest:", reply_markup=stb_selection_keyboard("speedtest"))
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    await update.message.reply_text(f"⏳ Menjalankan speedtest pada {name} (mungkin butuh waktu)...")
    result = await speedtest_result(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(f"📶 *Speedtest {name}:*\n{result}", parse_mode="Markdown")


async def cmd_speedtest_callback(query, context: ContextTypes.DEFAULT_TYPE, name: str):
    stb = get_stb_by_name(name)
    if not stb:
        await query.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return
    await query.message.reply_text(f"⏳ Menjalankan speedtest pada {name}...")
    result = await speedtest_result(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await query.message.reply_text(f"📶 *Speedtest {name}:*\n{result}", parse_mode="Markdown")


REBOOT_CONFIRM = 0


async def cmd_reboot_callback(query, context: ContextTypes.DEFAULT_TYPE, name: str):
    stb = get_stb_by_name(name)
    if not stb:
        await query.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return ConversationHandler.END
    context.user_data["reboot_name"] = name
    await query.answer()
    await query.message.reply_text(
        f"⚠️ Yakin ingin reboot *{name}*?\nBalas: `ya` / `tidak`",
        parse_mode="Markdown"
    )
    return REBOOT_CONFIRM


async def cmd_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return ConversationHandler.END

    if not context.args:
        if not stb_list:
            await update.message.reply_text("📭 Tidak ada STB terdaftar.")
            return ConversationHandler.END
        await update.message.reply_text("📋 Pilih STB untuk reboot:", reply_markup=stb_selection_keyboard("reboot"))
        return ConversationHandler.END

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return ConversationHandler.END

    context.user_data["reboot_name"] = name
    await update.message.reply_text(
        f"⚠️ Yakin ingin reboot *{name}*?\nBalas: `ya` / `tidak`",
        parse_mode="Markdown"
    )
    return REBOOT_CONFIRM


async def reboot_handle_yesno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("reboot_name")
    if not name:
        await update.message.reply_text("⏳ Session habis, gunakan /reboot lagi.")
        return ConversationHandler.END

    jawaban = update.message.text.strip().lower()
    if jawaban == "ya":
        stb = get_stb_by_name(name)
        if not stb:
            await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
            return ConversationHandler.END
        await update.message.reply_text(f"🔄 Mereset {name}...")
        result = await reboot_stb(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(f"✅ Reboot {name} dibatalkan.")

    context.user_data.pop("reboot_name", None)
    return ConversationHandler.END


async def reboot_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("reboot_name", None)
    await update.message.reply_text("✅ Reboot dibatalkan.")
    return ConversationHandler.END


async def run_git(cmd: list) -> str:
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)),
                                capture_output=True, text=True, timeout=30)
        output = result.stdout.strip() or result.stderr.strip()
        return output or "OK"
    except Exception as e:
        return f"Error: {str(e)}"


async def get_git_branch() -> str:
    branch = await run_git(["git", "rev-parse", "--abbrev", "HEAD"])
    return branch if not branch.startswith("Error") else "main"


async def cmd_check_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    branch = await get_git_branch()
    await update.message.reply_text(f"🔍 Memeriksa update (branch: {branch})...")
    await run_git(["git", "fetch"])
    status_result = await run_git(["git", "status", "-sb"])

    behind = await run_git(["git", "rev-list", "--count", f"HEAD..origin/{branch}"])
    if behind.isdigit() and int(behind) > 0:
        text = (
            f"📢 *Update tersedia!*\n"
            f"├ Branch: `{branch}`\n"
            f"├ {behind} commit di belakang\n"
            f"├ Status: `{status_result}`\n"
            f"└ Gunakan /script_update untuk update"
        )
    else:
        text = f"✅ *Bot sudah versi terbaru.*\nStatus: `{status_result}`"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_script_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    branch = await get_git_branch()
    await update.message.reply_text(f"📥 Mengupdate script dari branch `{branch}`...")
    pull_result = await run_git(["git", "pull", "origin", branch])

    if "Already up to date" in pull_result:
        await update.message.reply_text("✅ Script sudah versi terbaru.")
        return

    text = f"📥 *Update selesai!*\n```\n{pull_result}\n```\n🔄 Bot akan merestart..."
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info("Script updated via Telegram, restarting...")
    os._exit(0)


async def cmd_delete_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    await update.message.reply_text(
        "⚠️ *PERINGATAN!* Ini akan menghapus seluruh folder bot dari server!\n\n"
        "Jika yakin, gunakan:\n/delete_bot_confirm"
    )


async def cmd_delete_bot_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    await update.message.reply_text("🗑 Menghapus bot...")
    bot_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        subprocess.run(["systemctl", "disable", "stb-bot"], capture_output=True)
        subprocess.run(["systemctl", "stop", "stb-bot"], capture_output=True)
        subprocess.run(["rm", "-rf", bot_dir], capture_output=True, timeout=10)
        await update.message.reply_text("✅ Bot berhasil dihapus dari server.")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal menghapus: {str(e)}")


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    await update.message.reply_text("🔄 Merestart bot...")
    logger.info("Bot restart via Telegram command.")
    os._exit(0)


# ─── Background Monitoring ─────────────────────────────────────
MONITOR_INTERVAL = 10  # detik
monitor_enabled = True

class STBMonitorState:
    def __init__(self, name: str):
        self.name = name
        self.prev_online = None
        self.prev_internet = None
        self.cpu_high_count = 0

monitor_states = {stb["name"]: STBMonitorState(stb["name"]) for stb in stb_list}


def get_monitor_text() -> str:
    return "🔴 Monitoring aktif" if monitor_enabled else "⚪ Monitoring nonaktif"


async def notify_users(bot, text: str):
    if not allowed_users:
        logger.warning("Tidak ada user untuk notifikasi (allowed_users kosong)")
        return
    for uid in allowed_users:
        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
            logger.info(f"Notifikasi terkirim ke {uid}")
        except Exception as e:
            logger.warning(f"Gagal kirim notif ke {uid}: {e}")


async def monitor_check(bot):
    if not monitor_enabled:
        return
    for stb in stb_list:
        name = stb["name"]
        state = monitor_states.get(name)
        if not state:
            continue

        host = stb["host"]
        port = stb.get("port", 22)
        user = stb["username"]
        pw = stb["password"]

        # 1. Cek koneksi (online/offline)
        conn_raw = await async_ssh(host, port, user, pw, "echo ok")
        online = conn_raw is not None and conn_raw.strip() == "ok"
        logger.info(f"[Monitor] {name} - conn_raw={conn_raw!r}, online={online}, prev_online={state.prev_online}")

        if state.prev_online is False and online:
            logger.info(f"[Monitor] TRIGGER Power On: {name}")
            await notify_users(bot,
                f"✅ *Power On* — STB `{name}` ({host}) menyala kembali.\n└ {datetime.now():%H:%M:%S %d/%m/%Y}")
        elif state.prev_online is True and not online:
            logger.info(f"[Monitor] TRIGGER Power Off: {name}")
            await notify_users(bot,
                f"⚠️ *Power Off* — STB `{name}` ({host}) tidak merespons.\n└ {datetime.now():%H:%M:%S %d/%m/%Y}")

        state.prev_online = online
        if not online:
            state.cpu_high_count = 0
            continue

        # 2. Cek koneksi internet
        internet_res = await ping_test(host, port, user, pw, target="8.8.8.8", count=2)
        internet_ok = "packet loss" in internet_res and "0%" in internet_res

        if state.prev_internet is True and not internet_ok:
            await notify_users(bot,
                f"🌐 *Internet Hilang* — STB `{name}` ({host}) kehilangan koneksi internet.\n└ {datetime.now():%H:%M:%S %d/%m/%Y}")
        elif state.prev_internet is False and internet_ok:
            await notify_users(bot,
                f"🌐 *Internet Kembali* — STB `{name}` ({host}) terhubung kembali.\n└ {datetime.now():%H:%M:%S %d/%m/%Y}")

        state.prev_internet = internet_ok

        # 3. Cek CPU temp > 90°C selama 5+ detik
        temp_raw = await get_cpu_temp(host, port, user, pw)
        try:
            temp_val = float(temp_raw.replace("°C", ""))
        except (ValueError, AttributeError):
            temp_val = 0

        if temp_val > 90:
            state.cpu_high_count += 1
            if state.cpu_high_count == 1:
                # Kirim peringatan pertama (setelah ~10 detik)
                await notify_users(bot,
                    f"🔥 *CPU Overheating* — STB `{name}`\n"
                    f"├ 🌡 Suhu: {temp_raw}\n"
                    f"├ ⏱ Durasi: ~10 detik\n"
                    f"└ {datetime.now():%H:%M:%S %d/%m/%Y}")
        else:
            if state.cpu_high_count >= 1:
                await notify_users(bot,
                    f"✅ *CPU Normal* — STB `{name}` suhu turun ke {temp_raw}.\n└ {datetime.now():%H:%M:%S %d/%m/%Y}")
            state.cpu_high_count = 0


async def cmd_test_notif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return
    await notify_users(context.bot, "🧪 *Test Notifikasi*\nJika kamu melihat ini, notifikasi berfungsi!")
    await update.message.reply_text("✅ Notifikasi test terkirim.")


async def cmd_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    global monitor_enabled
    if not context.args:
        status = "🔴 aktif" if monitor_enabled else "⚪ nonaktif"
        await update.message.reply_text(f"📡 Monitoring saat ini {status}.\nGunakan `/monitor on` atau `/monitor off`.")
        return

    if context.args[0] == "on":
        monitor_enabled = True
        await update.message.reply_text("🔴 Monitoring diaktifkan.")
    elif context.args[0] == "off":
        monitor_enabled = False
        await update.message.reply_text("⚪ Monitoring dinonaktifkan.")
    else:
        await update.message.reply_text("Gunakan: `/monitor on` atau `/monitor off`")


def main():
    if not config.get("bot_token") or config["bot_token"] == "YOUR_BOT_TOKEN_HERE":
        print("[ERROR] Bot token belum diisi! Edit stb_list.json dan isi bot_token.")
        return

    if not stb_list:
        print("[WARNING] Daftar STB kosong. Tambahkan STB di stb_list.json.")

    # Background monitoring loop
    async def monitor_loop(app: Application):
        await asyncio.sleep(3)
        if allowed_users:
            await notify_users(app.bot, "🤖 *Bot STB Monitor aktif*\nMonitoring berjalan setiap `{}` detik.".format(MONITOR_INTERVAL))
        for stb in stb_list:
            state = monitor_states.get(stb["name"])
            if not state:
                continue
            raw = await async_ssh(stb["host"], stb.get("port", 22), stb["username"], stb["password"], "echo ok")
            state.prev_online = (raw is not None and raw.strip() == "ok")
            logger.info(f"[Monitor] Baseline {stb['name']}: online={state.prev_online}")
        while True:
            await asyncio.sleep(MONITOR_INTERVAL)
            try:
                await monitor_check(app.bot)
            except Exception as e:
                logger.exception(f"[Monitor] Error: {e}")

    async def post_init(app: Application):
        asyncio.create_task(monitor_loop(app))

    app = Application.builder().token(config["bot_token"]).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_stb))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cpu", cmd_cpu))
    app.add_handler(CommandHandler("ram", cmd_ram))
    app.add_handler(CommandHandler("storage", cmd_storage))
    app.add_handler(CommandHandler("uptime", cmd_uptime))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("speedtest", cmd_speedtest))
    reboot_handler = ConversationHandler(
        entry_points=[
            CommandHandler("reboot", cmd_reboot),
            CallbackQueryHandler(cmd_reboot_callback, pattern="^reboot_"),
        ],
        states={
            REBOOT_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, reboot_handle_yesno)],
        },
        fallbacks=[CommandHandler("cancel", reboot_cancel)],
        per_message=False,
    )
    app.add_handler(reboot_handler)
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("check_update", cmd_check_update))
    app.add_handler(CommandHandler("script_update", cmd_script_update))
    app.add_handler(CommandHandler("delete_bot", cmd_delete_bot))
    app.add_handler(CommandHandler("delete_bot_confirm", cmd_delete_bot_confirm))
    app.add_handler(CommandHandler("monitor", cmd_monitor))
    app.add_handler(CommandHandler("test_notif", cmd_test_notif))
    app.add_handler(CallbackQueryHandler(button_handler))

    if not allowed_users:
        logger.warning("allowed_users kosong — notifikasi tidak akan terkirim!")
    else:
        logger.info(f"Notifikasi akan dikirim ke {len(allowed_users)} user.")

    print(f"[INFO] Bot started. {get_monitor_text()}")
    app.run_polling()


if __name__ == "__main__":
    main()
