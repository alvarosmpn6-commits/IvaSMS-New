import os
import asyncio
import logging
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from scraper import create_scraper
from otp_filter import otp_filter
from utils import format_otp_message, format_multiple_otps, get_status_message
import threading
import time
import requests as http_requests  # for sync HTTP to Telegram

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')
IVASMS_EMAIL = os.getenv('IVASMS_EMAIL')
IVASMS_PASSWORD = os.getenv('IVASMS_PASSWORD')

bot_stats = {
    'start_time': datetime.now(),
    'total_otps_sent': 0,
    'last_check': 'Never',
    'last_error': None,
    'is_running': False
}

telegram_app = None
scraper = None

# ── Sync Telegram sender (works from any thread, no event loop needed) ─────────

def send_telegram_message(message, parse_mode='HTML'):
    """Send message via raw HTTP — safe to call from any thread."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = http_requests.post(url, json={
            'chat_id': GROUP_ID,
            'text': message,
            'parse_mode': parse_mode
        }, timeout=10)
        resp.raise_for_status()
        logger.info("Message sent to Telegram successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        bot_stats['last_error'] = str(e)
        return False

# ── Command handlers ────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """🤖 <b>Telegram OTP Bot</b>

🎯 <b>Available Commands:</b>
/start - Show this help message
/status - Show bot status and statistics
/check - Manually check for new OTPs
/test - Send a test OTP message
/stats - Show detailed statistics"""
    await update.message.reply_text(welcome_message, parse_mode='HTML')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - bot_stats['start_time']
    cache_stats = otp_filter.get_cache_stats()
    status_data = {
        'uptime': str(uptime).split('.')[0],
        'total_otps_sent': bot_stats['total_otps_sent'],
        'last_check': bot_stats['last_check'],
        'cache_size': cache_stats['total_cached'],
        'monitor_running': bot_stats['is_running']
    }
    await update.message.reply_text(get_status_message(status_data), parse_mode='HTML')

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 <b>Checking for new OTPs...</b>", parse_mode='HTML')
    try:
        check_and_send_otps()
        await update.message.reply_text(
            f"✅ <b>Done!</b>\nLast check: {bot_stats['last_check']}\n"
            f"Total sent: {bot_stats['total_otps_sent']}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ <b>Error:</b>\n<code>{e}</code>", parse_mode='HTML')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test_otp = {
        'otp': '123456', 'phone': '+8801234567890',
        'service': 'Test Service',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'raw_message': 'Test OTP message'
    }
    ok = send_telegram_message(format_otp_message(test_otp))
    reply = "✅ <b>Test message sent!</b>" if ok else "❌ <b>Failed to send test message.</b>"
    await update.message.reply_text(reply, parse_mode='HTML')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    cache_stats = otp_filter.get_cache_stats()
    msg = f"""📊 <b>Detailed Statistics</b>

