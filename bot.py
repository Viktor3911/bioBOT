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

async def director_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            # Клавиатура руководителя
            [
                KeyboardButton(text="Добавить задачу"),
                KeyboardButton(text="Добавить свою задачу"),
                KeyboardButton(text="Текущие задач"),
                KeyboardButton(text="Добавить студента"),
                KeyboardButton(text="Посмотреть список студентов")
            ],
            # Клавиатура после нажатия на "Добавить задачу"
            [
                KeyboardButton(text="Отмена"),
            ],
            [
                KeyboardButton(text="📝 Отчет по заказам"),
                KeyboardButton(text="📝 Отчет по работникам"),
            ]

        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def create_record_actions_keyboard():
    # "заготовленные задачи"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пассаж культуры клеток", callback_data="cell_culture_passage")],
        [InlineKeyboardButton(text="Центрифугирование образцов", callback_data="centrifugation")],
        [InlineKeyboardButton(text="Приготовление питательных сред", callback_data="media_preparation")],
        [InlineKeyboardButton(text="Стерилизация инструментов", callback_data="sterilization")],
        [InlineKeyboardButton(text="Выделение ДНК/РНК", callback_data="dna_rna_extraction")],
        [InlineKeyboardButton(text="Проведение ПЦР", callback_data="pcr")],
        [InlineKeyboardButton(text="Электрофорез", callback_data="electrophoresis")],
        [InlineKeyboardButton(text="Культивирование микроорганизмов", callback_data="microbial_cultivation")],
        [InlineKeyboardButton(text="Измерение оптической плотности", callback_data="optical_density_measurement")],
        [InlineKeyboardButton(text="Криоконсервация клеток", callback_data="cryopreservation")],
    ])

async def main():
    dp.startup.register(start_bot)
    await dp.start_polling(dependencies.bot)



if __name__ == '__main__':
    asyncio.run(main())
