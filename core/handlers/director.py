import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery, Message
from aiogram import Router
import logging

from core.utils import dependencies
from core.classes import User, DatabaseError, RecordNotFoundError, DuplicateRecordError

router = Router()

class DirectorState(StatesGroup):
    waiting_for_assistant_forward = State()
    choosing_director_for_assistant = State() # Состояние выбора директора - не нужно для директоров, но можно оставить для консистентности


def is_director(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь директором, проверяя его роль в БД.
    """
    user = User.get_by_id(user_id)
    if user and user.id_role == User.ROLE_DIRECTOR:
        return True
    return False


@router.message(Command("add_assistant"))
async def cmd_add_assistant_director(message: Message, state: FSMContext):
    """
    Обработчик команды /add_assistant для директоров.
    Директор добавляет ассистента, который будет подчиняться ему.
    """
    if not is_director(message.from_user.id): # Проверка, является ли пользователь директором
        return await message.answer("Только директора могут использовать эту команду.")

    director_id = message.from_user.id # ID директора, выполняющего команду

    await state.set_state(DirectorState.waiting_for_assistant_forward) # Переходим к состоянию ожидания пересылки от ассистента
    await state.update_data(chosen_director_id=director_id) # Сохраняем ID текущего директора как выбранного директора
    await message.answer("Перешлите сообщение от пользователя, которого вы хотите назначить ассистентом, подчиненным вам.")


@router.message(DirectorState.waiting_for_assistant_forward, F.forward_from)
async def process_assistant_forward_director(message: Message, state: FSMContext):
    """
    Обработчик получения пересланного сообщения для назначения ассистента директором.
    Извлекает ID ассистента из пересланного сообщения, ID директора берется из context (текущий директор),
    и создает запись ассистента с указанием директора (id_chief).
    """
    forward_from = message.forward_from
    if forward_from:
        assistant_user_id = forward_from.id
        state_data = await state.get_data()
        chosen_director_id = state_data.get('chosen_director_id') # Получаем ID директора из FSM (должен быть ID текущего директора)

        if not chosen_director_id:
            await message.answer("Ошибка: ID директора не найден в текущем состоянии. Попробуйте начать процесс добавления ассистента заново.") # Это сообщение не должно достигаться в этом контексте
            return await state.clear()

        if chosen_director_id != message.from_user.id: # Дополнительная проверка, что директор не пытается назначить ассистента другому директору через эту команду
            await message.answer("Ошибка: Несоответствие ID директора. Попробуйте начать процесс добавления ассистента заново.") # Это сообщение также не должно достигаться, если логика команд не нарушена
            return await state.clear()

        try:
            assistant = User.get_or_create(assistant_user_id) # Получаем или создаем ассистента
            if assistant.id_chief != 0: # Проверка, чтобы не переназначить директора
                await message.answer(f"У ассистента с ID {assistant_user_id} уже назначен директор. Назначение не выполнено.")
            else:
                assistant.id_chief = chosen_director_id # Устанавливаем id_chief (ID текущего директора)
                assistant.update() # Обновляем данные ассистента в БД
                await message.answer(f"Ассистент с ID {assistant_user_id} назначен вам (директору с ID {chosen_director_id}).")
            await state.clear()
        except RecordNotFoundError: # Хотя get_or_create не должен вызывать RecordNotFoundError
            await message.answer(f"Директор с ID {chosen_director_id} не найден.") # Это сообщение не должно достигаться
            await state.clear()
        except DatabaseError as e:
            logging.error(f"Ошибка базы данных при назначении ассистента директору: {e}")
            await message.answer("Произошла ошибка при назначении ассистента директору. Попробуйте позже.")
            await state.clear()
    else:
        await message.answer("Не удалось получить ID пользователя из пересланного сообщения ассистента. Убедитесь, что пересылаете сообщение от пользователя.")
        await state.clear()
