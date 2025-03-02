from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def director_keyboard():
    """
    Создает ReplyKeyboardMarkup для директора с кнопками управления.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Добавить ...")  # Открывает подменю добавления
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


def assistant_keyboard():
    """
    Создает ReplyKeyboardMarkup для директора с кнопками управления.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Добавить протоколы на день"),
                KeyboardButton(text="Мое расписание")
            ],
        ],
        resize_keyboard=True,  # Автоматически уменьшает размер клавиатуры
        one_time_keyboard=False  # Клавиатура не исчезает после первого использования
    )
    return keyboard


def add_menu_keyboard():
    """
    Создает InlineKeyboardMarkup для подменю кнопки "Добавить ...".
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кабинет", callback_data="add_cabinet")],
        [InlineKeyboardButton(text="Устройство", callback_data="add_device")],
        [InlineKeyboardButton(text="Задачу", callback_data="add_task")],
        [InlineKeyboardButton(text="Протокол", callback_data="add_protocol")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
    ])
