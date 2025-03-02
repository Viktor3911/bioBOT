import asyncio
import re
from datetime import timedelta, time
import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery, Message
from aiogram import Router
import logging

from core.utils import dependencies
from core.classes import User, DatabaseError, RecordNotFoundError, DuplicateRecordError, Cabinet, Device, StandartTask, Protocol, Reservation
from core.utils.keyboards import director_keyboard, add_menu_keyboard # Импорт клавиатуры директора

router = Router()

class DirectorState(StatesGroup):
    waiting_for_assistant_forward = State()
    choosing_director_for_assistant = State()

    waiting_for_cabinet_name = State()

    choosing_cabinet_for_device = State() 
    waiting_for_device_name = State()

    choosing_cabinet_for_task = State() # Новое состояние - выбор кабинета для задачи
    choosing_device_for_task = State() # Новое состояние - выбор устройства для задачи
    waiting_for_task_name = State() # Новое состояние - ожидание названия задачи
    waiting_for_task_parallel = State() # Новое состояние - ожидание выбора параллельности задачи
    waiting_for_task_time = State() # Новое состояние - ожидание ввода времени задачи

    waiting_for_protocol_name = State()
    choosing_task_for_protocol = State() # Новое состояние - выбор задач для протокола
    protocol_creation = State() # Новое состояние - создание протокола (сбор задач)

    # Добавляем состояния для расписания
    choosing_protocol_for_schedule = State()  # Состояние выбора протокола
    waiting_for_schedule_date = State()  # Состояние ожидания даты выполнения
    choosing_protocol_to_view_schedule = State() # Состояние выбора протокола для просмотра расписания

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







@router.message(F.text == "Добавить ...")
async def cmd_show_add_menu(message: Message):
    """
    Обработчик кнопки "Добавить ...".
    Показывает подменю с вариантами добавления.
    """
    await message.answer("Что вы хотите добавить?", reply_markup=add_menu_keyboard())

@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main(query: CallbackQuery):
    """
    Обработчик кнопки "⬅ Назад" в подменю добавления.
    Возвращает пользователя в главное меню директора.
    """
    await query.message.answer("Главное меню", reply_markup=director_keyboard())
    await query.answer()

@router.callback_query(F.data == "add_cabinet")
async def cmd_add_cabinet_director_callback(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Добавить кабинет" из подменю "Добавить ...".
    Запрашивает у директора название кабинета.
    """
    if not is_director(query.from_user.id):  # Проверка, является ли пользователь директором
        return await query.message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.waiting_for_cabinet_name)  # Переход в состояние ожидания названия кабинета
    await query.message.answer("Введите название нового кабинета:", reply_markup=ReplyKeyboardRemove())  # Убираем клавиатуру для ввода
    await query.answer()  # Убираем "часики" в боте


@router.message(DirectorState.waiting_for_cabinet_name, F.text) # Обработчик ожидания названия кабинета
async def process_cabinet_name(message: Message, state: FSMContext):
    """
    Обработчик получения названия кабинета от директора.
    Создает и добавляет новый кабинет в БД.
    """
    cabinet_name = message.text.strip()

    try:
        cabinet = Cabinet(name=cabinet_name)
        cabinet.add() # Добавляем кабинет в БД
        await message.answer(f"Кабинет '{cabinet_name}' успешно добавлен.", reply_markup=director_keyboard())
        await state.clear()
    except DuplicateRecordError: # Обработка ошибки, если кабинет с таким именем уже существует
        await message.answer(f"Кабинет с названием '{cabinet_name}' уже существует. Пожалуйста, введите другое название.")
        await state.clear()
    except DatabaseError as e: # Обработка общих ошибок БД
        logging.error(f"Ошибка базы данных при добавлении кабинета: {e}")
        await message.answer("Произошла ошибка при добавлении кабинета. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except ValueError as e: # Обработка ошибок валидации данных (если есть в классе Cabinet)
        logging.error(f"Ошибка валидации данных кабинета: {e}")
        await message.answer("Некорректное название кабинета.", reply_markup=director_keyboard())
        await state.clear()












@router.callback_query(F.data == "add_device")
async def cmd_add_device_director_callback(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Добавить устройство" из подменю "Добавить ...".
    Предлагает директору выбрать кабинет для устройства.
    """
    if not is_director(query.from_user.id):  # Проверка, является ли пользователь директором
        return await query.message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.choosing_cabinet_for_device)  # Переход в состояние выбора кабинета для устройства
    cabinets = Cabinet.get_all()  # Получаем список всех кабинетов из БД

    if cabinets:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=c.name, callback_data=f"choose_cabinet_device_{c.name}")]  # Используем имя кабинета в callback_data
            for c in cabinets
        ])
        await query.message.edit_text("Выберите кабинет для устройства:", reply_markup=markup)  # Используем edit_text для обновления сообщения
    else:
        await query.message.answer("В системе нет зарегистрированных кабинетов. Сначала добавьте кабинет.")
        await state.clear()

    await query.answer()  # Убираем "часики" у кнопки


