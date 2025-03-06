from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def director_keyboard():
    """
    Создает ReplyKeyboardMarkup для директора с кнопками управления.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Добавить...")  # Открывает подменю добавления
            ],
            [
                KeyboardButton(text="Добавить в расписание"),
                KeyboardButton(text="Посмотреть расписание")
            ],
        ],
        resize_keyboard=True,  # Автоматически уменьшает размер клавиатуры
        one_time_keyboard=False  # Клавиатура не исчезает после первого использования
    )
    return keyboard


def assistant_keyboard(has_protocol=False): # Добавим параметр has_protocol
    """
    Клавиатура для ассистента.
    Кнопка "Добавить протоколы на день" отображается, только если has_protocol=False.
    """
    buttons = [
        [KeyboardButton(text="Мое расписание")],
    ]
    # if not has_protocol: # Кнопка "Добавить протоколы на день" только если нет протокола
    buttons.insert(0, [KeyboardButton(text="Добавить протоколы на день")]) # Вставляем в начало списка

    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)
    return markup


def add_menu_keyboard():
    """
    Создает InlineKeyboardMarkup для подменю кнопки "Добавить...".
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кабинет", callback_data="add_cabinet")],
        [InlineKeyboardButton(text="Устройство", callback_data="add_device")],
        [InlineKeyboardButton(text="Задачу", callback_data="add_task")],
        [InlineKeyboardButton(text="Протокол", callback_data="add_protocol")],
        # [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
    ])
