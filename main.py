import os
import json
import logging
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
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

class BotManager:
    @staticmethod
    def load_json_file(filepath, default=None):
        """Load JSON file with error handling"""
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
        """Save JSON file with error handling"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")

    @staticmethod
    def load_language(code):
        """Load language file"""
        try:
            path = f"{LANG_PATH}/{code}.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading language {code}: {e}")
            # Return default English if language file not found
            return BotManager.get_default_language()

    @staticmethod
    def get_default_language():
        """Return default language strings"""
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
        """Get user's language preference"""
        users = BotManager.load_json_file(USERS_FILE)
        return users.get(str(user_id), "en")

    @staticmethod
    def set_user_lang(user_id, lang_code):
        """Set user's language preference"""
        users = BotManager.load_json_file(USERS_FILE)
        users[str(user_id)] = lang_code
        BotManager.save_json_file(USERS_FILE, users)

    @staticmethod
    def track_user_analytics(user_id, username, first_name, action, referrer=None):
        """Track user analytics for admin"""
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
        
        # Send to admin
        if ADMIN_ID:
            try:
                admin_msg = f"📊 User Activity:\n"
                admin_msg += f"👤 User: {first_name} (@{username or 'N/A'})\n"
                admin_msg += f"🆔 ID: {user_id}\n"
                admin_msg += f"🎯 Action: {action}\n"
                admin_msg += f"🔗 Referrer: {referrer or 'Direct'}\n"
                admin_msg += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                bot.send_message(ADMIN_ID, admin_msg)
            except Exception as e:
                logger.error(f"Error sending admin notification: {e}")

    @staticmethod
    def update_video_stats(code):
        """Update video download statistics"""
        stats = BotManager.load_json_file(STATS_FILE)
        stats[code] = stats.get(code, 0) + 1
        BotManager.save_json_file(STATS_FILE, stats)

    @staticmethod
    def check_subscription(user_id):
        """Check if user is subscribed to required channels"""
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
        """Send subscription prompt to user"""
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
        """Send message or edit last message"""
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
        """Get video information by code"""
        codes = BotManager.load_json_file(CODES_FILE)
        return codes.get(code)

# Bot command handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Unknown"
    
    # Extract referrer from start parameter
    referrer = None
    if len(message.text.split()) > 1:
        referrer = message.text.split()[1]
    
    # Track user analytics
    BotManager.track_user_analytics(user_id, username, first_name, "start", referrer)
    
    # Set default language if new user
    users = BotManager.load_json_file(USERS_FILE)
    if str(user_id) not in users:
        BotManager.set_user_lang(user_id, "en")
    
    lang = BotManager.get_user_lang(user_id)
    l = BotManager.load_language(lang)
    
    BotManager.send_or_edit_message(message.chat.id, l['welcome'])

