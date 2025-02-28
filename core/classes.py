from typing import List, Optional, Union
from typing import Tuple
from datetime import datetime, date, timedelta
import os
import random
import time
import logging
from core.utils import dependencies
import psycopg2

logging.basicConfig(level=logging.INFO)


class DatabaseError(Exception):
    """Базовое исключение для ошибок базы данных."""
    pass

class RecordNotFoundError(DatabaseError):
    """Исключение, если запись не найдена."""
    pass

class DuplicateRecordError(DatabaseError):
    """Исключение, если запись с таким ID уже существует."""
    pass


class User:
    table = "Users"
    columns = ['id', 'id_role', 'id_chief', 'fio', 'active']

    ROLE_ADMIN = 0
    ROLE_DIRECTOR = 1
    ROLE_ASSISTANT = 2

    def __init__(
        self,
        id: int,  # ID теперь обязательный параметр
        id_role: int = ROLE_ASSISTANT, # Роль по умолчанию - ассистент
        id_chief: int = 0,
        fio: str = None,
        active: bool = True
    ):
        if not isinstance(id, int):
            raise ValueError(f"Идентификатор '{id}' должен быть целым числом.")
        self.id: int = id # ID теперь точно int
        self.id_role: int = id_role
        self.id_chief: int = id_chief
        self.fio: Optional[str] = fio
        self.active: bool = active

    def add(self):
        """Добавляет пользователя в БД."""
        if User.get_by_id(self.id):  # Используем статический метод для проверки
            raise DuplicateRecordError(f"Пользователь с ID {self.id} уже существует.")
        if dependencies.db_manager.insert(User.table, User.columns, [self.id, self.id_role, self.id_chief, self.fio, self.active]) is None:
            raise DatabaseError("Ошибка при добавлении пользователя в БД.")
        return True # Возвращаем True при успешном добавлении


    def update(self):
        """Обновляет данные пользователя в БД."""
        if not User.get_by_id(self.id): # Проверяем, существует ли запись перед обновлением
            raise RecordNotFoundError(f"Пользователь с ID {self.id} не найден.")
        if not dependencies.db_manager.update(User.table, User.columns,
                                      [self.id_role, self.id_chief, self.fio, self.active], # id нельзя менять, обновляем остальные поля
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении пользователя с ID {self.id} в БД.")
        return True

    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Получает пользователя по ID."""
        data = dependencies.db_manager.find_records(table_name=User.table, search_columns=['id'], search_values=[user_id])
        if data:
            return User(**data) # Используем **data для инициализации
        return None

    @staticmethod
    def get_or_create(user_id: int) -> 'User':
        """Получает пользователя по ID, или создает нового ассистента, если не найден."""
        user = User.get_by_id(user_id)
        if not user:
            user = User(id=user_id) # Создаем нового пользователя с ролью ассистента по умолчанию
            user.add() # Добавляем в БД
        return user

    @staticmethod
    def get_all() -> List['User']:
        """Получает всех пользователей."""
        records = dependencies.db_manager.find_records(table_name=User.table, multiple=True)
        return [User(**record) for record in records] if records else []

    @staticmethod
    def find_by_fio(fio: str) -> List['User']:
        """Находит пользователей по ФИО (частичное совпадение)."""
        query = f"SELECT * FROM \"{User.table}\" WHERE fio LIKE %s"
        records = dependencies.db_manager.find_records(table_name=User.table, custom_query=query, query_params=(f"%{fio}%",), multiple=True)
        return [User(**record) for record in records] if records else []

    @staticmethod
    def set_role(user_id: int, role_id: int):
        """Устанавливает роль пользователя."""
        user = User.get_by_id(user_id)
        if not user:
            raise RecordNotFoundError(f"Пользователь с ID {user_id} не найден.")
        if not dependencies.db_manager.update(User.table, ['id_role'], [role_id], condition_columns=['id'], condition_values=[user_id]):
            raise DatabaseError(f"Ошибка при обновлении роли пользователя с ID {user_id} в БД.")
        return True


class Cabinet:
    table = "Cabinets"
    columns = ['id', 'name', 'active']

    def __init__(
        self,
        id: int, # ID теперь обязательный параметр
        name: str = None,
        active: bool = True
    ):
        if not isinstance(id, int):
            raise ValueError(f"Идентификатор '{id}' должен быть целым числом.")
        self.id: int = id # ID теперь точно int
        self.name: Optional[str] = name
        self.active: bool = active

    def add(self):
        """Добавляет кабинет в БД."""
        if Cabinet.get_by_id(self.id):
            raise DuplicateRecordError(f"Кабинет с ID {self.id} уже существует.")
        if dependencies.db_manager.insert(Cabinet.table, Cabinet.columns, [self.id, self.name, self.active]) is None:
            raise DatabaseError("Ошибка при добавлении кабинета в БД.")
        return True

    def update(self):
        """Обновляет данные кабинета в БД."""
        if not Cabinet.get_by_id(self.id):
            raise RecordNotFoundError(f"Кабинет с ID {self.id} не найден.")
        if not dependencies.db_manager.update(Cabinet.table, Cabinet.columns,
                                      [self.id, self.name, self.active],
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении кабинета с ID {self.id} в БД.")
        return True

    @staticmethod
    def get_by_id(cabinet_id: int) -> Optional['Cabinet']:
        """Получает кабинет по ID."""
        data = dependencies.db_manager.find_records(table_name=Cabinet.table, search_columns=['id'], search_values=[cabinet_id])
        if data:
            return Cabinet(**data)
        return None

    @staticmethod
    def get_all() -> List['Cabinet']:
        """Получает все кабинеты."""
        records = dependencies.db_manager.find_records(table_name=Cabinet.table, multiple=True)
        return [Cabinet(**record) for record in records] if records else []

    @staticmethod
    def find_by_name(name: str) -> List['Cabinet']:
        """Находит кабинеты по имени (частичное совпадение)."""
        query = f"SELECT * FROM \"{Cabinet.table}\" WHERE name LIKE %s"
        records = dependencies.db_manager.find_records(table_name=Cabinet.table, custom_query=query, query_params=(f"%{name}%",), multiple=True)
        return [Cabinet(**record) for record in records] if records else []


class Device:
    table = "Devices"
    columns = ['id_cabinet', 'name', 'active'] # id - SERIAL, поэтому не включаем в columns для insert

    def __init__(
        self,
        id_cabinet: int, # id_cabinet теперь обязательный параметр
        name: str = None,
        active: bool = True,
        id: int = None # id может быть None при создании нового устройства
    ):
        if not isinstance(id_cabinet, int):
            raise ValueError(f"ID кабинета '{id_cabinet}' должен быть целым числом.")
        self.id: Optional[int] = id # id может быть None
        self.id_cabinet: int = id_cabinet
        self.name: Optional[str] = name
        self.active: bool = active

    def add(self) -> Optional[int]: # Возвращаем ID добавленного устройства
        """Добавляет устройство в БД."""
        if dependencies.db_manager.insert(Device.table, Device.columns, [self.id_cabinet, self.name, self.active]) is None:
            raise DatabaseError("Ошибка при добавлении устройства в БД.")
        # Получаем ID добавленной записи (SERIAL PRIMARY KEY) - самый простой способ через поиск по id_cabinet и name
        device = Device.find_by_cabinet_and_name(self.id_cabinet, self.name)
        if device:
            return device.id
        else:
            logging.error("Не удалось получить ID добавленного устройства.")
            return None


    def update(self):
        """Обновляет данные устройства в БД."""
        if not Device.get_by_id(self.id):
            raise RecordNotFoundError(f"Устройство с ID {self.id} не найдено.")
        if not dependencies.db_manager.update(Device.table, Device.columns,
                                      [self.id_cabinet, self.name, self.active], # Обновляем только id_cabinet, name, active
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении устройства с ID {self.id} в БД.")
        return True

    @staticmethod
    def get_by_id(device_id: int) -> Optional['Device']:
        """Получает устройство по ID."""
        data = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['id'], search_values=[device_id])
        if data:
            return Device(**data)
        return None

    @staticmethod
    def get_all() -> List['Device']:
        """Получает все устройства."""
        records = dependencies.db_manager.find_records(table_name=Device.table, multiple=True)
        return [Device(**record) for record in records] if records else []

    @staticmethod
    def find_by_cabinet_id(cabinet_id: int) -> List['Device']:
        """Находит устройства по ID кабинета."""
        records = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['id_cabinet'], search_values=[cabinet_id], multiple=True)
        return [Device(**record) for record in records] if records else []

    @staticmethod
    def find_by_name(name: str) -> List['Device']:
        """Находит устройства по имени (частичное совпадение)."""
        query = f"SELECT * FROM \"{Device.table}\" WHERE name LIKE %s"
        records = dependencies.db_manager.find_records(table_name=Device.table, custom_query=query, query_params=(f"%{name}%",), multiple=True)
        return [Device(**record) for record in records] if records else []

    @staticmethod
    def find_by_cabinet_and_name(cabinet_id: int, name: str) -> Optional['Device']:
        """Находит устройство по ID кабинета и имени."""
        records = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['id_cabinet', 'name'], search_values=[cabinet_id, name], multiple=False)
        if records:
            return Device(**records)
        return None


class StandartTask:
    table = "StandartTasks"
    columns = ['id_cabinet', 'id_device', 'name', 'is_parallel', 'time'] # id - SERIAL, поэтому не включаем в columns для insert

    def __init__(
        self,
        id_cabinet: int, # id_cabinet теперь обязательный параметр
        id_device: int, # id_device теперь обязательный параметр
        name: str = None,
        is_parallel: bool = True,
        time_task: date = None,
        id: int = None # id может быть None при создании новой задачи
    ):
        if not isinstance(id_cabinet, int):
            raise ValueError(f"ID кабинета '{id_cabinet}' должен быть целым числом.")
        if not isinstance(id_device, int):
            raise ValueError(f"ID устройства '{id_device}' должен быть целым числом.")

        self.id: Optional[int] = id # id может быть None
        self.id_cabinet: int = id_cabinet
        self.id_device: int = id_device
        self.name: Optional[str] = name
        self.is_parallel: bool = is_parallel
        self.time: date = time_task

    def add(self) -> Optional[int]: # Возвращаем ID добавленной задачи
        """Добавляет стандартную задачу в БД."""
        if dependencies.db_manager.insert(StandartTask.table, StandartTask.columns, [self.id_cabinet, self.id_device, self.name, self.is_parallel, self.time]) is None:
            raise DatabaseError("Ошибка при добавлении стандартной задачи в БД.")
        # Получаем ID добавленной записи (SERIAL PRIMARY KEY) - самый простой способ через поиск по id_cabinet, id_device и name
        task = StandartTask.find_by_cabinet_device_name(self.id_cabinet, self.id_device, self.name)
        if task:
            return task.id
        else:
            logging.error("Не удалось получить ID добавленной стандартной задачи.")
            return None

    def update(self):
        """Обновляет данные стандартной задачи в БД."""
        if not StandartTask.get_by_id(self.id):
            raise RecordNotFoundError(f"Стандартная задача с ID {self.id} не найдена.")
        if not dependencies.db_manager.update(StandartTask.table, StandartTask.columns,
                                      [self.id_cabinet, self.id_device, self.name, self.is_parallel, self.time], # Обновляем все поля
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении стандартной задачи с ID {self.id} в БД.")
        return True

    @staticmethod
    def get_by_id(task_id: int) -> Optional['StandartTask']:
        """Получает стандартную задачу по ID."""
        data = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['id'], search_values=[task_id])
        if data:
            return StandartTask(**data)
        return None

    @staticmethod
    def get_all() -> List['StandartTask']:
        """Получает все стандартные задачи."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, multiple=True)
        return [StandartTask(**record) for record in records] if records else []

    @staticmethod
    def find_by_cabinet_id(cabinet_id: int) -> List['StandartTask']:
        """Находит стандартные задачи по ID кабинета."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['id_cabinet'], search_values=[cabinet_id], multiple=True)
        return [StandartTask(**record) for record in records] if records else []

    @staticmethod
    def find_by_device_id(device_id: int) -> List['StandartTask']:
        """Находит стандартные задачи по ID устройства."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['id_device'], search_values=[device_id], multiple=True)
        return [StandartTask(**record) for record in records] if records else []

    @staticmethod
    def find_by_cabinet_device_name(cabinet_id: int, device_id: int, name: str) -> Optional['StandartTask']:
        """Находит стандартную задачу по ID кабинета, ID устройства и имени."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['id_cabinet', 'id_device', 'name'], search_values=[cabinet_id, device_id, name], multiple=False)
        if records:
            return StandartTask(**records)
        return None


class Reservation:
    table = "Reservations"
    columns = ['id_task', 'assistants', 'start_date', 'end_date'] # id - SERIAL, поэтому не включаем в columns для insert

    def __init__(
        self,
        id_task: int, # id_task теперь обязательный параметр
        assistants: str = None,
        start_date: datetime = None, # Изменили тип на datetime
        end_date: datetime = None,   # Изменили тип на datetime
        id: int = None # id может быть None при создании новой резервации
    ):
        if not isinstance(id_task, int):
            raise ValueError(f"ID задачи '{id_task}' должен быть целым числом.")
        self.id: Optional[int] = id # id может быть None
        self.id_task: int = id_task
        self.assistants: Optional[str] = assistants
        self.start_date: Optional[datetime] = start_date
        self.end_date: Optional[datetime] = end_date

    def add(self) -> Optional[int]: # Возвращаем ID добавленной резервации
        """Добавляет резервацию в БД."""
        if dependencies.db_manager.insert(Reservation.table, Reservation.columns,
                                          [self.id_task, self.assistants, self.start_date, self.end_date]) is None:
            raise DatabaseError("Ошибка при добавлении резервации в БД.")
        # Получаем ID добавленной записи (SERIAL PRIMARY KEY) - самый простой способ через поиск по id_task, start_date и end_date
        reservation = Reservation.find_by_task_dates(self.id_task, self.start_date, self.end_date)
        if reservation:
            return reservation.id
        else:
            logging.error("Не удалось получить ID добавленной резервации.")
            return None

    def update(self):
        """Обновляет данные резервации в БД."""
        if not Reservation.get_by_id(self.id):
            raise RecordNotFoundError(f"Резервация с ID {self.id} не найдена.")
        if not dependencies.db_manager.update(Reservation.table, Reservation.columns,
                                      [self.id_task, self.assistants, self.start_date, self.end_date], # Обновляем все поля
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении резервации с ID {self.id} в БД.")
        return True

    @staticmethod
    def get_by_id(reservation_id: int) -> Optional['Reservation']:
        """Получает резервацию по ID."""
        data = dependencies.db_manager.find_records(table_name=Reservation.table, search_columns=['id'], search_values=[reservation_id])
        if data:
            return Reservation(**data)
        return None

    @staticmethod
    def get_all() -> List['Reservation']:
        """Получает все резервации."""
        records = dependencies.db_manager.find_records(table_name=Reservation.table, multiple=True)
        return [Reservation(**record) for record in records] if records else []

    @staticmethod
    def find_by_task_id(task_id: int) -> List['Reservation']:
        """Находит резервации по ID задачи."""
        records = dependencies.db_manager.find_records(table_name=Reservation.table, search_columns=['id_task'], search_values=[task_id], multiple=True)
        return [Reservation(**record) for record in records] if records else []

    @staticmethod
    def find_by_task_dates(task_id: int, start_date: datetime, end_date: datetime) -> Optional['Reservation']:
        """Находит резервацию по ID задачи, дате начала и дате окончания."""
        records = dependencies.db_manager.find_records(table_name=Reservation.table,
                                                    search_columns=['id_task', 'start_date', 'end_date'],
                                                    search_values=[task_id, start_date, end_date],
                                                    multiple=False) # Убедитесь, что даты приводятся к строкам в нужном формате, если необходимо
        if records:
            return Reservation(**records)
        return None


if __name__ == '__main__':
    pass