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
    "Каретникова А. & Аксенова В.", "Китаева С. & Бичева В.",
    "Лукашина М. & Руднева М.", "Ермаков С. & Королик К.",
    "Ганеева К. & Залунина М.", "Тарусова Н. & Мансурова Д.",
    "Самбурова А. & Басова С.", "Рыжухина М. & Трегубова К.",
    "Вовенко П. & Горбунова А.", "Демченко Т. & Фомичева В.",
    "Соколова У. & Миронова М.", "Мекедо В. (один)"
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
    
    days_diff = (target_date - START_DATE.date()).days
    if days_diff < 0:
        return None
    
    current_date = START_DATE.date()
    worked_days = 0
    
    while current_date < target_date:
        if not is_weekend(current_date):
            worked_days += 1
        current_date += timedelta(days=1)
    
    duty_index = worked_days % len(DUTY_LIST)
    return DUTY_LIST[duty_index]

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logging.error(f"Ошибка в обработчике: {context.error}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat.type in ['group', 'supergroup']:
            await update.message.reply_text(
                "🤖 Бот дежурств\n\n"
                "📋 Команды для всех:\n"
                "/today - дежурные сегодня\n"
                "/tomorrow - дежурные завтра\n"
                "/schedule - график на неделю\n\n"
                "⚙️ Админ-команды в ЛС с ботом"
            )
        else:
            await update.message.reply_text(
                "🤖 АДМИН-ПАНЕЛЬ\n\n"
                "⚙️ Команды управления:\n"
                "/setduty - назначить дежурных\n"
                "/resetduty - сбросить в авторежим\n"
                "/pausebot - приостановить бота\n"
                "/resumebot - возобновить работу\n\n"
                "🔐 Команды требуют пароль"
            )
    except TelegramError as e:
        logging.error(f"Ошибка в start: {e}")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if BOT_PAUSED:
            await update.message.reply_text("❌ Бот на паузе")
            return
        
        today_date = datetime.now().date()
        
        if MANUAL_DUTY:
            duty_text = f"⚡ Ручное назначение!\nДежурят: {MANUAL_DUTY}"
        elif is_weekend(today_date):
            duty_text = "Выходной! Дежурных нет 😊"
        else:
            duty_pair = get_duty_pair(today_date)
            duty_text = f"Дежурят: {duty_pair}"
        
        days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday_ru = days_ru[today_date.weekday()]
        date_str = today_date.strftime("%d.%m.%Y")
        
        await update.message.reply_text(f"📅 Сегодня, {date_str} ({weekday_ru})\n{duty_text}")
    except TelegramError as e:
        logging.error(f"Ошибка в today: {e}")

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if BOT_PAUSED:
            await update.message.reply_text("❌ Бот на паузе")
            return
        
        tomorrow_date = datetime.now().date() + timedelta(days=1)
        
        if is_weekend(tomorrow_date):
            duty_text = "Выходной! Дежурных нет 😊"
        else:
            duty_pair = get_duty_pair(tomorrow_date)
            duty_text = f"Дежурят: {duty_pair}"
        
        days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday_ru = days_ru[tomorrow_date.weekday()]
        date_str = tomorrow_date.strftime("%d.%m.%Y")
        
        await update.message.reply_text(f"📅 Завтра, {date_str} ({weekday_ru})\n{duty_text}")
    except TelegramError as e:
        logging.error(f"Ошибка в tomorrow: {e}")

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if BOT_PAUSED:
            await update.message.reply_text("❌ Бот на паузе")
            return
        
        today_date = datetime.now().date()
        schedule_text = "📊 График на неделю:\n\n"
        
        days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        
        for i in range(7):
            current_date = today_date + timedelta(days=i)
            weekday_ru = days_ru[current_date.weekday()]
            date_str = current_date.strftime("%d.%m")
            
            if is_weekend(current_date):
                duty_text = "➖ Выходной"
            else:
                duty_pair = get_duty_pair(current_date)
                duty_text = f"👥 {duty_pair}"
            
            schedule_text += f"{date_str} ({weekday_ru}): {duty_text}\n"
        
        await update.message.reply_text(schedule_text)
    except TelegramError as e:
        logging.error(f"Ошибка в schedule: {e}")

# АДМИН-КОМАНДЫ (только в ЛС)
async def set_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat.type in ['group', 'supergroup']:
            await update.message.reply_text("⚠️ Эта команда доступна только в личных сообщениях с ботом")
            return
        
        await update.message.reply_text("👥 Введите имена дежурных для ручного назначения:")
        context.user_data['waiting_for'] = 'duty_names'
    except TelegramError as e:
        logging.error(f"Ошибка в set_duty: {e}")

async def reset_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat.type in ['group', 'supergroup']:
            await update.message.reply_text("⚠️ Эта команда доступна только в личных сообщениях с ботом")
            return
        
        await update.message.reply_text("🔐 Введите пароль для сброса:")
        context.user_data['waiting_for'] = 'reset_password'
    except TelegramError as e:
        logging.error(f"Ошибка в reset_duty: {e}")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MANUAL_DUTY, BOT_PAUSED
    
    try:
        if update.effective_chat.type in ['group', 'supergroup']:
            return
        
        waiting_for = context.user_data.get('waiting_for')
        user_text = update.message.text
        
        if not waiting_for:
            await update.message.reply_text("ℹ️ Используйте команды из /start")
            return
        
        if waiting_for == 'duty_names':
            context.user_data['pending_duty_names'] = user_text
            context.user_data['waiting_for'] = 'duty_password'
            await update.message.reply_text("🔐 Введите пароль для подтверждения:")
            
        elif waiting_for == 'duty_password':
            if user_text == ADMIN_PASSWORD:
                duty_names = context.user_data['pending_duty_names']
                MANUAL_DUTY = duty_names
                await update.message.reply_text(f"✅ Назначены: {duty_names}")
            else:
                await update.message.reply_text("❌ Неверный пароль!")
            context.user_data.clear()
            
        elif waiting_for == 'reset_password':
            if user_text == ADMIN_PASSWORD:
                MANUAL_DUTY = None
                await update.message.reply_text("✅ Сброшено в авторежим")
            else:
                await update.message.reply_text("❌ Неверный пароль!")
            context.user_data.clear()
            
    except TelegramError as e:
        logging.error(f"Ошибка в handle_admin_message: {e}")

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
            
            # Регистрируем команды (работают везде)
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("today", today))
            application.add_handler(CommandHandler("tomorrow", tomorrow))
            application.add_handler(CommandHandler("schedule", schedule))
            
            # Админ-команды (только в ЛС)
            application.add_handler(CommandHandler("setduty", set_duty))
            application.add_handler(CommandHandler("resetduty", reset_duty))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
            
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