@bot.message_handler(commands=['help'])
def handle_help(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Unknown"
    
    BotManager.track_user_analytics(user_id, username, first_name, "help")
    
    lang = BotManager.get_user_lang(user_id)
    l = BotManager.load_language(lang)
    BotManager.send_or_edit_message(message.chat.id, l['help_text'])

@bot.message_handler(commands=['language'])
def handle_language(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Unknown"
    
    BotManager.track_user_analytics(user_id, username, first_name, "language_menu")
    
    lang = BotManager.get_user_lang(user_id)
    l = BotManager.load_language(lang)
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    BotManager.send_or_edit_message(message.chat.id, l['choose_language'], reply_markup=markup)

@bot.message_handler(commands=['feedback', 'complaint'])
def handle_feedback(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Unknown"
    
    BotManager.track_user_analytics(user_id, username, first_name, "feedback_start")
    
    FEEDBACK_STATE[user_id] = True
    lang = BotManager.get_user_lang(user_id)
    l = BotManager.load_language(lang)
    BotManager.send_or_edit_message(message.chat.id, l['send_feedback'])

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    stats = BotManager.load_json_file(STATS_FILE)
    users = BotManager.load_json_file(USERS_FILE)
    
    stats_text = f"📊 Bot Statistics:\n\n"
    stats_text += f"👥 Total Users: {len(users)}\n"
    stats_text += f"📹 Total Video Downloads: {sum(stats.values())}\n\n"
    
    if stats:
        stats_text += "🔥 Top Videos:\n"
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for code, count in sorted_stats:
            stats_text += f"• {code}: {count} downloads\n"
    
    bot.send_message(message.chat.id, stats_text)

# Callback query handlers
@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def handle_language_callback(call):
    code = call.data.split("_")[1]
    user_id = call.from_user.id
    username = call.from_user.username
    first_name = call.from_user.first_name or "Unknown"
    
    BotManager.track_user_analytics(user_id, username, first_name, f"language_change_{code}")
    
    BotManager.set_user_lang(user_id, code)
    l = BotManager.load_language(code)
    
    try:
        bot.edit_message_text(
            f"✅ Language changed!\n\n{l['welcome']}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except:
        bot.send_message(call.message.chat.id, f"✅ Language changed!\n\n{l['welcome']}")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_subscription_check(call):
    user_id = call.from_user.id
    
    if BotManager.check_subscription(user_id):
        lang = BotManager.get_user_lang(user_id)
        l = BotManager.load_language(lang)
        try:
            bot.edit_message_text(
                f"✅ Subscription verified!\n\n{l['welcome']}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
        except:
            bot.send_message(call.message.chat.id, f"✅ Subscription verified!\n\n{l['welcome']}")
    else:
        lang = BotManager.get_user_lang(user_id)
        l = BotManager.load_language(lang)
        bot.answer_callback_query(call.id, l['not_subscribed'], show_alert=True)

# Message handlers
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Unknown"
    text = message.text.strip()
    
    # Handle feedback
    if FEEDBACK_STATE.get(user_id):
        FEEDBACK_STATE[user_id] = False
        
        # Send feedback to admin
        if ADMIN_ID:
            feedback_msg = f"💬 New Feedback:\n\n"
            feedback_msg += f"👤 From: {first_name} (@{username or 'N/A'})\n"
            feedback_msg += f"🆔 ID: {user_id}\n"
            feedback_msg += f"📝 Message: {text}\n"
            feedback_msg += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            try:
                bot.send_message(ADMIN_ID, feedback_msg)
            except Exception as e:
                logger.error(f"Error sending feedback to admin: {e}")
        
        lang = BotManager.get_user_lang(user_id)
        l = BotManager.load_language(lang)
        BotManager.send_or_edit_message(message.chat.id, l['feedback_received'])
        
        BotManager.track_user_analytics(user_id, username, first_name, "feedback_sent")
        return
    
    # Check subscription
    if not BotManager.check_subscription(user_id):
        lang = BotManager.get_user_lang(user_id)
        BotManager.send_subscription_prompt(message.chat.id, lang)
        return
    
    # Handle video code
    video_info = BotManager.get_video_by_code(text)
    if video_info:
        BotManager.track_user_analytics(user_id, username, first_name, f"video_request_{text}")
        
        try:
            # Send video
            if video_info.get('file_id'):
                bot.send_video(message.chat.id, video_info['file_id'])
            elif video_info.get('url'):
                bot.send_video(message.chat.id, video_info['url'])
            else:
                lang = BotManager.get_user_lang(user_id)
                l = BotManager.load_language(lang)
                BotManager.send_or_edit_message(message.chat.id, l['video_not_found'])
                return
            
            # Update statistics
            BotManager.update_video_stats(text)
            
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            lang = BotManager.get_user_lang(user_id)
            l = BotManager.load_language(lang)
            BotManager.send_or_edit_message(message.chat.id, l['bot_error'])
    else:
        lang = BotManager.get_user_lang(user_id)
        l = BotManager.load_language(lang)
        BotManager.send_or_edit_message(message.chat.id, l['video_not_found'])

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
    
    # Start Flask app
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
