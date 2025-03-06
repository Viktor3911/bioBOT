from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.classes import User, Reservation, Device, Protocol, StandartTask
from core.keyboards.keyboards import assistant_keyboard
from datetime import date, datetime, time, timedelta
import logging
from core.utils import dependencies
from core.config import WORKING_DAY_START,  WORKING_DAY_END

router = Router()

class AssistantState(StatesGroup):
    choosing_protocol_to_add = State() # Состояние выбора протокола для добавления в расписание ассистента
    confirming_protocol_add = State() # Новое состояние - подтверждение добавления к протоколу
    protocol_selected = State() # Новое состояние
    viewing_my_schedule = State() # Добавим состояние для просмотра расписания с кнопками действий


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
    Показывает список протоколов на день для выбора ассистентом,
    только если ассистент еще не выбрал протокол на сегодня.
    """
    user_id = message.from_user.id
    # Проверяем, есть ли у ассистента уже протокол на сегодня
    existing_protocol = Reservation.find_by_assistant_and_date(user_id, date.today())

    if existing_protocol:
        await message.answer("Вы уже добавили протокол на сегодня. Для просмотра вашего расписания нажмите кнопку 'Мое расписание'.", reply_markup=assistant_keyboard(has_protocol=True)) # Изменим клавиатуру
    else:
        msg = await message.answer("0")
        await state.update_data(msg_id_protocol_to_add=msg.message_id)
        await cmd_show_protocols_to_add(state, user_id)

    await message.delete()


async def cmd_show_protocols_to_add(state: FSMContext, user_id):
    """
    Обработчик показа списка протоколов для добавления ассистентом.
    Исключает протоколы, которые уже выбраны другими ассистентами.
    """
    state_data = await state.get_data()
    msg_id_protocol_to_add = state_data.get('msg_id_protocol_to_add')
    # if not is_assistant(user_id):
    #     return await dependencies.bot.edit_message_text(chat_id=user_id, message_id=msg_id_protocol_to_add, text="Только ассистенты могут использовать эту команду.")

    await state.set_state(AssistantState.choosing_protocol_to_add)
    all_protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers() # Получаем все протоколы на день

    available_protocols = []
    for number_protocol, reservations in all_protocol_reservations_by_number:
        # Проверяем, есть ли в протоколе уже ассистенты
        has_assistants_assigned = False
        for res in reservations:
            if res.assistants: # Если список assistants не пустой
                has_assistants_assigned = True
                break # Если хоть у одной задачи есть ассистент, считаем протокол занятым
        if not has_assistants_assigned: # Если у протокола еще нет ассистентов, добавляем его в доступные
            available_protocols.append((number_protocol, reservations))

    if available_protocols:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Протокол №{number_protocol}", callback_data=f"show_protocol_info_{number_protocol}")]
            for number_protocol, reservations in available_protocols # Используем отфильтрованный список
        ])
        await dependencies.bot.edit_message_text(chat_id=user_id, message_id=msg_id_protocol_to_add, text="Выберите протоколы для добавления в свое расписание (по номеру протокола):", reply_markup=markup)
    else:
        await dependencies.bot.edit_message_text(chat_id=user_id, message_id=msg_id_protocol_to_add, text="На сегодня нет доступных протоколов для добавления.", reply_markup=assistant_keyboard())


@router.callback_query(AssistantState.choosing_protocol_to_add, F.data.startswith("show_protocol_info_"))
async def callback_show_protocol_info(query: CallbackQuery, state: FSMContext):
    """
    Обработчик показа информации о протоколе и подтверждения.
    """
    number_protocol = int(query.data.split("_")[3])

    protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers()
    selected_reservations = []
    for protocol_num, reservations in protocol_reservations_by_number:
        if protocol_num == number_protocol:
            selected_reservations = reservations
            break

    if not selected_reservations:
        return await query.answer(f"Резервации для протокола №{number_protocol} не найдены.", show_alert=True)

    protocol_info_text = await format_protocol_schedule_info(selected_reservations)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_add_protocol_{number_protocol}"),
            InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_protocol_choice")
        ]
    ])

    await state.set_state(AssistantState.confirming_protocol_add)
    await state.update_data(chosen_protocol_number=number_protocol)
    await query.message.edit_text(protocol_info_text + "\n<b>Добавить этот протокол в свое расписание?</b>", parse_mode="HTML", reply_markup=markup)
    await query.answer()


@router.callback_query(AssistantState.confirming_protocol_add, F.data.startswith("confirm_add_protocol_"))
async def callback_confirm_add_protocol(query: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения добавления протокола ассистентом.
    """
    state_data = await state.get_data()
    number_protocol = state_data.get('chosen_protocol_number')
    user_id = query.from_user.id
    today_date = date.today()

    if number_protocol is None:
        return await query.message.edit_text("Ошибка: номер протокола не найден.", show_alert=True)

    protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers()
    selected_reservations = []
    protocol_type_name = ""

    for protocol_num, reservations in protocol_reservations_by_number:
        if protocol_num == number_protocol:
            selected_reservations = reservations
            if reservations:
                protocol_type_name = reservations[0].type_protocol
            break

    if not selected_reservations:
        return await query.message.edit_text(f"Брони для протокола №{number_protocol} не найдены.", show_alert=True)

    added_to_protocol = False
    for reservation in selected_reservations:
        if reservation.start_date and reservation.start_date.date() == today_date:
            if user_id not in reservation.assistants:
                reservation.assistants.append(user_id)
                reservation.update()
                added_to_protocol = True

    if added_to_protocol:
        await query.message.edit_text(f"Вы добавлены к протоколу №{number_protocol} ({protocol_type_name}) на сегодня.") # Передаем has_protocol=True
        await query.answer("Подтверждено!", show_alert=False)
    else:
        await query.message.edit_text(f"Вы уже были добавлены к протоколу №{number_protocol} или для него нет задач на сегодня.") # Передаем has_protocol=True
        await query.answer("Ошибка", show_alert=True)

    await state.clear()


