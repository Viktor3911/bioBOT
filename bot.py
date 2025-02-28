import asyncio
from datetime import datetime
import re
import logging

from aiogram.filters.command import Command, CommandObject, CommandStart
from aiogram import F, Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, Message
from aiogram.types import PhotoSize
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import StateFilter
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.settings import BOT_TOKEN
import core.config as config
from core.commands import set_commands
from core.handlers import admin, register, base
from core.middlewares.middlewares import CustomFSMContextMiddleware 
from core.utils import dependencies

logging.basicConfig(level=logging.INFO)

dependencies.db_manager.initialize()
dependencies.storage.initialize()

dependencies.bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(storage=dependencies.storage)
dp.update.outer_middleware(CustomFSMContextMiddleware(storage=dependencies.storage))
dp.include_routers(admin.router, register.router, base.router)


async def start_bot(bot: Bot):
    await set_commands(bot)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Обработчик команды /help.
    """
    await message.answer(
        "Этот бот собирает данные для регистрации.\n"
    )


async def main():
    dp.startup.register(start_bot)
    await dp.start_polling(dependencies.bot)


if __name__ == '__main__':
    asyncio.run(main())
