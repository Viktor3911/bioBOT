from typing import List, Optional, Union
from typing import Tuple
from datetime import datetime, date, timedelta
import os
import random
import json
import time
import logging
from core.utils import dependencies
import psycopg2
import psycopg2.extras

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
        if not dependencies.db_manager.update(User.table, User.columns[1:],
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
    def get_all_directors() -> List['User']:
        """Получает всех пользователей с ролью 'директор'."""
        records = dependencies.db_manager.find_records(
            table_name=User.table,
            search_columns=['id_role'],
            search_values=[User.ROLE_DIRECTOR],
            multiple=True
        )
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
    columns = ['name', 'active']

    def __init__(
        self,
        name: str,
        active: bool = True
    ):
        if not isinstance(name, str):
            raise ValueError(f"Название кабинета '{name}' должно быть строкой.")
        self.name: str = name
        self.active: bool = active

    def add(self):
        """Добавляет кабинет в БД."""
        if Cabinet.get_by_name(self.name): # Используем статический метод для проверки по имени
            raise DuplicateRecordError(f"Кабинет с названием '{self.name}' уже существует.")
        if dependencies.db_manager.insert(Cabinet.table, Cabinet.columns, [self.name, self.active]) is None:
            raise DatabaseError("Ошибка при добавлении кабинета в БД.")
        return True

    def update(self):
        """Обновляет данные кабинета в БД."""
        if not Cabinet.get_by_name(self.name): # Проверяем, существует ли запись перед обновлением по имени
            raise RecordNotFoundError(f"Кабинет с названием '{self.name}' не найден.")
        if not dependencies.db_manager.update(Cabinet.table, ['active'],
                                      [self.active],
                                      condition_columns=['name'], condition_values=[self.name]): # Условие поиска по имени
            raise DatabaseError(f"Ошибка при обновлении кабинета с названием '{self.name}' в БД.")
        return True

    @staticmethod
    def get_by_name(cabinet_name: str) -> Optional['Cabinet']:
        """Получает кабинет по имени."""
        data = dependencies.db_manager.find_records(table_name=Cabinet.table, search_columns=['name'], search_values=[cabinet_name])
        if data:
            return Cabinet(**data)
        return None

    @staticmethod
    def get_all() -> List['Cabinet']:
        """Получает все кабинеты."""
        records = dependencies.db_manager.find_records(table_name=Cabinet.table, multiple=True)
        return [Cabinet(**record) for record in records] if records else []

    @staticmethod
    def find_by_name_substring(name_substring: str) -> List['Cabinet']:
        """Находит кабинеты по части имени (частичное совпадение)."""
        query = f"SELECT * FROM \"{Cabinet.table}\" WHERE name LIKE %s"
        records = dependencies.db_manager.find_records(table_name=Cabinet.table, custom_query=query, query_params=(f"%{name_substring}%",), multiple=True)
        return [Cabinet(**record) for record in records] if records else []


class Device:
    table = "Devices"
    columns = ['type_device', 'name_cabinet', 'name', 'active']

    def __init__(
        self,
        type_device: int,
        name_cabinet: str, # name_cabinet теперь обязательный параметр
        name: str = None,
        active: bool = True,
        id: int = None # id может быть None при создании нового устройства
    ):
        self.type_device: Optional[int] = type_device # может быть None
        self.id: Optional[int] = id # id может быть None
        self.name_cabinet: str = name_cabinet
        self.name: Optional[str] = name
        self.active: bool = active

    def add(self) -> Optional[int]: # Возвращаем ID добавленного устройства
        """Добавляет устройство в БД."""
        if dependencies.db_manager.insert(Device.table, Device.columns, [self.type_device, self.name_cabinet, self.name, self.active]) is None:
            raise DatabaseError("Ошибка при добавлении устройства в БД.")
        
        # Получаем ID последней добавленной записи с таким же именем
        last_device = Device.find_last_by_name(self.name)
        if last_device:
            self.id = last_device.id  # Присваиваем self.id
            return self.id
        else:
            logging.error("Не удалось получить ID добавленного устройства.")
            return None

    def update(self):
        """Обновляет данные устройства в БД."""
        if not Device.get_by_id(self.id):
            raise RecordNotFoundError(f"Устройство с ID {self.id} не найдено.")
        if not dependencies.db_manager.update(Device.table, Device.columns,
                                      [self.type_device, self.name_cabinet, self.name, self.active], # Обновляем только name_cabinet, name, active
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении устройства с ID {self.id} в БД.")
        return True

    @staticmethod
    def count_device_types() -> int:
        """Подсчитывает количество уникальных type_device в таблице Devices."""
        query = "SELECT COUNT(DISTINCT type_device) FROM \"Devices\""
        record = dependencies.db_manager.find_records(table_name=Device.table, custom_query=query)
        if record and record['count'] is not None: # 'count' - имя столбца, возвращаемого COUNT()
            return record['count']
        return 0
    
    @staticmethod
    def get_by_id(id_device: int) -> Optional['Device']:
        """Получает устройство по ID."""
        data = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['id'], search_values=[id_device])
        if data:
            return Device(**data)
        return None
    
    @staticmethod
    def get_by_type_device(type_device: int) -> Optional['Device']:
        """Получает устройство по ID."""
        data = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['type_device'], search_values=[type_device])
        if data:
            return Device(**data)
        return None

    @staticmethod
    def get_all() -> List['Device']:
        """Получает все устройства."""
        records = dependencies.db_manager.find_records(table_name=Device.table, multiple=True)
        return [Device(**record) for record in records] if records else []

    @staticmethod
    def find_by_name_cabinet(name_cabinet: str) -> List['Device']:
        """Находит устройства по имени кабинета."""
        records = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['name_cabinet'], search_values=[name_cabinet], multiple=True)
        return [Device(**record) for record in records] if records else []

    @staticmethod
    def find_by_name(name: str) -> List['Device']:
        """Находит устройства по имени (частичное совпадение)."""
        query = f"SELECT * FROM \"{Device.table}\" WHERE name LIKE %s"
        records = dependencies.db_manager.find_records(table_name=Device.table, custom_query=query, query_params=(f"%{name}%",), multiple=True)
        return [Device(**record) for record in records] if records else []

    @staticmethod
    def find_last_by_name(name: str) -> Optional['Device']:
        """Находит последнее устройство по имени."""
        query = f"SELECT * FROM \"{Device.table}\" WHERE name = %s ORDER BY id DESC LIMIT 1"
        records = dependencies.db_manager.find_records(table_name=Device.table, custom_query=query, query_params=(name,), multiple=False)
        if records:
            return Device(**records)
        return None
    
    @staticmethod
    def find_by_cabinet_and_name(name_cabinet: str, name: str) -> Optional['Device']:
        """Находит устройство по имени кабинета и имени."""
        records = dependencies.db_manager.find_records(table_name=Device.table, search_columns=['name_cabinet', 'name'], search_values=[name_cabinet, name], multiple=False)
        if records:
            return Device(**records)
        return None

    @staticmethod
    def find_available_device_by_type_and_time(type_device: int, start_time: datetime, end_time: datetime) -> Optional['Device']:
        """
        Ищет и возвращает первое доступное устройство заданного type_device на заданный временной интервал.
        Доступным считается устройство, у которого нет пересекающихся резерваций на это время.
        """
        query = f"""
            SELECT d.*
            FROM "{Device.table}" d
            WHERE d.type_device = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM "{Reservation.table}" r
                  JOIN "{StandartTask.table}" st ON r.name_task = st.name
                  WHERE st.type_device = d.type_device
                    AND r.id_device = d.id  -- Проверяем id_device
                    AND (
                        (r.start_date <= %s AND r.end_date > %s)
                        OR (r.start_date < %s AND r.end_date >= %s)
                        OR (r.start_date >= %s AND r.end_date <= %s)
                    )
              )
            LIMIT 1
        """
        query_params = (type_device, start_time, start_time, end_time, end_time, start_time, end_time)
        record = dependencies.db_manager.find_records(
            table_name=Device.table,
            custom_query=query,
            query_params=query_params,
            multiple=False
        )
        if record:
            return Device(**record)
        return None