@router.callback_query(DirectorState.choosing_cabinet_for_device, F.data.startswith("choose_cabinet_device_"))
async def callback_choose_cabinet_for_device(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора кабинета для устройства.
    Сохраняет название выбранного кабинета в FSM context и запрашивает название устройства.
    """
    cabinet_name = query.data.split("_")[3] # Извлекаем название кабинета из callback_data (индекс 3, так как "choose_cabinet_device_" - 21 символ, + "_")
    await state.update_data(chosen_cabinet_name=cabinet_name) # Сохраняем название кабинета в FSM
    await state.set_state(DirectorState.waiting_for_device_name) # Переходим к состоянию ожидания названия устройства
    await query.message.answer(f"Выбран кабинет '{cabinet_name}'. Теперь введите название устройства:", reply_markup=ReplyKeyboardRemove()) # Запрашиваем название устройства, убираем клавиатуру
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.message(DirectorState.waiting_for_device_name, F.text) # Обработчик ожидания названия устройства
async def process_device_name(message: Message, state: FSMContext):
    """
    Обработчик получения названия устройства от директора.
    Создает и добавляет новое устройство в БД, привязанное к выбранному кабинету.
    """
    device_name = message.text.strip()
    state_data = await state.get_data()
    chosen_cabinet_name = state_data.get('chosen_cabinet_name') # Получаем название кабинета из FSM

    if not chosen_cabinet_name:
        await message.answer("Ошибка: Название кабинета не найдено в текущем состоянии. Попробуйте начать процесс добавления устройства заново.")
        return await state.clear()

    try:
        cabinet = Cabinet.get_by_name(chosen_cabinet_name) # Находим кабинет по имени
        if not cabinet:
            await message.answer(f"Кабинет с названием '{chosen_cabinet_name}' не найден в базе данных. Попробуйте выбрать кабинет заново.")
            return await state.clear()

        # Получаем количество типов устройств, чтобы определить id_device для нового устройства
        # Следующий ID типа устройства будет равен текущему количеству
        next_device_id = Device.count_device_types() + 1

        # Проверяем, не существует ли уже устройство с таким именем в этом кабинете
        existing_device = Device.find_last_by_name(device_name)
        if existing_device:
            await message.answer(f"Устройство с названием '{device_name}' уже существует в кабинете '{chosen_cabinet_name}'. Будет добавлено еще один экземпляр прибора.")
            next_device_id = existing_device.type_device


        device = Device(type_device=next_device_id, name_cabinet=chosen_cabinet_name, name=device_name) # Создаем объект Device, используя name_cabinet и name
        added_device_id = device.add() # Добавляем устройство в БД и получаем сгенерированный ID

        if added_device_id:
            await message.answer(f"Устройство '{device_name}' (тип ID Device: {next_device_id}, ID в базе данных: {added_device_id}) успешно добавлено в кабинет '{chosen_cabinet_name}'.", reply_markup=director_keyboard()) # Сообщаем об успехе и возвращаем клавиатуру директора
        else:
            await message.answer("Не удалось добавить устройство. Произошла ошибка.", reply_markup=director_keyboard())

        await state.clear()
    except DatabaseError as e: # Обработка общих ошибок БД
        logging.error(f"Ошибка базы данных при добавлении устройства: {e}")
        await message.answer("Произошла ошибка при добавлении устройства. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except ValueError as e: # Обработка ошибок валидации данных (если есть в классе Device)
        logging.error(f"Ошибка валидации данных устройства: {e}")
        await message.answer("Некорректное название устройства.", reply_markup=director_keyboard())
        await state.clear()












@router.callback_query(F.data == "add_task")
async def cmd_add_task_director_callback(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Добавить задачу" из подменю "Добавить ...".
    Предлагает директору выбрать кабинет для задачи.
    """
    if not is_director(query.from_user.id):  # Проверка, является ли пользователь директором
        return await query.message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.choosing_cabinet_for_task)  # Переход в состояние выбора кабинета для задачи
    cabinets = Cabinet.get_all()  # Получаем список всех кабинетов из БД

    if cabinets:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=c.name, callback_data=f"choose_cabinet_task_{c.name}")]  # Используем имя кабинета в callback_data
            for c in cabinets
        ])
        await query.message.edit_text("Выберите кабинет для стандартной задачи:", reply_markup=markup)  # Обновляем сообщение
    else:
        await query.message.answer("В системе нет зарегистрированных кабинетов. Сначала добавьте кабинет.")
        await state.clear()

    await query.answer()  # Убираем "часики" у кнопки

