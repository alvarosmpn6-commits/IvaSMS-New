@echo off
echo ========================================
echo    Telegram OTP Bot - Windows Setup
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python is installed
python --version

:: Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo Please reinstall Python with pip included
    pause
    exit /b 1
)

echo ✅ pip is available

:: Install dependencies
echo.
echo 📦 Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo ✅ Dependencies installed successfully

:: Check if .env file exists
if not exist ".env" (
    echo.
    echo 📝 Creating .env file...
    copy ".env.example" ".env"
    echo.
    echo ⚠️  IMPORTANT: Please edit .env file with your credentials:
    echo    - IVASMS_EMAIL
    echo    - IVASMS_PASSWORD  
    echo    - TELEGRAM_BOT_TOKEN
    echo    - TELEGRAM_GROUP_ID
    echo.
    echo Opening .env file for editing...
    notepad .env
    echo.
    echo Press any key after you've saved your credentials...
    pause >nul
)

:: Run tests
echo.
echo 🧪 Running tests...
python test_bot.py

if errorlevel 1 (
    echo.
    echo ⚠️  Some tests failed. Please check the output above.
    echo You may still be able to run the bot if core components work.
    echo.
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo 🚀 To start the bot:
echo    python main.py
echo.
echo 🌐 Dashboard will be available at:
echo    http://localhost:5000
echo.
echo 📋 Quick test:
echo    python start.py
echo.
echo Press any key to start the bot now...
pause >nul

python main.py
