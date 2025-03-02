from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.classes import User, Reservation, Device, Protocol
from core.utils.keyboards import assistant_keyboard
from datetime import date
import logging
from core.utils import dependencies

router = Router()

class AssistantState(StatesGroup):
    choosing_protocol_to_add = State() # Состояние выбора протокола для добавления в расписание ассистента
    confirming_protocol_add = State() # Новое состояние - подтверждение добавления к протоколу

def is_assistant(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь ассистентом, проверяя его роль в БД.
    """
    user = User.get_by_id(user_id)
    if user and user.id_role == User.ROLE_ASSISTANT:
        return True
    return False

async def format_assistant_task_info(reservation: Reservation) -> str:
    """
    Функция для формирования информации о задаче для ассистента в расписании.
    """
    task_name = reservation.name_task
    start_time = reservation.start_date.strftime("%H:%M") if reservation.start_date else "Не задано"
    end_time = reservation.end_date.strftime("%H:%M") if reservation.end_date else "Не задано"
    device = Device.get_by_id(reservation.id_device)
    cabinet_name = device.name_cabinet if device else "Неизвестно"
    device_name = device.name if device else "Неизвестно"
    protocol_name = reservation.type_protocol
    number_protocol = reservation.number_protocol # Добавляем number_protocol в информацию

    task_info = (
        f"<b>Задача:</b> {task_name}\n"
        f"<b>Время:</b> {start_time} - {end_time}\n"
        f"<b>Кабинет:</b> {cabinet_name}\n"
        f"<b>Устройство:</b> {device_name}\n"
    )
    return task_info

async def format_protocol_schedule_info(reservations: list[Reservation]) -> str:
    """
    Функция для формирования общей информации о протоколе для подтверждения.
    """
    if not reservations:
        return "Нет задач для данного протокола."

    protocol_name = reservations[0].type_protocol # Предполагаем, что все задачи в списке из одного протокола
    number_protocol = reservations[0].number_protocol

    protocol_info = f"<b>Протокол №:</b> {number_protocol} ({protocol_name})\n"
    protocol_info += "<b>Задачи:</b>\n"
    for reservation in reservations:
        protocol_info += await format_assistant_task_info(reservation)
        protocol_info += "-------------------------\n" # Разделитель между задачами

    return protocol_info


@router.message(F.text == "Добавить протоколы на день")
async def wrapper_cmd_show_protocols_to_add(message: Message, state: FSMContext):
    """
    Обработчик кнопки "Добавить протоколы на день" для ассистента.
    Показывает список протоколов на день для выбора ассистентом, группируя по number_protocol.
    """
    await cmd_show_protocols_to_add(state, message.from_user.id)


async def cmd_show_protocols_to_add(state: FSMContext, user_id):
    """
    Обработчик кнопки "Добавить протоколы на день" для ассистента.
    Показывает список протоколов на день для выбора ассистентом, группируя по number_protocol.
    """
    if not is_assistant(user_id):
        return await dependencies.bot.send_message(chat_id=user_id, text="Только ассистенты могут использовать эту команду.")

    await state.set_state(AssistantState.choosing_protocol_to_add) # Переходим в состояние выбора протокола
    protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers() # Получаем сгруппированные по number_protocol резервации

    if protocol_reservations_by_number:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Протокол №{number_protocol}", callback_data=f"show_protocol_info_{number_protocol}")] # Изменяем callback_data
            for number_protocol, reservations in protocol_reservations_by_number # Итерируемся по кортежам (number_protocol, reservations)
        ])
        await dependencies.bot.send_message(chat_id=user_id, text="Выберите протоколы для добавления в свое расписание (по номеру протокола):", reply_markup=markup)
    else:
        await dependencies.bot.send_message(chat_id=user_id, text="На сегодня расписание не добавлено.", reply_markup=assistant_keyboard())


@router.callback_query(AssistantState.choosing_protocol_to_add, F.data.startswith("show_protocol_info_")) # Изменен фильтр callback_data
async def callback_show_protocol_info(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после выбора протокола для показа информации и подтверждения.
    Показывает информацию о протоколе и кнопки "Подтвердить" и "Назад".
    """
    number_protocol = int(query.data.split("_")[3]) # Извлекаем number_protocol из callback_data

    protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers() # Получаем сгруппированные резервации
    selected_reservations = []
    for protocol_num, reservations in protocol_reservations_by_number:
        if protocol_num == number_protocol:
            selected_reservations = reservations # Находим список резерваций для выбранного number_protocol
            break

    if not selected_reservations:
        return await query.answer(f"Резервации для протокола №{number_protocol} не найдены.", show_alert=True)

    protocol_info_text = await format_protocol_schedule_info(selected_reservations) # Формируем информацию о протоколе

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_add_protocol_{number_protocol}"), # Callback для подтверждения
            InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_protocol_choice") # Callback для возврата к выбору протокола
        ]
    ])

    await state.set_state(AssistantState.confirming_protocol_add) # Переходим в состояние подтверждения
    await state.update_data(chosen_protocol_number=number_protocol) # Сохраняем выбранный number_protocol в state data
    await query.message.edit_text(protocol_info_text + "\n<b>Добавить этот протокол в свое расписание?</b>", parse_mode="HTML", reply_markup=markup) # Редактируем сообщение, добавляем кнопки
    await query.answer()