@router.callback_query(DirectorState.choosing_cabinet_for_task, F.data.startswith("choose_cabinet_task_"))
async def callback_choose_cabinet_for_task(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора кабинета для задачи.
    Сохраняет название выбранного кабинета в FSM context и предлагает выбрать устройство.
    """
    cabinet_name = query.data.split("_")[3] # Извлекаем название кабинета из callback_data
    await state.update_data(chosen_cabinet_name_task=cabinet_name) # Сохраняем название кабинета в FSM
    await state.set_state(DirectorState.choosing_device_for_task) # Переходим к состоянию выбора устройства для задачи

    devices = Device.find_by_name_cabinet(cabinet_name) # Получаем список устройств в выбранном кабинете
    if devices:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=d.name, callback_data=f"choose_type_device_task_{d.type_device}")] # Используем ID устройства в callback_data
            for d in devices
        ])
        await query.message.answer(f"Выбран кабинет '{cabinet_name}'. Теперь выберите устройство для стандартной задачи:", reply_markup=markup)
    else:
        await query.message.answer(f"В кабинете '{cabinet_name}' нет зарегистрированных устройств. Сначала добавьте устройство в кабинет.")
        await state.clear()
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.callback_query(DirectorState.choosing_device_for_task, F.data.startswith("choose_type_device_task_"))
async def callback_choose_type_device_for_task(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора устройства для задачи.
    Сохраняет ID выбранного устройства в FSM context и запрашивает название задачи.
    """
    type_device = int(query.data.split("_")[4]) # Извлекаем ID устройства из callback_data
    await state.update_data(chosen_type_device_task=type_device) # Сохраняем ID устройства в FSM
    await state.set_state(DirectorState.waiting_for_task_name) # Переходим к состоянию ожидания названия задачи
    await query.message.answer("Выбрано устройство. Теперь введите название стандартной задачи:", reply_markup=ReplyKeyboardRemove()) # Запрашиваем название задачи, убираем клавиатуру
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.message(DirectorState.waiting_for_task_name, F.text) # Обработчик ожидания названия задачи
async def process_task_name(message: Message, state: FSMContext):
    """
    Обработчик получения названия стандартной задачи от директора.
    Запрашивает, является ли задача параллельной.
    """
    task_name = message.text.strip()
    await state.update_data(task_name=task_name) # Сохраняем название задачи в FSM
    await state.set_state(DirectorState.waiting_for_task_parallel) # Переходим к состоянию ожидания выбора параллельности
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="task_parallel_yes"),
            InlineKeyboardButton(text="Нет", callback_data="task_parallel_no"),
        ]
    ])
    await message.answer("Сделать задачу параллельной?", reply_markup=markup) # Запрашиваем, является ли задача параллельной


