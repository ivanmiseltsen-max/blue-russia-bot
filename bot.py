import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import json
import os
import asyncio
from flask import Flask
import threading
import requests
import time

# ===== НАСТРОЙКИ (ЗАМЕНИ ТОКЕН!) =====
TOKEN = '8968112083:AAF9UbvAvJ8sJs7CPeFTfetGXxadEO9SQVE'
CREATOR_ID = 7743220894
FOUNDER_NAME = 'Савелий'

logging.basicConfig(level=logging.INFO)

# ===== ДАННЫЕ =====
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'roles': {},
        'warns': {},
        'mutes': {},
        'banned': []
    }

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data = load_data()

# ===== ВСЕ РОЛИ =====
ROLES = {
    'Основатель': 0,
    'Зам.основателя': 1,
    'Специальный администратор': 2,
    'Заместитель Специального Администратора': 3,
    'Главный администратор': 4,
    'Основной заместитель ГА': 5,
    'Заместитель главного администратора (ЗГА)': 6,
    'Куратор администрации': 7,
    'ГС': 8,
    'Старший администратор': 9,
    'Заместитель ГС': 10,
    'Администратор': 11,
    'Старший модератор': 12,
    'Модератор': 13,
    'Младший модератор': 14,
    'Главный Тех.Специалист': 15,
    'Заместитель главного Технического Специалиста': 16,
    'Главный куратор Тех.Специалистов': 17,
    'Куратор Тех.Специалистов': 18,
    'Технический специалист': 19,
    'Контроль качества': 20,
    'Тестировщик': 21,
    'Участник': 22
}

ROLE_NAMES = list(ROLES.keys())

def get_user_role(user_id):
    return data['roles'].get(str(user_id), 'Участник')

def get_role_level(user_id):
    role = get_user_role(user_id)
    return ROLES.get(role, 999)

def is_admin(user_id):
    return get_role_level(user_id) <= 11

def is_moder(user_id):
    return get_role_level(user_id) <= 14

def is_creator(user_id):
    return user_id == CREATOR_ID

def can_manage(user_id, target_id):
    return get_role_level(user_id) < get_role_level(target_id)