@router.callback_query(AssistantState.confirming_protocol_add, F.data == "back_to_protocol_choice")
async def callback_back_to_protocol_choice(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Назад" - возврат к списку протоколов.
    """
    await state.set_state(AssistantState.choosing_protocol_to_add)
    await cmd_show_protocols_to_add(state, query.from_user.id)
    await query.answer()


@router.message(F.text == "Мое расписание")
async def cmd_view_my_schedule(message: Message, state: FSMContext):
    """
    Обработчик кнопки "Мое расписание" для ассистента.
    Показывает расписание ассистента на день с кнопками действий для текущей задачи.
    """
    # if not is_assistant(message.from_user.id):
    #     return await message.answer("Только ассистенты могут использовать эту команду.")

    user_id = message.from_user.id
    today_date = date.today()
    reservations_today = Reservation.find_by_assistant_and_date(user_id, today_date)

    schedule_info = f"<b>Ваше расписание на {today_date.strftime('%d.%m.%Y')}:</b>\n\n"
    tasks_info = []

    if reservations_today:
        for reservation in reservations_today:
            task_info = await format_assistant_task_info(reservation)
            tasks_info.append(task_info)

        schedule_info += "\n".join(tasks_info)

        # Ищем текущую задачу или последнюю завершенную для кнопок действий
        current_task = None
        now = datetime.now()
        last_completed_task = None # Добавим переменную для последней завершенной задачи

        for res in reservations_today:
            if res.end_date <= now: # Если задача уже завершилась
                last_completed_task = res # Запоминаем как последнюю завершенную
            elif res.start_date <= now <= res.end_date: # Если задача идет прямо сейчас (start_date <= now <= end_date)
                current_task = res # Нашли текущую задачу, используем ее
                break # Текущая задача найдена, можно выйти из цикла
            elif res.start_date > now and not current_task:
                current_task = res # Если текущая не найдена и это первая будущая, то назначаем как ближайшую для кнопок действий

        if not current_task and last_completed_task: # Если текущая задача не найдена, но есть завершенные
            current_task = last_completed_task # Берем последнюю завершенную задачу для кнопок действий
        elif not current_task and reservations_today: # Если нет ни текущей, ни завершенных, но есть вообще задачи на сегодня
            current_task = reservations_today[0] # Берем первую задачу из списка (самую раннюю на сегодня)


        if current_task:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⏰ Опоздание - 10 мин", callback_data=f"delay_task_{current_task.id}"),
                    InlineKeyboardButton(text="↩️ Вернуть протокол", callback_data=f"return_protocol_{current_task.number_protocol}")
                ],
                # [
                #     InlineKeyboardButton(text="🔄 Обновить расписание", callback_data="back_to_schedule")
                # ]
            ])
            await message.answer(schedule_info, parse_mode="HTML", reply_markup=markup)
            await state.set_state(AssistantState.viewing_my_schedule)
            return
    else:
        schedule_info += "На сегодня задач не запланировано."

    await message.answer(schedule_info, parse_mode="HTML", reply_markup=assistant_keyboard(has_protocol=True)) # Передаем has_protocol=True, даже если нет задач, чтобы убрать кнопку "Добавить протоколы"
    await state.clear() # Сбрасываем состояние, если нет задач или кнопки действий не нужны

    await message.delete()


@router.callback_query(AssistantState.viewing_my_schedule, F.data.startswith("delay_task_"))
async def callback_delay_task(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Опоздание - 10 минут".
    ПЕРЕЗАПИСЫВАЕТ все расписание на день, с учетом увеличенного времени задачи.
    Исправленная версия, учитывающая ошибки и требования пользователя.
    """
    reservation_id = int(query.data.split("_")[2])
    delayed_reservation = Reservation.get_by_id(reservation_id)
    if not delayed_reservation:
        return await query.message.edit_text("Задача не найдена.", show_alert=True)

    logging.info(f"Нажата кнопка 'Опоздание' для задачи ID: {reservation_id}, задача: {delayed_reservation.name_task}, протокол: {delayed_reservation.type_protocol}")

    # 1. Увеличиваем время задержанной задачи в памяти и БД
    delayed_reservation.delay_task(10)
    logging.info(f"Время задачи ID: {reservation_id} увеличено на 10 минут. Новое время окончания: {delayed_reservation.end_date}")

    # 2. Получаем все протоколы на сегодня (вместе с резервациями, сгруппированные по номеру протокола)
    all_protocols_today_reservations = Reservation.get_all_by_today_with_protocol_numbers()
    if not all_protocols_today_reservations:
        return await query.message.edit_text("На сегодня нет запланированных протоколов.")

    logging.info(f"Получены все протоколы на сегодня: {len(all_protocols_today_reservations)} протоколов")

    # 3. Очищаем все резервации на сегодня из БД
    Reservation.delete_all_by_today()
    logging.info("Все резервации на сегодня удалены из БД для перепланирования.")

    await query.message.edit_text("Расписание на сегодня перепланируется с учетом задержки...")

    total_tasks_rescheduled = 0
    tasks_not_scheduled = []
    next_protocol_number = 1  # Начинаем нумерацию протоколов с 1

    # 4. Перепланируем все протоколы заново
    for protocol_number, protocol_reservations in all_protocols_today_reservations:
        protocol_name = protocol_reservations[0].type_protocol # Имя протокола берем из первой резервации списка
        protocol = Protocol.get_by_name(protocol_name)
        if not protocol:
            logging.warning(f"Протокол '{protocol_name}' не найден, пропуск.")
            continue

        standart_tasks_names = protocol.list_standart_tasks
        current_task_start_time = datetime.combine(date.today(), WORKING_DAY_START) # **Начинаем с начала рабочего дня для каждого протокола!**
        schedule_end_datetime = datetime.combine(date.today(), WORKING_DAY_END)

        logging.info(f"Перепланирование протокола '{protocol_name}', номер протокола: {protocol_number}")

        for task_name in standart_tasks_names:
            standart_task = StandartTask.get_by_name(task_name)
            if not standart_task:
                logging.warning(f"Стандартная задача '{task_name}' не найдена, пропуск.")
                tasks_not_scheduled.append(task_name)
                continue

            task_duration = standart_task.time_task
            if task_duration is None:
                logging.warning(f"Для задачи '{task_name}' не указано время выполнения, пропуск.")
                tasks_not_scheduled.append(task_name)
                continue

            device_type = standart_task.type_device

            available_slot_found = False
            schedule_attempt_time = current_task_start_time

            logging.info(f"Поиск слота для задачи '{task_name}', длительность: {task_duration}, type_device: {device_type}")

            while schedule_attempt_time + task_duration <= schedule_end_datetime:
                available_device = Device.find_available_device_by_type_and_time(
                    type_device=device_type,
                    start_time=schedule_attempt_time,
                    end_time=schedule_attempt_time + task_duration
                )
                if available_device:
                    device_id = available_device.id
                    task_end_time = schedule_attempt_time + task_duration

                    # **Важно**: Создаем НОВУЮ резервацию для каждой задачи, даже для задержанной, чтобы пересчитать время
                    reservation_to_reschedule = Reservation(
                        type_protocol=protocol_name,
                        name_task=task_name,
                        id_device=device_id,
                        number_protocol=next_protocol_number # Используем текущий номер протокола
                    )

                    reservation_to_reschedule.id_device = device_id
                    reservation_to_reschedule.start_date = schedule_attempt_time
                    reservation_to_reschedule.end_date = task_end_time
                    reservation_to_reschedule.assistants = protocol_reservations[0].assistants

                    # **Специальная обработка для задержанной задачи**: Проверяем ID, а не имя задачи
                    if (delayed_reservation.number_protocol == protocol_number) and (task_name == delayed_reservation.name_task) and (protocol_name == delayed_reservation.type_protocol):
                        reservation_to_reschedule = delayed_reservation # Используем УЖЕ задержанную резервацию, но нужно пересчитать время начала/конца

                    reservation_id_added = reservation_to_reschedule.add(next_protocol_number) # Добавляем в БД и получаем ID
                    if reservation_id_added:
                        total_tasks_rescheduled += 1
                        logging.info(f"Задача '{task_name}' (ID: {reservation_id_added}) запланирована на {schedule_attempt_time.strftime('%H:%M')}-{task_end_time.strftime('%H:%M')}, устройство ID: {device_id}")
                    else:
                        logging.error(f"Не удалось добавить резервацию для задачи '{task_name}'.")
                        tasks_not_scheduled.append(task_name)

                    current_task_start_time = reservation_to_reschedule.end_date
                    available_slot_found = True
                    break # Переходим к следующей задаче протокола
                else:
                    schedule_attempt_time += timedelta(minutes=5)
                    if schedule_attempt_time.time() > WORKING_DAY_END:
                        break

            if not available_slot_found:
                logging.warning(f"Не удалось запланировать задачу '{task_name}' из протокола '{protocol_name}'. Нет доступного времени/устройств.")
                tasks_not_scheduled.append(task_name)
        next_protocol_number += 1 # Увеличиваем номер протокола для следующего протокола в списке

    message_text = f"✅ Расписание на сегодня полностью перепланировано. Успешно запланировано {total_tasks_rescheduled} задач."
    if tasks_not_scheduled:
        not_scheduled_tasks_str = "\n".join([f"- {task_name}" for task_name in tasks_not_scheduled])
        message_text += f"\n\n⚠️ Не удалось запланировать следующие задачи:\n{not_scheduled_tasks_str}"

    await query.message.edit_text(message_text)

    await state.clear()
    await query.answer()


@router.callback_query(AssistantState.viewing_my_schedule, F.data.startswith("return_protocol_"))
async def callback_return_protocol(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Вернуть протокол в общий список".
    Удаляет ассистента из протокола, делая его доступным для других.
    """
    number_protocol = int(query.data.split("_")[2])
    user_id = query.from_user.id

    protocol_reservations_by_number = Reservation.get_all_by_today_with_protocol_numbers()
    selected_reservations = []
    for protocol_num, reservations in protocol_reservations_by_number:
        if protocol_num == number_protocol:
            selected_reservations = reservations
            break

    if not selected_reservations:
        return await query.message.edit_text(f"Резервации для протокола №{number_protocol} не найдены.", show_alert=True)

    protocol_returned = False
    for reservation in selected_reservations:
        if user_id in reservation.assistants:
            reservation.remove_assistant(user_id) # Удаляем ассистента из списка
            reservation.update()
            protocol_returned = True

    if protocol_returned:
        await query.message.edit_text(f"Протокол №{number_protocol} возвращен в общий список.") # Возвращаем обычную клавиатуру
        await query.message.edit_text("Протокол возвращен!", show_alert=False)
    else:
        await query.message.edit_text(f"Не удалось вернуть протокол №{number_protocol} или вы не были к нему привязаны.", show_alert=True)

    await state.clear() # Сбрасываем состояние просмотра расписания