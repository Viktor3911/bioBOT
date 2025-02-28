import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery, Message
from aiogram import Router
import logging

from core.utils import dependencies
from core.classes import User, DatabaseError, RecordNotFoundError, DuplicateRecordError

router = Router()

class AdminState(StatesGroup):
    waiting_for_director_forward = State()
    waiting_for_assistant_forward = State()


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором, проверяя его роль в БД.
    """
    user = User.get_by_id(user_id)
    if user and user.id_role == User.ROLE_ADMIN:
        return True
    return False


@router.message(Command("add_director"))
async def cmd_add_director(message: Message, state: FSMContext):
    """
    Обработчик команды /add_director.
    Ожидает пересылку сообщения от пользователя, которого нужно назначить директором.
    Проверяет права администратора через БД.
    """
    if not is_admin(message.from_user.id): # Используем функцию is_admin, проверяющую БД
        return await message.answer("Только администраторы могут использовать эту команду.")

    await state.set_state(AdminState.waiting_for_director_forward)
    await message.answer("Перешлите сообщение от пользователя, которого вы хотите назначить директором.")


@router.message(Command("add_assistant"))
async def cmd_add_assistant(message: Message, state: FSMContext):
    """
    Обработчик команды /add_assistant.
    Ожидает пересылку сообщения от пользователя, которого нужно назначить ассистентом.
    Проверяет права администратора через БД.
    """
    if not is_admin(message.from_user.id): # Используем функцию is_admin, проверяющую БД
        return await message.answer("Только администраторы могут использовать эту команду.")

    await state.set_state(AdminState.waiting_for_assistant_forward)
    await message.answer("Перешлите сообщение от пользователя, которого вы хотите назначить ассистентом.")


@router.message(AdminState.waiting_for_director_forward, F.forward_from) # Фильтр на наличие forward_from
async def process_director_forward(message: Message, state: FSMContext):
    """
    Обработчик получения пересланного сообщения для назначения директора.
    Извлекает ID пользователя из пересланного сообщения и создает запись директора.
    Использует message.forward_from для получения ID.
    """
    forward_from = message.forward_from
    if forward_from: # Проверяем, что forward_from не None
        director_user_id = forward_from.id
        try:
            user = User.get_or_create(director_user_id)
            if user.id_role != User.ROLE_ASSISTANT:
                await message.answer(f"Пользователь с ID {director_user_id} уже имеет роль '{'директор' if user.id_role == User.ROLE_DIRECTOR else 'админ' if user.id_role == User.ROLE_ADMIN else 'ассистент' }'. Роль директора не назначена.")
            else:
                User.set_role(director_user_id, User.ROLE_DIRECTOR)
                await message.answer(f"Пользователь с ID {director_user_id} назначен директором.")
            await state.clear()
        except DuplicateRecordError: # Не должен возникать, но на всякий случай
            await message.answer(f"Пользователь с ID {director_user_id} уже зарегистрирован.")
            await state.clear()
        except DatabaseError as e:
            logging.error(f"Ошибка базы данных при назначении директора: {e}")
            await message.answer("Произошла ошибка при назначении директора. Попробуйте позже.")
            await state.clear()
    else:
        await message.answer("Не удалось получить ID пользователя из пересланного сообщения. Убедитесь, что пересылаете сообщение от пользователя.")
        await state.clear()


@router.message(AdminState.waiting_for_assistant_forward, F.forward_from) # Фильтр на forward_from
async def process_assistant_forward(message: Message, state: FSMContext):
    """
    Обработчик получения пересланного сообщения для назначения ассистента.
    Извлекает ID пользователя из пересланного сообщения и создает запись ассистента.
    Использует message.forward_from для получения ID.
    """
    forward_from = message.forward_from
    if forward_from: # Проверяем, что forward_from не None
        assistant_user_id = forward_from.id
        try:
            user = User.get_or_create(assistant_user_id)
            if user.id_role != User.ROLE_ASSISTANT:
                 await message.answer(f"Пользователь с ID {assistant_user_id} уже имеет роль '{'директор' if user.id_role == User.ROLE_DIRECTOR else 'админ' if user.id_role == User.ROLE_ADMIN else 'ассистент' }'. Роль ассистента не назначена.")
            else:
                User.set_role(assistant_user_id, User.ROLE_ASSISTANT)
                await message.answer(f"Пользователь с ID {assistant_user_id} назначен ассистентом.")
            await state.clear()
        except DuplicateRecordError: # Не должен возникать, но на всякий случай
            await message.answer(f"Пользователь с ID {assistant_user_id} уже зарегистрирован.")
            await state.clear()
        except DatabaseError as e:
            logging.error(f"Ошибка базы данных при назначении ассистента: {e}")
            await message.answer("Произошла ошибка при назначении ассистента. Попробуйте позже.")
            await state.clear()
    else:
        await message.answer("Не удалось получить ID пользователя из пересланного сообщения. Убедитесь, что пересылаете сообщение от пользователя.")
        await state.clear()
