import logging
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from flask import Flask
from threading import Thread

# Настройки
BOT_TOKEN = "8054800343:AAFxaBqHugbeRcfJkquqZEkUoBfwkJ4KXc4"
ADMIN_PASSWORD = "PaN9w2YN49"

# Список дежурных (30 пар)
DUTY_LIST = [
    "Аль Надф С. & Косяков А.", "Асадов Д. & Шевченко К.", 
    "Голуб. В & Попова Н.", "Михайлов М. & Литвиненко А.",
    "Папоротная Р. & Лыткина В.", "Райзбурд С. & Таджибаева Р.",
    "Каретникова А. & Аксенова В.", "Китаева С. & Бичева В.",
    "Лукашина М. & Руднева М.", "Ермаков С. & Королик К.",
    "Ганеева К. & Залунина М.", "Тарусова Н. & Мансурова Д.",
    "Самбурова А. & Басова С.", "Рыжухина М. & Трегубова К.",
    "Вовенко П. & Горбунова А.", "Демченко Т. & Фомичева В.",
    "Соколова У. & Миронова М.", "Мекедо В. (один)"
]

# ИСПРАВЛЕННАЯ ДАТА!
START_DATE = datetime(2025, 10, 13)  # 13 октября 2025 года
BOT_PAUSED = False
MANUAL_DUTY = None

# Веб-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот дежурств работает! 🚀"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def is_weekend(date):
    return date.weekday() >= 5

def get_duty_pair(target_date):
    if is_weekend(target_date):
        return None
    
    current_date = START_DATE
    duty_index = 0
    
    while current_date < target_date:
        if not is_weekend(current_date):
            duty_index = (duty_index + 1) % len(DUTY_LIST)
        current_date += timedelta(days=1)
    
    return DUTY_LIST[duty_index]

def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Бот графика дежурств активирован!\n\nКоманды:\n/today - дежурные сегодня\n/tomorrow - дежурные завтра\n/schedule - график на неделю\n/set_duty [пароль] [имена] - ручное назначение\n/reset [пароль] - сброс в авторежим\n/pause [пароль] - приостановить бота\n/resume [пароль] - возобновить работу")

def today(update: Update, context: CallbackContext):
    if BOT_PAUSED:
        update.message.reply_text("❌ Бот приостановлен. Используйте /resume для возобновления.")
        return
    
    today_date = datetime.now().date()
    
    if MANUAL_DUTY:
        duty_text = f"⚡ Ручное назначение!\nДежурят: {MANUAL_DUTY}"
    elif is_weekend(today_date):
        duty_text = "Выходной! Дежурных нет 😊"
    else:
        duty_pair = get_duty_pair(today_date)
        duty_text = f"Дежурят: {duty_pair}"
    
    weekday = today_date.strftime("%A")
    date_str = today_date.strftime("%d.%m.%Y")
    
    update.message.reply_text(f"📅 Сегодня, {date_str} ({weekday})\n{duty_text}")

def tomorrow(update: Update, context: CallbackContext):
    if BOT_PAUSED:
        update.message.reply_text("❌ Бот приостановлен. Используйте /resume для возобновления.")
        return
    
    tomorrow_date = datetime.now().date() + timedelta(days=1)
    
    if is_weekend(tomorrow_date):
        duty_text = "Выходной! Дежурных нет 😊"
    else:
        duty_pair = get_duty_pair(tomorrow_date)
        duty_text = f"Дежурят: {duty_pair}"
    
    weekday = tomorrow_date.strftime("%A") 
    date_str = tomorrow_date.strftime("%d.%m.%Y")
    
    update.message.reply_text(f"📅 Завтра, {date_str} ({weekday})\n{duty_text}")

def schedule(update: Update, context: CallbackContext):
    if BOT_PAUSED:
        update.message.reply_text("❌ Бот приостановлен. Используйте /resume для возобновления.")
        return
    
    today_date = datetime.now().date()
    schedule_text = "📊 График на неделю:\n\n"
    
    for i in range(7):
        current_date = today_date + timedelta(days=i)
        weekday = current_date.strftime("%A")
        date_str = current_date.strftime("%d.%m.%Y")
        
        if is_weekend(current_date):
            duty_text = "➖ Выходной"
        else:
            duty_pair = get_duty_pair(current_date)
            duty_text = f"👥 {duty_pair}"
        
        schedule_text += f"{date_str} ({weekday}): {duty_text}\n"
    
    update.message.reply_text(schedule_text)

def set_duty(update: Update, context: CallbackContext):
    global MANUAL_DUTY
    
    if len(context.args) < 2:
        update.message.reply_text("❌ Использование: /set_duty [пароль] [имена дежурных]")
        return
    
    password = context.args[0]
    duty_names = " ".join(context.args[1:])
    
    if password != ADMIN_PASSWORD:
        update.message.reply_text("❌ Неверный пароль!")
        return
    
    MANUAL_DUTY = duty_names
    update.message.reply_text(f"✅ На сегодня ручно назначены: {duty_names}")

def reset(update: Update, context: CallbackContext):
    global MANUAL_DUTY
    
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        update.message.reply_text("❌ Неверный пароль!")
        return
    
    MANUAL_DUTY = None
    update.message.reply_text("✅ Возврат к автоматическому графику")

def pause(update: Update, context: CallbackContext):
    global BOT_PAUSED
    
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        update.message.reply_text("❌ Неверный пароль!")
        return
    
    BOT_PAUSED = True
    update.message.reply_text("⏸️ Бот приостановлен. Используйте /resume для возобновления.")

def resume(update: Update, context: CallbackContext):
    global BOT_PAUSED
    
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        update.message.reply_text("❌ Неверный пароль!")
        return
    
    BOT_PAUSED = False
    update.message.reply_text("▶️ Бот снова активен! График возобновлен.")

def main():
    # Запускаем веб-сервер в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем бота (старая версия API)
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("today", today))
    dispatcher.add_handler(CommandHandler("tomorrow", tomorrow))
    dispatcher.add_handler(CommandHandler("schedule", schedule))
    dispatcher.add_handler(CommandHandler("set_duty", set_duty))
    dispatcher.add_handler(CommandHandler("reset", reset))
    dispatcher.add_handler(CommandHandler("pause", pause))
    dispatcher.add_handler(CommandHandler("resume", resume))
    
    print("Бот запущен...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

