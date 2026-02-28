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

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask
app = Flask(__name__)

# Config
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}")
REQUIRED_CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Bot
bot = telebot.TeleBot(TOKEN)

# Paths
LANG_PATH = 'langs'
USERS_FILE = 'data/users.json'
CODES_FILE = 'data/codes.json'
STATS_FILE = 'data/stats.json'
ANALYTICS_FILE = 'data/analytics.json'

FEEDBACK_STATE = {}
LAST_MESSAGES = {}

os.makedirs('data', exist_ok=True)
os.makedirs(LANG_PATH, exist_ok=True)


# ================== BOT MANAGER ==================

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
    def get_video_by_code(code):
        codes = BotManager.load_json_file(CODES_FILE)
        return codes.get(code)


# ================== WEBHOOK SETUP ==================

commands = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Get help"),
    BotCommand("language", "Change language"),
    BotCommand("feedback", "Send feedback")
]

try:
    bot.set_my_commands(commands)
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info("Webhook successfully set")
except Exception as e:
    logger.error(f"Webhook setup error: {e}")


# ================== FLASK ROUTES ==================

@app.route('/')
def home():
    return "🤖 Telegram Video Bot is running!"

@app.route('/health')
def health():
    return {"status": "healthy"}

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Bad Request", 400
