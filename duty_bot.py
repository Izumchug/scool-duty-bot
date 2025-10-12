import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Настройки
BOT_TOKEN = "8054800343:AAFxaBqHugbeRcfJkquqZEkUoBfwkJ4KXc4"
ADMIN_PASSWORD = "PaN9w2YN49"

# Список дежурных
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
    
    days_diff = (target_date - START_DATE.date()).days
    if days_diff < 0:
        return "❌ Дата до начала графика"
    
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
        "🤖 Бот графика дежурств!\n\n"
        "📋 КОМАНДЫ:\n"
        "/today - дежурные сегодня\n"
        "/tomorrow - дежурные завтра\n"
        "/schedule - график на неделю\n\n"
        "⚙️ АДМИН - в ЛС с ботом"
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

def main():
    # Создаем application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("tomorrow", tomorrow))
    application.add_handler(CommandHandler("schedule", schedule))
    
    print("🤖 Бот запущен!")
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
