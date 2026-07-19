import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import json
import os
import asyncio

# ===== НАСТРОЙКИ =====
TOKEN = '8968112083:AAGXiHHEWQNHW1UmQSTWAPB_L6vJQjmj_8o'
CREATOR_ID = 7743220894  # ID создателя (@eaxpa) — замени на свой
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

# ===== ВСЕ РОЛИ (ПОЛНАЯ ИЕРАРХИЯ — ИСПРАВЛЕНА) =====
ROLES = {
    # Высшее руководство
    'Основатель': 0,
    'Зам.основателя': 1,
    'Специальный администратор': 2,
    'Заместитель Специального Администратора': 3,
    
    # Главные администраторы
    'Главный администратор': 4,
    'Основной заместитель ГА': 5,
    'Заместитель главного администратора (ЗГА)': 6,
    'Куратор администрации': 7,
    
    # Администраторы
    'ГС': 8,
    'Старший администратор': 9,
    'Заместитель ГС': 10,
    'Администратор': 11,
    
    # Модераторы
    'Старший модератор': 12,
    'Модератор': 13,
    'Младший модератор': 14,
    
    # Тех.специалисты (отдельная ветка)
    'Главный Тех.Специалист': 15,
    'Заместитель главного Технического Специалиста': 16,
    'Главный куратор Тех.Специалистов': 17,
    'Куратор Тех.Специалистов': 18,
    'Технический специалист': 19,
    
    # Доп. администрация
    'Контроль качества': 20,
    'Тестировщик': 21,
    
    # Обычные
    'Участник': 22
}

ROLE_NAMES = list(ROLES.keys())

# ===== ПРОВЕРКА ПРАВ =====
def get_user_role(user_id):
    return data['roles'].get(str(user_id), 'Участник')

def get_role_level(user_id):
    role = get_user_role(user_id)
    return ROLES.get(role, 999)

def is_admin(user_id):
    level = get_role_level(user_id)
    return level <= 11  # Администратор и выше

def is_moder(user_id):
    level = get_role_level(user_id)
    return level <= 14  # Модератор и выше

def is_tech(user_id):
    level = get_role_level(user_id)
    return 15 <= level <= 19  # Тех.специалисты

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
                f"⚡ Используй /start для начала работы\n"
                f"📋 Команды модерации:\n"
                f"/ban, /kick, /mute, /unmute, /warn, /unwarn"
            )
            return
        
        user_id = member.id
        if str(user_id) not in data['roles']:
            data['roles'][str(user_id)] = 'Участник'
            save_data()
        
        await update.message.reply_text(
            f"👋 Добро пожаловать, {member.full_name}!\n"
            f"🌊 Ты в проекте BLUE RUSSIA"
        )

# ===== КОМАНДЫ =====
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
        f"🤖 Создатель: @eaxpa\n\n"
        f"Используй кнопки для навигации.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def profile(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    role = get_user_role(user_id)
    warns = data['warns'].get(str(user_id), 0)
    muted = data['mutes'].get(str(user_id), False)
    banned = str(user_id) in data['banned']
    
    text = f"👤 **Профиль**\n\n"
    text += f"🆔 ID: `{user_id}`\n"
    text += f"🎖️ Роль: **{role}**\n"
    text += f"⚠️ Варнов: {warns}\n"
    text += f"🔇 Мут: {'Да' if muted else 'Нет'}\n"
    text += f"🚫 Бан: {'Да' if banned else 'Нет'}\n"
    
    await query.edit_message_text(text, parse_mode='Markdown')

