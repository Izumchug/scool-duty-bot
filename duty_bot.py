import logging
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# Настройки
BOT_TOKEN = "8054800343:AAFxaBqHugbeRcfJkquqZEkUoBfwkJ4KXc4"
ADMIN_PASSWORD = "PaN9w2YN49"

# Список дежурных (30 пар)
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

START_DATE = datetime(2025, 10, 13)  # 13 октября 2025
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

def calculate_duty_index(target_date):
    """Рассчитать индекс дежурных для указанной даты"""
    if is_weekend(target_date):
        return None
    
    # Считаем РАБОЧИЕ дни между START_DATE и target_date
    current = START_DATE
    worked_days = 0
    
    while current < target_date:
        if not is_weekend(current):
            worked_days += 1
        current += timedelta(days=1)
    
    return worked_days % len(DUTY_LIST)

def get_duty_pair(target_date):
    """Получить пару дежурных для указанной даты"""
    duty_index = calculate_duty_index(target_date)
    if duty_index is None:
        return None
    return DUTY_LIST[duty_index]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот графика дежурств активирован!\n\n"
        "📋 ОСНОВНЫЕ КОМАНДЫ:\n"
        "/today - дежурные сегодня\n"
        "/tomorrow - дежурные завтра\n"
        "/schedule - график на неделю\n\n"
        "⚙️ АДМИН-КОМАНДЫ (требуют пароль):\n"
        "/setduty [имена] - ручное назначение\n"
        "/resetduty - сброс в авторежим\n"
        "/pausebot - приостановить бота\n"
        "/resumebot - возобновить работу\n\n"
        "🔐 Пароль: PaN9w2YN49\n"
        "📅 График начинается с 13.10.2025"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Используйте /resumebot для возобновления.")
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
        await update.message.reply_text("❌ Бот приостановлен. Используйте /resumebot для возобновления.")
        return
    
    tomorrow_date = datetime.now().date() + timedelta(days=1)
    
    if is_weekend(tomorrow_date):
        duty_text = "Выходной! Дежурных нет 😊"
    else:
        duty_pair = get_duty_pair(tomorrow_date)
        duty_text = f"Дежурят: {duty_pair}"
    
    days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресеньe"]
    weekday_ru = days_ru[tomorrow_date.weekday()]
    date_str = tomorrow_date.strftime("%d.%m.%Y")
    
    await update.message.reply_text(f"📅 Завтра, {date_str} ({weekday_ru})\n{duty_text}")

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Используйте /resumebot для возобновления.")
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
            duty_text = f"👥 {duty_pair}" if duty_pair else "❌ Ошибка"
        
        schedule_text += f"{date_str} ({weekday_ru}): {duty_text}\n"
    
    await update.message.reply_text(schedule_text)

# АДМИН-КОМАНДЫ (с проверкой пароля в аргументах)
async def set_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенная команда для ручного назначения"""
    global MANUAL_DUTY
    
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: /setduty [имена дежурных]\n"
            "📝 Пример: /setduty Иванов Петров\n\n"
            "🔐 После ввода запросит пароль"
        )
        return
    
    # Запрашиваем пароль
    await update.message.reply_text("🔐 Введите пароль для подтверждения:")
    
    # Сохраняем имена для следующего шага
    context.user_data['pending_duty_names'] = " ".join(context.args)

async def confirm_set_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение ручного назначения с паролем"""
    global MANUAL_DUTY
    
    password = update.message.text
    duty_names = context.user_data.get('pending_duty_names')
    
    if not duty_names:
        await update.message.reply_text("❌ Ошибка: не найдены имена дежурных")
        return
    
    if password != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    MANUAL_DUTY = duty_names
    await update.message.reply_text(f"✅ На сегодня ручно назначены: {duty_names}")
    
    # Очищаем временные данные
    context.user_data.pop('pending_duty_names', None)

async def reset_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенная команда сброса"""
    await update.message.reply_text("🔐 Введите пароль для сброса:")

async def confirm_reset_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение сброса с паролем"""
    global MANUAL_DUTY
    
    password = update.message.text
    
    if password != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    MANUAL_DUTY = None
    await update.message.reply_text("✅ Возврат к автоматическому графику")

async def pause_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенная команда паузы"""
    await update.message.reply_text("🔐 Введите пароль для приостановки бота:")

async def confirm_pause_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение паузы с паролем"""
    global BOT_PAUSED
    
    password = update.message.text
    
    if password != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    BOT_PAUSED = True
    await update.message.reply_text("⏸️ Бот приостановлен. Используйте /resumebot для возобновления.")

async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенная команда возобновления"""
    global BOT_PAUSED
    
    password = update.message.text if context.args else None
    
    if not password:
        await update.message.reply_text("🔐 Введите пароль для возобновления работы:")
        return
    
    if password != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    BOT_PAUSED = False
    await update.message.reply_text("▶️ Бот снова активен! График возобновлен.")

def main():
    # Запускаем веб-сервер в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("tomorrow", tomorrow))
    application.add_handler(CommandHandler("schedule", schedule))
    
    # Упрощенные админ-команды
    application.add_handler(CommandHandler("setduty", set_duty))
    application.add_handler(CommandHandler("resetduty", reset_duty))
    application.add_handler(CommandHandler("pausebot", pause_bot))
    application.add_handler(CommandHandler("resumebot", resume_bot))
    
    # Обработчики для подтверждения с паролем
    application.add_handler(CommandHandler("confirm_set_duty", confirm_set_duty))
    application.add_handler(CommandHandler("confirm_reset_duty", confirm_reset_duty))
    application.add_handler(CommandHandler("confirm_pause_bot", confirm_pause_bot))
    
    print("🤖 Бот дежурств запущен!")
    print("📅 Дата начала графика:", START_DATE.strftime("%d.%m.%Y"))
    print("👥 Всего пар дежурных:", len(DUTY_LIST))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