@router.callback_query(DirectorState.waiting_for_task_parallel, F.data.startswith("task_parallel_"))
async def callback_choose_task_parallel(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора параллельности задачи.
    Сохраняет выбор параллельности в FSM context и запрашивает время выполнения задачи.
    """
    is_parallel_str = query.data.split("_")[2] # Извлекаем выбор параллельности ("yes" или "no")
    is_parallel = is_parallel_str == "yes" # Преобразуем "yes" или "no" в булево значение
    await state.update_data(task_is_parallel=is_parallel) # Сохраняем выбор параллельности в FSM
    await state.set_state(DirectorState.waiting_for_task_time) # Переходим к состоянию ожидания ввода времени задачи
    await query.message.answer("Введите время выполнения задачи (например, 1 час, 30 минут, и т.д.):", reply_markup=ReplyKeyboardRemove()) # Запрашиваем время задачи, убираем клавиатуру
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.message(DirectorState.waiting_for_task_time, F.text) # Обработчик ожидания ввода времени задачи
async def process_task_time(message: Message, state: FSMContext):
    """
    Обработчик получения длительности выполнения стандартной задачи от директора.
    Парсит введенное время в timedelta и создает стандартную задачу в БД.
    """
    task_time_str = message.text.strip()
    state_data = await state.get_data()
    chosen_cabinet_name_task = state_data.get('chosen_cabinet_name_task')
    chosen_type_device_task = state_data.get('chosen_type_device_task')
    task_name = state_data.get('task_name')
    task_is_parallel = state_data.get('task_is_parallel')

    if not chosen_cabinet_name_task or not chosen_type_device_task or not task_name:
        print(f'chosen_cabinet_name_task : {chosen_cabinet_name_task}')
        print(f'chosen_type_device_task : {chosen_type_device_task}')
        print(f'task_name : {task_name}')
        await message.answer("Ошибка: Недостаточно данных для создания задачи. Попробуйте начать процесс добавления задачи заново.", reply_markup=director_keyboard())
        return await state.clear()

    try:
        cabinet = Cabinet.get_by_name(chosen_cabinet_name_task)
        device = Device.get_by_type_device(chosen_type_device_task)
        if not cabinet or not device:
            await message.answer("Ошибка: Кабинет или устройство не найдены в базе данных. Попробуйте выбрать кабинет и устройство заново.", reply_markup=director_keyboard())
            return await state.clear()

        # Парсинг времени из строки в timedelta (простой пример, можно улучшить)
        time_match = re.match(r'(?:(\d+)\s*час(?:а|ов|)?\s*)?(?:(\d+)\s*мин(?:ута|уты|ут)?)?', task_time_str, re.IGNORECASE)
        if not time_match or (time_match.group(1) is None and time_match.group(2) is None):
            await message.answer("Некорректный формат времени. Пожалуйста, введите время в формате, например, '1 час 30 минут' или '30 минут'.")
            return

        hours = int(time_match.group(1)) if time_match.group(1) else 0
        minutes = int(time_match.group(2)) if time_match.group(2) else 0
        task_timedelta = timedelta(hours=hours, minutes=minutes)

        standart_task = StandartTask(
            name=task_name,
            type_device=device.type_device,
            is_parallel=task_is_parallel,
            time_task=task_timedelta # Передаем timedelta объект
        )
        standart_task.add()
        await message.answer(f"Стандартная задача '{task_name}' (длительность: {task_time_str}) успешно добавлена в кабинет '{chosen_cabinet_name_task}' для устройства '{device.name}'.", reply_markup=director_keyboard())
        await state.clear()
    except DuplicateRecordError:
        await message.answer(f"Стандартная задача с именем '{task_name}' уже существует. Пожалуйста, введите другое название.")
        await state.clear()
    except DatabaseError as e:
        logging.error(f"Ошибка базы данных при добавлении стандартной задачи: {e}")
        await message.answer("Произошла ошибка при добавлении стандартной задачи. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except ValueError as e:
        logging.error(f"Ошибка валидации данных стандартной задачи: {e}")
        await message.answer("Некорректные данные стандартной задачи.", reply_markup=director_keyboard())
        await state.clear()











@router.callback_query(F.data == "add_protocol")
async def cmd_add_protocol_director_callback(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Добавить протокол" из подменю "Добавить ...".
    Запрашивает у директора название протокола и переходит к выбору задач.
    """
    if not is_director(query.from_user.id):  # Проверка, является ли пользователь директором
        return await query.message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.waiting_for_protocol_name)  # Переход в состояние ожидания названия протокола
    await query.message.answer("Введите название нового протокола:")  # Отправляем запрос на ввод
    await query.answer()  # Убираем "часики" у кнопки


