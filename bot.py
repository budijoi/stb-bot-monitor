import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import load_config
from stb_monitor import (
    get_cpu_temp, get_ram_usage, get_storage_usage, get_uptime,
    get_load_average, check_connection, ping_test, speedtest_result,
    reboot_stb, get_all_status
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
        "🤖 *STB Monitor Bot*\n\n"
        "Bot untuk monitoring server STB.\n\n"
        "*Commands:*\n"
        "/list - Lihat daftar STB\n"
        "/status <nama> - Status lengkap STB\n"
        "/cpu <nama> - CPU temperature\n"
        "/ram <nama> - RAM usage\n"
        "/storage <nama> - Storage usage\n"
        "/uptime <nama> - Uptime\n"
        "/ping <nama> - Ping test STB\n"
        "/speedtest <nama> - Speedtest STB\n"
        "/reboot <nama> - Reboot STB\n"
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
        await update.message.reply_text("⚠️ Gunakan: /status <nama_stb>")
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
        await update.message.reply_text("⚠️ Gunakan: /ping <nama_stb>")
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


async def cmd_speedtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /speedtest <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    await update.message.reply_text(f"⏳ Menjalankan speedtest pada {name} (mungkin butuh waktu)...")
    result = await speedtest_result(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(f"📶 *Speedtest {name}:*\n{result}", parse_mode="Markdown")


async def cmd_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /reboot <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    await update.message.reply_text(f"⚠️ Yakin ingin reboot {name}? (gunakan: /reboot_confirm {name})")


async def cmd_reboot_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed_users and update.effective_user.id not in allowed_users:
        return

    if not context.args:
        await update.message.reply_text("⚠️ Gunakan: /reboot_confirm <nama_stb>")
        return

    name = " ".join(context.args)
    stb = get_stb_by_name(name)
    if not stb:
        await update.message.reply_text(f"❌ STB '{name}' tidak ditemukan.")
        return

    await update.message.reply_text(f"🔄 Mereset {name}...")
    result = await reboot_stb(stb["host"], stb.get("port", 22), stb["username"], stb["password"])
    await update.message.reply_text(result)


def main():
    if not config.get("bot_token") or config["bot_token"] == "YOUR_BOT_TOKEN_HERE":
        print("[ERROR] Bot token belum diisi! Edit stb_list.json dan isi bot_token.")
        return

    if not stb_list:
        print("[WARNING] Daftar STB kosong. Tambahkan STB di stb_list.json.")

    app = Application.builder().token(config["bot_token"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_stb))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cpu", cmd_cpu))
    app.add_handler(CommandHandler("ram", cmd_ram))
    app.add_handler(CommandHandler("storage", cmd_storage))
    app.add_handler(CommandHandler("uptime", cmd_uptime))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("speedtest", cmd_speedtest))
    app.add_handler(CommandHandler("reboot", cmd_reboot))
    app.add_handler(CommandHandler("reboot_confirm", cmd_reboot_confirm))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("[INFO] Bot started. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
