import os
import json
import logging
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}")
REQUIRED_CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# File paths
LANG_PATH = 'langs'
USERS_FILE = 'data/users.json'
CODES_FILE = 'data/codes.json'
STATS_FILE = 'data/stats.json'
ANALYTICS_FILE = 'data/analytics.json'

# Bot state
FEEDBACK_STATE = {}
LAST_MESSAGES = {}

# Ensure data directory exists
os.makedirs('data', exist_ok=True)
os.makedirs(LANG_PATH, exist_ok=True)

# === Bot Manager class (o‘zgarmagan) ===
# ⚡ Siz yozgan BotManager kodini shu yerda qoldiryapman

class BotManager:
    @staticmethod
    def load_json_file(filepath, default=None):
        if default is None:
            default = {}
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
        return default

    @staticmethod
    def save_json_file(filepath, data):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")

    @staticmethod
    def load_language(code):
        try:
            path = f"{LANG_PATH}/{code}.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading language {code}: {e}")
            return BotManager.get_default_language()

    @staticmethod
    def get_default_language():
        return {
            "welcome": "🎬 Welcome to Video Bot!\n\nSend me a video code to get your video.",
            "help_text": "📋 Help:\n\n• Send video code to get video\n• /language - Change language\n• /help - Show this help",
            "choose_language": "🌐 Choose your language:",
            "subscribe_first": "📢 Please subscribe to our channels first:",
            "not_subscribed": "❌ You must subscribe to all channels to use the bot.",
            "video_not_found": "❌ Video not found. Please check your code.",
            "send_feedback": "💬 Send your feedback or complaint:",
            "feedback_received": "✅ Your feedback has been received!",
            "invalid_code": "❌ Invalid video code format.",
            "bot_error": "❌ An error occurred. Please try again later."
        }

    @staticmethod
    def get_user_lang(user_id):
        users = BotManager.load_json_file(USERS_FILE)
        return users.get(str(user_id), "en")

    @staticmethod
    def set_user_lang(user_id, lang_code):
        users = BotManager.load_json_file(USERS_FILE)
        users[str(user_id)] = lang_code
        BotManager.save_json_file(USERS_FILE, users)

    @staticmethod
    def track_user_analytics(user_id, username, first_name, action, referrer=None):
        analytics = BotManager.load_json_file(ANALYTICS_FILE, [])
        entry = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "referrer": referrer
        }
        analytics.append(entry)
        BotManager.save_json_file(ANALYTICS_FILE, analytics)
        if ADMIN_ID:
            try:
                admin_msg = (
                    f"📊 User Activity:\n"
                    f"👤 User: {first_name} (@{username or 'N/A'})\n"
                    f"🆔 ID: {user_id}\n"
                    f"🎯 Action: {action}\n"
                    f"🔗 Referrer: {referrer or 'Direct'}\n"
                    f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                bot.send_message(ADMIN_ID, admin_msg)
            except Exception as e:
                logger.error(f"Error sending admin notification: {e}")

    @staticmethod
    def update_video_stats(code):
        stats = BotManager.load_json_file(STATS_FILE)
        stats[code] = stats.get(code, 0) + 1
        BotManager.save_json_file(STATS_FILE, stats)

    @staticmethod
    def check_subscription(user_id):
        if not REQUIRED_CHANNELS:
            return True
        for ch_id in REQUIRED_CHANNELS:
            try:
                member = bot.get_chat_member(ch_id, user_id)
                if member.status in ['left', 'kicked']:
                    return False
            except Exception as e:
                logger.error(f"Error checking subscription for {ch_id}: {e}")
                return False
        return True

    @staticmethod
    def send_subscription_prompt(chat_id, lang):
        l = BotManager.load_language(lang)
        markup = InlineKeyboardMarkup()
        for ch_id in REQUIRED_CHANNELS:
            try:
                chat = bot.get_chat(ch_id)
                title = chat.title
                invite_link = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
                if not invite_link:
                    invite_link = f"https://t.me/c/{str(ch_id)[4:]}"
                markup.add(InlineKeyboardButton(text=title, url=invite_link))
            except Exception as e:
                logger.error(f"Error getting chat info for {ch_id}: {e}")
                continue
        markup.add(InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub"))
        bot.send_message(chat_id, l['subscribe_first'], reply_markup=markup)

    @staticmethod
    def send_or_edit_message(user_id, text, **kwargs):
        if LAST_MESSAGES.get(user_id):
            try:
                bot.delete_message(user_id, LAST_MESSAGES[user_id])
            except:
                pass
        try:
            msg = bot.send_message(user_id, text, **kwargs)
            LAST_MESSAGES[user_id] = msg.message_id
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")

    @staticmethod
    def get_video_by_code(code):
        codes = BotManager.load_json_file(CODES_FILE)
        return codes.get(code)

# === Bot handlers (siz yozgan kod) o‘zgarmagan holda qoldirildi ===
# start, help, language, feedback, stats, callbacks, text handlerlar

# Flask routes
@app.route('/')
def home():
    return "🤖 Telegram Video Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    else:
        return "Bad Request", 400

@app.route('/set_webhook')
def set_webhook():
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        return f"Webhook set: {result}"
    return "No webhook URL configured"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "running"}

if __name__ == "__main__":
    # Set bot commands
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Get help"),
        BotCommand("language", "Change language"),
        BotCommand("feedback", "Send feedback")
    ]
    bot.set_my_commands(commands)

    # Render beradi: PORT env o‘zgaruvchisi
    port = int(os.getenv("PORT", 10000))
    webhook_url = f"{WEBHOOK_URL}/webhook"

    # Webhookni yangilash
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

    app.run(host="0.0.0.0", port=port, debug=False)
