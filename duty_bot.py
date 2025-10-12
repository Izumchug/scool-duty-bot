import logging
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8054800343:AAFxaBqHugbeRcfJkquqZEkUoBfwkJ4KXc4"
ADMIN_PASSWORD = "PaN9w2YN49"

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

START_DATE = datetime(2024, 10, 13)
BOT_PAUSED = False
MANUAL_DUTY = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот графика дежурств активирован!\n\nКоманды:\n/today - дежурные сегодня\n/tomorrow - дежурные завтра\n/schedule - график на неделю\n/set_duty [пароль] [имена] - ручное назначение\n/reset [пароль] - сброс в авторежим\n/pause [пароль] - приостановить бота\n/resume [пароль] - возобновить работу")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Используйте /resume для возобновления.")
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
    
    await update.message.reply_text(f"📅 Сегодня, {date_str} ({weekday})\n{duty_text}")

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Используйте /resume для возобновления.")
        return
    
    tomorrow_date = datetime.now().date() + timedelta(days=1)
    
    if is_weekend(tomorrow_date):
        duty_text = "Выходной! Дежурных нет 😊"
    else:
        duty_pair = get_duty_pair(tomorrow_date)
        duty_text = f"Дежурят: {duty_pair}"
    
    weekday = tomorrow_date.strftime("%A") 
    date_str = tomorrow_date.strftime("%d.%m.%Y")
    
    await update.message.reply_text(f"📅 Завтра, {date_str} ({weekday})\n{duty_text}")

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Используйте /resume для возобновления.")
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
    
    await update.message.reply_text(schedule_text)

async def set_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MANUAL_DUTY
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /set_duty [пароль] [имена дежурных]")
        return
    
    password = context.args[0]
    duty_names = " ".join(context.args[1:])
    
    if password != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    MANUAL_DUTY = duty_names
    await update.message.reply_text(f"✅ На сегодня ручно назначены: {duty_names}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MANUAL_DUTY
    
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    MANUAL_DUTY = None
    await update.message.reply_text("✅ Возврат к автоматическому графику")

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_PAUSED
    
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    BOT_PAUSED = True
    await update.message.reply_text("⏸️ Бот приостановлен. Используйте /resume для возобновления.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_PAUSED
    
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        return
    
    BOT_PAUSED = False
    await update.message.reply_text("▶️ Бот снова активен! График возобновлен.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("tomorrow", tomorrow))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CommandHandler("set_duty", set_duty))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    
    print("Бот запущен...")
    application.run_polling()

if name == "main":
    main()