class StandartTask:
    table = "StandartTasks"
    columns = ['name', 'type_device', 'is_parallel', 'time_task']

    def __init__(
        self,
        name: str,
        type_device: int,
        is_parallel: bool = True,
        time_task: timedelta = None, # Изменили тип на timedelta
    ):
        if not isinstance(name, str):
            raise ValueError(f"Название задачи '{name}' должно быть строкой.")

        if not isinstance(type_device, int):
            raise ValueError(f"ID устройства '{type_device}' должен быть целым числом.")

        self.name: str = name
        self.type_device: int = type_device
        self.is_parallel: bool = is_parallel
        self.time_task: timedelta = time_task # Сохраняем время как timedelta

    def add(self) -> Optional[int]: # Возвращаем ID добавленной задачи (хотя ID нет, можно вернуть None или True)
        """Добавляет стандартную задачу в БД."""
        if StandartTask.get_by_name(self.name): # Проверяем, существует ли задача с таким именем
            raise DuplicateRecordError(f"Стандартная задача с именем '{self.name}' уже существует.")
        if dependencies.db_manager.insert(StandartTask.table, StandartTask.columns, [self.name, self.type_device, self.is_parallel, self.time_task]) is None:
            raise DatabaseError("Ошибка при добавлении стандартной задачи в БД.")
        return True # Или можно вернуть None, так как id не генерируется

    def update(self):
        """Обновляет данные стандартной задачи в БД."""
        if not StandartTask.get_by_name(self.name): # Ищем задачу по имени (PK)
            raise RecordNotFoundError(f"Стандартная задача с именем '{self.name}' не найдена.")
        if not dependencies.db_manager.update(StandartTask.table,
                                      ['type_device', 'is_parallel', 'time_task'], # Обновляем все поля, кроме name (PK)
                                      [self.type_device, self.is_parallel, self.time_task],
                                      condition_columns=['name'], condition_values=[self.name]): # Условие поиска по имени
            raise DatabaseError(f"Ошибка при обновлении стандартной задачи с именем '{self.name}' в БД.")
        return True

    @staticmethod
    def get_by_name(task_name: str) -> Optional['StandartTask']:
        """Получает стандартную задачу по имени (PK)."""
        data = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['name'], search_values=[task_name])
        if data:
            # Преобразуем time из INTERVAL в timedelta при чтении из БД
            if data['time_task']:
                interval_val = data['time_task'] # Получаем объект psycopg2.extras.Interval
                data['time_task'] = timedelta(seconds=interval_val.total_seconds()) # Создаем timedelta из компонентов INTERVAL            
                return StandartTask(**data)
        return None

    @staticmethod
    def get_all() -> List['StandartTask']:
        """Получает все стандартные задачи."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, multiple=True)
        for record in records:
            if record['time_task']:
                interval_val = record['time_task'] # Получаем объект psycopg2.extras.Interval
                record['time_task'] = timedelta(seconds=interval_val.total_seconds()) # Создаем timedelta из компонентов INTERVAL            tasks.append(StandartTask(**record))
        return [StandartTask(**record) for record in records] if records else []

    @staticmethod
    def find_by_type_device(type_device: int) -> List['StandartTask']:
        """Находит стандартные задачи по ID устройства."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['type_device'], search_values=[type_device], multiple=True)
        return [StandartTask(**record) for record in records] if records else []

    @staticmethod
    def find_by_cabinet_and_type_device(name_cabinet: str, type_device: int) -> List['StandartTask']:
        """Находит стандартные задачи по имени кабинета и ID устройства."""
        records = dependencies.db_manager.find_records(table_name=StandartTask.table, search_columns=['type_device'], search_values=[name_cabinet, type_device], multiple=True)
        tasks = []
        for record in records:
            if record['time_task']:
                interval_val = record['time_task'] # Получаем объект psycopg2.extras.Interval
                record['time_task'] = timedelta(seconds=interval_val.total_seconds()) # Создаем timedelta из компонентов INTERVAL
            tasks.append(StandartTask(**record))
        return tasks


