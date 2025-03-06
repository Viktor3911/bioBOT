import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, KeyboardButton, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from aiogram import Router
import logging

from core.utils import dependencies
from core.classes import User, DuplicateRecordError, DatabaseError, RecordNotFoundError
from core.keyboards.keyboards import director_keyboard, assistant_keyboard # Импорт клавиатуры директора

router = Router()

class RegistrationState(StatesGroup):
    waiting_for_fio = State()


@router.message(CommandStart(deep_link=True, magic=F.args == "director_show_register"))
async def cmd_start_director_show_register(message: types.Message, state: FSMContext):
    """
    Обработчик команды /start с диплинком "director_show_register".
    Регистрирует пользователя как директора.
    """
    logging.info(f"Регистрация через диплинк")
    user_id = 1

    user = User.get_or_create(user_id)
    user.id_role = 1
    user.update()
    if user.fio:
        return await message.answer(f"Приветствую, директор {user.fio}!", reply_markup=director_keyboard()) # Отправляем клавиатуру директора

    await state.set_state(RegistrationState.waiting_for_fio)
    await state.update_data(registration_role=User.ROLE_DIRECTOR) # Сохраняем роль директора
    await state.update_data(user_id=user_id)
    await message.answer("Регистрация директора. Пожалуйста, введите ваше ФИО.")


@router.message(CommandStart(deep_link=True, magic=F.args == "assistant_show_register"))
async def cmd_start_assistant_show_register(message: types.Message, state: FSMContext):
    """
    Обработчик команды /start с диплинком "assistant_show_register".
    Регистрирует пользователя асситента.
    """
    logging.info(f"Регистрация через диплинк")
    user_id = message.from_user.id

    user = User.get_or_create(user_id)
    user.id_role = 2
    user.id_chief = 1
    user.update()
    if user.fio:
        return await message.answer(f"Приветствую, ассистент {user.fio}!", reply_markup=assistant_keyboard()) # Отправляем клавиатуру директора

    await state.set_state(RegistrationState.waiting_for_fio)
    await state.update_data(registration_role=User.ROLE_ASSISTANT) # Сохраняем роль директора
    await state.update_data(user_id=user_id)
    await message.answer("Регистрация асситента. Пожалуйста, введите ваше ФИО.")


@router.message(CommandStart(deep_link=True, magic=F.args == "director_register"))
async def cmd_start_director_register(message: types.Message, state: FSMContext):
    """
    Обработчик команды /start с диплинком "director_register".
    Регистрирует пользователя как директора.
    """
    logging.info(f"Регистрация через диплинк")
    user_id = message.from_user.id

    user = User.get_or_create(user_id)
    user.id_role = 1
    user.update()
    if user.fio:
        return await message.answer(f"Приветствую, директор {user.fio}!", reply_markup=director_keyboard()) # Отправляем клавиатуру директора

    await state.set_state(RegistrationState.waiting_for_fio)
    await state.update_data(registration_role=User.ROLE_DIRECTOR) # Сохраняем роль директора
    await state.update_data(user_id=user_id)
    await message.answer("Регистрация директора. Пожалуйста, введите ваше ФИО.")


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Обработчик команды /start.
    Проверяет, зарегистрирован ли пользователь, или начинает процесс регистрации.
    """
    user_id = message.from_user.id
    user = User.get_by_id(user_id)

    if user:
        if user.fio:
            if user.id_role == User.ROLE_DIRECTOR: # Проверяем роль пользователя
                await message.answer(f"Приветствую, директор {user.fio}!", reply_markup=director_keyboard()) # Отправляем клавиатуру директора
            else:
                await message.answer(f"Привет, {user.fio}! Вы уже зарегистрированы.", reply_markup=assistant_keyboard())
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
    # user_id = message.from_user.id
    state_data = await state.get_data()
    user_id = state_data.get('user_id')
    try:
        user = User.get_or_create(user_id) # Получаем или создаем пользователя
        user.fio = fio
        user.update() # Обновляем ФИО
        await message.answer(f"Спасибо, {fio}! Вы успешно зарегистрированы.", reply_markup=assistant_keyboard()) # Убираем ReplyKeyboardRemove, если хотим оставить клавиатуру директора
        if user.id_role == User.ROLE_DIRECTOR: # Если роль директора, отправляем клавиатуру
            await message.answer("Теперь вы можете использовать команды директора.", reply_markup=director_keyboard())
        await state.clear()
    except DatabaseError as e:
        logging.error(f"Ошибка базы данных при регистрации пользователя: {e}")
        await message.answer("Произошла ошибка при регистрации. Попробуйте позже.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    except ValueError as e:
        logging.error(f"Ошибка валидации данных: {e}")
        await message.answer("Некорректные данные ФИО.", reply_markup=ReplyKeyboardRemove())
        await state.clear()