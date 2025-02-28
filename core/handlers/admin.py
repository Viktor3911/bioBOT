import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery, Message
from aiogram import Router

from core.utils import dependencies

router = Router()

@router.message(F.text, Command("add_admin"))
async def add_to_admin_list(message: Message):
    if message.from_user.id not in config.adminsId:
        return

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        username = user.username or "без имени пользователя"
    else:
        args = message.text.split()[1:]
        if not args:
            msg = await message.reply("Использование: /add_admin <user_id> или ответьте на сообщение пользователя командой /add_admin")
            fc.delete_message_with_delay(msg)
            return

        try:
            user_id = int(args[0])
            user = await dependencies.bot.get_chat_member(message.chat.id, user_id)
            username = user.user.username or "без имени пользователя"
        except ValueError:
            msg = await message.reply("Некорректный ID пользователя. Используйте число или ответьте на сообщение пользователя.")
            fc.delete_message_with_delay(msg)
            return
        except Exception:
            await message.reply(f"Не удалось найти пользователя с ID {args[0]}.")
            return

    if user_id not in config.adminsId:
        config.adminsId.append(user_id)
        with open(config.ADMINS_FILE, "a", encoding='utf-8') as f:
            f.write(f"\n{user_id}")
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) добавлен в список админов.")
        await fc.log_admin_action(message.from_user.id, "add_admin", f"Added admin: {user_id} (@{username})")
    else:
        await message.reply(f"Пользователь @{html.escape(username)} (ID: {user_id}) уже является админом.")
