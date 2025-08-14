# Telegram Video Bot

A modern Telegram bot that sends videos in multiple languages (Uzbek, Russian, English) with comprehensive admin analytics.

## Features

- 🎬 Video sharing by code
- 🌐 Multi-language support (Uzbek, Russian, English)
- 📊 Comprehensive user analytics for admins
- 📢 Channel subscription verification
- 💬 Feedback system
- 📈 Video download statistics
- 🔄 Modern webhook-based deployment

## Setup

### 1. Create Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Get your bot token

### 2. Deploy on Render

1. Fork this repository
2. Connect to [Render](https://render.com)
3. Create a new Web Service
4. Connect your GitHub repository
5. Set environment variables:
   - `TELEGRAM_TOKEN`: Your bot token
   - `WEBHOOK_URL`: Your Render app URL (e.g., https://your-app.onrender.com)
   - `ADMIN_ID`: Your Telegram user ID
   - `CHANNELS`: Comma-separated channel IDs (optional)

### 3. Set Webhook

After deployment, visit: `https://your-app.onrender.com/set_webhook`

### 4. Configure Videos

Edit `data/codes.json` to add your video codes and file IDs/URLs:

\`\`\`json
{
  "CODE123": {
    "title": "My Video",
    "file_id": "BAACAgIAAxkBAAI...",
    "url": "https://example.com/video.mp4",
    "description": "Video description"
  }
}
\`\`\`

## Admin Features

- `/stats` - View bot statistics (admin only)
- Real-time user activity notifications
- Feedback collection
- User source tracking

## Bot Commands

- `/start` - Start the bot
- `/help` - Show help
- `/language` - Change language
- `/feedback` - Send feedback

## File Structure

\`\`\`
├── main.py              # Main bot application
├── langs/               # Language files
│   ├── en.json         # English
│   ├── ru.json         # Russian
│   └── uz.json         # Uzbek
├── data/               # Data storage
│   ├── codes.json      # Video codes
│   ├── users.json      # User preferences
│   ├── stats.json      # Download statistics
│   └── analytics.json  # User analytics
├── requirements.txt    # Python dependencies
├── render.yaml        # Render deployment config
└── README.md          # This file
\`\`\`

## Environment Variables

- `TELEGRAM_TOKEN` - Your Telegram bot token (required)
- `WEBHOOK_URL` - Your deployment URL (required)
- `ADMIN_ID` - Admin Telegram user ID (required)
- `CHANNELS` - Required channel IDs, comma-separated (optional)
- `PORT` - Server port (default: 5000)

## License

MIT License
