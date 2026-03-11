# Deployment Guide

## Local Development

### Prerequisites
- Python 3.8 or higher
- Git (optional)

### Quick Start
1. **Clone/Download the project**
   ```bash
   git clone <repository-url>
   cd TG_cyber24
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Test the setup**
   ```bash
   python test_bot.py
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## Replit Deployment (Recommended)

### Step 1: Create Replit Project
1. Go to [Replit.com](https://replit.com)
2. Click "Create Repl"
3. Choose "Import from GitHub" or "Upload files"
4. Upload all project files

### Step 2: Configure Secrets
1. In Replit, click on "Secrets" (lock icon) in the sidebar
2. Add these secrets:
   - `IVASMS_EMAIL`: Your IVASMS email
   - `IVASMS_PASSWORD`: Your IVASMS password  
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `TELEGRAM_GROUP_ID`: Your group chat ID

### Step 3: Install Dependencies
Replit should automatically install from `requirements.txt`, but if not:
```bash
pip install -r requirements.txt
```

### Step 4: Run the Bot
Click the "Run" button in Replit. The bot will start on port 5000.

### Step 5: Keep Alive with UptimeRobot
1. Copy your Replit app URL (looks like: https://your-repl-name.username.repl.co)
2. Go to [UptimeRobot.com](https://uptimerobot.com)
3. Create a free account
4. Add a new monitor:
   - Type: HTTP(s)
   - URL: Your Replit URL
   - Monitoring interval: 5 minutes
5. This will ping your bot every 5 minutes to keep it alive

## Heroku Deployment

### Prerequisites
- Heroku CLI installed
- Git repository

### Steps
1. **Create Heroku app**
   ```bash
   heroku create your-bot-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set IVASMS_EMAIL=your_email@example.com
   heroku config:set IVASMS_PASSWORD=your_password
   heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token
   heroku config:set TELEGRAM_GROUP_ID=your_group_id
   ```

3. **Create Procfile**
   ```
   web: python main.py
   ```

4. **Deploy**
   ```bash
   git add .
   git commit -m "Deploy bot"
   git push heroku main
   ```

## Railway Deployment

1. Go to [Railway.app](https://railway.app)
2. Connect your GitHub repository
3. Add environment variables in Railway dashboard
4. Deploy automatically

## PythonAnywhere Deployment

1. Upload files to PythonAnywhere
2. Create a web app with Flask
3. Set environment variables in WSGI configuration
4. Point to main.py

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `IVASMS_EMAIL` | Your IVASMS account email | user@example.com |
| `IVASMS_PASSWORD` | Your IVASMS account password | yourpassword |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | 123456:ABC-DEF... |
| `TELEGRAM_GROUP_ID` | Target group chat ID | -1001234567890 |
| `PORT` | Server port (optional) | 5000 |
| `FLASK_ENV` | Flask environment | production |

## Monitoring Endpoints

Once deployed, your bot will have these endpoints:

- `GET /` - Health check and status
- `GET /check-otp` - Manual OTP check
- `GET /status` - Detailed bot status
- `GET /status?send=true` - Send status to Telegram
- `GET /test-message` - Send test message
- `GET /clear-cache` - Clear OTP cache
- `GET /start-monitor` - Start background monitoring
- `GET /stop-monitor` - Stop background monitoring

## Troubleshooting

### Common Issues

1. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`

2. **Bot not responding**
   - Check Telegram bot token is correct
   - Verify group ID is correct (should start with -)
   - Check bot has permission to send messages to group

3. **IVASMS login fails**
   - Verify email and password are correct
   - Check if IVASMS.com is accessible
   - Website structure may have changed (update scraper.py)

4. **No OTPs detected**
   - Check if you have received SMS messages in IVASMS account
   - Review scraper logic for website changes
   - Check scraper.py logs for errors

5. **Bot keeps stopping (Replit)**
   - Set up UptimeRobot to ping every 5 minutes
   - Ensure your Replit is always on (upgrade to paid plan if needed)

### Logs and Debugging

- Check console output for error messages
- Use `/status` endpoint to see bot statistics
- Enable debug mode by setting `FLASK_ENV=development`

### Security Notes

- Never commit `.env` file to version control
- Use environment variables for all credentials
- Only use for authorized/ethical purposes
- Regularly rotate credentials

## Support

If you encounter issues:

1. Run `python test_bot.py` to diagnose problems
2. Check the logs in your deployment platform
3. Verify all environment variables are set correctly
4. Test endpoints manually using a browser or curl

## Legal and Ethical Usage

This bot should only be used for:
- Your own IVASMS account
- Authorized security testing
- Educational purposes

Do not use for:
- Unauthorized access to others' accounts
- Spam or malicious activities
- Violating terms of service
