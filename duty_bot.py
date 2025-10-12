import logging
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
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
GROUP_CHAT_ID = None  # ID группового чата

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
    global GROUP_CHAT_ID
    
    # Сохраняем ID чата (группы или ЛС)
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ['group', 'supergroup']:
        GROUP_CHAT_ID = chat_id
        await update.message.reply_text(
            "🤖 Бот графика дежурств активирован!\n\n"
            "📋 КОМАНДЫ ДЛЯ ВСЕХ:\n"
            "/today - дежурные сегодня\n"
            "/tomorrow - дежурные завтра\n"
            "/schedule - график на неделю\n\n"
            "⚙️ АДМИНИСТРИРОВАНИЕ:\n"
            "Напишите боту в ЛС для управления графиком\n\n"
            "📅 График начинается с 13.10.2025"
        )
    else:
        # ЛС с ботом
        await update.message.reply_text(
            "🤖 Панель администратора\n\n"
            "📋 КОМАНДЫ УПРАВЛЕНИЯ:\n"
            "/setduty - ручное назначение\n"
            "/resetduty - сброс в авторежим\n"
            "/pausebot - приостановить бота\n"
            "/resumebot - возобновить работу\n\n"
            "🔐 Все команды требуют пароль"
        )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Админ может возобновить работу через ЛС.")
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
        await update.message.reply_text("❌ Бот приостановлен. Админ может возобновить работу через ЛС.")
        return
    
    tomorrow_date = datetime.now().date() + timedelta(days=1)
    
    if is_weekend(tomorrow_date):
        duty_text = "Выходной! Дежурных нет 😊"
    else:
        duty_pair = get_duty_pair(tomorrow_date)
        duty_text = f"Дежурят: {duty_pair}" if duty_pair else "❌ Ошибка расчета"
    
    days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    weekday_ru = days_ru[tomorrow_date.weekday()]
    date_str = tomorrow_date.strftime("%d.%m.%Y")
    
    await update.message.reply_text(f"📅 Завтра, {date_str} ({weekday_ru})\n{duty_text}")

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if BOT_PAUSED:
        await update.message.reply_text("❌ Бот приостановлен. Админ может возобновить работу через ЛС.")
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

async def send_to_group(message):
    """Отправить сообщение в группу"""
    global GROUP_CHAT_ID
    if GROUP_CHAT_ID:
        from telegram.error import TelegramError
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
        except TelegramError as e:
            print(f"Ошибка отправки в группу: {e}")

# АДМИН-КОМАНДЫ (только в ЛС)
async def set_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало ручного назначения (только в ЛС)"""
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Эта команда доступна только в личных сообщениях с ботом")
        return
    
    await update.message.reply_text(
        "👥 Введите имена дежурных для ручного назначения:\n"
        "Пример: Иванов Петров"
    )
    context.user_data['waiting_for'] = 'duty_names'

async def reset_duty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало сброса (только в ЛС)"""
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Эта команда доступна только в личных сообщениях с ботом")
        return
    
    await update.message.reply_text("🔐 Введите пароль для сброса:")
    context.user_data['waiting_for'] = 'reset_password'

async def pause_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало приостановки (только в ЛС)"""
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Эта команда доступна только в личных сообщениях с ботом")
        return
    
    await update.message.reply_text("🔐 Введите пароль для приостановки бота:")
    context.user_data['waiting_for'] = 'pause_password'

async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало возобновления (только в ЛС)"""
    if update.effective_chat.type in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ Эта команда доступна только в личных сообщениях с ботом")
        return
    
    await update.message.reply_text("🔐 Введите пароль для возобновления работы:")
    context.user_data['waiting_for'] = 'resume_password'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений (для двухшаговых команд)"""
    global MANUAL_DUTY, BOT_PAUSED
    
    # Только ЛС для админ-команд
    if update.effective_chat.type in ['group', 'supergroup']:
        return
    
    waiting_for = context.user_data.get('waiting_for')
    user_text = update.message.text
    
    if not waiting_for:
        # Обычное сообщение в ЛС
        await update.message.reply_text("ℹ️ Используйте команды из меню /start")
        return
    
    if waiting_for == 'duty_names':
        # Получили имена дежурных, теперь запрашиваем пароль
        context.user_data['pending_duty_names'] = user_text
        context.user_data['waiting_for'] = 'duty_password'
        await update.message.reply_text("🔐 Введите пароль для подтверждения:")
        
    elif waiting_for == 'duty_password':
        # Проверяем пароль для ручного назначения
        if user_text == ADMIN_PASSWORD:
            duty_names = context.user_data.get('pending_duty_names', '')
            MANUAL_DUTY = duty_names
            await update.message.reply_text("✅ Дежурные назначены!")
            # Отправляем сообщение в группу
            await send_to_group(f"⚡ Ручное назначение!\n📅 Дежурят: {duty_names}")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        # Очищаем временные данные
        context.user_data.pop('waiting_for', None)
        context.user_data.pop('pending_duty_names', None)
        
    elif waiting_for == 'reset_password':
        # Проверяем пароль для сброса
        if user_text == ADMIN_PASSWORD:
            MANUAL_DUTY = None
            await update.message.reply_text("✅ График сброшен!")
            await send_to_group("✅ Возврат к автоматическому графику")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        context.user_data.pop('waiting_for', None)
        
    elif waiting_for == 'pause_password':
        # Проверяем пароль для паузы
        if user_text == ADMIN_PASSWORD:
            BOT_PAUSED = True
            await update.message.reply_text("✅ Бот приостановлен!")
            await send_to_group("⏸️ Бот приостановлен. Админ может возобновить работу через ЛС.")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        context.user_data.pop('waiting_for', None)
        
    elif waiting_for == 'resume_password':
        # Проверяем пароль для возобновления
        if user_text == ADMIN_PASSWORD:
            BOT_PAUSED = False
            await update.message.reply_text("✅ Бот возобновлен!")
            await send_to_group("▶️ Бот снова активен! График возобновлен.")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
        context.user_data.pop('waiting_for', None)

def main():
    # Запускаем веб-сервер в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("tomorrow", tomorrow))
    application.add_handler(CommandHandler("schedule", schedule))
    
    # Админ-команды (только в ЛС)
    application.add_handler(CommandHandler("setduty", set_duty))
    application.add_handler(CommandHandler("resetduty", reset_duty))
    application.add_handler(CommandHandler("pausebot", pause_bot))
    application.add_handler(CommandHandler("resumebot", resume_bot))
    
    # Обработчик всех сообщений (для двухшаговых команд)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот дежурств запущен!")
    print("📅 Дата начала графика:", START_DATE.strftime("%d.%m.%Y"))
    print("👥 Всего пар дежурных:", len(DUTY_LIST))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
