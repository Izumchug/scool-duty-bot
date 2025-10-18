import logging
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError
from flask import Flask, request
from threading import Thread
import os

# Настройки
BOT_TOKEN = "8054800343:AAFxaBqHugbeRcfJkquqZEkUoBfwkJ4KXc4"
ADMIN_PASSWORD = "PaN9w2YN49"

# ПОЛНЫЙ список дежурных (18 пар)
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

# Flask app
app = Flask(__name__)
application = None

@app.route('/')
def home():
    return "🤖 Бот дежурств работает!"

@app.route('/wakeup')
def wakeup():
    print("🔔 Бот разбужен cron-запросом")
    return "Бот активен!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if application:
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)
    return "OK"

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот дежурств\n\n"
        "📋 Команды:\n"
        "/today - дежурные сегодня\n"
        "/tomorrow - дежурные завтра\n"
        "/schedule - график на неделю\n\n"
        "⚙️ Админ-команды:\n"
        "/setduty - назначить дежурных\n"
        "/resetduty - сбросить\n"
        "/pausebot - пауза\n"
        "/resumebot - возобновить"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# АДМИН-КОМАНДЫ
async def set_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👥 Введите имена дежурных:")
    context.user_data['waiting_for'] = 'duty_names'

async def reset_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Введите пароль для сброса:")
    context.user_data['waiting_for'] = 'reset_password'

async def pause_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Введите пароль для паузы:")
    context.user_data['waiting_for'] = 'pause_password'

async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Введите пароль для возобновления:")
    context.user_data['waiting_for'] = 'resume_password'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MANUAL_DUTY, BOT_PAUSED
    
    waiting_for = context.user_data.get('waiting_for')
    user_text = update.message.text
    
    if not waiting_for:
        await update.message.reply_text("ℹ️ Используйте команды из /start")
        return
    
    if waiting_for == 'duty_names':
        context.user_data['pending_duty_names'] = user_text
        context.user_data['waiting_for'] = 'duty_password'
        await update.message.reply_text("🔐 Введите пароль:")
        
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
            await update.message.reply_text("✅ Сброшено")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        context.user_data.clear()
        
    elif waiting_for == 'pause_password':
        if user_text == ADMIN_PASSWORD:
            BOT_PAUSED = True
            await update.message.reply_text("✅ Бот на паузе")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        context.user_data.clear()
        
    elif waiting_for == 'resume_password':
        if user_text == ADMIN_PASSWORD:
            BOT_PAUSED = False
            await update.message.reply_text("✅ Бот активен")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        context.user_data.clear()

def setup_bot():
    global application
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Фильтр для работы в группах и личных сообщениях
    chat_filter = filters.ChatType.GROUPS | filters.ChatType.PRIVATE
    
    # Основные команды
    application.add_handler(CommandHandler("start", start, filters=chat_filter))
    application.add_handler(CommandHandler("today", today, filters=chat_filter))
    application.add_handler(CommandHandler("tomorrow", tomorrow, filters=chat_filter))
    application.add_handler(CommandHandler("schedule", schedule, filters=chat_filter))
    
    # Админ-команды
    application.add_handler(CommandHandler("setduty", set_duty, filters=chat_filter))
    application.add_handler(CommandHandler("resetduty", reset_duty, filters=chat_filter))
    application.add_handler(CommandHandler("pausebot", pause_bot, filters=chat_filter))
    application.add_handler(CommandHandler("resumebot", resume_bot, filters=chat_filter))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & chat_filter, handle_message))
    
    return application

def main():
    try:
        # Настройка webhook
        render_url = os.environ.get('RENDER_EXTERNAL_URL')  # Render автоматически устанавливает эту переменную
        bot_app = setup_bot()
        
        if render_url:
            # Webhook режим для Render
            print("🚀 Запуск в режиме Webhook...")
            bot_app.run_webhook(
                listen="0.0.0.0",
                port=5000,
                url_path=BOT_TOKEN,
                webhook_url=f"{render_url}/webhook"
            )
        else:
            # Polling режим для локального тестирования
            print("🔍 Запуск в режиме Polling...")
            bot_app.run_polling()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("🔁 Перезапуск через 10 секунд...")
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
