import asyncio
import re
from datetime import timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery, Message
from aiogram import Router
import logging

from core.utils import dependencies
from core.classes import User, DatabaseError, RecordNotFoundError, DuplicateRecordError, Cabinet, Device, StandartTask, Protocol
from core.utils.keyboards import director_keyboard # Импорт клавиатуры директора

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








@router.message(F.text == "Добавить кабинет")
async def cmd_add_cabinet_director_button(message: Message, state: FSMContext):
    """
    Обработчик команды "Добавить кабинет" через ReplyKeyboard.
    Запрашивает у директора название кабинета.
    """
    if not is_director(message.from_user.id): # Проверка, является ли пользователь директором (хотя кнопка видна только директорам)
        return await message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.waiting_for_cabinet_name) # Переходим в состояние ожидания названия кабинета
    await message.answer("Введите название нового кабинета:", reply_markup=ReplyKeyboardRemove()) # Убираем клавиатуру для ввода названия


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















@router.message(F.text == "Добавить устройство")
async def cmd_add_device_director_button(message: Message, state: FSMContext):
    """
    Обработчик команды "Добавить устройство" через ReplyKeyboard.
    Предлагает директору выбрать кабинет для устройства.
    """
    if not is_director(message.from_user.id): # Проверка, является ли пользователь директором
        return await message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.choosing_cabinet_for_device) # Переходим в состояние выбора кабинета для устройства
    cabinets = Cabinet.get_all() # Получаем список всех кабинетов из БД
    if cabinets:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=c.name, callback_data=f"choose_cabinet_device_{c.name}")] # Используем name кабинета в callback_data
            for c in cabinets
        ])
        await message.answer("Выберите кабинет для устройства:", reply_markup=markup)
    else:
        await message.answer("В системе нет зарегистрированных кабинетов. Сначала добавьте кабинет.")
        await state.clear()


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

        device = Device(id_device=, name_cabinet=cabinet.name, name=device_name) # Создаем объект Device, используя ID кабинета
        device.add() # Добавляем устройство в БД
        await message.answer(f"Устройство '{device_name}' с ID {device.id} успешно добавлено в кабинет '{chosen_cabinet_name}'.", reply_markup=director_keyboard()) # Сообщаем об успехе и возвращаем клавиатуру директора
        await state.clear()
    except DuplicateRecordError: # Обработка ошибки, если устройство с таким ID уже существует
        await message.answer(f"Устройство с ID {device.id} уже существует. Попробуйте другое ID или обратитесь к администратору.")
        await state.clear()
    except DatabaseError as e: # Обработка общих ошибок БД
        logging.error(f"Ошибка базы данных при добавлении устройства: {e}")
        await message.answer("Произошла ошибка при добавлении устройства. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except ValueError as e: # Обработка ошибок валидации данных (если есть в классе Device)
        logging.error(f"Ошибка валидации данных устройства: {e}")
        await message.answer("Некорректное название устройства.", reply_markup=director_keyboard())
        await state.clear()














@router.message(F.text == "Добавить задачу") # Обработчик на текстовую кнопку "Добавить задачу"
async def cmd_add_task_director_button(message: Message, state: FSMContext):
    """
    Обработчик команды "Добавить задачу" через ReplyKeyboard.
    Предлагает директору выбрать кабинет для задачи.
    """
    if not is_director(message.from_user.id): # Проверка, является ли пользователь директором
        return await message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.choosing_cabinet_for_task) # Переходим в состояние выбора кабинета для задачи
    cabinets = Cabinet.get_all() # Получаем список всех кабинетов из БД
    if cabinets:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=c.name, callback_data=f"choose_cabinet_task_{c.name}")] # Используем name кабинета в callback_data
            for c in cabinets
        ])
        await message.answer("Выберите кабинет для стандартной задачи:", reply_markup=markup)
    else:
        await message.answer("В системе нет зарегистрированных кабинетов. Сначала добавьте кабинет.")
        await state.clear()


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
            [InlineKeyboardButton(text=d.name, callback_data=f"choose_device_task_{d.id}")] # Используем ID устройства в callback_data
            for d in devices
        ])
        await query.message.answer(f"Выбран кабинет '{cabinet_name}'. Теперь выберите устройство для стандартной задачи:", reply_markup=markup)
    else:
        await query.message.answer(f"В кабинете '{cabinet_name}' нет зарегистрированных устройств. Сначала добавьте устройство в кабинет.")
        await state.clear()
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.callback_query(DirectorState.choosing_device_for_task, F.data.startswith("choose_device_task_"))
async def callback_choose_device_for_task(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора устройства для задачи.
    Сохраняет ID выбранного устройства в FSM context и запрашивает название задачи.
    """
    device_id = int(query.data.split("_")[3]) # Извлекаем ID устройства из callback_data
    await state.update_data(chosen_device_id_task=device_id) # Сохраняем ID устройства в FSM
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
    chosen_device_id_task = state_data.get('chosen_device_id_task')
    task_name = state_data.get('task_name')
    task_is_parallel = state_data.get('task_is_parallel')

    if not chosen_cabinet_name_task or not chosen_device_id_task or not task_name:
        await message.answer("Ошибка: Недостаточно данных для создания задачи. Попробуйте начать процесс добавления задачи заново.")
        return await state.clear()

    try:
        cabinet = Cabinet.get_by_name(chosen_cabinet_name_task)
        device = Device.get_by_id(chosen_device_id_task)
        if not cabinet or not device:
            await message.answer("Ошибка: Кабинет или устройство не найдены в базе данных. Попробуйте выбрать кабинет и устройство заново.")
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
            name_cabinet=cabinet.name,
            id_device=device.id,
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














@router.message(F.text == "Добавить протокол") # Обработчик для кнопки "Добавить протокол"
async def cmd_add_protocol_director_button(message: types.Message, state: FSMContext):
    """
    Обработчик команды "Добавить протокол" через ReplyKeyboard.
    Запрашивает у директора название протокола и переходит к выбору задач.
    """
    if not is_director(message.from_user.id): # Проверка, является ли пользователь директором
        return await message.answer("Только директора могут использовать эту команду.")

    await state.set_state(DirectorState.waiting_for_protocol_name) # Переходим в состояние ожидания названия протокола
    await message.answer("Введите название нового протокола:", reply_markup=ReplyKeyboardRemove()) # Запрашиваем название протокола, убираем клавиатуру


@router.message(DirectorState.waiting_for_protocol_name, F.text) # Обработчик ожидания названия протокола
async def process_protocol_name(message: types.Message, state: FSMContext):
    """
    Обработчик получения названия протокола от директора.
    Сохраняет название протокола в FSM context и предлагает выбрать первую задачу.
    """
    protocol_name = message.text.strip()
    await state.update_data(protocol_name=protocol_name, protocol_tasks=[]) # Сохраняем название протокола и инициализируем список задач
    await state.set_state(DirectorState.choosing_task_for_protocol) # Переходим к состоянию выбора задач
    await show_tasks_for_protocol_choice(message, state) # Функция для отображения кнопок выбора задач


async def show_tasks_for_protocol_choice(message: types.Message, state: FSMContext):
    """
    Функция для отображения кнопок выбора стандартных задач для протокола.
    Получает список всех стандартных задач из БД и формирует InlineKeyboard.
    """
    standart_tasks = StandartTask.get_all() # Получаем список всех стандартных задач
    if standart_tasks:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=task.name, callback_data=f"choose_protocol_task_{task.name}")] # Используем name задачи в callback_data
            for task in standart_tasks
        ] + [[InlineKeyboardButton(text="✅ Готово", callback_data="protocol_tasks_done")]]) # Кнопка "Готово"
        await message.answer("Выберите задачи для протокола (по порядку, начиная с первой):", reply_markup=markup)
    else:
        await message.answer("В системе нет стандартных задач. Сначала добавьте стандартные задачи.", reply_markup=director_keyboard())
        await state.clear()


@router.callback_query(DirectorState.choosing_task_for_protocol, F.data.startswith("choose_protocol_task_"))
async def callback_choose_task_for_protocol(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора стандартной задачи для протокола.
    Добавляет выбранную задачу в список задач протокола в FSM context и предлагает выбрать следующую задачу.
    """
    task_name = query.data.split("_")[3] # Извлекаем название задачи из callback_data
    state_data = await state.get_data()
    protocol_tasks = state_data.get('protocol_tasks', []) # Получаем текущий список задач протокола из FSM или пустой список

    protocol_tasks.append(task_name) # Добавляем выбранное название задачи в список
    await state.update_data(protocol_tasks=protocol_tasks) # Обновляем список задач в FSM

    await query.message.answer(f"Задача '{task_name}' добавлена в протокол. Выберите следующую задачу или нажмите '✅ Готово'.")
    await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"


@router.callback_query(DirectorState.choosing_task_for_protocol, F.data == "protocol_tasks_done")
async def callback_protocol_tasks_done(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после нажатия кнопки "Готово" при выборе задач для протокола.
    Завершает создание протокола, сохраняет его в БД и очищает FSM.
    """
    state_data = await state.get_data()
    protocol_name = state_data.get('protocol_name')
    protocol_tasks = state_data.get('protocol_tasks')

    if not protocol_name or not protocol_tasks:
        await query.message.answer("Ошибка: Недостаточно данных для создания протокола. Попробуйте начать процесс добавления протокола заново.")
        return await state.clear()

    try:
        protocol = Protocol(name=protocol_name, list_standart_tasks=protocol_tasks) # Создаем объект Protocol с названием и списком задач
        protocol_id = protocol.add() # Добавляем протокол в БД и получаем ID
        if protocol_id:
            tasks_str = "\n".join([f"- {task_name}" for task_name in protocol_tasks]) # Формируем список задач для сообщения
            await query.message.answer(f"Протокол '{protocol_name}' успешно создан с ID {protocol_id} и включает следующие задачи:\n{tasks_str}", reply_markup=director_keyboard()) # Сообщаем об успехе, показываем ID и список задач, возвращаем клавиатуру
        else:
            await query.message.answer(f"Не удалось добавить протокол '{protocol_name}'. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except DuplicateRecordError:
        await query.message.answer(f"Протокол с названием '{protocol_name}' уже существует. Пожалуйста, введите другое название.")
        await state.clear()
    except DatabaseError as e:
        logging.error(f"Ошибка базы данных при добавлении протокола: {e}")
        await query.message.answer("Произошла ошибка при добавлении протокола. Попробуйте позже.", reply_markup=director_keyboard())
        await state.clear()
    except ValueError as e:
        logging.error(f"Ошибка валидации данных протокола: {e}")
        await query.message.answer("Некорректные данные протокола.", reply_markup=director_keyboard())
        await state.clear()
    finally:
        await query.answer() # Обязательно ответить на callback, чтобы убрать "часики"