⏱️ Uptime: {uptime}
📨 OTPs Sent: {bot_stats['total_otps_sent']}
🕐 Last Check: {bot_stats['last_check']}
🗂️ Cache: {cache_stats['total_cached']} items ({cache_stats['expire_minutes']}m expiry)
🔴 Last Error: {bot_stats['last_error'] or 'None'}
🟢 Monitor: {'Running' if bot_stats['is_running'] else 'Stopped'}"""
    await update.message.reply_text(msg, parse_mode='HTML')

# ── Core logic ──────────────────────────────────────────────────────────────────

def initialize_bot():
    global telegram_app, scraper

    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    if not GROUP_ID:
        raise ValueError("TELEGRAM_GROUP_ID not set")
    if not IVASMS_EMAIL or not IVASMS_PASSWORD:
        raise ValueError("IVASMS credentials not set")

    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("status", status_command))
    telegram_app.add_handler(CommandHandler("check", check_command))
    telegram_app.add_handler(CommandHandler("test", test_command))
    telegram_app.add_handler(CommandHandler("stats", stats_command))
    logger.info("Telegram bot initialized")

    scraper = create_scraper(IVASMS_EMAIL, IVASMS_PASSWORD)
    if scraper:
        logger.info("IVASMS scraper initialized")
    else:
        logger.warning("Failed to initialize IVASMS scraper")

def check_and_send_otps():
    if not scraper:
        logger.error("Scraper not initialized")
        return

    logger.info("Checking for new OTPs...")
    messages = scraper.fetch_messages()
    bot_stats['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not messages:
        logger.info("No messages found")
        return

    new_messages = otp_filter.filter_new_otps(messages)
    if not new_messages:
        logger.info("No new OTPs (all duplicates)")
        return

    logger.info(f"Found {len(new_messages)} new OTPs")
    message = format_otp_message(new_messages[0]) if len(new_messages) == 1 \
        else format_multiple_otps(new_messages)

    if send_telegram_message(message):
        bot_stats['total_otps_sent'] += len(new_messages)

def background_monitor():
    bot_stats['is_running'] = True
    logger.info("Background OTP monitor started")
    while bot_stats['is_running']:
        try:
            check_and_send_otps()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            bot_stats['last_error'] = str(e)
            time.sleep(120)

# ── Flask routes (unchanged) ────────────────────────────────────────────────────

@app.route('/')
def home():
    if 'text/html' in request.headers.get('Accept', ''):
        return render_template('dashboard.html')
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    return jsonify({'status': 'running', 'uptime': uptime, **bot_stats})

@app.route('/check-otp')
def manual_check():
    try:
        check_and_send_otps()
        return jsonify({'status': 'success', 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/status')
def bot_status():
    uptime = str(datetime.now() - bot_stats['start_time']).split('.')[0]
    cache_stats = otp_filter.get_cache_stats()
    status = {
        'uptime': uptime,
        'total_otps_sent': bot_stats['total_otps_sent'],
        'last_check': bot_stats['last_check'],
        'cache_size': cache_stats['total_cached'],
        'monitor_running': bot_stats['is_running']
    }
    if request.args.get('send') == 'true':
        ok = send_telegram_message(get_status_message(status))
        return jsonify({'status': 'success' if ok else 'error'})
    return jsonify(status)

@app.route('/test-message')
def test_message():
    msg = "🧪 <b>Test Message</b>\n\n🔢 OTP: <code>123456</code>\n📱 <code>+1234567890</code>"
    ok = send_telegram_message(msg)
    return jsonify({'status': 'success' if ok else 'error'})

@app.route('/clear-cache')
def clear_cache():
    try:
        result = otp_filter.clear_cache()
        return jsonify({'status': 'success', 'message': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/start-monitor')
def start_monitor():
    if bot_stats['is_running']:
        return jsonify({'status': 'info', 'message': 'Already running'})
    threading.Thread(target=background_monitor, daemon=True).start()
    return jsonify({'status': 'success'})

@app.route('/stop-monitor')
def stop_monitor():
    bot_stats['is_running'] = False
    return jsonify({'status': 'success'})

@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error', 'message': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'status': 'error', 'message': 'Internal error'}), 500

# ── Entry point ─────────────────────────────────────────────────────────────────

def main():
    logger.info("Starting Telegram OTP Bot...")
    initialize_bot()  # raises on misconfiguration

    send_telegram_message("🚀 <b>Bot Started!</b>\n\n✅ Scraper ready\n✅ Commands active\n🔍 Monitoring OTPs...")

    # Flask + OTP monitor run in background threads
    threading.Thread(target=background_monitor, daemon=True).start()

    port = int(os.environ.get('PORT', 8080))
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    )
    flask_thread.start()
    logger.info(f"Flask server started on port {port}")

    # Telegram bot runs on the MAIN thread — required for signal handlers
    logger.info("Starting Telegram polling on main thread...")
    telegram_app.run_polling(drop_pending_updates=True)  # blocks here

if __name__ == '__main__':
    main()
