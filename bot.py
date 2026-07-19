import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import json
import os
import asyncio
from flask import Flask
import threading

# ===== НАСТРОЙКИ (ЗАМЕНИ ТОКЕН!) =====
TOKEN = '8968112083:AAGXiHHEWQNHW1UmQSTWAPB_L6vJQjmj_8o'
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
        'users': {},
        'roles': {},
        'warns': {},
        'mutes': {},
        'banned': [],
        'creator': CREATOR_ID,
        'founder': FOUNDER_NAME
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
    level = get_role_level(user_id)
    return level <= 11

def is_moder(user_id):
    level = get_role_level(user_id)
    return level <= 14

def is_creator(user_id):
    return user_id == CREATOR_ID

def can_manage(user_id, target_id):
    user_level = get_role_level(user_id)
    target_level = get_role_level(target_id)
    return user_level < target_level

# ===== ПРИВЕТСТВИЕ =====
async def handle_new_chat_members(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text(
                f"🌊 Привет! Я проект **BLUE RUSSIA**\n"
                f"🤝 Рад с вами познакомиться!\n\n"
                f"👑 Мой создатель: товарищь **{FOUNDER_NAME}**\n"
                f"🤖 Мой разработчик: @eaxpa\n\n"
                f"⚡ Используй /start для начала работы"
            )
            return
        user_id = member.id
        if str(user_id) not in data['roles']:
            data['roles'][str(user_id)] = 'Участник'
            save_data()
        await update.message.reply_text(f"👋 Добро пожаловать, {member.full_name}!\n🌊 Ты в проекте BLUE RUSSIA")

# ===== СТАРТ =====
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if str(user_id) not in data['roles']:
        data['roles'][str(user_id)] = 'Участник'
        save_data()
    role = get_user_role(user_id)
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data='profile')],
        [InlineKeyboardButton("📋 Список ролей", callback_data='roles_list')],
        [InlineKeyboardButton("👑 Команда проекта", callback_data='team_list')]
    ]
    if is_creator(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Панель создателя", callback_data='apanel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🌊 **BLUE RUSSIA**\n\n"
        f"👤 Твоя роль: **{role}**\n"
        f"👑 Основатель бота: **{FOUNDER_NAME}**\n"
        f"🤖 Создатель: @eaxpa",
        reply_markup=reply_markup,
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
    text = f"👤 **Профиль**\n\n🆔 ID: `{user_id}`\n🎖️ Роль: **{role}**\n⚠️ Варнов: {warns}\n🔇 Мут: {'Да' if muted else 'Нет'}\n🚫 Бан: {'Да' if banned else 'Нет'}"
    await query.edit_message_text(text, parse_mode='Markdown')

# ===== СПИСОК РОЛЕЙ =====
async def roles_list(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    text = "📋 **Все роли (от высшей к низшей):**\n\n"
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
    text += f"👑 **Основатель бота:** {FOUNDER_NAME}"
    await query.edit_message_text(text, parse_mode='Markdown')

# ===== КОМАНДА ПРОЕКТА =====
async def team_list(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    text = "👑 **Команда проекта BLUE RUSSIA**\n\n"
    team = {}
    for uid, role in data['roles'].items():
        if role != 'Участник':
            if role not in team:
                team[role] = []
            team[role].append(uid)
    if not team:
        text += "Пока никого нет в команде."
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
        await update.message.reply_text("❌ Только создатель может выдавать роли!")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат!\n"
            "Использование: `/setrole ID Роль`\n"
            "Пример: `/setrole 7743220894 Основатель`\n\n"
            "Доступные роли:\n" + "\n".join(ROLE_NAMES)
        )
        return

    target_id = args[0]
    role_name = ' '.join(args[1:])

    if role_name not in ROLES:
        await update.message.reply_text(
            f"❌ Роль '{role_name}' не существует!\n"
            "Доступные роли:\n" + "\n".join(ROLE_NAMES)
        )
        return

    data['roles'][str(target_id)] = role_name
    save_data()

    await update.message.reply_text(
        f"✅ Пользователю `{target_id}` выдана роль **{role_name}**!",
        parse_mode='Markdown'
    )

# ===== ЗАБОР РОЛИ =====
async def removerole(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_creator(user_id):
        await update.message.reply_text("❌ Только создатель может забирать роли!")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат!\n"
            "Использование: `/removerole ID Роль`\n"
            "Пример: `/removerole 7743220894 Администратор`"
        )
        return

    target_id = args[0]
    role_name = ' '.join(args[1:])

    if data['roles'].get(str(target_id)) == role_name:
        data['roles'][str(target_id)] = 'Участник'
        save_data()
        await update.message.reply_text(
            f"✅ У пользователя `{target_id}` забрана роль **{role_name}**!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ У пользователя нет роли {role_name}!")

# ===== ПАНЕЛЬ СОЗДАТЕЛЯ =====
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👑 **Панель создателя**\n\n"
        "Используй команды:\n"
        "`/setrole ID Роль` — выдать роль\n"
        "`/removerole ID Роль` — забрать роль",
        reply_markup=reply_markup,
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
        text = f"📊 **Статистика:**\n\n👥 Пользователей: {len(data['users'])}\n🎖️ Ролей выдано: {len(data['roles'])}\n⚠️ Варнов выдано: {sum(data['warns'].values())}\n🔇 В муте: {sum(1 for v in data['mutes'].values() if v)}\n🚫 Забанено: {len(data['banned'])}"
        await query.edit_message_text(text, parse_mode='Markdown')
    elif action == 'users_list':
        text = "📋 **Пользователи с ролями:**\n\n"
        for uid, role in data['roles'].items():
            text += f"🆔 `{uid}` — **{role}**\n"
        await query.edit_message_text(text, parse_mode='Markdown')
    elif action == 'reset_data':
        data['users'] = {}
        data['roles'] = {}
        data['warns'] = {}
        data['mutes'] = {}
        data['banned'] = []
        save_data()
        await query.edit_message_text("✅ Все данные сброшены!")

# ===== МОДЕРАЦИЯ =====
async def ban(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❗ /ban @user [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if not can_manage(user_id, target_id):
        await update.message.reply_text("❌ Нельзя забанить пользователя с высшей ролью!")
        return
    reason = ' '.join(context.args[1:]) or 'Не указана'
    data['banned'].append(str(target_id))
    save_data()
    await update.message.reply_text(f"✅ Забанен {context.args[0]}!\nПричина: {reason}")

async def kick(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❗ /kick @user [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if not can_manage(user_id, target_id):
        await update.message.reply_text("❌ Нельзя кикнуть пользователя с высшей ролью!")
        return
    reason = ' '.join(context.args[1:]) or 'Не указана'
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await context.bot.unban_chat_member(update.effective_chat.id, target_id)
        await update.message.reply_text(f"✅ Кикнут {context.args[0]}!\nПричина: {reason}")
    except:
        await update.message.reply_text("❌ Ошибка при кике!")

async def mute(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❗ /mute @user [минуты] [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if not can_manage(user_id, target_id):
        await update.message.reply_text("❌ Нельзя замутить пользователя с высшей ролью!")
        return
    minutes = int(context.args[1]) if len(context.args) > 1 else 5
    reason = ' '.join(context.args[2:]) or 'Не указана'
    data['mutes'][str(target_id)] = True
    save_data()
    await update.message.reply_text(f"✅ Замучен {context.args[0]} на {minutes} мин!\nПричина: {reason}")
    await asyncio.sleep(minutes * 60)
    data['mutes'][str(target_id)] = False
    save_data()

async def unmute(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❗ /unmute @user")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    data['mutes'][str(target_id)] = False
    save_data()
    await update.message.reply_text(f"✅ Размучен {context.args[0]}!")

async def warn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❗ /warn @user [причина]")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    reason = ' '.join(context.args[1:]) or 'Не указана'
    data['warns'][str(target_id)] = data['warns'].get(str(target_id), 0) + 1
    save_data()
    await update.message.reply_text(f"⚠️ Варн {context.args[0]}!\nПричина: {reason}\nВсего варнов: {data['warns'][str(target_id)]}")

async def unwarn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❗ /unwarn @user")
        return
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    if data['warns'].get(str(target_id), 0) > 0:
        data['warns'][str(target_id)] -= 1
        save_data()
        await update.message.reply_text(f"✅ Снят варн с {context.args[0]}!\nОсталось варнов: {data['warns'][str(target_id)]}")
    else:
        await update.message.reply_text("❌ У пользователя нет варнов!")

# ===== ФЛАСК ДЛЯ RENDER =====
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "BLUE RUSSIA Bot is running!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

# ===== ТЕЛЕГРАМ БОТ =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('apanel', apanel))
app.add_handler(CommandHandler('setrole', setrole))
app.add_handler(CommandHandler('removerole', removerole))
app.add_handler(CommandHandler('ban', ban))
app.add_handler(CommandHandler('kick', kick))
app.add_handler(CommandHandler('mute', mute))
app.add_handler(CommandHandler('unmute', unmute))
app.add_handler(CommandHandler('warn', warn))
app.add_handler(CommandHandler('unwarn', unwarn))

app.add_handler(CallbackQueryHandler(profile, pattern='profile'))
app.add_handler(CallbackQueryHandler(roles_list, pattern='roles_list'))
app.add_handler(CallbackQueryHandler(team_list, pattern='team_list'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='apanel'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='stats'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='users_list'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='reset_data'))

app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))

# ===== ЗАПУСК =====
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    print("🤖 Бот BLUE RUSSIA запущен!")
    print(f"👑 Основатель: {FOUNDER_NAME}")
    print(f"📋 Всего ролей: {len(ROLES)}")
    app.run_polling()
