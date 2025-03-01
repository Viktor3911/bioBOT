from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Регистрация'),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command='add_director', description='Добавить директора'),
        BotCommand(command='add_assistant', description='Добавить ассистента'),
        BotCommand(command='add_assistant_admin', description='.'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
