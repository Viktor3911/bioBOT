import asyncio
import re
from datetime import datetime, timedelta # Добавим timedelta
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
from core.commands import set_commands
from core.handlers import admin, director, register, assistant
from core.middlewares.middlewares import CustomFSMContextMiddleware 
from core.utils import dependencies
from core.classes import Reservation, User, Device

logging.basicConfig(level=logging.INFO)

dependencies.db_manager.initialize()
dependencies.storage.initialize()

dependencies.bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(storage=dependencies.storage)
dp.update.outer_middleware(CustomFSMContextMiddleware(storage=dependencies.storage))
dp.include_routers(admin.router, director.router, register.router, assistant.router)


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


async def check_schedule_and_notify():
    """
    Фоновая задача для проверки расписания и отправки уведомлений.
    Запускается асинхронно в main().
    """
    logging.info('Фоновая задача рассылки напоминаний запущена')
    while True:
        now = datetime.now()

        reservations_today = Reservation.get_all_by_today() # Получаем все резервации на сегодня
        for reservation in reservations_today:
            if reservation.start_date:
                time_remaining = reservation.start_date - now
                if timedelta(minutes=4) <= time_remaining <= timedelta(minutes=5): # Проверяем, что время до начала задачи между 4 и 5 минутами
                    for assistant_id in reservation.assistants:
                        try:
                            user = User.get_by_id(assistant_id)
                            if user:
                                await dependencies.bot.send_message(
                                    chat_id=assistant_id,
                                    text=f"🔔 Напоминание: Через 5 минут начинается задача '{reservation.name_task}' (протокол '{reservation.type_protocol}') в {reservation.start_date.strftime('%H:%M')}. Кабинет: {Device.get_by_id(reservation.id_device).name_cabinet if Device.get_by_id(reservation.id_device) else 'Неизвестно'}.",
                                )
                        except Exception as e:
                            logging.error(f"Ошибка при отправке уведомления ассистенту {assistant_id}: {e}")
        await asyncio.sleep(60) # Проверяем каждую минуту


async def main():
    dp.startup.register(start_bot)
    asyncio.create_task(check_schedule_and_notify()) # Запускаем фоновую задачу уведомлений
    await dp.start_polling(dependencies.bot)



if __name__ == '__main__':
    asyncio.run(main())