class Reservation:
    table = "Reservations"
    # id SERIAL PRIMARY KEY, number_protocol INTEGER, type_protocol TEXT, name_task TEXT, assistants JSONB, start_date TIMESTAMP, end_date TIMESTAMP, active BOOLEAN, FOREIGN KEY (type_protocol) REFERENCES "Protocols"(name), FOREIGN KEY (name_task) REFERENCES "StandartTasks"(name)
    columns = ['number_protocol', 'type_protocol', 'id_device', 'name_task', 'assistants', 'start_date', 'end_date', 'active'] # added 'id_device'

    def __init__(
        self,
        type_protocol: str,
        name_task: str,
        id_device: int, # added id_device
        assistants: List[int] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        active: bool = True,
        number_protocol: int = None,
        id: int = None
    ):
        if not isinstance(name_task, str):
            raise ValueError(f"Название задачи '{name_task}' должно быть строкой.")
        if not isinstance(type_protocol, str):
            raise ValueError(f"Тип протокола '{type_protocol}' должен быть строкой.")
        if not isinstance(id_device, int): # added check for id_device
            raise ValueError(f"ID устройства '{id_device}' должно быть целым числом.")

        self.id: Optional[int] = id
        self.number_protocol: Optional[int] = number_protocol
        self.type_protocol: str = type_protocol
        self.id_device: int = id_device # added id_device
        self.name_task: str = name_task
        self.assistants: Optional[List[int]] = assistants if assistants is not None else []
        self.start_date: Optional[datetime] = start_date
        self.end_date: Optional[datetime] = end_date
        self.active: bool = active

    def add(self, next_protocol_number) -> Optional[int]:
        """Добавляет резервацию в БД."""
        self.number_protocol = next_protocol_number

        assistants_json = json.dumps(self.assistants)

        if dependencies.db_manager.insert(Reservation.table, Reservation.columns,
                                          [self.number_protocol, self.type_protocol, self.id_device, self.name_task, assistants_json, self.start_date, self.end_date, self.active]) is None: # added self.id_device
            raise DatabaseError("Ошибка при добавлении резервации в БД.")

        reservation = Reservation.find_by_protocol_task_device_dates(self.number_protocol, self.type_protocol, self.id_device, self.name_task, self.start_date, self.end_date) # added self.id_device
        if reservation:
            return reservation.id
        else:
            logging.error("Не удалось получить ID добавленной резервации.")
            return None

    def update(self):
        """Обновляет данные резервации в БД."""
        if not Reservation.get_by_id(self.id):
            raise RecordNotFoundError(f"Резервация с ID {self.id} не найдена.")
        assistants_json = json.dumps(self.assistants)
        if not dependencies.db_manager.update(Reservation.table,
                                      ['number_protocol', 'type_protocol', 'id_device', 'name_task', 'assistants', 'start_date', 'end_date', 'active'], # added 'id_device'
                                      [self.number_protocol, self.type_protocol, self.id_device, self.name_task, assistants_json, self.start_date, self.end_date, self.active], # added self.id_device
                                      condition_columns=['id'], condition_values=[self.id]):
            raise DatabaseError(f"Ошибка при обновлении резервации с ID {self.id} в БД.")
        return True

    @staticmethod
    def get_by_id(reservation_id: int) -> Optional['Reservation']:
        """Получает резервацию по ID."""
        data = dependencies.db_manager.find_records(table_name=Reservation.table, search_columns=['id'], search_values=[reservation_id])
        if data:
            if isinstance(data['assistants'], str):  # Проверяем, является ли значение строкой
                if data['assistants']:
                    data['assistants'] = json.loads(data['assistants'])
            return Reservation(**data)
        return None

    @staticmethod
    def get_all() -> List['Reservation']:
        """Получает все резервации."""
        records = dependencies.db_manager.find_records(table_name=Reservation.table, multiple=True)
        reservations = []
        for record in records:
            if isinstance(records['assistants'], str):  # Проверяем, является ли значение строкой
                if record['assistants']:
                    record['assistants'] = json.loads(record['assistants'])
            reservations.append(Reservation(**record))
        return reservations

    @staticmethod
    def find_by_task_name(name_task: str) -> List['Reservation']:
        """Находит резервации по имени задачи."""
        records = dependencies.db_manager.find_records(table_name=Reservation.table, search_columns=['name_task'], search_values=[name_task], multiple=True)
        reservations = []
        for record in records:
            if isinstance(record['assistants'], str):  # Проверяем, является ли значение строкой
                if record['assistants']:
                    record['assistants'] = json.loads(record['assistants'])
            reservations.append(Reservation(**record))
        return reservations

    @staticmethod
    def find_by_protocol_name(type_protocol: str) -> List['Reservation']:
        """Находит резервации по имени протокола."""
        records = dependencies.db_manager.find_records(table_name=Reservation.table, search_columns=['type_protocol'], search_values=[type_protocol], multiple=True)
        reservations = []
        for record in records:
            if isinstance(record['assistants'], str):  # Проверяем, является ли значение строкой
                if record['assistants']:
                    record['assistants'] = json.loads(record['assistants'])
            reservations.append(Reservation(**record))
        return reservations

    @staticmethod
    def find_by_protocol_task_device_dates(number_protocol: int, type_protocol: str, id_device: int, name_task: str, start_date: datetime, end_date: datetime) -> Optional['Reservation']: # added id_device
        """Находит резервацию по номеру протокола, типу протокола, ID устройства, имени задачи, дате начала и дате окончания.""" # added 'ID устройства'
        records = dependencies.db_manager.find_records(table_name=Reservation.table,
                                                    search_columns=['number_protocol', 'type_protocol', 'id_device', 'name_task', 'start_date', 'end_date'], # added 'id_device'
                                                    search_values=[number_protocol, type_protocol, id_device, name_task, start_date, end_date], # added id_device
                                                    multiple=False)
        if records:
            if isinstance(records['assistants'], str):  # Проверяем, является ли значение строкой
                if records['assistants']:
                    records['assistants'] = json.loads(records['assistants'])
            return Reservation(**records)
        return None

    @staticmethod
    def count_protocol_numbers() -> int:
        """Подсчитывает количество уникальных number_protocol в таблице Reservations."""
        query = "SELECT COALESCE(MAX(number_protocol), 0) + 1 FROM \"Reservations\""
        record = dependencies.db_manager.find_records(table_name=Reservation.table, custom_query=query)
        if record and list(record.values()): # Проверяем, что record не None и не пустой
            return list(record.values())[0] # Возвращаем первое значение из словаря record (независимо от имени ключа)
        return 1

    @staticmethod
    def find_by_assistant_and_date(user_id: int, date_reservation: date = None) -> List['Reservation']:
        """
        Находит резервации, в которых ассистент (user_id) есть в списке assistants,
        и фильтрует по дате начала резервации (по умолчанию - текущая дата).
        """
        if date_reservation is None:
            date_reservation = date.today()

        query = f"""
            SELECT * FROM "{Reservation.table}"
            WHERE assistants::jsonb @> %s
              AND DATE(start_date) = %s
        """
        query_params = (json.dumps([user_id]), date_reservation)

        records = dependencies.db_manager.find_records(
            table_name=Reservation.table,
            custom_query=query,
            query_params=query_params,
            multiple=True
        )
        reservations = []
        for record in records:
            reservations.append(Reservation(**record))
        return reservations

    @staticmethod
    def find_overlapping_reservations(id_device: int, start_time: datetime, end_time: datetime) -> List['Reservation']: # updated to filter by id_device
        """
        Находит резервации для заданного id_device, которые пересекаются с заданным временным интервалом. # updated to filter by id_device
        """
        query = f"""
            SELECT r.*
            FROM "{Reservation.table}" r
            WHERE r.id_device = %s  -- Фильтрация по id_device
              AND (
                  (r.start_date <= %s AND r.end_date > %s)
                  OR (r.start_date < %s AND r.end_date >= %s)
                  OR (r.start_date >= %s AND r.end_date <= %s)
              )
        """
        query_params = (id_device, start_time, start_time, end_time, end_time, start_time, end_time) # updated query_params
        records = dependencies.db_manager.find_records(
            table_name=Reservation.table,
            custom_query=query,
            query_params=query_params,
            multiple=True
        )
        reservations = []
        for record in records:
            if isinstance(record['assistants'], str):  # Проверяем, является ли значение строкой
                if record['assistants']:
                    record['assistants'] = json.loads(records['assistants'])
            reservations.append(Reservation(**record))
        return reservations

    @staticmethod
    def get_all_by_today() -> List['Reservation']:
        """
        Получает все резервации на текущий день.
        """
        today_date = date.today()
        query = f"""
            SELECT * FROM "{Reservation.table}"
            WHERE DATE(start_date) = %s
        """
        query_params = (today_date,)
        records = dependencies.db_manager.find_records(
            table_name=Reservation.table,
            custom_query=query,
            query_params=query_params,
            multiple=True
        )
        reservations = []
        for record in records:
            if isinstance(record['assistants'], str):  # Проверяем, является ли значение строкой
                if record['assistants']:
                    record['assistants'] = json.loads(record['assistants'])
            reservations.append(Reservation(**record))
        return reservations
      
    @staticmethod
    def get_all_by_today_with_protocol_numbers() -> List[Tuple[int, List['Reservation']]]:
        """
        Получает все резервации на текущий день, сгруппированные по number_protocol.

        Returns:
            List[Tuple[int, List['Reservation']]]: Список кортежей, где каждый кортеж содержит:
            - number_protocol (int): Номер протокола.
            - List['Reservation']: Список резерваций для данного number_protocol.
        """
        today_date = date.today()
        query = f"""
            SELECT * FROM "{Reservation.table}"
            WHERE DATE(start_date) = %s
            ORDER BY number_protocol, start_date
        """
        query_params = (today_date,)
        records = dependencies.db_manager.find_records(
            table_name=Reservation.table,
            custom_query=query,
            query_params=query_params,
            multiple=True
        )
        reservations: list[Reservation] = []
        for record in records:
            if isinstance(record['assistants'], str):  # Проверяем, является ли значение строкой
                if record['assistants']:
                    record['assistants'] = json.loads(record['assistants'])
            reservations.append(Reservation(**record))

        protocol_reservations_map = {} # Словарь для группировки по number_protocol
        for res in reservations:
            if res.number_protocol not in protocol_reservations_map:
                protocol_reservations_map[res.number_protocol] = []
            protocol_reservations_map[res.number_protocol].append(res)

        return list(protocol_reservations_map.items()) # Возвращаем список кортежей (number_protocol, [reservations])