async def roles_list(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    text = "📋 **Все роли BLUE RUSSIA (от высшей к низшей):**\n\n"
    
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
                emoji = "👑" if ROLES[role] <= 3 else "⚔️" if ROLES[role] <= 11 else "🛡️" if ROLES[role] <= 14 else "🔧" if ROLES[role] <= 19 else "📌"
                text += f"  {emoji} {role}\n"
        text += "\n"
    
    text += f"👑 **Основатель бота:** {FOUNDER_NAME}"
    
    await query.edit_message_text(text, parse_mode='Markdown')

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

# ===== ПАНЕЛЬ СОЗДАТЕЛЯ =====
async def apanel(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_creator(user_id):
        await update.message.reply_text("❌ Только создатель бота может использовать эту команду!")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Выдать роль", callback_data='give_role')],
        [InlineKeyboardButton("➖ Забрать роль", callback_data='remove_role')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
        [InlineKeyboardButton("📋 Список пользователей", callback_data='users_list')],
        [InlineKeyboardButton("🔄 Сброс данных", callback_data='reset_data')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👑 **Панель создателя**\n\n"
        f"👤 Создатель: @eaxpa\n"
        f"👑 Основатель: **{FOUNDER_NAME}**\n\n"
        f"Выбери действие:",
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
    
    if action == 'give_role':
        roles_text = "\n".join([f"• {r}" for r in ROLE_NAMES])
        await query.edit_message_text(
            f"📝 **Выдать роль**\n\n"
            f"Введите ID пользователя и роль через пробел.\n"
            f"Доступные роли:\n{roles_text}\n\n"
            f"Пример: `123456789 Администратор`"
        )
        context.user_data['action'] = 'give_role'
    
    elif action == 'remove_role':
        await query.edit_message_text(
            f"📝 **Забрать роль**\n\n"
            f"Введите ID пользователя и роль через пробел.\n"
            f"Пример: `123456789 Модератор`"
        )
        context.user_data['action'] = 'remove_role'
    
    elif action == 'stats':
        text = "📊 **Статистика бота:**\n\n"
        text += f"👥 Пользователей: {len(data['users'])}\n"
        text += f"🎖️ Ролей выдано: {len(data['roles'])}\n"
        text += f"⚠️ Варнов выдано: {sum(data['warns'].values())}\n"
        text += f"🔇 Замучено: {sum(1 for v in data['mutes'].values() if v)}\n"
        text += f"🚫 Забанено: {len(data['banned'])}\n"
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
        await update.message.reply_text("❗ Использование: /ban @username [причина]")
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
    
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else 'Не указана'
    data['banned'].append(str(target_id))
    save_data()
    
    await update.message.reply_text(f"✅ Пользователь {context.args[0]} забанен!\nПричина: {reason}")

async def kick(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❗ Использование: /kick @username [причина]")
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
    
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else 'Не указана'
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await context.bot.unban_chat_member(update.effective_chat.id, target_id)
        await update.message.reply_text(f"✅ Пользователь {context.args[0]} кикнут!\nПричина: {reason}")
    except:
        await update.message.reply_text("❌ Ошибка при кике!")

async def mute(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❗ Использование: /mute @username [время в минутах] [причина]")
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
    reason = ' '.join(context.args[2:]) if len(context.args) > 2 else 'Не указана'
    
    data['mutes'][str(target_id)] = True
    save_data()
    
    await update.message.reply_text(f"✅ Пользователь {context.args[0]} замучен на {minutes} минут!\nПричина: {reason}")
    
    await asyncio.sleep(minutes * 60)
    data['mutes'][str(target_id)] = False
    save_data()

async def unmute(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❗ Использование: /unmute @username")
        return
    
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    
    data['mutes'][str(target_id)] = False
    save_data()
    await update.message.reply_text(f"✅ Пользователь {context.args[0]} размучен!")

async def warn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❗ Использование: /warn @username [причина]")
        return
    
    try:
        target = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        target_id = target.user.id
    except:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else 'Не указана'
    data['warns'][str(target_id)] = data['warns'].get(str(target_id), 0) + 1
    save_data()
    
    await update.message.reply_text(
        f"⚠️ Пользователь {context.args[0]} получил предупреждение!\n"
        f"Причина: {reason}\n"
        f"Всего варнов: {data['warns'][str(target_id)]}"
    )

async def unwarn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_moder(user_id):
        await update.message.reply_text("❌ Недостаточно прав!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("❗ Использование: /unwarn @username")
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
        await update.message.reply_text(
            f"✅ Снято предупреждение с {context.args[0]}!\n"
            f"Осталось варнов: {data['warns'][str(target_id)]}"
        )
    else:
        await update.message.reply_text("❌ У пользователя нет варнов!")

# ===== ОБРАБОТЧИК СООБЩЕНИЙ =====
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if str(user_id) in data['banned']:
        await update.message.delete()
        return
    
    if data['mutes'].get(str(user_id), False):
        await update.message.delete()
        await update.message.reply_text("🔇 Вы в муте! Не пишите.")

async def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if context.user_data.get('action') == 'give_role':
        parts = update.message.text.split()
        if len(parts) == 2:
            target_id, role = parts
            if role in ROLES:
                data['roles'][target_id] = role
                save_data()
                await update.message.reply_text(f"✅ Пользователю {target_id} выдана роль **{role}**!", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Роль '{role}' не существует!")
        else:
            await update.message.reply_text("❌ Неверный формат! ID и роль через пробел.")
        context.user_data['action'] = None
    
    elif context.user_data.get('action') == 'remove_role':
        parts = update.message.text.split()
        if len(parts) == 2:
            target_id, role = parts
            if data['roles'].get(target_id) == role:
                data['roles'][target_id] = 'Участник'
                save_data()
                await update.message.reply_text(f"✅ У пользователя {target_id} забрана роль **{role}**!", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ У пользователя нет роли {role}!")
        else:
            await update.message.reply_text("❌ Неверный формат! ID и роль через пробел.")
        context.user_data['action'] = None

# ===== ЗАПУСК =====
app = Application.builder().token(TOKEN).build()

# Команды
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('apanel', apanel))
app.add_handler(CommandHandler('ban', ban))
app.add_handler(CommandHandler('kick', kick))
app.add_handler(CommandHandler('mute', mute))
app.add_handler(CommandHandler('unmute', unmute))
app.add_handler(CommandHandler('warn', warn))
app.add_handler(CommandHandler('unwarn', unwarn))

# Callback
app.add_handler(CallbackQueryHandler(profile, pattern='profile'))
app.add_handler(CallbackQueryHandler(roles_list, pattern='roles_list'))
app.add_handler(CallbackQueryHandler(team_list, pattern='team_list'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='apanel'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='give_role'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='remove_role'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='stats'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='users_list'))
app.add_handler(CallbackQueryHandler(apanel_callback, pattern='reset_data'))

# Обработчики сообщений
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.ALL, handle_message))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))

print("🤖 Бот BLUE RUSSIA запущен!")
print(f"👑 Основатель: {FOUNDER_NAME}")
print(f"🤖 Создатель: @eaxpa")
print(f"📋 Всего ролей: {len(ROLES)}")

app.run_polling()