@router.message(DirectorState.waiting_for_protocol_name, F.text)
async def process_protocol_name(message: Message, state: FSMContext):
    """
    Обработчик получения названия протокола от директора.
    Сохраняет название протокола в FSM context и предлагает выбрать первую задачу.
    """
    protocol_name = message.text.strip()
    await state.update_data(protocol_name=protocol_name, protocol_tasks=[])  # Сохраняем название протокола
    await state.set_state(DirectorState.choosing_task_for_protocol)  # Переходим к выбору задач
    await show_tasks_for_protocol_choice(message, state)  # Вызываем функцию показа задач


async def show_tasks_for_protocol_choice(message: Message, state: FSMContext):
    """
    Функция для отображения кнопок выбора стандартных задач для протокола.
    """
    standart_tasks = StandartTask.get_all()  # Получаем список всех стандартных задач

    if standart_tasks:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=task.name, callback_data=f"c_{task.name}")] # с - choose_protocok_task
            for task in standart_tasks
        ] + [[InlineKeyboardButton(text="✅ Готово", callback_data="protocol_tasks_done")]])  # Кнопка "Готово"

        await message.answer("Выберите задачи для протокола (по порядку, начиная с первой):", reply_markup=markup)
    else:
        await message.answer("В системе нет стандартных задач. Сначала добавьте стандартные задачи.", reply_markup=director_keyboard())
        await state.clear()


@router.callback_query(DirectorState.choosing_task_for_protocol, F.data.startswith("c_"))
async def callback_choose_task_for_protocol(query: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора стандартной задачи для протокола.
    """
    task_name = query.data.split("_")[1]  # Извлекаем название задачи из callback_data
    state_data = await state.get_data()
    protocol_tasks = state_data.get('protocol_tasks', [])  # Получаем текущий список задач протокола

    protocol_tasks.append(task_name)  # Добавляем задачу
    await state.update_data(protocol_tasks=protocol_tasks)  # Обновляем список задач

    await query.message.answer(f"Задача '{task_name}' добавлена в протокол.\nВыберите следующую задачу или нажмите '✅ Готово'.")
    await query.answer()  # Убираем "часики"


@router.callback_query(DirectorState.choosing_task_for_protocol, F.data == "protocol_tasks_done")
async def callback_protocol_tasks_done(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Готово" после выбора задач для протокола.
    """
    state_data = await state.get_data()
    protocol_name = state_data.get('protocol_name')
    protocol_tasks = state_data.get('protocol_tasks')

    if not protocol_name or not protocol_tasks:
        await query.message.answer("Ошибка: Недостаточно данных для создания протокола. Попробуйте заново.", reply_markup=director_keyboard())
        return await state.clear()

    try:
        protocol = Protocol(name=protocol_name, list_standart_tasks=protocol_tasks)  # Создаем объект Protocol
        protocol_id = protocol.add()  # Добавляем протокол в БД

        if protocol_id:
            tasks_str = "\n".join([f"- {task_name}" for task_name in protocol_tasks])  # Формируем список задач
            await query.message.answer(f"✅ Протокол '{protocol_name}' (ID: {protocol_id}) создан!\nСостав задач:\n{tasks_str}", reply_markup=director_keyboard())
        else:
            await query.message.answer(f"Не удалось добавить протокол '{protocol_name}'. Попробуйте позже.", reply_markup=director_keyboard())

        await state.clear()

    except DuplicateRecordError:
        await query.message.answer(f"Протокол '{protocol_name}' уже существует. Введите другое название.", reply_markup=director_keyboard())
        await state.clear()
    except DatabaseError as e:
        logging.error(f"Ошибка БД при добавлении протокола: {e}")
        await query.message.answer("Ошибка при создании протокола. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except ValueError as e:
        logging.error(f"Ошибка валидации данных протокола: {e}")
        await query.message.answer("Некорректные данные протокола.", reply_markup=director_keyboard())
        await state.clear()
    finally:
        await query.answer()  # Убираем "часики"


WORKING_DAY_START = time(9, 0)  # Начало рабочего дня - 9:00
WORKING_DAY_END = time(18, 0)    # Конец рабочего дня - 18:00


@router.message(F.text == "Добавить в расписание")
async def cmd_add_to_schedule(message: Message, state: FSMContext):
    """
    Обработчик кнопки "Добавить в расписание".
    Предлагает директору выбрать протокол для добавления в расписание на день.
    """
    if not is_director(message.from_user.id):  # Проверка, является ли пользователь директором
        return await message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.choosing_protocol_for_schedule) # Переходим в состояние выбора протокола
    protocols = Protocol.get_all() # Получаем список всех протоколов из БД

    if protocols:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=p.name, callback_data=f"schedule_protocol_{p.name}")]
            for p in protocols
        ])
        await message.answer("Выберите протокол для добавления в расписание на сегодня:", reply_markup=markup)
    else:
        await message.answer("В системе нет зарегистрированных протоколов. Сначала добавьте протокол.", reply_markup=director_keyboard())
        await state.clear() # Очищаем состояние, так как нечего выбирать


