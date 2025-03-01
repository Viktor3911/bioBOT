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

class AdminState(StatesGroup):
    waiting_for_director_forward = State() # Команда /add_director остается без изменений
    waiting_for_assistant_forward = State()
    choosing_director_for_assistant = State() # Новое состояние - выбор директора из списка
    # waiting_for_director_for_assistant - удалено, теперь директор выбирается через callback


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором, проверяя его роль в БД.
    """
    user = User.get_by_id(user_id)
    if user and user.id_role == User.ROLE_ADMIN:
        return True
    return False


@router.message(Command("add_director"))
async def cmd_add_director(message: types.Message, state: FSMContext):
    """
    Обработчик команды /add_director.
    Ожидает пересылку сообщения от пользователя, которого нужно назначить директором.
    Проверяет права администратора через БД.
    """
    if not is_admin(message.from_user.id): # Используем функцию is_admin, проверяющую БД
        return await message.answer("Только администраторы могут использовать эту команду.")

    await state.set_state(AdminState.waiting_for_director_forward)
    await message.answer("Перешлите сообщение от пользователя, которого вы хотите назначить директором.")


@router.message(Command("add_assistant_admin"))
async def cmd_add_assistant(message: types.Message, state: FSMContext):
    """
    Обработчик команды /add_assistant.
    Сначала предлагает выбрать директора из списка.
    Проверяет права администратора через БД.
    """
    if not is_admin(message.from_user.id): # Используем функцию is_admin, проверяющую БД
        return await message.answer("Только администраторы могут использовать эту команду.")

    await state.set_state(AdminState.choosing_director_for_assistant) # Переходим к состоянию выбора директора
    directors = User.get_all_directors() # Получаем список всех директоров из БД
    if directors:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=d.fio, callback_data=f"choose_director_{d.id}")]
            for d in directors
        ])
        await message.answer("Выберите директора для ассистента:", reply_markup=markup)
    else:
        await message.answer("В системе нет зарегистрированных директоров. Сначала добавьте директора.")
        await state.clear()


@router.callback_query(AdminState.choosing_director_for_assistant, F.data.startswith("choose_director_"))
async def callback_choose_director_for_assistant(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора директора для ассистента.
    Сохраняет ID выбранного директора в FSM context и запрашивает пересылку сообщения от ассистента.
    """
    director_id = int(query.data.split("_")[2]) # Получаем ID директора из callback_data
    await state.update_data(chosen_director_id=director_id) # Сохраняем ID директора в FSM
    await state.set_state(AdminState.waiting_for_assistant_forward) # Переходим к ожиданию пересылки от ассистента
    await query.message.answer(f"Выбран директор. Теперь, пожалуйста, перешлите сообщение от пользователя, которого вы хотите назначить ассистентом для выбранного директора.")
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.message(AdminState.waiting_for_director_forward, F.forward_from)
async def process_director_forward(message: types.Message, state: FSMContext):
    """
    Обработчик получения пересланного сообщения для назначения директора.
    Извлекает ID пользователя из пересланного сообщения и создает запись директора.
    Использует message.forward_from для получения ID.
    """
    forward_from = message.forward_from
    if forward_from:
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


@router.message(AdminState.waiting_for_assistant_forward, F.forward_from)
async def process_assistant_forward(message: types.Message, state: FSMContext):
    """
    Обработчик получения пересланного сообщения для назначения ассистента.
    Извлекает ID ассистента из пересланного сообщения, получает ID директора из FSM context,
    и создает запись ассистента с указанием выбранного директора (id_chief).
    """
    forward_from = message.forward_from
    if forward_from:
        assistant_user_id = forward_from.id
        state_data = await state.get_data()
        chosen_director_id = state_data.get('chosen_director_id') # Получаем ID директора из FSM

        if not chosen_director_id:
            await message.answer("Ошибка: ID директора не найден в текущем состоянии. Попробуйте начать процесс добавления ассистента заново.")
            return await state.clear()

        try:
            assistant = User.get_or_create(assistant_user_id) # Получаем или создаем ассистента
            if assistant.id_chief != 0: # Проверка, чтобы не переназначить директора
                await message.answer(f"У ассистента с ID {assistant_user_id} уже назначен директор. Назначение не выполнено.")
            else:
                assistant.id_chief = chosen_director_id # Устанавливаем id_chief (ID выбранного директора)
                assistant.update() # Обновляем данные ассистента в БД
                await message.answer(f"Ассистент с ID {assistant_user_id} назначен директору с ID {chosen_director_id}.")
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