@router.callback_query(AssistantState.confirming_protocol_add, F.data.startswith("confirm_add_protocol_")) # Обработчик подтверждения
async def callback_confirm_add_protocol(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после нажатия кнопки "Подтвердить".
    Добавляет ассистента к выбранному number_protocol.
    """
    state_data = await state.get_data()
    number_protocol = state_data.get('chosen_protocol_number') # Получаем number_protocol из state data
    user_id = query.from_user.id
    today_date = date.today()

    if number_protocol is None:
        return await query.answer("Ошибка: номер протокола не найден.", show_alert=True)

    protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers() # Снова получаем сгруппированные резервации
    selected_reservations = []
    protocol_type_name = ""

    for protocol_num, reservations in protocol_reservations_by_number:
        if protocol_num == number_protocol:
            selected_reservations = reservations
            if reservations:
                protocol_type_name = reservations[0].type_protocol # Получаем имя протокола
            break

    if not selected_reservations:
        return await query.answer(f"Резервации для протокола №{number_protocol} не найдены.", show_alert=True)

    added_to_protocol = False
    for reservation in selected_reservations:
        if reservation.start_date and reservation.start_date.date() == today_date:
            if user_id not in reservation.assistants:
                reservation.assistants.append(user_id)
                reservation.update()
                added_to_protocol = True

    if added_to_protocol:
        await query.message.edit_text(f"Вы добавлены к протоколу №{number_protocol} ({protocol_type_name}) на сегодня.") # Редактируем сообщение об успехе
    else:
        await query.message.edit_text(f"Вы уже были добавлены к протоколу №{number_protocol} или для него нет задач на сегодня.") # Редактируем сообщение об ошибке

    await state.clear() # Очищаем состояние
    await query.answer("Подтверждено!", show_alert=False) # Отвечаем на callback


@router.callback_query(AssistantState.confirming_protocol_add, F.data == "back_to_protocol_choice") # Обработчик кнопки "Назад"
async def callback_back_to_protocol_choice(query: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса после нажатия кнопки "Назад".
    Возвращает к списку выбора протоколов.
    """
    await state.set_state(AssistantState.choosing_protocol_to_add) # Возвращаем состояние выбора протокола
    # Повторно вызываем cmd_show_protocols_to_add, чтобы обновить список протоколов
    await cmd_show_protocols_to_add(state, query.from_user.id)
    await query.answer()


@router.message(F.text == "Мое расписание")
async def cmd_view_my_schedule(message: Message):
    """
    Обработчик кнопки "Мое расписание" для ассистента.
    Показывает расписание ассистента на текущий день (только его задачи).
    """
    if not is_assistant(message.from_user.id):
        return await message.answer("Только ассистенты могут использовать эту команду.")

    user_id = message.from_user.id
    today_date = date.today()
    reservations_today = Reservation.find_by_assistant_and_date(user_id, today_date) # Теперь получаем резервации *только* для этого ассистента

    schedule_info = f"<b>Ваше расписание на {today_date.strftime('%d.%m.%Y')}:</b>\n\n"
    tasks_info = []

    if reservations_today:
        for reservation in reservations_today:
            task_info = await format_assistant_task_info(reservation)
            tasks_info.append(task_info)

        schedule_info += "\n".join(tasks_info)
    else:
        schedule_info += "На сегодня задач не запланировано."

    await message.answer(schedule_info, parse_mode="HTML", reply_markup=assistant_keyboard())