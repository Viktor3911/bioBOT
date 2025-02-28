import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardButton, ReplyKeyboardBuilder
from aiogram import Router
import logging

from core.utils import dependencies
from core.classes import User, DuplicateRecordError, DatabaseError, RecordNotFoundError

router = Router()

class RegistrationState(StatesGroup):
    waiting_for_fio = State()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Обработчик команды /start.
    Проверяет, зарегистрирован ли пользователь, или начинает процесс регистрации.
    """
    user_id = message.from_user.id
    user = User.get_by_id(user_id)

    if user.fio:
        await message.answer(f"Привет, {user.fio}! Вы уже зарегистрированы.")
    else:
        await state.set_state(RegistrationState.waiting_for_fio)
        await message.answer("Здравствуйте! Пожалуйста, введите ваше ФИО для регистрации.")


@router.message(RegistrationState.waiting_for_fio, F.text)
async def process_fio(message: types.Message, state: FSMContext):
    """
    Обработчик ввода ФИО.
    Получает ФИО от пользователя, создает и добавляет пользователя в БД.
    """
    fio = message.text.strip()
    user_id = message.from_user.id

    try:
        user = User.get_or_create(user_id) # Получаем или создаем пользователя
        user.fio = fio
        user.update() # Обновляем ФИО
        await message.answer(f"Спасибо, {fio}! Вы успешно зарегистрированы.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    except DatabaseError as e:
        logging.error(f"Ошибка базы данных при регистрации пользователя: {e}")
        await message.answer("Произошла ошибка при регистрации. Попробуйте позже.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    except ValueError as e:
        logging.error(f"Ошибка валидации данных: {e}")
        await message.answer("Некорректные данные ФИО.", reply_markup=ReplyKeyboardRemove())
        await state.clear()