from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def director_keyboard():
    """
    Создает ReplyKeyboardMarkup для директора с кнопками управления.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Добавить кабинет"),
                KeyboardButton(text="Добавить устройство"),
            ],
            [
                KeyboardButton(text="Добавить задачу"),
                KeyboardButton(text="Добавить протокол") # Кнопка для будущего функционала
            ],
        ],
        resize_keyboard=True, # Автоматически уменьшать размер клавиатуры
        one_time_keyboard=False # Клавиатура не исчезает после первого использования
    )
    return keyboard