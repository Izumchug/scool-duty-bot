import logging
import time
import sys
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError, NetworkError
from flask import Flask
from threading import Thread

# Настройки
BOT_TOKEN = "8054800343:AAFxaBqHugbeRcfJkquqZEkUoBfwkJ4KXc4"
ADMIN_PASSWORD = "PaN9w2YN49"

DUTY_LIST = [
    "Аль Ндаф С. & Косяков А.", "Асадов Д. & Шевченко К.",
    "Голуб. В & Попова Н.", "Михайлов М. & Литвиненко А.",
    "Папоротная Р. & Лыткина В.", "Райзбурд С. & Таджибаева Р.",
]

START_DATE = datetime(2025, 10, 13)
BOT_PAUSED = False
MANUAL_DUTY = None

# Flask app для будильника
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Бот дежурств работает!"

@app.route('/wakeup')
def wakeup():
    print("🔔 Бот разбужен")
    return "Бот активен!"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_weekend(date):
    return date.weekday() >= 5

def get_duty_pair(target_date):
    if is_weekend(target_date):
        return None
    days = (target_date - START_DATE.date()).days
    if days < 0:
        return None
    return DUTY_LIST[days % len(DUTY_LIST)]

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logging.error(f"Ошибка в обработчике: {context.error}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat.type in ['group', 'supergroup']:
            await update.message.reply_text("🤖 Бот дежурств\nКоманды: /today /tomorrow")
        else:
            await update.message.reply_text("🤖 Админ-панель\nКоманды: /setduty /resetduty")
    except TelegramError as e:
        logging.error(f"Ошибка в start: {e}")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if BOT_PAUSED:
            await update.message.reply_text("❌ Бот на паузе")
            return
        
        today_date = datetime.now().date()
        duty = get_duty_pair(today_date)
        text = f"📅 Сегодня: {duty}" if duty else "📅 Выходной!"
        await update.message.reply_text(text)
    except TelegramError as e:
        logging.error(f"Ошибка в today: {e}")

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if BOT_PAUSED:
            await update.message.reply_text("❌ Бот на паузе")
            return
        
        tomorrow_date = datetime.now().date() + timedelta(days=1)
        duty = get_duty_pair(tomorrow_date)
        text = f"📅 Завтра: {duty}" if duty else "📅 Выходной!"
        await update.message.reply_text(text)
    except TelegramError as e:
        logging.error(f"Ошибка в tomorrow: {e}")

def run_bot():
    """Запуск бота с перехватом всех ошибок"""
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        try:
            # Запускаем Flask в отдельном потоке
            flask_thread = Thread(target=run_flask)
            flask_thread.daemon = True
            flask_thread.start()
            
            # Создаем приложение
            application = Application.builder().token(BOT_TOKEN).build()
            
            # Добавляем обработчик ошибок
            application.add_error_handler(error_handler)
            
            # Регистрируем команды
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("today", today))
            application.add_handler(CommandHandler("tomorrow", tomorrow))
            
            print(f"🤖 Запуск бота (попытка {restart_count + 1})...")
            application.run_polling(drop_pending_updates=True)
            
        except NetworkError as e:
            logging.error(f"Сетевая ошибка: {e}")
            restart_count += 1
            print(f"🔁 Перезапуск через 10 секунд... ({restart_count}/{max_restarts})")
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"Критическая ошибка: {e}")
            restart_count += 1
            print(f"🔁 Перезапуск через 30 секунд... ({restart_count}/{max_restarts})")
            time.sleep(30)
    
    print("❌ Достигнут лимит перезапусков. Бот остановлен.")

def main():
    print("🚀 Запуск бота с авто-перезапуском...")
    run_bot()

if __name__ == "__main__":
    main()