class Protocol:
    table = "Protocols"
    columns = ['name', 'list_standart_tasks'] # id - SERIAL, list_standart_tasks - JSONB

    def __init__(
        self,
        name: str,
        list_standart_tasks: list = None, # Список названий стандартных задач
    ):
        if not isinstance(name, str):
            raise ValueError(f"Название протокола '{name}' должно быть строкой.")
        self.name: str = name
        self.list_standart_tasks: Optional[list] = list_standart_tasks if list_standart_tasks is not None else [] # Инициализация пустым списком по умолчанию

    def add(self) -> Optional[int]: # Возвращаем ID добавленного протокола
        """Добавляет протокол в БД."""
        if Protocol.get_by_name(self.name): # Проверяем, существует ли протокол с таким именем
            raise DuplicateRecordError(f"Протокол с именем '{self.name}' уже существует.")
        if dependencies.db_manager.insert(Protocol.table, Protocol.columns, [self.name, json.dumps(self.list_standart_tasks)]) is None:
            raise DatabaseError("Ошибка при добавлении протокола в БД.")

        return self.name

    def update(self):
        """Обновляет данные протокола в БД."""
        if not Protocol.get_by_name(self.name):
            raise RecordNotFoundError(f"Протокол с именем '{self.name}' не найден.")
        if not dependencies.db_manager.update(Protocol.table, columns=['list_standart_tasks'],
                                      values=[json.dumps(self.list_standart_tasks, ensure_ascii=False)],
                                      condition_columns=['name'], condition_values=[self.name]):
            raise DatabaseError(f"Ошибка при обновлении протокола с именем '{self.name}' в БД.")
        return True

    @staticmethod
    def get_by_id(protocol_id: int) -> Optional['Protocol']:
        """Получает протокол по ID."""
        data = dependencies.db_manager.find_records(table_name=Protocol.table, search_columns=['id'], search_values=[protocol_id])
        if data:
            # Преобразуем list_standart_tasks из JSONB строки в список Python при чтении из БД
            if isinstance(data['list_standart_tasks'], str):  # Проверяем, является ли значение строкой
                if data['list_standart_tasks']:
                    data['list_standart_tasks'] = json.loads(data['list_standart_tasks']) # Преобразование JSONB в список Python для каждого элемента списка
            return Protocol(**data)
        return None

    @staticmethod
    def get_by_name(protocol_name: str) -> Optional['Protocol']:
        """Получает протокол по имени."""
        data = dependencies.db_manager.find_records(table_name=Protocol.table, search_columns=['name'], search_values=[protocol_name])
        if data:
            # Преобразуем list_standart_tasks из JSONB строки в список Python при чтении из БД
            if isinstance(data['list_standart_tasks'], str):  # Проверяем, является ли значение строкой
                if data['list_standart_tasks']:
                    data['list_standart_tasks'] = json.loads(data['list_standart_tasks']) # Преобразование JSONB в список Python для каждого элемента списка
            return Protocol(**data)
        return None

    @staticmethod
    def get_all() -> List['Protocol']:
        """Получает все протоколы."""
        records = dependencies.db_manager.find_records(table_name=Protocol.table, multiple=True)
        protocols = []
        for record in records:
            if isinstance(record['list_standart_tasks'], str):  # Проверяем, является ли значение строкой
                if record['list_standart_tasks']:
                    record['list_standart_tasks'] = json.loads(record['list_standart_tasks']) # Преобразование JSONB в список Python для каждого элемента списка
            protocols.append(Protocol(**record))
        return protocols

    @staticmethod
    def find_last_by_name(name: str) -> Optional['Protocol']:
        """Находит последний протокол по имени."""
        query = f"SELECT * FROM \"{Protocol.table}\" WHERE name = %s ORDER BY id DESC LIMIT 1"
        records = dependencies.db_manager.find_records(table_name=Protocol.table, custom_query=query, query_params=(name,), multiple=False)
        if records:
            # Преобразуем list_standart_tasks из JSONB строки в список Python при чтении из БД
            if isinstance(records['list_standart_tasks'], str):  # Проверяем, является ли значение строкой
                if records['list_standart_tasks']:
                    records['list_standart_tasks'] = json.loads(records['list_standart_tasks']) # Преобразование JSONB в список Python для каждого элемента списка
            return Protocol(**records)
        return None


if __name__ == '__main__':
    pass