@router.callback_query(DirectorState.choosing_protocol_for_schedule, F.data.startswith("schedule_protocol_"))
async def callback_choose_protocol_for_schedule(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора протокола для расписания.
    Добавляет задачи из выбранного протокола в расписание на текущий день,
    выбирая свободное устройство (Device) и учитывая занятость.
    """
    protocol_name = query.data.split("_")[2]
    protocol = Protocol.get_by_name(protocol_name)

    if not protocol:
        await query.message.answer(f"Протокол '{protocol_name}' не найден.")
        return await state.clear()

    standart_tasks_names = protocol.list_standart_tasks
    today_date = datetime.datetime.now() # Используем текущую дату и время для расписания на день
    schedule_start_datetime = datetime.datetime.combine(today_date, WORKING_DAY_START)
    schedule_end_datetime = datetime.datetime.combine(today_date, WORKING_DAY_END)
    current_task_start_time = schedule_start_datetime
    next_protocol_number = Reservation.count_protocol_numbers()

    added_tasks_count = 0
    tasks_not_scheduled = []

    for task_name in standart_tasks_names:
        standart_task = StandartTask.get_by_name(task_name)
        if not standart_task:
            logging.warning(f"Стандартная задача '{task_name}' не найдена, пропуск.")
            tasks_not_scheduled.append(task_name)
            continue

        task_duration = standart_task.time_task
        if task_duration is None:
            logging.warning(f"Для задачи '{task_name}' не указано время выполнения (time_task), пропуск.")
            tasks_not_scheduled.append(task_name)
            continue

        device_type = standart_task.type_device

        if device_type is None:
            logging.warning(f"У задачи '{task_name}' не указан type_device, пропуск.")
            tasks_not_scheduled.append(task_name)
            continue

        # Поиск доступного времени и устройства
        available_slot_found = False
        schedule_attempt_time = current_task_start_time
        while schedule_attempt_time + task_duration <= schedule_end_datetime:
            available_device = Device.find_available_device_by_type_and_time(
                type_device=device_type,
                start_time=schedule_attempt_time,
                end_time=schedule_attempt_time + task_duration
            )
            if available_device:
                # Найдено доступное устройство и время
                device_id = available_device.id # Получаем ID доступного устройства
                task_end_time = schedule_attempt_time + task_duration
                reservation = Reservation(
                    type_protocol=protocol_name,
                    name_task=task_name,
                    id_device=device_id, # Assign device_id to reservation
                    start_date=schedule_attempt_time,
                    end_date=task_end_time
                )
                reservation.add(next_protocol_number)
                current_task_start_time = task_end_time
                added_tasks_count += 1
                available_slot_found = True
                break # Переходим к следующей задаче
            else:
                # Нет доступных устройств, сдвигаем время и пробуем снова
                schedule_attempt_time += timedelta(minutes=5) # Шаг сдвига времени, можно настроить
                if schedule_attempt_time.time() > WORKING_DAY_END:
                    break # Вышли за пределы рабочего дня

        if not available_slot_found:
            logging.warning(f"Не удалось запланировать задачу '{task_name}' на сегодня из-за занятости оборудования.")
            tasks_not_scheduled.append(task_name)

    message_text = f"✅ В расписание на сегодня добавлено {added_tasks_count} задач из протокола '{protocol_name}'."
    if tasks_not_scheduled:
        not_scheduled_tasks_str = "\n".join([f"- {task_name}" for task_name in tasks_not_scheduled])
        message_text += f"\n\n⚠️ Не удалось запланировать следующие задачи (из-за занятости оборудования, отсутствия данных о времени выполнения или type_device):\n{not_scheduled_tasks_str}"

    await query.message.answer(message_text, reply_markup=director_keyboard())
    await state.clear()
    await query.answer()


@router.message(F.text == "Посмотреть расписание")
async def cmd_view_schedule(message: Message, state: FSMContext):
    """
    Обработчик кнопки "Посмотреть расписание".
    Предлагает директору выбрать протокол для просмотра расписания на день.
    """
    if not is_director(message.from_user.id):  # Проверка, является ли пользователь директором
        return await message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.choosing_protocol_to_view_schedule) # Переходим в состояние выбора протокола
    reservations_today = Reservation.get_all_by_today()
    protocol_names_today = set()

    for res in reservations_today:
        protocol_names_today.add(res.type_protocol)

    if protocol_names_today:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=p_name, callback_data=f"v_{p_name}")] # v - view_protocol_schedule_s
            for p_name in protocol_names_today
        ])
        await message.answer("Выберите протокол для просмотра расписания на сегодня:", reply_markup=markup)
    else:
        await message.answer("На сегодня расписание не добавлено.", reply_markup=director_keyboard())
        await state.clear() # Очищаем состояние, так как нечего выбирать


@router.callback_query(DirectorState.choosing_protocol_to_view_schedule, F.data.startswith("v_"))
async def callback_view_protocol_schedule(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора протокола для просмотра расписания.
    Показывает детальное расписание для выбранного протокола на текущий день.
    """
    protocol_name = query.data.split("_")[1] # Извлекаем название протокола из callback_data
    today_date = datetime.datetime.now() # Используем текущую дату и время для расписания на день
    protocol_reservations = Reservation.find_by_protocol_name(protocol_name) # Получаем резервации для выбранного протокола

    schedule_info = f"<b>Расписание протокола '{protocol_name}' на {today_date.strftime('%d.%m.%Y')}:</b>\n\n"
    tasks_info = []

    for reservation in protocol_reservations:
        task_info = await format_task_schedule_info(reservation) # Формируем информацию о задаче
        tasks_info.append(task_info)

    if tasks_info:
        schedule_info += "\n".join(tasks_info)
    else:
        schedule_info += "Нет задач для данного протокола на сегодня."

    await query.message.answer(schedule_info, parse_mode="HTML", reply_markup=director_keyboard()) # Отправляем информацию и возвращаем в главное меню
    await state.clear() # Очищаем состояние
    await query.answer() # Убираем "часики"


async def format_task_schedule_info(reservation: Reservation) -> str:
    """
    Функция для формирования информации о задаче протокола для расписания.
    """
    task_name = reservation.name_task
    start_time = reservation.start_date.strftime("%H:%M") if reservation.start_date else "Не задано"
    end_time = reservation.end_date.strftime("%H:%M") if reservation.end_date else "Не задано"
    device = Device.get_by_id(reservation.id_device)
    cabinet_name = device.name_cabinet if device else "Неизвестно"
    device_name = device.name if device else "Неизвестно"

    task_info = (
        f"<b>Задача:</b> {task_name}\n"
        f"<b>Время:</b> {start_time} - {end_time}\n"
        f"<b>Кабинет:</b> {cabinet_name}\n"
        f"<b>Устройство:</b> {device_name}\n"
        f"-------------------------"
    )
    return task_info