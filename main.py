import os
import json
import logging
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

# ================= LOAD =================
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}")
REQUIRED_CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN)

LANG_PATH = 'langs'
USERS_FILE = 'data/users.json'
CODES_FILE = 'data/codes.json'
STATS_FILE = 'data/stats.json'
ANALYTICS_FILE = 'data/analytics.json'

FEEDBACK_STATE = {}
LAST_MESSAGES = {}

os.makedirs('data', exist_ok=True)
os.makedirs(LANG_PATH, exist_ok=True)

# ================= BOT MANAGER =================

class BotManager:

    @staticmethod
    def load_json_file(filepath, default=None):
        if default is None:
            default = {}
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            return default
        return default

    @staticmethod
    def save_json_file(filepath, data):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def get_video_by_code(code):
        codes = BotManager.load_json_file(CODES_FILE)
        return codes.get(code)

# ================= HANDLERS (siz yozganlaringiz qoladi) =================

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, "🎬 Welcome! Send video code.")

@bot.message_handler(commands=['help'])
def help_handler(message):
    bot.send_message(message.chat.id, "📋 Send video code to receive video.")

@bot.message_handler(func=lambda message: True)
def text_handler(message):
    code = message.text.strip()
    video = BotManager.get_video_by_code(code)

    if video:
        bot.send_video(message.chat.id, video)
    else:
        bot.send_message(message.chat.id, "❌ Video not found.")

# ================= WEBHOOK AUTO SETUP =================

commands = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Get help"),
]

try:
    bot.set_my_commands(commands)
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info("Webhook successfully set")
except Exception as e:
    logger.error(f"Webhook error: {e}")

# ================= FLASK ROUTES =================

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
