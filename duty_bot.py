import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
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
    print("🔔 Бот разбужен cron-запросом")
    return "Бот активен!"

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

logging.basicConfig(level=logging.INFO)

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
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text(
            "🤖 Бот дежурств\n\n"
            "📋 Команды:\n/today - дежурные сегодня\n/tomorrow - дежурные завтра\n/schedule - график на неделю\n\n"
            "⚙️ Админ-панель в ЛС с ботом"
        )
    else:
        await update.message.reply_text(
            "🤖 АДМИН-ПАНЕЛЬ\n\n"
            "⚙️ Команды управления:\n/setduty - назначить дежурных\n/resetduty - сбросить в авторежим\n/pausebot - приостановить бота\n/resumebot - возобновить работу\n\n"
            "🔐 Команды требуют пароль"
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
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Команда только в ЛС с ботом")
        return
    
    await update.message.reply_text("👥 Введите имена дежурных:")
    context.user_data['waiting_for'] = 'duty_names'

async def reset_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Команда только в ЛС с ботом")
        return
    
    await update.message.reply_text("🔐 Введите пароль для сброса:")
    context.user_data['waiting_for'] = 'reset_password'

async def pause_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Команда только в ЛС с ботом")
        return
    
    await update.message.reply_text("🔐 Введите пароль для паузы:")
    context.user_data['waiting_for'] = 'pause_password'

async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Команда только в ЛС с ботом")
        return
    
    await update.message.reply_text("🔐 Введите пароль для возобновления:")
    context.user_data['waiting_for'] = 'resume_password'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MANUAL_DUTY, BOT_PAUSED
    
    if update.effective_chat.type in ['group', 'supergroup']:
        return
    
    waiting_for = context.user_data.get('waiting_for')
    user_text = update.message.text
    
    if not waiting_for:
        await update.message.reply_text("❓ Используйте команды из /start")
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
            await update.message.reply_text("✅ Сброшено в авторежим")
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

def main():
    # Запускаем Flask в отдельном потоке для будильника
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем бота (новая версия API)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("tomorrow", tomorrow))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CommandHandler("setduty", set_duty))
    application.add_handler(CommandHandler("resetduty", reset_duty))
    application.add_handler(CommandHandler("pausebot", pause_bot))
    application.add_handler(CommandHandler("resumebot", resume_bot))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот запущен с будильником!")
    
    # Запускаем бота (новая версия)
    application.run_polling()

if __name__ == "__main__":
    main()