# ===== ПРИВЕТСТВИЕ =====
async def handle_new_chat_members(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text(
                f"🌊 Привет! Я проект **BLUE RUSSIA**\n"
                f"🤝 Рад с вами познакомиться!\n"
                f"👑 Создатель: товарищь **{FOUNDER_NAME}**\n"
                f"🤖 Разработчик: @eaxpa\n"
                f"⚡ Используй /start"
            )
            return
        user_id = member.id
        if str(user_id) not in data['roles']:
            data['roles'][str(user_id)] = 'Участник'
            save_data()
        await update.message.reply_text(f"👋 Добро пожаловать, {member.full_name}!")

# ===== СТАРТ =====
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if str(user_id) not in data['roles']:
        data['roles'][str(user_id)] = 'Участник'
        save_data()
    role = get_user_role(user_id)
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data='profile')],
        [InlineKeyboardButton("📋 Роли", callback_data='roles_list')],
        [InlineKeyboardButton("👑 Команда", callback_data='team_list')]
    ]
    if is_creator(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Админка", callback_data='apanel')])
    await update.message.reply_text(
        f"🌊 **BLUE RUSSIA**\n"
        f"👤 Твоя роль: **{role}**\n"
        f"👑 Основатель: **{FOUNDER_NAME}**\n"
        f"🤖 Создатель: @eaxpa",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ===== ПРОФИЛЬ =====
async def profile(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    role = get_user_role(user_id)
    warns = data['warns'].get(str(user_id), 0)
    muted = data['mutes'].get(str(user_id), False)
    banned = str(user_id) in data['banned']
    await query.edit_message_text(
        f"👤 **Профиль**\n"
        f"🆔 ID: `{user_id}`\n"
        f"🎖️ Роль: **{role}**\n"
        f"⚠️ Варнов: {warns}\n"
        f"🔇 Мут: {'Да' if muted else 'Нет'}\n"
        f"🚫 Бан: {'Да' if banned else 'Нет'}",
        parse_mode='Markdown'
    )

# ===== РОЛИ =====
async def roles_list(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    text = "📋 **Все роли:**\n\n"
    groups = {
        '👑 Высшее руководство': ['Основатель', 'Зам.основателя', 'Специальный администратор', 'Заместитель Специального Администратора'],
        '👑 Главные администраторы': ['Главный администратор', 'Основной заместитель ГА', 'Заместитель главного администратора (ЗГА)', 'Куратор администрации'],
        '⚔️ Администраторы': ['ГС', 'Старший администратор', 'Заместитель ГС', 'Администратор'],
        '🛡️ Модераторы': ['Старший модератор', 'Модератор', 'Младший модератор'],
        '🔧 Тех.специалисты': ['Главный Тех.Специалист', 'Заместитель главного Технического Специалиста', 'Главный куратор Тех.Специалистов', 'Куратор Тех.Специалистов', 'Технический специалист'],
        '📌 Доп. администрация': ['Контроль качества', 'Тестировщик'],
        '👤 Участники': ['Участник']
    }
    for group, roles in groups.items():
        text += f"**{group}**\n"
        for role in roles:
            if role in ROLES:
                text += f"  • {role}\n"
        text += "\n"
    await query.edit_message_text(text, parse_mode='Markdown')

# ===== КОМАНДА ПРОЕКТА =====
async def team_list(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    text = "👑 **Команда проекта:**\n\n"
    team = {}
    for uid, role in data['roles'].items():
        if role != 'Участник':
            if role not in team:
                team[role] = []
            team[role].append(uid)
    if not team:
        text += "Пока никого нет."
    else:
        for role in ROLE_NAMES:
            if role in team and role != 'Участник':
                text += f"**{role}:**\n"
                for uid in team[role]:
                    text += f"  • `{uid}`\n"
                text += "\n"
    await query.edit_message_text(text, parse_mode='Markdown')

# ===== ВЫДАЧА РОЛИ =====
async def setrole(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_creator(user_id):
        await update.message.reply_text("❌ Только создатель!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /setrole ID Роль\nПример: /setrole 7743220894 Основатель")
        return
    target_id = context.args[0]
    role_name = ' '.join(context.args[1:])
    if role_name not in ROLES:
        await update.message.reply_text(f"❌ Роль '{role_name}' не существует!")
        return
    data['roles'][str(target_id)] = role_name
    save_data()
    await update.message.reply_text(f"✅ Пользователю `{target_id}` выдана роль **{role_name}**!", parse_mode='Markdown')

# ===== ЗАБОР РОЛИ =====
async def removerole(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_creator(user_id):
        await update.message.reply_text("❌ Только создатель!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /removerole ID Роль")
        return
    target_id = context.args[0]
    role_name = ' '.join(context.args[1:])
    if data['roles'].get(str(target_id)) == role_name:
        data['roles'][str(target_id)] = 'Участник'
        save_data()
        await update.message.reply_text(f"✅ У `{target_id}` забрана роль **{role_name}**!", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ У пользователя нет роли {role_name}!")

# ===== КИК =====
async def kick(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Нет прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ /kick @username [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
        target_name = target.user.username or target.user.first_name
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if target_id == user_id or target_id == CREATOR_ID or not can_manage(user_id, target_id):
        await update.message.reply_text("❌ Нельзя кикнуть этого пользователя!")
        return
    reason = ' '.join(context.args[1:]) or 'Не указана'
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await context.bot.unban_chat_member(update.effective_chat.id, target_id)
        await update.message.reply_text(f"✅ @{target_name} кикнут! Причина: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ===== БАН =====
async def ban(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ /ban @username [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
        target_name = target.user.username or target.user.first_name
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if target_id == user_id or target_id == CREATOR_ID or not can_manage(user_id, target_id):
        await update.message.reply_text("❌ Нельзя забанить!")
        return
    reason = ' '.join(context.args[1:]) or 'Не указана'
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        data['banned'].append(str(target_id))
        save_data()
        await update.message.reply_text(f"✅ @{target_name} забанен! Причина: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ===== МУТ =====
async def mute(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Нет прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ /mute @username [минуты] [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
        target_name = target.user.username or target.user.first_name
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if not can_manage(user_id, target_id):
        await update.message.reply_text("❌ Нельзя замутить!")
        return
    minutes = int(context.args[1]) if len(context.args) > 1 else 5
    reason = ' '.join(context.args[2:]) or 'Не указана'
    data['mutes'][str(target_id)] = True
    save_data()
    await update.message.reply_text(f"✅ @{target_name} замучен на {minutes} мин! Причина: {reason}")
    await asyncio.sleep(minutes * 60)
    data['mutes'][str(target_id)] = False
    save_data()

# ===== АНМУТ =====
async def unmute(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Нет прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ /unmute @username")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
        target_name = target.user.username or target.user.first_name
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if str(target_id) in data['mutes']:
        data['mutes'][str(target_id)] = False
        save_data()
        await update.message.reply_text(f"✅ @{target_name} размучен!")
    else:
        await update.message.reply_text("❌ Пользователь не в муте!")

# ===== ВАРН =====
async def warn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Нет прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ /warn @username [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
        target_name = target.user.username or target.user.first_name
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    reason = ' '.join(context.args[1:]) or 'Не указана'
    data['warns'][str(target_id)] = data['warns'].get(str(target_id), 0) + 1
    save_data()
    await update.message.reply_text(f"⚠️ @{target_name} получил варн! Причина: {reason}\nВсего: {data['warns'][str(target_id)]}")

# ===== АНВАРН =====
async def unwarn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Нет прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ /unwarn @username")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
        target_name = target.user.username or target.user.first_name
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if data['warns'].get(str(target_id), 0) > 0:
        data['warns'][str(target_id)] -= 1
        save_data()
        await update.message.reply_text(f"✅ Снят варн с @{target_name}! Осталось: {data['warns'][str(target_id)]}")
    else:
        await update.message.reply_text("❌ Нет варнов!")

# ===== АДМИНКА =====
async def apanel(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_creator(user_id):
        await update.message.reply_text("❌ Только создатель!")
        return
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
        [InlineKeyboardButton("📋 Список пользователей", callback_data='users_list')],
        [InlineKeyboardButton("🔄 Сброс данных", callback_data='reset_data')]
    ]
    await update.message.reply_text(
        "👑 **Панель создателя**\n\n"
        "Команды:\n"
        "/setrole ID Роль — выдать роль\n"
        "/removerole ID Роль — забрать роль",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def apanel_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_creator(user_id):
        await query.edit_message_text("❌ Только создатель!")
        return
    action = query.data
    if action == 'stats':
        text = f"📊 **Статистика:**\n👥 Пользователей: {len(data['roles'])}\n⚠️ Варнов: {sum(data['warns'].values())}\n🔇 В муте: {sum(1 for v in data['mutes'].values() if v)}\n🚫 Забанено: {len(data['banned'])}"
        await query.edit_message_text(text, parse_mode='Markdown')
    elif action == 'users_list':
        text = "📋 **Пользователи:**\n"
        for uid, role in data['roles'].items():
            text += f"🆔 `{uid}` — **{role}**\n"
        await query.edit_message_text(text, parse_mode='Markdown')
    elif action == 'reset_data':
        data['roles'] = {}
        data['warns'] = {}
        data['mutes'] = {}
        data['banned'] = []
        save_data()
        await query.edit_message_text("✅ Все данные сброшены!")

# ===== ОБРАБОТЧИК СООБЩЕНИЙ =====
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if str(user_id) in data['banned']:
        await update.message.delete()
        return
    if data['mutes'].get(str(user_id), False):
        await update.message.delete()
        await update.message.reply_text("🔇 Вы в муте!")

# ===== ФЛАСК ДЛЯ ПИНГА (RENDER НЕ ЗАСЫПАЕТ) =====
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "BLUE RUSSIA Bot is running!"

@app_flask.route('/ping')
def ping():
    return "PONG", 200

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

# ===== ТЕЛЕГРАМ БОТ =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('setrole', setrole))
app.add_handler(CommandHandler('removerole', removerole))
app.add_handler(CommandHandler('kick', kick))
app.add_handler(CommandHandler('ban', ban))
app.add_handler(CommandHandler('mute', mute))
app.add_handler(CommandHandler('unmute', unmute))
app.add_handler(CommandHandler('warn', warn))
app.add_handler(CommandHandler('unwarn', unwarn))
app.add_handler(CommandHandler('apanel', apanel))

app.add_handler(CallbackQueryHandler(profile, pattern='profile'))
app.add_handler(CallbackQueryHandler(roles_list, pattern='roles_list'))
app.add_handler(CallbackQueryHandler(team_list, pattern='team_list'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='apanel'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='stats'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='users_list'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='reset_data'))

app.add_handler(MessageHandler(filters.ALL, handle_message))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))

# ===== ПИНГ-СИСТЕМА (ЧТОБЫ НЕ ЗАСЫПАЛ) =====
def keep_alive():
    while True:
        try:
            requests.get('https://blue-russia-bot.onrender.com/ping')
        except:
            pass
        time.sleep(300)  # 5 минут

# ===== ЗАПУСК =====
if __name__ == '__main__':
    # Запускаем Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Запускаем пинг-систему
    ping_thread = threading.Thread(target=keep_alive)
    ping_thread.start()
    
    print("🤖 БОТ ЗАПУЩЕН!")
    print(f"👑 Основатель: {FOUNDER_NAME}")
    print("✅ Данные сохраняются в data.json")
    print("✅ Команды: /kick, /ban, /mute, /unmute, /warn, /unwarn")
    print("✅ Пинг-система активна (бот не засыпает)")
    
    app.run_polling()
